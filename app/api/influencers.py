"""Influencer API router."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import BlacklistViolationError, ValidationError
from app.models.domain import UserRole
from app.services.blacklist_service import BlacklistService
from app.services.rbac import get_current_user, require_role

router = APIRouter(prefix="/influencers", tags=["influencers"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SelectionCriteriaRequest(BaseModel):
    min_followers: Optional[int] = None
    max_followers: Optional[int] = None
    min_engagement_rate: Optional[float] = None
    content_categories: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    campaign_id: Optional[str] = None


class InfluencerCard(BaseModel):
    id: str
    name: str
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    relevance_score: Optional[float] = None


class SelectionResponse(BaseModel):
    influencers: List[InfluencerCard]
    total: int


class BlacklistEntry(BaseModel):
    id: str
    influencer_id: str
    influencer_name: str
    reason: str
    added_by: str
    added_at: str


class AddBlacklistRequest(BaseModel):
    influencer_id: str
    reason: str


class RemoveBlacklistRequest(BaseModel):
    removal_reason: str = "Removed by administrator"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/select", response_model=SelectionResponse)
async def select_influencers(
    body: SelectionCriteriaRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SelectionResponse:
    """Seleksi influencer berdasarkan criteria."""
    import json
    import uuid

    from sqlalchemy import text

    from app.agents.selector_agent import SelectorAgent
    from app.models.domain import Influencer, InfluencerStatus, SelectionCriteria

    criteria = SelectionCriteria(
        id=str(uuid.uuid4()),
        name="api_selection",
        min_followers=body.min_followers,
        max_followers=body.max_followers,
        min_engagement_rate=body.min_engagement_rate,
        content_categories=body.content_categories,
        locations=body.locations,
    )

    # Fetch all active influencers from DB
    result = await db.execute(
        text("SELECT * FROM influencers WHERE blacklisted = FALSE ORDER BY follower_count DESC")
    )
    rows = result.mappings().all()

    influencer_list: List[Influencer] = []
    for row in rows:
        cats = row["content_categories"]
        if isinstance(cats, str):
            cats = json.loads(cats)
        influencer_list.append(
            Influencer(
                id=str(row["id"]),
                tiktok_user_id=str(row.get("tiktok_user_id", "")),
                name=str(row["name"]),
                phone_number=str(row.get("phone_number", "")),
                follower_count=int(row["follower_count"]),
                engagement_rate=float(row["engagement_rate"]),
                content_categories=list(cats or []),
                location=str(row.get("location", "")),
                status=InfluencerStatus(row.get("status", "ACTIVE")),
                blacklisted=bool(row.get("blacklisted", False)),
            )
        )

    from app.services.blacklist_service import BlacklistService

    blacklist_svc = BlacklistService(db)
    agent = SelectorAgent(blacklist_service=blacklist_svc)
    campaign_id = body.campaign_id or str(uuid.uuid4())
    selection_result = await agent.select_influencers(criteria, campaign_id, influencer_list)

    cards = [
        InfluencerCard(
            id=inf.id,
            name=inf.name,
            follower_count=inf.follower_count,
            engagement_rate=inf.engagement_rate,
            content_categories=inf.content_categories,
            location=inf.location,
            relevance_score=inf.relevance_score,
        )
        for inf in selection_result.influencers
    ]
    return SelectionResponse(influencers=cards, total=len(cards))


@router.get("/blacklist", response_model=List[BlacklistEntry])
async def get_blacklist(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[BlacklistEntry]:
    """Daftar hitam influencer."""
    svc = BlacklistService(db)
    entries = await svc.get_blacklist()
    return [
        BlacklistEntry(
            id=str(e["id"]),
            influencer_id=str(e["influencer_id"]),
            influencer_name=str(e.get("influencer_name", "")),
            reason=str(e["reason"]),
            added_by=str(e["added_by"]),
            added_at=str(e["added_at"]),
        )
        for e in entries
    ]


@router.post("/blacklist", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_to_blacklist(
    body: AddBlacklistRequest,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Tambah influencer ke daftar hitam."""
    svc = BlacklistService(db)
    try:
        entry_id = await svc.add_to_blacklist(
            influencer_id=body.influencer_id,
            reason=body.reason,
            added_by_user_id=current_user["sub"],
        )
    except BlacklistViolationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    return {"id": entry_id, "influencer_id": body.influencer_id, "status": "blacklisted"}


@router.delete("/blacklist/{influencer_id}", response_model=Dict[str, Any])
async def remove_from_blacklist(
    influencer_id: str,
    current_user: Dict[str, Any] = Depends(require_role(UserRole.ADMINISTRATOR)),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Hapus influencer dari daftar hitam (Administrator only)."""
    svc = BlacklistService(db)
    await svc.remove_from_blacklist(
        influencer_id=influencer_id,
        removed_by_user_id=current_user["sub"],
        removal_reason="Removed via API",
    )
    return {"influencer_id": influencer_id, "status": "removed_from_blacklist"}
