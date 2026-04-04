"""Campaign Service — CRUD dan orkestrasi kampanye."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ValidationError
from app.models.domain import Campaign, CampaignSettings, CampaignStatus


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _row_to_campaign(row: Any) -> Campaign:
    settings_raw = row.get("settings") or {}
    if isinstance(settings_raw, str):
        settings_raw = json.loads(settings_raw)

    settings = CampaignSettings(
        max_invitations_per_minute=settings_raw.get("max_invitations_per_minute", 100),
        monitoring_interval_minutes=settings_raw.get("monitoring_interval_minutes", 30),
        compliance_check_enabled=settings_raw.get("compliance_check_enabled", True),
        alert_thresholds=settings_raw.get("alert_thresholds", {}),
    )

    return Campaign(
        id=str(row["id"]),
        name=row["name"],
        description=row.get("description", ""),
        status=CampaignStatus(row["status"]),
        selection_criteria_id=str(row["selection_criteria_id"]),
        template_id=str(row["template_id"]),
        start_date=row["start_date"],
        end_date=row["end_date"],
        created_by=str(row["created_by"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        settings=settings,
    )


class CampaignService:
    """Handles CRUD dan orkestrasi kampanye."""

    def __init__(self, orchestrator: Optional[Any] = None) -> None:
        self._orchestrator = orchestrator

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        name: str,
        description: str,
        selection_criteria_id: str,
        template_id: str,
        start_date: datetime,
        end_date: datetime,
        created_by: str,
        db: AsyncSession,
        settings: Optional[CampaignSettings] = None,
    ) -> Campaign:
        """INSERT kampanye baru ke tabel campaigns, kembalikan Campaign."""
        campaign_id = str(uuid.uuid4())
        now = _now_utc()
        campaign_settings = settings or CampaignSettings()

        settings_dict = {
            "max_invitations_per_minute": campaign_settings.max_invitations_per_minute,
            "monitoring_interval_minutes": campaign_settings.monitoring_interval_minutes,
            "compliance_check_enabled": campaign_settings.compliance_check_enabled,
            "alert_thresholds": campaign_settings.alert_thresholds,
        }

        await db.execute(
            text(
                """
                INSERT INTO campaigns
                    (id, name, description, status, selection_criteria_id, template_id,
                     start_date, end_date, created_by, settings, created_at, updated_at)
                VALUES
                    (:id, :name, :description, :status, :selection_criteria_id, :template_id,
                     :start_date, :end_date, :created_by, :settings::jsonb, :now, :now)
                """
            ),
            {
                "id": campaign_id,
                "name": name,
                "description": description,
                "status": CampaignStatus.DRAFT.value,
                "selection_criteria_id": selection_criteria_id,
                "template_id": template_id,
                "start_date": start_date,
                "end_date": end_date,
                "created_by": created_by,
                "settings": json.dumps(settings_dict),
                "now": now,
            },
        )
        await db.flush()

        return Campaign(
            id=campaign_id,
            name=name,
            description=description,
            status=CampaignStatus.DRAFT,
            selection_criteria_id=selection_criteria_id,
            template_id=template_id,
            start_date=start_date,
            end_date=end_date,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            settings=campaign_settings,
        )

    # ------------------------------------------------------------------
    # Get
    # ------------------------------------------------------------------

    async def get(self, campaign_id: str, db: AsyncSession) -> Campaign:
        """SELECT kampanye by id. Raises ValidationError jika tidak ditemukan."""
        result = await db.execute(
            text("SELECT * FROM campaigns WHERE id = :id"),
            {"id": campaign_id},
        )
        row = result.mappings().first()
        if row is None:
            raise ValidationError(f"Kampanye dengan id '{campaign_id}' tidak ditemukan.")
        return _row_to_campaign(row)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(
        self,
        campaign_id: str,
        db: AsyncSession,
        **kwargs: Any,
    ) -> Campaign:
        """UPDATE fields yang diberikan pada kampanye."""
        # Pastikan kampanye ada
        await self.get(campaign_id, db)

        now = _now_utc()
        allowed_fields = {
            "name", "description", "selection_criteria_id", "template_id",
            "start_date", "end_date", "status",
        }

        set_clauses = ["updated_at = :now"]
        params: Dict[str, Any] = {"id": campaign_id, "now": now}

        for key, value in kwargs.items():
            if key in allowed_fields:
                set_clauses.append(f"{key} = :{key}")
                if isinstance(value, CampaignStatus):
                    params[key] = value.value
                else:
                    params[key] = value

        if len(set_clauses) > 1:
            await db.execute(
                text(f"UPDATE campaigns SET {', '.join(set_clauses)} WHERE id = :id"),
                params,
            )
            await db.flush()

        return await self.get(campaign_id, db)

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete(self, campaign_id: str, db: AsyncSession) -> None:
        """DELETE kampanye. Hanya jika status DRAFT."""
        campaign = await self.get(campaign_id, db)
        if campaign.status != CampaignStatus.DRAFT:
            raise ValidationError(
                f"Kampanye '{campaign_id}' tidak dapat dihapus karena status bukan DRAFT "
                f"(status saat ini: {campaign.status.value})."
            )

        await db.execute(
            text("DELETE FROM campaigns WHERE id = :id"),
            {"id": campaign_id},
        )
        await db.flush()

    # ------------------------------------------------------------------
    # Start / Stop (delegasi ke AgentOrchestrator)
    # ------------------------------------------------------------------

    async def start_campaign(self, campaign_id: str, db: AsyncSession) -> Any:
        """Delegasikan ke AgentOrchestrator.start_campaign()."""
        if self._orchestrator is None:
            raise ValidationError("AgentOrchestrator tidak dikonfigurasi.")
        return await self._orchestrator.start_campaign(campaign_id, db)

    async def stop_campaign(self, campaign_id: str, db: AsyncSession) -> None:
        """Delegasikan ke AgentOrchestrator.stop_campaign()."""
        if self._orchestrator is None:
            raise ValidationError("AgentOrchestrator tidak dikonfigurasi.")
        await self._orchestrator.stop_campaign(campaign_id, db)

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_campaigns(
        self,
        db: AsyncSession,
        status: Optional[CampaignStatus] = None,
    ) -> List[Campaign]:
        """SELECT semua kampanye, filter opsional by status."""
        if status is not None:
            result = await db.execute(
                text("SELECT * FROM campaigns WHERE status = :status ORDER BY created_at DESC"),
                {"status": status.value},
            )
        else:
            result = await db.execute(
                text("SELECT * FROM campaigns ORDER BY created_at DESC")
            )

        rows = result.mappings().all()
        return [_row_to_campaign(row) for row in rows]
