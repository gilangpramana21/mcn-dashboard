"""Unit tests for AgentOrchestrator."""

from __future__ import annotations

from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.orchestrator import AgentOrchestrator, CampaignResult
from app.agents.classifier_agent import ClassifierAgent, ClassificationResult
from app.agents.monitor_agent import MonitorAgent
from app.agents.selector_agent import SelectorAgent, SelectionResult
from app.agents.sender_agent import SenderAgent, InvitationReport
from app.exceptions import ValidationError
from app.models.domain import (
    Campaign,
    CampaignSettings,
    CampaignStatus,
    FeedbackCategory,
    Influencer,
    InfluencerFeedback,
    InfluencerStatus,
    SelectionCriteria,
)


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_influencer(id: str = "inf-1") -> Influencer:
    return Influencer(
        id=id,
        tiktok_user_id=f"tt-{id}",
        name=f"Influencer {id}",
        phone_number="+6281234567890",
        follower_count=50_000,
        engagement_rate=0.05,
        content_categories=["fashion"],
        location="Jakarta",
    )


def _make_campaign(
    campaign_id: str = "camp-1",
    status: CampaignStatus = CampaignStatus.DRAFT,
) -> Campaign:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    return Campaign(
        id=campaign_id,
        name="Test Campaign",
        description="Deskripsi kampanye",
        status=status,
        selection_criteria_id="crit-1",
        template_id="tmpl-1",
        start_date=now,
        end_date=now,
        created_by="user-1",
        created_at=now,
        updated_at=now,
        settings=CampaignSettings(),
    )


def _make_criteria() -> SelectionCriteria:
    return SelectionCriteria(id="crit-1", name="Test Criteria")


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock(mappings=MagicMock(return_value=MagicMock(first=MagicMock(return_value=None)))))
    db.flush = AsyncMock()
    return db


def _make_orchestrator(
    selected_influencers: Optional[List[Influencer]] = None,
    total_sent: int = 2,
    total_failed: int = 0,
) -> AgentOrchestrator:
    influencers = selected_influencers or [_make_influencer("inf-1"), _make_influencer("inf-2")]

    selector = MagicMock(spec=SelectorAgent)
    selector.select_influencers = AsyncMock(
        return_value=SelectionResult(
            influencers=influencers,
            total_found=len(influencers),
        )
    )

    sender = MagicMock(spec=SenderAgent)
    sender.send_bulk_invitations = AsyncMock(
        return_value=InvitationReport(
            campaign_id="camp-1",
            total_sent=total_sent,
            total_failed=total_failed,
            total_pending=0,
            total_processed=len(influencers),
        )
    )

    monitor = MagicMock(spec=MonitorAgent)
    monitor.start_monitoring = AsyncMock()
    monitor.stop_monitoring = MagicMock()

    classifier = MagicMock(spec=ClassifierAgent)
    classifier.classify_feedback = AsyncMock(
        return_value=ClassificationResult(
            feedback_id="fb-1",
            category=FeedbackCategory.ACCEPTED,
            confidence_score=0.9,
            requires_manual_review=False,
        )
    )

    affiliate_client = MagicMock()
    affiliate_client.get_influencers = AsyncMock(
        return_value=MagicMock(items=influencers)
    )

    return AgentOrchestrator(
        selector_agent=selector,
        sender_agent=sender,
        monitor_agent=monitor,
        classifier_agent=classifier,
        affiliate_client=affiliate_client,
    )


# ---------------------------------------------------------------------------
# Tests: start_campaign
# ---------------------------------------------------------------------------


