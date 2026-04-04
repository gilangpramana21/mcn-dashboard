"""Unit tests for CampaignService."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import ValidationError
from app.models.domain import Campaign, CampaignSettings, CampaignStatus
from app.services.campaign_service import CampaignService


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_campaign_row(
    campaign_id: str = "camp-1",
    name: str = "Test Campaign",
    status: str = "DRAFT",
) -> Dict[str, Any]:
    now = _now()
    return {
        "id": campaign_id,
        "name": name,
        "description": "Deskripsi",
        "status": status,
        "selection_criteria_id": "crit-1",
        "template_id": "tmpl-1",
        "start_date": now,
        "end_date": now,
        "created_by": "user-1",
        "settings": "{}",
        "created_at": now,
        "updated_at": now,
    }


def _make_db_with_row(row: Optional[Dict] = None) -> AsyncMock:
    """Buat mock DB yang mengembalikan row tertentu saat execute dipanggil."""
    db = AsyncMock()
    mock_row = MagicMock()
    mock_row.__getitem__ = lambda self, key: row[key] if row else None
    mock_row.get = lambda key, default=None: row.get(key, default) if row else default

    mappings_mock = MagicMock()
    mappings_mock.first = MagicMock(return_value=mock_row if row else None)
    mappings_mock.all = MagicMock(return_value=[mock_row] if row else [])

    result_mock = MagicMock()
    result_mock.mappings = MagicMock(return_value=mappings_mock)

    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()
    return db


def _make_service(orchestrator: Optional[Any] = None) -> CampaignService:
    return CampaignService(orchestrator=orchestrator)


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestCreate:
    @pytest.mark.asyncio
    async def test_create_returns_campaign_with_draft_status(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.flush = AsyncMock()

        service = _make_service()
        now = _now()

        campaign = await service.create(
            name="Kampanye Baru",
            description="Deskripsi",
            selection_criteria_id="crit-1",
            template_id="tmpl-1",
            start_date=now,
            end_date=now,
            created_by="user-1",
            db=db,
        )

        assert campaign.name == "Kampanye Baru"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.selection_criteria_id == "crit-1"
        assert campaign.template_id == "tmpl-1"
        assert campaign.created_by == "user-1"

    @pytest.mark.asyncio
    async def test_create_generates_uuid(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.flush = AsyncMock()

        service = _make_service()
        now = _now()

        campaign = await service.create(
            name="Kampanye",
            description="",
            selection_criteria_id="crit-1",
            template_id="tmpl-1",
            start_date=now,
            end_date=now,
            created_by="user-1",
            db=db,
        )

        assert len(campaign.id) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_create_calls_db_execute_and_flush(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.flush = AsyncMock()

        service = _make_service()
        now = _now()

        await service.create(
            name="Kampanye",
            description="",
            selection_criteria_id="crit-1",
            template_id="tmpl-1",
            start_date=now,
            end_date=now,
            created_by="user-1",
            db=db,
        )

        db.execute.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_custom_settings(self):
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.flush = AsyncMock()

        service = _make_service()
        now = _now()
        settings = CampaignSettings(max_invitations_per_minute=50)

        campaign = await service.create(
            name="Kampanye",
            description="",
            selection_criteria_id="crit-1",
            template_id="tmpl-1",
            start_date=now,
            end_date=now,
            created_by="user-1",
            db=db,
            settings=settings,
        )

        assert campaign.settings.max_invitations_per_minute == 50


# ---------------------------------------------------------------------------
# Tests: get
# ---------------------------------------------------------------------------


class TestGet:
    @pytest.mark.asyncio
    async def test_get_returns_campaign(self):
        row = _make_campaign_row(campaign_id="camp-42", name="Kampanye 42")
        db = _make_db_with_row(row)

        service = _make_service()
        campaign = await service.get("camp-42", db)

        assert campaign.id == "camp-42"
        assert campaign.name == "Kampanye 42"

    @pytest.mark.asyncio
    async def test_get_raises_if_not_found(self):
        db = _make_db_with_row(None)

        service = _make_service()

        with pytest.raises(ValidationError):
            await service.get("nonexistent", db)

    @pytest.mark.asyncio
    async def test_get_returns_correct_status(self):
        row = _make_campaign_row(status="ACTIVE")
        db = _make_db_with_row(row)

        service = _make_service()
        campaign = await service.get("camp-1", db)

        assert campaign.status == CampaignStatus.ACTIVE


# ---------------------------------------------------------------------------
# Tests: update
# ---------------------------------------------------------------------------


class TestUpdate:
    @pytest.mark.asyncio
    async def test_update_calls_db_execute(self):
        row = _make_campaign_row()
        db = _make_db_with_row(row)

        service = _make_service()
        await service.update("camp-1", db, name="Nama Baru")

        # execute dipanggil minimal 2x: SELECT (get) + UPDATE + SELECT (get after update)
        assert db.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_update_raises_if_campaign_not_found(self):
        db = _make_db_with_row(None)

        service = _make_service()

        with pytest.raises(ValidationError):
            await service.update("nonexistent", db, name="Nama Baru")


# ---------------------------------------------------------------------------
# Tests: delete
# ---------------------------------------------------------------------------


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_draft_campaign_succeeds(self):
        row = _make_campaign_row(status="DRAFT")
        db = _make_db_with_row(row)

        service = _make_service()
        # Tidak boleh raise
        await service.delete("camp-1", db)

        db.execute.assert_called()

    @pytest.mark.asyncio
    async def test_delete_active_campaign_raises(self):
        row = _make_campaign_row(status="ACTIVE")
        db = _make_db_with_row(row)

        service = _make_service()

        with pytest.raises(ValidationError):
            await service.delete("camp-1", db)

    @pytest.mark.asyncio
    async def test_delete_completed_campaign_raises(self):
        row = _make_campaign_row(status="COMPLETED")
        db = _make_db_with_row(row)

        service = _make_service()

        with pytest.raises(ValidationError):
            await service.delete("camp-1", db)

    @pytest.mark.asyncio
    async def test_delete_raises_if_not_found(self):
        db = _make_db_with_row(None)

        service = _make_service()

        with pytest.raises(ValidationError):
            await service.delete("nonexistent", db)


# ---------------------------------------------------------------------------
# Tests: start_campaign / stop_campaign (delegasi ke orchestrator)
# ---------------------------------------------------------------------------


class TestStartStopCampaign:
    @pytest.mark.asyncio
    async def test_start_campaign_delegates_to_orchestrator(self):
        orchestrator = MagicMock()
        orchestrator.start_campaign = AsyncMock(return_value="result")

        service = _make_service(orchestrator=orchestrator)
        db = AsyncMock()

        result = await service.start_campaign("camp-1", db)

        orchestrator.start_campaign.assert_called_once_with("camp-1", db)
        assert result == "result"

    @pytest.mark.asyncio
    async def test_stop_campaign_delegates_to_orchestrator(self):
        orchestrator = MagicMock()
        orchestrator.stop_campaign = AsyncMock()

        service = _make_service(orchestrator=orchestrator)
        db = AsyncMock()

        await service.stop_campaign("camp-1", db)

        orchestrator.stop_campaign.assert_called_once_with("camp-1", db)

    @pytest.mark.asyncio
    async def test_start_campaign_raises_if_no_orchestrator(self):
        service = _make_service(orchestrator=None)
        db = AsyncMock()

        with pytest.raises(ValidationError):
            await service.start_campaign("camp-1", db)

    @pytest.mark.asyncio
    async def test_stop_campaign_raises_if_no_orchestrator(self):
        service = _make_service(orchestrator=None)
        db = AsyncMock()

        with pytest.raises(ValidationError):
            await service.stop_campaign("camp-1", db)


# ---------------------------------------------------------------------------
# Tests: list_campaigns
# ---------------------------------------------------------------------------


class TestListCampaigns:
    @pytest.mark.asyncio
    async def test_list_campaigns_returns_all(self):
        row = _make_campaign_row()
        db = _make_db_with_row(row)

        service = _make_service()
        campaigns = await service.list_campaigns(db)

        assert isinstance(campaigns, list)
        assert len(campaigns) == 1

    @pytest.mark.asyncio
    async def test_list_campaigns_with_status_filter(self):
        row = _make_campaign_row(status="ACTIVE")
        db = _make_db_with_row(row)

        service = _make_service()
        campaigns = await service.list_campaigns(db, status=CampaignStatus.ACTIVE)

        assert isinstance(campaigns, list)

    @pytest.mark.asyncio
    async def test_list_campaigns_empty_returns_empty_list(self):
        db = _make_db_with_row(None)

        service = _make_service()
        campaigns = await service.list_campaigns(db)

        assert campaigns == []
