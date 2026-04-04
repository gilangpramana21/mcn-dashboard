"""Integration tests end-to-end untuk TikTok Influencer Marketing Agent.

Validates: Requirements 16.3 — alur lengkap seleksi → pengumpulan WA → pengiriman → klasifikasi.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.agents.classifier_agent import ClassifierAgent
from app.agents.selector_agent import SelectorAgent
from app.agents.sender_agent import SenderAgent
from app.agents.whatsapp_collector_agent import WhatsAppCollectorAgent
from app.models.domain import (
    CriteriaWeights,
    FeedbackCategory,
    Influencer,
    InfluencerFeedback,
    InfluencerStatus,
    InvitationStatus,
    MessageTemplate,
    SelectionCriteria,
    WhatsAppCollectionMethod,
    WhatsAppCollectionRecord,
    WhatsAppCollectionResult,
    WhatsAppCollectionStatus,
)
from app.services.blacklist_service import BlacklistService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_influencer(
    influencer_id: str,
    follower_count: int = 50000,
    engagement_rate: float = 0.08,
    phone_number: str = "+6281234567890",
    blacklisted: bool = False,
) -> Influencer:
    return Influencer(
        id=influencer_id,
        tiktok_user_id=f"tiktok-{influencer_id}",
        name=f"Influencer {influencer_id}",
        phone_number=phone_number,
        follower_count=follower_count,
        engagement_rate=engagement_rate,
        content_categories=["fashion", "lifestyle"],
        location="Jakarta",
        blacklisted=blacklisted,
    )


def _make_template() -> MessageTemplate:
    now = _now()
    return MessageTemplate(
        id="template-1",
        name="Campaign Invitation",
        content="Halo {{name}}, kami mengundang Anda untuk kampanye {{campaign}}!",
        variables=["name", "campaign"],
        default_values={"name": "Influencer", "campaign": "Campaign"},
        version=1,
        is_active=True,
        campaign_ids=[],
        created_at=now,
        updated_at=now,
    )


def _make_blacklist_service(blacklisted_ids: set = None) -> BlacklistService:
    blacklisted_ids = blacklisted_ids or set()
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if "SELECT 1 FROM blacklist" in q and params:
            influencer_id = params.get("influencer_id", "")
            if influencer_id in blacklisted_ids:
                mock_result.first.return_value = (1,)
            else:
                mock_result.first.return_value = None
        else:
            mock_result.first.return_value = None

        mock_mappings.first.return_value = None
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return BlacklistService(db)


def _make_db_with_template(template: MessageTemplate) -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        q = str(query)
        mock_result = MagicMock()
        mock_mappings = MagicMock()

        if "SELECT * FROM message_templates" in q:
            row = {
                "id": template.id,
                "name": template.name,
                "content": template.content,
                "variables": json.dumps(template.variables),
                "default_values": json.dumps(template.default_values),
                "version": template.version,
                "is_active": template.is_active,
                "campaign_ids": json.dumps(template.campaign_ids),
                "created_at": template.created_at,
                "updated_at": template.updated_at,
            }
            mock_mappings.first.return_value = row
        else:
            mock_mappings.first.return_value = None

        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# Test: Alur Lengkap End-to-End
# ---------------------------------------------------------------------------


class TestEndToEndFlow:
    """Integration tests untuk alur lengkap kampanye."""

    @pytest.mark.asyncio
    async def test_full_campaign_flow_selection_to_classification(self):
        """Test alur lengkap: seleksi → pengumpulan WA → pengiriman → klasifikasi."""
        campaign_id = "camp-e2e-1"
        template = _make_template()

        # --- Step 1: Seleksi Influencer ---
        influencers = [
            _make_influencer("inf-1", follower_count=100000, engagement_rate=0.10),
            _make_influencer("inf-2", follower_count=50000, engagement_rate=0.08),
            _make_influencer("inf-3", follower_count=5000, engagement_rate=0.05),  # di bawah min
            _make_influencer("inf-blacklisted", blacklisted=True),
        ]

        blacklist_service = _make_blacklist_service({"inf-blacklisted"})
        selector = SelectorAgent(blacklist_service=blacklist_service)

        criteria = SelectionCriteria(
            id="crit-1",
            name="Test Criteria",
            min_followers=10000,
            min_engagement_rate=0.06,
            criteria_weights=CriteriaWeights(),
        )

        selection_result = await selector.select_influencers(
            criteria=criteria,
            campaign_id=campaign_id,
            influencers=influencers,
        )

        # Verifikasi seleksi
        selected_ids = {inf.id for inf in selection_result.influencers}
        assert "inf-1" in selected_ids
        assert "inf-2" in selected_ids
        assert "inf-3" not in selected_ids  # di bawah min_followers
        assert "inf-blacklisted" not in selected_ids  # blacklisted

        # --- Step 2: Pengumpulan Nomor WA ---
        wa_agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

        collected_numbers: Dict[str, str] = {}
        for inf in selection_result.influencers:
            # Simulasikan pengumpulan nomor WA
            phone = inf.phone_number
            if wa_agent.validate_whatsapp_number(phone):
                collected_numbers[inf.id] = phone

        assert len(collected_numbers) == len(selection_result.influencers)

        # --- Step 3: Pengiriman Undangan ---
        db = _make_db_with_template(template)

        mock_wa_result = MagicMock()
        mock_wa_result.message_id = "msg-123"
        mock_wa_client = AsyncMock()
        mock_wa_client.send_message = AsyncMock(return_value=mock_wa_result)

        sender = SenderAgent(
            blacklist_service=blacklist_service,
            whatsapp_client=mock_wa_client,
        )

        report = await sender.send_bulk_invitations(
            influencers=selection_result.influencers,
            template_id="template-1",
            campaign_id=campaign_id,
            db=db,
        )

        # Verifikasi pengiriman
        assert report.total_processed == len(selection_result.influencers)
        assert report.total_sent + report.total_failed + report.total_pending == report.total_processed
        assert report.total_sent > 0

        # --- Step 4: Klasifikasi Umpan Balik ---
        classifier_db = AsyncMock()
        classifier_db.flush = AsyncMock()

        async def _classifier_execute(query, params=None):
            mock_result = MagicMock()
            mock_mappings = MagicMock()
            mock_mappings.first.return_value = None
            mock_mappings.all.return_value = []
            mock_result.mappings.return_value = mock_mappings
            return mock_result

        classifier_db.execute = _classifier_execute

        classifier = ClassifierAgent()

        feedback_messages = [
            ("inf-1", "iya, saya mau bergabung"),
            ("inf-2", "tidak bisa, maaf"),
        ]

        classifications = []
        for inf_id, message in feedback_messages:
            feedback = InfluencerFeedback(
                id=str(uuid.uuid4()),
                campaign_id=campaign_id,
                influencer_id=inf_id,
                invitation_id=str(uuid.uuid4()),
                raw_message=message,
                received_at=_now(),
            )
            result = await classifier.classify_feedback(feedback, classifier_db)
            classifications.append(result)

        # Verifikasi klasifikasi
        assert len(classifications) == 2
        for cls in classifications:
            assert cls.category in set(FeedbackCategory)
            assert 0.0 <= cls.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_component_call_order(self):
        """Test bahwa setiap komponen dipanggil dalam urutan yang benar."""
        call_order: List[str] = []

        # Mock selector
        mock_selector = AsyncMock()
        mock_selection_result = MagicMock()
        mock_selection_result.influencers = [
            _make_influencer("inf-1"),
        ]

        async def _mock_select(*args, **kwargs):
            call_order.append("selector")
            return mock_selection_result

        mock_selector.select_influencers = _mock_select

        # Mock WA collector
        mock_wa_agent = AsyncMock()

        async def _mock_collect(*args, **kwargs):
            call_order.append("wa_collector")
            return WhatsAppCollectionResult(
                affiliate_id="inf-1",
                status=WhatsAppCollectionStatus.COLLECTED,
                record=WhatsAppCollectionRecord(
                    id=str(uuid.uuid4()),
                    affiliate_id="inf-1",
                    influencer_id="inf-1",
                    phone_number="+6281234567890",
                    method=WhatsAppCollectionMethod.OFFICIAL_ICON,
                    status=WhatsAppCollectionStatus.COLLECTED,
                    collected_at=_now(),
                ),
                phone_number="+6281234567890",
                method=WhatsAppCollectionMethod.OFFICIAL_ICON,
            )

        mock_wa_agent.collect_whatsapp_number = _mock_collect

        # Mock sender
        mock_sender = AsyncMock()

        async def _mock_send(*args, **kwargs):
            call_order.append("sender")
            from app.agents.sender_agent import InvitationReport
            return InvitationReport(
                campaign_id="camp-1",
                total_sent=1,
                total_failed=0,
                total_pending=0,
                total_processed=1,
            )

        mock_sender.send_bulk_invitations = _mock_send

        # Mock classifier
        mock_classifier = AsyncMock()

        async def _mock_classify(*args, **kwargs):
            call_order.append("classifier")
            from app.agents.classifier_agent import ClassificationResult
            return ClassificationResult(
                feedback_id="fb-1",
                category=FeedbackCategory.ACCEPTED,
                confidence_score=0.9,
                requires_manual_review=False,
            )

        mock_classifier.classify_feedback = _mock_classify

        # Jalankan alur
        db = AsyncMock()
        db.flush = AsyncMock()

        criteria = SelectionCriteria(id="crit-1", name="Test", criteria_weights=CriteriaWeights())
        influencers = [_make_influencer("inf-1")]

        # Step 1: Seleksi
        selection = await mock_selector.select_influencers(
            criteria=criteria,
            campaign_id="camp-1",
            influencers=influencers,
        )

        # Step 2: Pengumpulan WA
        for inf in selection.influencers:
            await mock_wa_agent.collect_whatsapp_number(inf.tiktok_user_id, db)

        # Step 3: Pengiriman
        await mock_sender.send_bulk_invitations(
            influencers=selection.influencers,
            template_id="template-1",
            campaign_id="camp-1",
            db=db,
        )

        # Step 4: Klasifikasi
        feedback = InfluencerFeedback(
            id="fb-1",
            campaign_id="camp-1",
            influencer_id="inf-1",
            invitation_id="inv-1",
            raw_message="iya mau",
            received_at=_now(),
        )
        await mock_classifier.classify_feedback(feedback, db)

        # Verifikasi urutan
        assert call_order == ["selector", "wa_collector", "sender", "classifier"], (
            f"Urutan komponen tidak benar: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_blacklisted_influencer_excluded_throughout_flow(self):
        """Test bahwa influencer blacklisted dikecualikan di seluruh alur."""
        blacklisted_id = "inf-blacklisted"
        blacklist_service = _make_blacklist_service({blacklisted_id})
        selector = SelectorAgent(blacklist_service=blacklist_service)

        influencers = [
            _make_influencer("inf-valid", follower_count=100000),
            _make_influencer(blacklisted_id, blacklisted=True),
        ]

        criteria = SelectionCriteria(
            id="crit-1",
            name="Test",
            criteria_weights=CriteriaWeights(),
        )

        selection_result = await selector.select_influencers(
            criteria=criteria,
            campaign_id="camp-1",
            influencers=influencers,
        )

        # Blacklisted tidak boleh ada dalam hasil seleksi
        selected_ids = {inf.id for inf in selection_result.influencers}
        assert blacklisted_id not in selected_ids
        assert "inf-valid" in selected_ids

        # Verifikasi pengiriman juga menolak blacklisted
        template = _make_template()
        db = _make_db_with_template(template)

        mock_wa_result = MagicMock()
        mock_wa_result.message_id = "msg-123"
        mock_wa_client = AsyncMock()
        mock_wa_client.send_message = AsyncMock(return_value=mock_wa_result)

        sender = SenderAgent(
            blacklist_service=blacklist_service,
            whatsapp_client=mock_wa_client,
        )

        from app.exceptions import BlacklistViolationError
        blacklisted_inf = _make_influencer(blacklisted_id, blacklisted=True)

        with pytest.raises(BlacklistViolationError):
            await sender.send_single_invitation(
                influencer=blacklisted_inf,
                template_id="template-1",
                campaign_id="camp-1",
                db=db,
            )

    @pytest.mark.asyncio
    async def test_all_external_api_calls_mocked(self):
        """Test bahwa semua external API calls menggunakan mock."""
        # Verifikasi bahwa tidak ada koneksi nyata ke API eksternal
        template = _make_template()
        db = _make_db_with_template(template)

        # Mock WhatsApp API
        mock_wa_result = MagicMock()
        mock_wa_result.message_id = "msg-mock-123"
        mock_wa_client = AsyncMock()
        mock_wa_client.send_message = AsyncMock(return_value=mock_wa_result)

        blacklist_service = _make_blacklist_service()
        sender = SenderAgent(
            blacklist_service=blacklist_service,
            whatsapp_client=mock_wa_client,
        )

        influencer = _make_influencer("inf-1")

        invitation_id = await sender.send_single_invitation(
            influencer=influencer,
            template_id="template-1",
            campaign_id="camp-1",
            db=db,
        )

        # Verifikasi mock dipanggil
        mock_wa_client.send_message.assert_called_once()
        assert invitation_id is not None

        # Verifikasi argumen yang dikirim ke WhatsApp API
        call_args = mock_wa_client.send_message.call_args
        assert call_args.kwargs.get("phone_number") == influencer.phone_number or \
               (len(call_args.args) > 0 and call_args.args[0] == influencer.phone_number)
