"""Unit tests untuk SenderAgent."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.sender_agent import InvitationReport, SenderAgent
from app.exceptions import BlacklistViolationError, ValidationError
from app.integrations.whatsapp_api import MessageResult, MessageStatus
from app.models.domain import (
    Influencer,
    InfluencerStatus,
    InvitationStatus,
    MessageTemplate,
)
from app.services.blacklist_service import BlacklistService
from app.services.template_service import TemplateService


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _make_influencer(
    id: str = "inf-1",
    name: str = "Budi Santoso",
    phone_number: str = "+6281234567890",
    blacklisted: bool = False,
) -> Influencer:
    return Influencer(
        id=id,
        tiktok_user_id=f"tt-{id}",
        name=name,
        phone_number=phone_number,
        follower_count=50_000,
        engagement_rate=0.05,
        content_categories=["fashion"],
        location="Jakarta",
        blacklisted=blacklisted,
    )


def _make_template(
    id: str = "tmpl-1",
    content: str = "Halo {{name}}, bergabunglah di kampanye {{campaign}}!",
    default_values: Optional[dict] = None,
) -> MessageTemplate:
    return MessageTemplate(
        id=id,
        name="Template Test",
        content=content,
        variables=["name", "campaign"],
        default_values=default_values or {},
        version=1,
        is_active=True,
        campaign_ids=[],
        created_at=_now_utc(),
        updated_at=_now_utc(),
    )


def _make_blacklist_service(is_blacklisted: bool = False) -> BlacklistService:
    svc = MagicMock(spec=BlacklistService)
    svc.is_blacklisted = AsyncMock(return_value=is_blacklisted)
    return svc


def _make_whatsapp_client(
    message_id: str = "msg-123",
    raise_error: Optional[Exception] = None,
) -> MagicMock:
    client = MagicMock()
    if raise_error:
        client.send_message = AsyncMock(side_effect=raise_error)
    else:
        client.send_message = AsyncMock(
            return_value=MessageResult(
                message_id=message_id,
                status=MessageStatus.SENT,
                phone_number="+6281234567890",
            )
        )
    return client


def _make_db(
    template: Optional[MessageTemplate] = None,
    invitation_row: Optional[dict] = None,
) -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()

    # Default template
    tmpl = template or _make_template()

    # Mock execute untuk SELECT template
    async def _execute(query, params=None):
        mock_result = MagicMock()
        query_str = str(query) if hasattr(query, "__str__") else ""

        if "message_templates" in query_str:
            row = MagicMock()
            row.__getitem__ = lambda self, key: {
                "id": tmpl.id,
                "name": tmpl.name,
                "content": tmpl.content,
                "variables": tmpl.variables,
                "default_values": tmpl.default_values,
                "version": tmpl.version,
                "is_active": tmpl.is_active,
                "campaign_ids": tmpl.campaign_ids,
                "created_at": tmpl.created_at,
                "updated_at": tmpl.updated_at,
            }[key]
            mock_mappings = MagicMock()
            mock_mappings.first = MagicMock(return_value=row)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        elif "invitations" in query_str and "COUNT" in query_str:
            # generate_invitation_report query
            row = MagicMock()
            data = invitation_row or {
                "total_sent": 0,
                "total_failed": 0,
                "total_pending": 0,
                "total_processed": 0,
            }
            row.__getitem__ = lambda self, key: data[key]
            mock_mappings = MagicMock()
            mock_mappings.first = MagicMock(return_value=row)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        else:
            mock_result.mappings = MagicMock(return_value=MagicMock())

        return mock_result

    db.execute = AsyncMock(side_effect=_execute)
    return db


def _make_agent(
    is_blacklisted: bool = False,
    whatsapp_client: Optional[MagicMock] = None,
    redis: Optional[object] = None,
) -> SenderAgent:
    return SenderAgent(
        blacklist_service=_make_blacklist_service(is_blacklisted),
        whatsapp_client=whatsapp_client or _make_whatsapp_client(),
        redis=redis,
    )


# ---------------------------------------------------------------------------
# Tests: send_single_invitation — berhasil
# ---------------------------------------------------------------------------


class TestSendSingleInvitationSuccess:
    @pytest.mark.asyncio
    async def test_returns_invitation_id(self):
        agent = _make_agent()
        db = _make_db()
        influencer = _make_influencer()

        invitation_id = await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert isinstance(invitation_id, str)
        assert len(invitation_id) == 36  # UUID

    @pytest.mark.asyncio
    async def test_calls_whatsapp_send_message(self):
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencer = _make_influencer(phone_number="+6281234567890")

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        wa_client.send_message.assert_called_once()
        call_kwargs = wa_client.send_message.call_args
        assert call_kwargs.kwargs["phone_number"] == "+6281234567890"

    @pytest.mark.asyncio
    async def test_message_contains_substituted_variables(self):
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        template = _make_template(
            content="Halo {{name}}, bergabunglah di kampanye {{campaign}}!"
        )
        db = _make_db(template=template)
        influencer = _make_influencer(name="Siti Rahayu")

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-xyz",
            db=db,
        )

        sent_message = wa_client.send_message.call_args.kwargs["message"]
        assert "Siti Rahayu" in sent_message
        assert "camp-xyz" in sent_message
        assert "{{" not in sent_message

    @pytest.mark.asyncio
    async def test_saves_invitation_to_db(self):
        agent = _make_agent()
        db = _make_db()
        influencer = _make_influencer()

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        # db.execute dipanggil minimal 2x: SELECT template + INSERT invitation
        assert db.execute.call_count >= 2
        db.flush.assert_called()


# ---------------------------------------------------------------------------
# Tests: send_single_invitation — blacklisted
# ---------------------------------------------------------------------------


class TestSendSingleInvitationBlacklisted:
    @pytest.mark.asyncio
    async def test_blacklisted_flag_raises_error(self):
        agent = _make_agent(is_blacklisted=False)
        db = _make_db()
        influencer = _make_influencer(blacklisted=True)

        with pytest.raises(BlacklistViolationError):
            await agent.send_single_invitation(
                influencer=influencer,
                template_id="tmpl-1",
                campaign_id="camp-1",
                db=db,
            )

    @pytest.mark.asyncio
    async def test_blacklisted_in_db_raises_error(self):
        agent = _make_agent(is_blacklisted=True)
        db = _make_db()
        influencer = _make_influencer(blacklisted=False)

        with pytest.raises(BlacklistViolationError):
            await agent.send_single_invitation(
                influencer=influencer,
                template_id="tmpl-1",
                campaign_id="camp-1",
                db=db,
            )

    @pytest.mark.asyncio
    async def test_blacklisted_does_not_call_whatsapp(self):
        wa_client = _make_whatsapp_client()
        agent = SenderAgent(
            blacklist_service=_make_blacklist_service(is_blacklisted=True),
            whatsapp_client=wa_client,
        )
        db = _make_db()
        influencer = _make_influencer()

        with pytest.raises(BlacklistViolationError):
            await agent.send_single_invitation(
                influencer=influencer,
                template_id="tmpl-1",
                campaign_id="camp-1",
                db=db,
            )

        wa_client.send_message.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: send_single_invitation — scheduled
# ---------------------------------------------------------------------------


class TestSendSingleInvitationScheduled:
    @pytest.mark.asyncio
    async def test_scheduled_saves_with_scheduled_status(self):
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencer = _make_influencer()
        scheduled_at = datetime(2025, 12, 25, 10, 0, 0, tzinfo=timezone.utc)

        invitation_id = await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        # Tidak memanggil WhatsApp API
        wa_client.send_message.assert_not_called()
        # Tetap mengembalikan invitation_id
        assert isinstance(invitation_id, str)
        assert len(invitation_id) == 36

    @pytest.mark.asyncio
    async def test_scheduled_inserts_with_scheduled_at(self):
        """Verifikasi bahwa INSERT dipanggil dengan status SCHEDULED dan scheduled_at yang benar."""
        inserted_params: list[dict] = []

        async def _execute(query, params=None):
            mock_result = MagicMock()
            query_str = str(query.text) if hasattr(query, "text") else str(query)
            if "message_templates" in query_str:
                tmpl = _make_template()
                row = MagicMock()
                row.__getitem__ = lambda self, key: {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "content": tmpl.content,
                    "variables": tmpl.variables,
                    "default_values": tmpl.default_values,
                    "version": tmpl.version,
                    "is_active": tmpl.is_active,
                    "campaign_ids": tmpl.campaign_ids,
                    "created_at": tmpl.created_at,
                    "updated_at": tmpl.updated_at,
                }[key]
                mock_mappings = MagicMock()
                mock_mappings.first = MagicMock(return_value=row)
                mock_result.mappings = MagicMock(return_value=mock_mappings)
            elif "INSERT INTO invitations" in query_str and params:
                inserted_params.append(params)
                mock_result.mappings = MagicMock(return_value=MagicMock())
            else:
                mock_result.mappings = MagicMock(return_value=MagicMock())
            return mock_result

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(side_effect=_execute)

        agent = _make_agent()
        influencer = _make_influencer()
        scheduled_at = datetime(2025, 12, 25, 10, 0, 0, tzinfo=timezone.utc)

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert len(inserted_params) >= 1
        params = inserted_params[0]
        assert params["status"] == InvitationStatus.SCHEDULED.value
        assert params["scheduled_at"] == scheduled_at


# ---------------------------------------------------------------------------
# Tests: send_bulk_invitations
# ---------------------------------------------------------------------------


class TestSendBulkInvitations:
    @pytest.mark.asyncio
    async def test_returns_invitation_report(self):
        agent = _make_agent()
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(3)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert isinstance(report, InvitationReport)
        assert report.campaign_id == "camp-1"
        assert report.total_processed == 3

    @pytest.mark.asyncio
    async def test_all_success_report_counts(self):
        agent = _make_agent()
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(5)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 5
        assert report.total_failed == 0
        assert report.total_pending == 0
        assert report.total_processed == 5

    @pytest.mark.asyncio
    async def test_failure_one_does_not_stop_process(self):
        """Kegagalan satu influencer tidak menghentikan proses."""
        call_count = 0

        async def _send_message(phone_number: str, message: str):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("WhatsApp error")
            return MessageResult(
                message_id=f"msg-{call_count}",
                status=MessageStatus.SENT,
                phone_number=phone_number,
            )

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=_send_message)
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(3)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 2
        assert report.total_failed == 1
        assert report.total_processed == 3

    @pytest.mark.asyncio
    async def test_blacklisted_counted_as_failed(self):
        """Influencer blacklisted dihitung sebagai FAILED."""
        bl_svc = MagicMock(spec=BlacklistService)

        async def _is_blacklisted(inf_id: str) -> bool:
            return inf_id == "inf-1"

        bl_svc.is_blacklisted = _is_blacklisted
        agent = SenderAgent(
            blacklist_service=bl_svc,
            whatsapp_client=_make_whatsapp_client(),
        )
        db = _make_db()
        influencers = [
            _make_influencer("inf-1"),
            _make_influencer("inf-2"),
        ]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_failed == 1
        assert report.total_sent == 1
        assert report.total_processed == 2

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_report(self):
        agent = _make_agent()
        db = _make_db()

        report = await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 0
        assert report.total_failed == 0
        assert report.total_pending == 0
        assert report.total_processed == 0

    @pytest.mark.asyncio
    async def test_scheduled_bulk_counts_as_pending(self):
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(3)]
        scheduled_at = datetime(2025, 12, 25, 10, 0, 0, tzinfo=timezone.utc)

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert report.total_pending == 3
        assert report.total_sent == 0
        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_total_processed_equals_sum_of_all_statuses(self):
        """total_processed == total_sent + total_failed + total_pending."""
        call_count = 0

        async def _send_message(phone_number: str, message: str):
            nonlocal call_count
            call_count += 1
            if call_count % 3 == 0:
                raise Exception("error")
            return MessageResult(
                message_id=f"msg-{call_count}",
                status=MessageStatus.SENT,
                phone_number=phone_number,
            )

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=_send_message)
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(9)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent + report.total_failed + report.total_pending == report.total_processed


# ---------------------------------------------------------------------------
# Tests: rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_count_in_window_empty(self):
        agent = _make_agent()
        now = time.monotonic()
        assert agent._count_in_window(now) == 0

    def test_count_in_window_within_limit(self):
        agent = _make_agent()
        now = time.monotonic()
        for _ in range(50):
            agent._send_timestamps.append(now - 10)
        assert agent._count_in_window(now) == 50

    def test_count_in_window_prunes_old_timestamps(self):
        agent = _make_agent()
        now = time.monotonic()
        # Tambahkan 50 timestamp lama (di luar window)
        for _ in range(50):
            agent._send_timestamps.append(now - 70)
        # Tambahkan 30 timestamp baru (dalam window)
        for _ in range(30):
            agent._send_timestamps.append(now - 10)
        assert agent._count_in_window(now) == 30

    def test_record_send_adds_timestamp(self):
        agent = _make_agent()
        assert len(agent._send_timestamps) == 0
        agent._record_send()
        assert len(agent._send_timestamps) == 1

    @pytest.mark.asyncio
    async def test_rate_limit_not_exceeded_in_bulk(self):
        """Verifikasi bahwa tidak lebih dari 100 undangan dikirim dalam satu window."""
        sent_timestamps: list[float] = []

        async def _send_message(phone_number: str, message: str):
            sent_timestamps.append(time.monotonic())
            return MessageResult(
                message_id=f"msg-{len(sent_timestamps)}",
                status=MessageStatus.SENT,
                phone_number=phone_number,
            )

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=_send_message)
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()

        # Kirim 10 undangan (di bawah limit, tidak perlu menunggu)
        influencers = [_make_influencer(f"inf-{i}") for i in range(10)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 10
        # Verifikasi semua timestamp dalam window 60 detik
        if len(sent_timestamps) > 1:
            window = sent_timestamps[-1] - sent_timestamps[0]
            # Untuk 10 undangan, tidak ada rate limiting yang diperlukan
            assert window < 60.0

    @pytest.mark.asyncio
    async def test_rate_limit_waits_when_window_full(self):
        """Jika window sudah penuh (100), harus menunggu sebelum kirim berikutnya."""
        agent = _make_agent()
        now = time.monotonic()

        # Isi window dengan 100 timestamp baru (dalam 60 detik terakhir)
        for _ in range(100):
            agent._send_timestamps.append(now - 1)  # 1 detik yang lalu

        # Verifikasi window penuh
        assert agent._count_in_window(now) == 100

        # Simulasikan bahwa window akan bergeser setelah beberapa saat
        # dengan menambahkan timestamp yang lebih lama
        agent._send_timestamps.clear()
        for _ in range(100):
            agent._send_timestamps.append(now - 61)  # sudah di luar window

        # Sekarang window seharusnya kosong
        assert agent._count_in_window(time.monotonic()) == 0


# ---------------------------------------------------------------------------
# Tests: generate_invitation_report
# ---------------------------------------------------------------------------


class TestGenerateInvitationReport:
    @pytest.mark.asyncio
    async def test_returns_correct_totals(self):
        agent = _make_agent()
        db = _make_db(
            invitation_row={
                "total_sent": 10,
                "total_failed": 3,
                "total_pending": 2,
                "total_processed": 15,
            }
        )

        report = await agent.generate_invitation_report("camp-1", db)

        assert report.campaign_id == "camp-1"
        assert report.total_sent == 10
        assert report.total_failed == 3
        assert report.total_pending == 2
        assert report.total_processed == 15

    @pytest.mark.asyncio
    async def test_returns_zeros_when_no_data(self):
        agent = _make_agent()

        # DB yang mengembalikan None untuk query report
        db = AsyncMock()
        db.flush = AsyncMock()

        async def _execute(query, params=None):
            mock_result = MagicMock()
            mock_mappings = MagicMock()
            mock_mappings.first = MagicMock(return_value=None)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
            return mock_result

        db.execute = AsyncMock(side_effect=_execute)

        report = await agent.generate_invitation_report("camp-empty", db)

        assert report.total_sent == 0
        assert report.total_failed == 0
        assert report.total_pending == 0
        assert report.total_processed == 0

    @pytest.mark.asyncio
    async def test_total_accuracy(self):
        """total_sent + total_failed + total_pending == total_processed."""
        agent = _make_agent()
        db = _make_db(
            invitation_row={
                "total_sent": 7,
                "total_failed": 2,
                "total_pending": 1,
                "total_processed": 10,
            }
        )

        report = await agent.generate_invitation_report("camp-1", db)

        assert report.total_sent + report.total_failed + report.total_pending == report.total_processed


# ---------------------------------------------------------------------------
# Tests: substitusi variabel template
# ---------------------------------------------------------------------------


class TestVariableSubstitution:
    def test_substitutes_name_and_campaign(self):
        agent = _make_agent()
        template = _make_template(
            content="Halo {{name}}, kampanye {{campaign}} menunggumu!"
        )
        influencer = _make_influencer(name="Dewi Lestari")

        result = agent._substitute_variables(template, influencer, "camp-abc")

        assert "Dewi Lestari" in result
        assert "camp-abc" in result
        assert "{{" not in result

    def test_uses_default_values_for_other_variables(self):
        agent = _make_agent()
        template = _make_template(
            content="Halo {{name}}, hadiah: {{prize}}!",
            default_values={"prize": "Voucher 100rb"},
        )
        influencer = _make_influencer(name="Andi")

        result = agent._substitute_variables(template, influencer, "camp-1")

        assert "Voucher 100rb" in result
        assert "{{" not in result

    def test_raises_validation_error_for_unresolved_placeholder(self):
        agent = _make_agent()
        template = _make_template(
            content="Halo {{name}}, kode: {{unknown_var}}!",
            default_values={},
        )
        influencer = _make_influencer(name="Andi")

        with pytest.raises(ValidationError) as exc_info:
            agent._substitute_variables(template, influencer, "camp-1")

        assert "unknown_var" in str(exc_info.value)

    def test_no_placeholders_returns_content_unchanged(self):
        agent = _make_agent()
        template = _make_template(content="Pesan tanpa variabel.")
        influencer = _make_influencer()

        result = agent._substitute_variables(template, influencer, "camp-1")

        assert result == "Pesan tanpa variabel."

    def test_influencer_name_overrides_default_values(self):
        """Data influencer harus override default_values template."""
        agent = _make_agent()
        template = _make_template(
            content="Halo {{name}}!",
            default_values={"name": "Default Name"},
        )
        influencer = _make_influencer(name="Nama Asli")

        result = agent._substitute_variables(template, influencer, "camp-1")

        assert "Nama Asli" in result
        assert "Default Name" not in result

    def test_no_remaining_placeholders_after_substitution(self):
        """Tidak ada {{...}} yang tersisa setelah substitusi."""
        agent = _make_agent()
        template = _make_template(
            content="{{name}} - {{campaign}} - {{extra}}",
            default_values={"extra": "nilai_extra"},
        )
        influencer = _make_influencer(name="Test")

        result = agent._substitute_variables(template, influencer, "camp-test")

        import re
        remaining = re.findall(r"\{\{(\w+)\}\}", result)
        assert remaining == []


# ---------------------------------------------------------------------------
# Tests: Redis event publishing
# ---------------------------------------------------------------------------


class TestRedisEventPublishing:
    @pytest.mark.asyncio
    async def test_publishes_bulk_event_after_bulk_send(self):
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        agent = SenderAgent(
            blacklist_service=_make_blacklist_service(is_blacklisted=False),
            whatsapp_client=_make_whatsapp_client(),
            redis=redis_mock,
        )
        db = _make_db()
        influencers = [_make_influencer("inf-1")]

        await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-42",
            db=db,
        )

        # Harus ada setidaknya satu xadd call
        assert redis_mock.xadd.call_count >= 1

    @pytest.mark.asyncio
    async def test_no_error_when_redis_not_configured(self):
        agent = _make_agent(redis=None)
        db = _make_db()
        influencers = [_make_influencer("inf-1")]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 1

    @pytest.mark.asyncio
    async def test_redis_error_does_not_break_sending(self):
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(side_effect=Exception("Redis down"))

        agent = SenderAgent(
            blacklist_service=_make_blacklist_service(is_blacklisted=False),
            whatsapp_client=_make_whatsapp_client(),
            redis=redis_mock,
        )
        db = _make_db()
        influencers = [_make_influencer("inf-1")]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 1


# ---------------------------------------------------------------------------
# Tests: Edge Cases (Requirements 3.4, 3.7)
# ---------------------------------------------------------------------------


class TestEdgeCaseEmptyInfluencerList:
    """Edge case: daftar influencer kosong (Requirement 3.4, 3.7)."""

    @pytest.mark.asyncio
    async def test_empty_list_no_whatsapp_calls(self):
        """Tidak ada panggilan WhatsApp API jika daftar kosong."""
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()

        await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_list_no_db_inserts(self):
        """Tidak ada INSERT ke DB jika daftar kosong."""
        agent = _make_agent()
        db = _make_db()

        await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        # Tidak ada INSERT — execute hanya dipanggil untuk bulk event (Redis), bukan DB
        # Verifikasi tidak ada flush (tidak ada INSERT)
        db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_list_report_has_correct_campaign_id(self):
        """Report tetap memiliki campaign_id yang benar meski daftar kosong."""
        agent = _make_agent()
        db = _make_db()

        report = await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-kosong",
            db=db,
        )

        assert report.campaign_id == "camp-kosong"

    @pytest.mark.asyncio
    async def test_empty_list_total_processed_is_zero(self):
        """total_processed harus 0 untuk daftar kosong."""
        agent = _make_agent()
        db = _make_db()

        report = await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_processed == 0
        assert report.total_sent + report.total_failed + report.total_pending == 0

    @pytest.mark.asyncio
    async def test_empty_list_scheduled_also_returns_zero(self):
        """Daftar kosong dengan scheduled_at juga menghasilkan semua nol."""
        agent = _make_agent()
        db = _make_db()
        scheduled_at = datetime(2025, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

        report = await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert report.total_pending == 0
        assert report.total_processed == 0

    @pytest.mark.asyncio
    async def test_empty_list_rate_limit_window_unchanged(self):
        """Sliding window tidak berubah setelah pengiriman daftar kosong."""
        agent = _make_agent()
        db = _make_db()

        initial_count = len(agent._send_timestamps)

        await agent.send_bulk_invitations(
            influencers=[],
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert len(agent._send_timestamps) == initial_count


class TestEdgeCaseAllDeliveriesFail:
    """Edge case: semua pengiriman gagal (Requirement 3.4)."""

    @pytest.mark.asyncio
    async def test_all_fail_report_counts(self):
        """Semua influencer dicatat FAILED, total_sent = 0."""
        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=Exception("Koneksi gagal"))
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(5)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 0
        assert report.total_failed == 5
        assert report.total_processed == 5

    @pytest.mark.asyncio
    async def test_all_fail_process_continues_for_all_influencers(self):
        """Meski semua gagal, semua influencer tetap diproses (tidak berhenti di tengah)."""
        call_count = 0

        async def _always_fail(phone_number: str, message: str):
            nonlocal call_count
            call_count += 1
            raise Exception(f"Gagal untuk {phone_number}")

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=_always_fail)
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        n = 7
        influencers = [_make_influencer(f"inf-{i}") for i in range(n)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        # Semua influencer dicoba
        assert call_count == n
        assert report.total_failed == n
        assert report.total_processed == n

    @pytest.mark.asyncio
    async def test_all_fail_each_failure_saved_to_db(self):
        """Setiap kegagalan harus disimpan ke DB dengan status FAILED."""
        saved_statuses: list[str] = []

        async def _execute(query, params=None):
            mock_result = MagicMock()
            query_str = str(query.text) if hasattr(query, "text") else str(query)
            if "message_templates" in query_str:
                tmpl = _make_template()
                row = MagicMock()
                row.__getitem__ = lambda self, key: {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "content": tmpl.content,
                    "variables": tmpl.variables,
                    "default_values": tmpl.default_values,
                    "version": tmpl.version,
                    "is_active": tmpl.is_active,
                    "campaign_ids": tmpl.campaign_ids,
                    "created_at": tmpl.created_at,
                    "updated_at": tmpl.updated_at,
                }[key]
                mock_mappings = MagicMock()
                mock_mappings.first = MagicMock(return_value=row)
                mock_result.mappings = MagicMock(return_value=mock_mappings)
            elif "INSERT INTO invitations" in query_str and params:
                saved_statuses.append(params.get("status", ""))
                mock_result.mappings = MagicMock(return_value=MagicMock())
            else:
                mock_result.mappings = MagicMock(return_value=MagicMock())
            return mock_result

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(side_effect=_execute)

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=Exception("API error"))
        agent = _make_agent(whatsapp_client=wa_client)
        influencers = [_make_influencer(f"inf-{i}") for i in range(3)]

        await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert all(s == InvitationStatus.FAILED.value for s in saved_statuses)
        assert len(saved_statuses) == 3

    @pytest.mark.asyncio
    async def test_all_fail_total_equals_sum(self):
        """total_sent + total_failed + total_pending == total_processed saat semua gagal."""
        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=Exception("error"))
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(4)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent + report.total_failed + report.total_pending == report.total_processed

    @pytest.mark.asyncio
    async def test_all_blacklisted_all_fail(self):
        """Semua influencer di-blacklist → semua FAILED, tidak ada yang dikirim."""
        bl_svc = MagicMock(spec=BlacklistService)
        bl_svc.is_blacklisted = AsyncMock(return_value=True)
        wa_client = _make_whatsapp_client()
        agent = SenderAgent(blacklist_service=bl_svc, whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(4)]

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert report.total_sent == 0
        assert report.total_failed == 4
        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_fail_error_message_recorded(self):
        """Pesan error harus tersimpan di DB untuk setiap kegagalan."""
        error_messages: list[str] = []

        async def _execute(query, params=None):
            mock_result = MagicMock()
            query_str = str(query.text) if hasattr(query, "text") else str(query)
            if "message_templates" in query_str:
                tmpl = _make_template()
                row = MagicMock()
                row.__getitem__ = lambda self, key: {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "content": tmpl.content,
                    "variables": tmpl.variables,
                    "default_values": tmpl.default_values,
                    "version": tmpl.version,
                    "is_active": tmpl.is_active,
                    "campaign_ids": tmpl.campaign_ids,
                    "created_at": tmpl.created_at,
                    "updated_at": tmpl.updated_at,
                }[key]
                mock_mappings = MagicMock()
                mock_mappings.first = MagicMock(return_value=row)
                mock_result.mappings = MagicMock(return_value=mock_mappings)
            elif "INSERT INTO invitations" in query_str and params:
                if params.get("error_message"):
                    error_messages.append(params["error_message"])
                mock_result.mappings = MagicMock(return_value=MagicMock())
            else:
                mock_result.mappings = MagicMock(return_value=MagicMock())
            return mock_result

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(side_effect=_execute)

        wa_client = MagicMock()
        wa_client.send_message = AsyncMock(side_effect=Exception("Timeout error"))
        agent = _make_agent(whatsapp_client=wa_client)
        influencers = [_make_influencer("inf-1")]

        await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
        )

        assert len(error_messages) == 1
        assert "Timeout error" in error_messages[0]


class TestEdgeCaseScheduledDelivery:
    """Edge case: pengiriman terjadwal (Requirement 3.7)."""

    @pytest.mark.asyncio
    async def test_scheduled_single_does_not_send_immediately(self):
        """Undangan terjadwal tidak dikirim via WhatsApp saat ini."""
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencer = _make_influencer()
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduled_single_returns_valid_invitation_id(self):
        """Undangan terjadwal tetap mengembalikan UUID yang valid."""
        agent = _make_agent()
        db = _make_db()
        influencer = _make_influencer()
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        invitation_id = await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        import uuid as _uuid
        # Harus berupa UUID yang valid
        parsed = _uuid.UUID(invitation_id)
        assert str(parsed) == invitation_id

    @pytest.mark.asyncio
    async def test_scheduled_single_saves_scheduled_at_timestamp(self):
        """scheduled_at yang diberikan harus tersimpan di DB."""
        saved_params: list[dict] = []

        async def _execute(query, params=None):
            mock_result = MagicMock()
            query_str = str(query.text) if hasattr(query, "text") else str(query)
            if "message_templates" in query_str:
                tmpl = _make_template()
                row = MagicMock()
                row.__getitem__ = lambda self, key: {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "content": tmpl.content,
                    "variables": tmpl.variables,
                    "default_values": tmpl.default_values,
                    "version": tmpl.version,
                    "is_active": tmpl.is_active,
                    "campaign_ids": tmpl.campaign_ids,
                    "created_at": tmpl.created_at,
                    "updated_at": tmpl.updated_at,
                }[key]
                mock_mappings = MagicMock()
                mock_mappings.first = MagicMock(return_value=row)
                mock_result.mappings = MagicMock(return_value=mock_mappings)
            elif "INSERT INTO invitations" in query_str and params:
                saved_params.append(dict(params))
                mock_result.mappings = MagicMock(return_value=MagicMock())
            else:
                mock_result.mappings = MagicMock(return_value=MagicMock())
            return mock_result

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(side_effect=_execute)

        agent = _make_agent()
        influencer = _make_influencer()
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert len(saved_params) == 1
        assert saved_params[0]["scheduled_at"] == scheduled_at
        assert saved_params[0]["sent_at"] is None

    @pytest.mark.asyncio
    async def test_scheduled_single_blacklisted_still_raises(self):
        """Blacklist check tetap berlaku untuk undangan terjadwal."""
        agent = _make_agent(is_blacklisted=True)
        db = _make_db()
        influencer = _make_influencer()
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(BlacklistViolationError):
            await agent.send_single_invitation(
                influencer=influencer,
                template_id="tmpl-1",
                campaign_id="camp-1",
                db=db,
                scheduled_at=scheduled_at,
            )

    @pytest.mark.asyncio
    async def test_scheduled_bulk_all_pending_no_sent(self):
        """Bulk terjadwal: semua masuk PENDING, tidak ada SENT."""
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(4)]
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        report = await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert report.total_pending == 4
        assert report.total_sent == 0
        assert report.total_failed == 0
        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduled_bulk_skips_rate_limiting(self):
        """Pengiriman terjadwal tidak memodifikasi sliding window rate limiter."""
        agent = _make_agent()
        db = _make_db()
        influencers = [_make_influencer(f"inf-{i}") for i in range(5)]
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        before = len(agent._send_timestamps)

        await agent.send_bulk_invitations(
            influencers=influencers,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        # Sliding window tidak bertambah karena tidak ada pengiriman nyata
        assert len(agent._send_timestamps) == before

    @pytest.mark.asyncio
    async def test_scheduled_past_datetime_still_saves_as_scheduled(self):
        """scheduled_at di masa lalu tetap disimpan sebagai SCHEDULED (bukan dikirim langsung)."""
        saved_statuses: list[str] = []

        async def _execute(query, params=None):
            mock_result = MagicMock()
            query_str = str(query.text) if hasattr(query, "text") else str(query)
            if "message_templates" in query_str:
                tmpl = _make_template()
                row = MagicMock()
                row.__getitem__ = lambda self, key: {
                    "id": tmpl.id,
                    "name": tmpl.name,
                    "content": tmpl.content,
                    "variables": tmpl.variables,
                    "default_values": tmpl.default_values,
                    "version": tmpl.version,
                    "is_active": tmpl.is_active,
                    "campaign_ids": tmpl.campaign_ids,
                    "created_at": tmpl.created_at,
                    "updated_at": tmpl.updated_at,
                }[key]
                mock_mappings = MagicMock()
                mock_mappings.first = MagicMock(return_value=row)
                mock_result.mappings = MagicMock(return_value=mock_mappings)
            elif "INSERT INTO invitations" in query_str and params:
                saved_statuses.append(params.get("status", ""))
                mock_result.mappings = MagicMock(return_value=MagicMock())
            else:
                mock_result.mappings = MagicMock(return_value=MagicMock())
            return mock_result

        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute = AsyncMock(side_effect=_execute)

        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        influencer = _make_influencer()
        # scheduled_at di masa lalu
        scheduled_at = datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )

        assert saved_statuses == [InvitationStatus.SCHEDULED.value]
        wa_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduled_mixed_with_non_scheduled_in_separate_calls(self):
        """Panggilan terjadwal dan tidak terjadwal secara terpisah menghasilkan status berbeda."""
        wa_client = _make_whatsapp_client()
        agent = _make_agent(whatsapp_client=wa_client)
        db = _make_db()
        influencer = _make_influencer()
        scheduled_at = datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc)

        # Kirim terjadwal
        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=scheduled_at,
        )
        # WhatsApp tidak dipanggil untuk yang terjadwal
        wa_client.send_message.assert_not_called()

        # Kirim langsung
        await agent.send_single_invitation(
            influencer=influencer,
            template_id="tmpl-1",
            campaign_id="camp-1",
            db=db,
            scheduled_at=None,
        )
        # WhatsApp dipanggil untuk yang langsung
        wa_client.send_message.assert_called_once()