class TestStartCampaign:
    @pytest.mark.asyncio
    async def test_start_campaign_calls_selector_sender_monitor_in_order(self):
        """start_campaign harus memanggil selector, sender, monitor secara berurutan."""
        call_order = []

        influencers = [_make_influencer("inf-1"), _make_influencer("inf-2")]

        selector = MagicMock(spec=SelectorAgent)

        async def _select(*args, **kwargs):
            call_order.append("selector")
            return SelectionResult(influencers=influencers, total_found=2)

        selector.select_influencers = _select

        sender = MagicMock(spec=SenderAgent)

        async def _send(*args, **kwargs):
            call_order.append("sender")
            return InvitationReport(
                campaign_id="camp-1",
                total_sent=2,
                total_failed=0,
                total_pending=0,
                total_processed=2,
            )

        sender.send_bulk_invitations = _send

        monitor = MagicMock(spec=MonitorAgent)

        async def _monitor(*args, **kwargs):
            call_order.append("monitor")

        monitor.start_monitoring = _monitor

        classifier = MagicMock(spec=ClassifierAgent)
        affiliate_client = MagicMock()
        affiliate_client.get_influencers = AsyncMock(return_value=MagicMock(items=influencers))

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            affiliate_client=affiliate_client,
        )

        campaign = _make_campaign()
        criteria = _make_criteria()
        db = _make_db()

        # Mock _get_campaign dan _get_selection_criteria
        orchestrator._get_campaign = AsyncMock(return_value=campaign)
        orchestrator._get_selection_criteria = AsyncMock(return_value=criteria)
        orchestrator._update_campaign_status = AsyncMock()

        await orchestrator.start_campaign("camp-1", db)

        assert call_order == ["selector", "sender", "monitor"]

    @pytest.mark.asyncio
    async def test_start_campaign_returns_campaign_result(self):
        orchestrator = _make_orchestrator(total_sent=3, total_failed=1)
        campaign = _make_campaign()
        criteria = _make_criteria()
        db = _make_db()

        orchestrator._get_campaign = AsyncMock(return_value=campaign)
        orchestrator._get_selection_criteria = AsyncMock(return_value=criteria)
        orchestrator._update_campaign_status = AsyncMock()

        result = await orchestrator.start_campaign("camp-1", db)

        assert isinstance(result, CampaignResult)
        assert result.campaign_id == "camp-1"
        assert result.status == CampaignStatus.ACTIVE
        assert result.influencers_selected == 2
        assert result.invitations_sent == 3
        assert result.invitations_failed == 1

    @pytest.mark.asyncio
    async def test_start_campaign_raises_if_campaign_not_found(self):
        orchestrator = _make_orchestrator()
        db = _make_db()

        orchestrator._get_campaign = AsyncMock(return_value=None)

        with pytest.raises(ValidationError):
            await orchestrator.start_campaign("nonexistent", db)

    @pytest.mark.asyncio
    async def test_start_campaign_updates_status_to_active(self):
        orchestrator = _make_orchestrator()
        campaign = _make_campaign()
        criteria = _make_criteria()
        db = _make_db()

        orchestrator._get_campaign = AsyncMock(return_value=campaign)
        orchestrator._get_selection_criteria = AsyncMock(return_value=criteria)
        orchestrator._update_campaign_status = AsyncMock()

        await orchestrator.start_campaign("camp-1", db)

        orchestrator._update_campaign_status.assert_called_once_with(
            "camp-1", CampaignStatus.ACTIVE, db
        )

    @pytest.mark.asyncio
    async def test_start_campaign_passes_selected_influencers_to_sender(self):
        influencers = [_make_influencer("inf-A"), _make_influencer("inf-B")]

        selector = MagicMock(spec=SelectorAgent)
        selector.select_influencers = AsyncMock(
            return_value=SelectionResult(influencers=influencers, total_found=2)
        )

        sender = MagicMock(spec=SenderAgent)
        sender.send_bulk_invitations = AsyncMock(
            return_value=InvitationReport(
                campaign_id="camp-1",
                total_sent=2,
                total_failed=0,
                total_pending=0,
                total_processed=2,
            )
        )

        monitor = MagicMock(spec=MonitorAgent)
        monitor.start_monitoring = AsyncMock()

        classifier = MagicMock(spec=ClassifierAgent)
        affiliate_client = MagicMock()
        affiliate_client.get_influencers = AsyncMock(return_value=MagicMock(items=influencers))

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            affiliate_client=affiliate_client,
        )

        campaign = _make_campaign()
        criteria = _make_criteria()
        db = _make_db()

        orchestrator._get_campaign = AsyncMock(return_value=campaign)
        orchestrator._get_selection_criteria = AsyncMock(return_value=criteria)
        orchestrator._update_campaign_status = AsyncMock()

        await orchestrator.start_campaign("camp-1", db)

        call_kwargs = sender.send_bulk_invitations.call_args
        assert call_kwargs.kwargs["influencers"] == influencers


