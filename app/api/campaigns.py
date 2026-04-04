"""Campaign API router."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import ValidationError
from app.models.domain import CampaignSettings, CampaignStatus, UserRole
from app.services.campaign_service import CampaignService
from app.services.rbac import get_current_user, require_role

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CampaignSettingsSchema(BaseModel):
    max_invitations_per_minute: int = 100
    monitoring_interval_minutes: int = 30
    compliance_check_enabled: bool = True
    alert_thresholds: Dict[str, float] = {}


class CreateCampaignRequest(BaseModel):
    name: str
    description: str = ""
    selection_criteria_id: str
    template_id: str
    start_date: datetime
    end_date: datetime
    settings: Optional[CampaignSettingsSchema] = None


class CampaignResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    selection_criteria_id: str
    template_id: str
    start_date: datetime
    end_date: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime
    settings: CampaignSettingsSchema


class CampaignStatusResponse(BaseModel):
    campaign_id: str
    status: str
    cached: bool = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _campaign_to_response(campaign: Any) -> CampaignResponse:
    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status.value,
        selection_criteria_id=campaign.selection_criteria_id,
        template_id=campaign.template_id,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
        settings=CampaignSettingsSchema(
            max_invitations_per_minute=campaign.settings.max_invitations_per_minute,
            monitoring_interval_minutes=campaign.settings.monitoring_interval_minutes,
            compliance_check_enabled=campaign.settings.compliance_check_enabled,
            alert_thresholds=campaign.settings.alert_thresholds,
        ),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=List[CampaignResponse])
async def list_campaigns(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[CampaignResponse]:
    """Daftar semua kampanye."""
    from sqlalchemy import text
    import json
    result = await db.execute(
        text("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 100")
    )
    rows = result.mappings().all()
    campaigns = []
    for row in rows:
        alert_thresholds = row.get("alert_thresholds") or {}
        if isinstance(alert_thresholds, str):
            try: alert_thresholds = json.loads(alert_thresholds)
            except: alert_thresholds = {}
        campaigns.append(CampaignResponse(
            id=str(row["id"]),
            name=row["name"],
            description=row.get("description") or "",
            status=row["status"],
            selection_criteria_id=str(row.get("selection_criteria_id") or ""),
            template_id=str(row.get("template_id") or ""),
            start_date=row["start_date"],
            end_date=row["end_date"],
            created_by=str(row["created_by"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            settings=CampaignSettingsSchema(
                max_invitations_per_minute=row.get("max_invitations_per_minute", 100),
                monitoring_interval_minutes=row.get("monitoring_interval_minutes", 30),
                compliance_check_enabled=row.get("compliance_check_enabled", True),
                alert_thresholds=alert_thresholds,
            ),
        ))
    return campaigns


@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_campaign(
    body: CreateCampaignRequest,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> CampaignResponse:
    """Buat kampanye baru."""
    svc = CampaignService()
    settings = None
    if body.settings:
        settings = CampaignSettings(
            max_invitations_per_minute=body.settings.max_invitations_per_minute,
            monitoring_interval_minutes=body.settings.monitoring_interval_minutes,
            compliance_check_enabled=body.settings.compliance_check_enabled,
            alert_thresholds=body.settings.alert_thresholds,
        )
    try:
        campaign = await svc.create(
            name=body.name,
            description=body.description,
            selection_criteria_id=body.selection_criteria_id,
            template_id=body.template_id,
            start_date=body.start_date,
            end_date=body.end_date,
            created_by=current_user["sub"],
            db=db,
            settings=settings,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return _campaign_to_response(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CampaignResponse:
    """Detail kampanye."""
    svc = CampaignService()
    try:
        campaign = await svc.get(campaign_id, db)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
    return _campaign_to_response(campaign)


@router.post("/{campaign_id}/start", response_model=Dict[str, Any])
async def start_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Mulai kampanye."""
    svc = CampaignService()
    try:
        result = await svc.start_campaign(campaign_id, db)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return {"campaign_id": campaign_id, "status": "started", "result": str(result)}


@router.post("/{campaign_id}/stop", response_model=Dict[str, Any])
async def stop_campaign(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Hentikan kampanye."""
    svc = CampaignService()
    try:
        await svc.stop_campaign(campaign_id, db)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return {"campaign_id": campaign_id, "status": "stopped"}


@router.get("/{campaign_id}/status", response_model=CampaignStatusResponse)
async def get_campaign_status(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CampaignStatusResponse:
    """Status kampanye — cached di Redis jika tersedia."""
    import json

    from app.config import get_settings

    settings = get_settings()
    cached = False
    campaign_status: Optional[str] = None

    # Try Redis cache first
    try:
        import redis.asyncio as aioredis  # type: ignore

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        cache_key = f"campaign:status:{campaign_id}"
        cached_value = await redis_client.get(cache_key)
        await redis_client.aclose()
        if cached_value:
            data = json.loads(cached_value)
            return CampaignStatusResponse(
                campaign_id=campaign_id,
                status=data["status"],
                cached=True,
            )
    except Exception:
        pass  # Redis unavailable — fall through to DB

    svc = CampaignService()
    try:
        campaign = await svc.get(campaign_id, db)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)

    # Store in Redis cache (best-effort)
    try:
        import redis.asyncio as aioredis  # type: ignore

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        cache_key = f"campaign:status:{campaign_id}"
        await redis_client.setex(cache_key, 60, json.dumps({"status": campaign.status.value}))
        await redis_client.aclose()
    except Exception:
        pass

    return CampaignStatusResponse(
        campaign_id=campaign_id,
        status=campaign.status.value,
        cached=False,
    )


@router.get("/{campaign_id}/report", response_model=Dict[str, Any])
async def get_campaign_report(
    campaign_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Laporan kampanye."""
    from app.services.report_service import ReportService

    svc = ReportService()
    report = await svc.generate_campaign_report(campaign_id, db)
    return {
        "campaign_id": report.campaign_id,
        "total_influencers": report.total_influencers,
        "acceptance_rate": report.acceptance_rate,
        "total_views": report.total_views,
        "total_gmv": report.total_gmv,
        "cost_per_conversion": report.cost_per_conversion,
        "generated_at": report.generated_at.isoformat(),
    }
