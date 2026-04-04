"""Domain models — dataclasses and Enums for the TikTok Influencer Marketing Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CampaignStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class InfluencerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    BLACKLISTED = "BLACKLISTED"


class InvitationStatus(str, Enum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


class FeedbackCategory(str, Enum):
    ACCEPTED = "Menerima"
    REJECTED = "Menolak"
    NEEDS_MORE_INFO = "Membutuhkan_Informasi_Lebih_Lanjut"
    NO_RESPONSE = "Tidak_Merespons"


class UserRole(str, Enum):
    ADMINISTRATOR = "Administrator"
    CAMPAIGN_MANAGER = "Manajer_Kampanye"
    REVIEWER = "Peninjau"


class WhatsAppCollectionMethod(str, Enum):
    OFFICIAL_ICON = "official_icon"
    BIO_PARSING = "bio_parsing"
    CHAT_REPLY = "chat_reply"


class WhatsAppCollectionStatus(str, Enum):
    COLLECTED = "collected"
    UNAVAILABLE = "unavailable"
    PENDING_CHAT = "pending_chat"


class ModelType(str, Enum):
    SELECTION = "SELECTION"
    CLASSIFIER = "CLASSIFIER"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CampaignSettings:
    max_invitations_per_minute: int = 100
    monitoring_interval_minutes: int = 30
    compliance_check_enabled: bool = True
    alert_thresholds: Dict[str, float] = field(default_factory=dict)


@dataclass
class Campaign:
    id: str
    name: str
    description: str
    status: CampaignStatus
    selection_criteria_id: str
    template_id: str
    start_date: datetime
    end_date: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime
    settings: CampaignSettings = field(default_factory=CampaignSettings)


@dataclass
class Influencer:
    id: str
    tiktok_user_id: str
    name: str
    phone_number: str
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    relevance_score: Optional[float] = None
    status: InfluencerStatus = InfluencerStatus.ACTIVE
    blacklisted: bool = False
    blacklist_reason: Optional[str] = None


@dataclass
class CriteriaWeights:
    follower_count: float = 0.3
    engagement_rate: float = 0.4
    category_match: float = 0.2
    location_match: float = 0.1


@dataclass
class SelectionCriteria:
    id: str
    name: str
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    min_engagement_rate: Optional[float] = None
    content_categories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    criteria_weights: CriteriaWeights = field(default_factory=CriteriaWeights)
    is_template: bool = False


@dataclass
class Invitation:
    id: str
    campaign_id: str
    influencer_id: str
    template_id: str
    message_content: str
    status: InvitationStatus
    sent_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None
    error_message: Optional[str] = None
    whatsapp_message_id: Optional[str] = None


@dataclass
class ContentMetrics:
    id: str
    campaign_id: str
    influencer_id: str
    tiktok_video_id: str
    views: int
    likes: int
    comments: int
    shares: int
    has_valid_affiliate_link: bool
    gmv_generated: float
    conversion_rate: float
    recorded_at: datetime
    is_compliant: bool


@dataclass
class InfluencerFeedback:
    id: str
    campaign_id: str
    influencer_id: str
    invitation_id: str
    raw_message: str
    classification: Optional[FeedbackCategory] = None
    confidence_score: Optional[float] = None
    requires_manual_review: bool = False
    classified_at: Optional[datetime] = None
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MessageTemplate:
    id: str
    name: str
    content: str
    variables: List[str]
    default_values: Dict[str, str]
    version: int
    is_active: bool
    campaign_ids: List[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    role: UserRole
    is_active: bool
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None


@dataclass
class WhatsAppCollectionRecord:
    id: str
    affiliate_id: str
    influencer_id: str
    status: WhatsAppCollectionStatus
    phone_number: Optional[str] = None
    method: Optional[WhatsAppCollectionMethod] = None
    chat_message_id: Optional[str] = None
    raw_extracted: Optional[str] = None
    collected_at: Optional[datetime] = None
    chat_sent_at: Optional[datetime] = None
    timeout_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WhatsAppCollectionResult:
    affiliate_id: str
    status: WhatsAppCollectionStatus
    record: WhatsAppCollectionRecord
    phone_number: Optional[str] = None
    method: Optional[WhatsAppCollectionMethod] = None


@dataclass
class AffiliateCard:
    id: str
    name: str
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    has_whatsapp: bool
    photo_url: Optional[str] = None


@dataclass
class AffiliateDetail:
    id: str
    name: str
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    contact_channel: str
    photo_url: Optional[str] = None
    bio: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_collection_status: Optional[WhatsAppCollectionStatus] = None
    tiktok_profile_url: Optional[str] = None


@dataclass
class ModelVersion:
    id: str
    model_type: ModelType
    version: int
    accuracy_after: float
    trained_at: datetime
    training_data_size: int
    accuracy_before: Optional[float] = None


@dataclass
class InfluencerRecommendation:
    influencer_id: str
    predicted_conversion_rate: float
    predicted_gmv: float
    confidence_score: float
    based_on_campaigns: List[str]


@dataclass
class CampaignOutcome:
    id: str
    campaign_id: str
    influencer_id: str
    accepted: bool
    gmv_generated: float
    conversion_rate: float
    content_count: int
    recorded_at: datetime


@dataclass
class Product:
    id: str
    tiktok_product_id: str
    name: str
    price: float
    category: Optional[str] = None
    image_url: Optional[str] = None
    shop_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContentVideo:
    id: str
    tiktok_video_id: str
    creator_id: str
    product_id: Optional[str] = None
    title: Optional[str] = None
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    gmv_generated: float = 0.0
    buyers: int = 0
    posted_at: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)
