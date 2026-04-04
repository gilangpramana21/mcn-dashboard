"""Template API router."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import TemplateInUseError, ValidationError
from app.models.domain import UserRole
from app.services.rbac import get_current_user, require_role
from app.services.template_service import TemplateService

router = APIRouter(prefix="/templates", tags=["templates"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CreateTemplateRequest(BaseModel):
    name: str
    content: str
    default_values: Dict[str, str] = {}
    message_type: str = "campaign_invitation"
    channel: str = "whatsapp"
    wa_category: Optional[str] = None  # FnB, Fashion, Skincare, dll. None = semua kategori


class UpdateTemplateRequest(BaseModel):
    content: Optional[str] = None
    default_values: Optional[Dict[str, str]] = None
    message_type: Optional[str] = None
    channel: Optional[str] = None
    wa_category: Optional[str] = None


class TemplateResponse(BaseModel):
    id: str
    name: str
    content: str
    variables: List[str]
    default_values: Dict[str, str]
    version: int
    is_active: bool
    campaign_ids: List[str]
    message_type: str
    channel: str
    wa_category: Optional[str] = None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _template_to_response(t: Any) -> TemplateResponse:
    return TemplateResponse(
        id=t.id,
        name=t.name,
        content=t.content,
        variables=t.variables,
        default_values=t.default_values,
        version=t.version,
        is_active=t.is_active,
        campaign_ids=t.campaign_ids,
        message_type=getattr(t, 'message_type', 'campaign_invitation'),
        channel=getattr(t, 'channel', 'whatsapp'),
        wa_category=getattr(t, 'wa_category', None),
        created_at=t.created_at.isoformat(),
        updated_at=t.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: CreateTemplateRequest,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """Buat template pesan baru."""
    svc = TemplateService(db)
    try:
        template = await svc.create(
            name=body.name,
            content=body.content,
            default_values=body.default_values,
            message_type=body.message_type,
            channel=body.channel,
            wa_category=body.wa_category,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return _template_to_response(template)


@router.get("", response_model=List[TemplateResponse])
async def list_templates(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[TemplateResponse]:
    """Daftar semua template."""
    from sqlalchemy import text

    result = await db.execute(text("SELECT * FROM message_templates ORDER BY created_at DESC"))
    rows = result.mappings().all()

    import json

    templates = []
    for row in rows:
        variables = row["variables"]
        if isinstance(variables, str):
            variables = json.loads(variables)
        default_values = row["default_values"]
        if isinstance(default_values, str):
            default_values = json.loads(default_values)
        campaign_ids = row["campaign_ids"] or []
        if isinstance(campaign_ids, str):
            campaign_ids = json.loads(campaign_ids)

        templates.append(
            TemplateResponse(
                id=str(row["id"]),
                name=row["name"],
                content=row["content"],
                variables=list(variables),
                default_values=dict(default_values),
                version=int(row["version"]),
                is_active=bool(row["is_active"]),
                campaign_ids=[str(c) for c in campaign_ids],
                message_type=row.get("message_type") or "campaign_invitation",
                channel=row.get("channel") or "whatsapp",
                wa_category=row.get("wa_category"),
                created_at=row["created_at"].isoformat(),
                updated_at=row["updated_at"].isoformat(),
            )
        )
    return templates


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: str,
    body: UpdateTemplateRequest,
    current_user: Dict[str, Any] = Depends(
        require_role(UserRole.CAMPAIGN_MANAGER, UserRole.ADMINISTRATOR)
    ),
    db: AsyncSession = Depends(get_db_session),
) -> TemplateResponse:
    """Update template pesan."""
    svc = TemplateService(db)
    try:
        template = await svc.update(
            template_id=template_id,
            content=body.content,
            default_values=body.default_values,
            wa_category=body.wa_category,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.message)
    return _template_to_response(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: str,
    current_user: Dict[str, Any] = Depends(require_role(UserRole.ADMINISTRATOR)),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Hapus template (Administrator only)."""
    svc = TemplateService(db)
    try:
        await svc.delete(template_id)
    except TemplateInUseError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message)