# ---------------------------------------------------------------------------
# Tests: stop_campaign
# ---------------------------------------------------------------------------


class TestStopCampaign:
    @pytest.mark.asyncio
    async def test_stop_campaign_stops_monitoring(self):
        orchestrator = _make_orchestrator()
        db = _make_db()
        orchestrator._update_campaign_status = AsyncMock()

        await orchestrator.stop_campaign("camp-1", db)

        orchestrator._monitor.stop_monitoring.assert_called_once_with("camp-1")

    @pytest.mark.asyncio
    async def test_stop_campaign_updates_status_to_completed(self):
        orchestrator = _make_orchestrator()
        db = _make_db()
        orchestrator._update_campaign_status = AsyncMock()

        await orchestrator.stop_campaign("camp-1", db)

        orchestrator._update_campaign_status.assert_called_once_with(
            "camp-1", CampaignStatus.COMPLETED, db
        )

    @pytest.mark.asyncio
    async def test_stop_campaign_calls_learning_engine_if_available(self):
        orchestrator = _make_orchestrator()
        db = _make_db()
        orchestrator._update_campaign_status = AsyncMock()

        learning_engine = MagicMock()
        learning_engine.record_campaign_outcome = AsyncMock()
        learning_engine.retrain_selection_model = AsyncMock()
        learning_engine.retrain_classifier_model = AsyncMock()
        orchestrator._learning_engine = learning_engine

        await orchestrator.stop_campaign("camp-1", db)

        learning_engine.record_campaign_outcome.assert_called_once_with("camp-1", db)


# ---------------------------------------------------------------------------
# Tests: get_campaign_status
# ---------------------------------------------------------------------------


class TestGetCampaignStatus:
    @pytest.mark.asyncio
    async def test_returns_campaign_status(self):
        orchestrator = _make_orchestrator()
        db = _make_db()
        campaign = _make_campaign(status=CampaignStatus.ACTIVE)
        orchestrator._get_campaign = AsyncMock(return_value=campaign)

        status = await orchestrator.get_campaign_status("camp-1", db)

        assert status == CampaignStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_raises_if_campaign_not_found(self):
        orchestrator = _make_orchestrator()
        db = _make_db()
        orchestrator._get_campaign = AsyncMock(return_value=None)

        with pytest.raises(ValidationError):
            await orchestrator.get_campaign_status("nonexistent", db)


# ---------------------------------------------------------------------------
# Tests: handle_agent_event
# ---------------------------------------------------------------------------


class TestHandleAgentEvent:
    @pytest.mark.asyncio
    async def test_feedback_received_calls_classifier(self):
        orchestrator = _make_orchestrator()
        db = _make_db()

        from datetime import datetime, timezone

        feedback = InfluencerFeedback(
            id="fb-1",
            campaign_id="camp-1",
            influencer_id="inf-1",
            invitation_id="inv-1",
            raw_message="iya saya mau",
            received_at=datetime.now(timezone.utc),
        )

        event = {"type": "feedback_received", "feedback": feedback}
        await orchestrator.handle_agent_event(event, db)

        orchestrator._classifier.classify_feedback.assert_called_once_with(
            feedback=feedback, db=db
        )

    @pytest.mark.asyncio
    async def test_content_non_compliant_logs_notification(self, caplog):
        import logging

        orchestrator = _make_orchestrator()
        db = _make_db()

        event = {
            "type": "content_non_compliant",
            "campaign_id": "camp-1",
            "influencer_id": "inf-1",
            "video_id": "vid-123",
        }

        with caplog.at_level(logging.WARNING):
            await orchestrator.handle_agent_event(event, db)

        assert "content_non_compliant" in caplog.text or "Konten tidak sesuai" in caplog.text

    @pytest.mark.asyncio
    async def test_unknown_event_does_not_raise(self):
        orchestrator = _make_orchestrator()
        db = _make_db()

        event = {"type": "unknown_event_type"}
        # Tidak boleh raise exception
        await orchestrator.handle_agent_event(event, db)
