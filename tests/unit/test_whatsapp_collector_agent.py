"""Unit tests untuk WhatsAppCollectorAgent."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.whatsapp_collector_agent import WhatsAppCollectorAgent
from app.exceptions import InvalidPhoneNumberError
from app.models.domain import (
    WhatsAppCollectionMethod,
    WhatsAppCollectionRecord,
    WhatsAppCollectionStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent() -> WhatsAppCollectorAgent:
    """Buat agent dengan TikTokAPIClient yang di-mock."""
    agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
    agent._tiktok = MagicMock()
    return agent


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=MagicMock())
    db.flush = AsyncMock()
    return db


def _make_record(
    affiliate_id: str = "aff-1",
    influencer_id: str = "inf-1",
    phone_number: str = "+6281234567890",
    method: WhatsAppCollectionMethod = WhatsAppCollectionMethod.OFFICIAL_ICON,
    status: WhatsAppCollectionStatus = WhatsAppCollectionStatus.COLLECTED,
) -> WhatsAppCollectionRecord:
    now = datetime.utcnow()
    return WhatsAppCollectionRecord(
        id="rec-1",
        affiliate_id=affiliate_id,
        influencer_id=influencer_id,
        phone_number=phone_number,
        method=method,
        status=status,
        collected_at=now,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# normalize_to_e164
# ---------------------------------------------------------------------------


class TestNormalizeToE164:
    def setup_method(self):
        self.agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

    def test_format_08xxx(self):
        assert self.agent.normalize_to_e164("0812345678") == "+62812345678"

    def test_format_plus628xxx(self):
        assert self.agent.normalize_to_e164("+6281234567890") == "+6281234567890"

    def test_format_628xxx_no_plus(self):
        assert self.agent.normalize_to_e164("6281234567890") == "+6281234567890"

    def test_format_wa_me(self):
        assert self.agent.normalize_to_e164("wa.me/6281234567890") == "+6281234567890"

    def test_format_wa_colon_space(self):
        assert self.agent.normalize_to_e164("WA: 0812345678") == "+62812345678"

    def test_format_wa_colon_no_space(self):
        assert self.agent.normalize_to_e164("WA:0812345678") == "+62812345678"

    def test_format_wa_space(self):
        assert self.agent.normalize_to_e164("WA 0812345678") == "+62812345678"

    def test_strips_dashes_and_spaces(self):
        # Nomor dengan spasi/tanda hubung setelah ekstraksi digit
        assert self.agent.normalize_to_e164("0812-3456-7890") == "+62812345678" + "90"

    def test_wa_me_short_number(self):
        # wa.me/6281234 → digits "6281234" → strip "62" prefix → "81234" → "+6281234"
        assert self.agent.normalize_to_e164("wa.me/6281234") == "+6281234"

    def test_plus628_prefix_preserved(self):
        result = self.agent.normalize_to_e164("+628111222333")
        assert result.startswith("+62")
        assert result == "+628111222333"


# ---------------------------------------------------------------------------
# validate_whatsapp_number
# ---------------------------------------------------------------------------


class TestValidateWhatsappNumber:
    def setup_method(self):
        self.agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

    # Valid cases
    def test_valid_9_digits_after_62(self):
        assert self.agent.validate_whatsapp_number("+62812345678") is True

    def test_valid_12_digits_after_62(self):
        assert self.agent.validate_whatsapp_number("+628123456789012") is False  # 13 digit → invalid

    def test_valid_standard_number(self):
        assert self.agent.validate_whatsapp_number("+6281234567890") is True

    def test_valid_min_length(self):
        # +62 + 1 digit non-zero + 8 digit = 9 digit setelah +62 → valid
        assert self.agent.validate_whatsapp_number("+62812345678") is True

    def test_valid_max_length(self):
        # +62 + 12 digit = valid
        assert self.agent.validate_whatsapp_number("+621234567890123") is False  # 13 digit → invalid
        assert self.agent.validate_whatsapp_number("+62123456789012") is True   # 12 digit → valid

    # Invalid cases
    def test_invalid_no_plus(self):
        assert self.agent.validate_whatsapp_number("6281234567890") is False

    def test_invalid_wrong_country_code(self):
        assert self.agent.validate_whatsapp_number("+1234567890") is False

    def test_invalid_too_short(self):
        assert self.agent.validate_whatsapp_number("+6281234567") is False  # hanya 8 digit setelah +62

    def test_invalid_starts_with_zero_after_62(self):
        assert self.agent.validate_whatsapp_number("+62012345678") is False

    def test_invalid_empty_string(self):
        assert self.agent.validate_whatsapp_number("") is False

    def test_invalid_letters(self):
        assert self.agent.validate_whatsapp_number("+62abc123456") is False


# ---------------------------------------------------------------------------
# parse_bio_for_whatsapp
# ---------------------------------------------------------------------------


class TestParseBioForWhatsapp:
    def setup_method(self):
        self.agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

    def test_wa_me_format(self):
        bio = "Hubungi saya di wa.me/6281234567890"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6281234567890"

    def test_plus62_format(self):
        bio = "WA: +6281234567890 untuk kolaborasi"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "+6281234567890"

    def test_wa_colon_space_format(self):
        bio = "Kontak: WA: 0812345678"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_08xxx_format(self):
        bio = "Nomor saya 0812345678 ya"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_628xxx_format(self):
        bio = "Hubungi 6281234567890"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6281234567890"

    def test_empty_bio_returns_none(self):
        assert self.agent.parse_bio_for_whatsapp("") is None

    def test_none_like_empty_string(self):
        assert self.agent.parse_bio_for_whatsapp("") is None

    def test_bio_without_number_returns_none(self):
        bio = "Saya seorang content creator yang suka fashion dan beauty."
        assert self.agent.parse_bio_for_whatsapp(bio) is None

    def test_returns_first_match(self):
        bio = "WA: 0812345678 atau 0898765432"
        result = self.agent.parse_bio_for_whatsapp(bio)
        # Harus mengembalikan yang pertama ditemukan
        assert result is not None

    def test_wa_me_takes_priority_over_plain(self):
        bio = "wa.me/6281234567890 juga bisa 0898765432"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6281234567890"

    # --- Edge cases: bio kosong ---

    def test_whitespace_only_bio_returns_none(self):
        assert self.agent.parse_bio_for_whatsapp("   ") is None

    def test_newline_only_bio_returns_none(self):
        assert self.agent.parse_bio_for_whatsapp("\n\n\t") is None

    def test_bio_with_only_emoji_returns_none(self):
        assert self.agent.parse_bio_for_whatsapp("✨🌟💫🎉") is None

    def test_bio_with_only_url_no_wa_returns_none(self):
        assert self.agent.parse_bio_for_whatsapp("https://instagram.com/myprofile") is None

    # --- Edge cases: bio dengan beberapa nomor ---

    def test_bio_with_multiple_numbers_returns_first_wa_me(self):
        bio = "wa.me/6281111111111 atau wa.me/6282222222222"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6281111111111"

    def test_bio_with_multiple_plain_numbers_returns_first(self):
        bio = "Bisa hubungi 0811111111 atau 0822222222"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0811111111"

    def test_bio_with_wa_me_and_plain_number_prefers_wa_me(self):
        # wa.me pattern has higher priority in _WA_PATTERNS
        bio = "0812345678 atau cek wa.me/6289876543210"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6289876543210"

    def test_bio_with_plus62_and_plain_prefers_plus62(self):
        # +628xxx pattern comes before plain 08xxx
        bio = "0812345678 juga +6289876543210"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "+6289876543210"

    def test_bio_with_three_different_formats(self):
        bio = "WA: 0811111111 | +6282222222222 | wa.me/6283333333333"
        result = self.agent.parse_bio_for_whatsapp(bio)
        # wa.me is highest priority
        assert result == "6283333333333"

    # --- Edge cases: format tidak standar ---

    def test_wa_uppercase(self):
        bio = "WA:0812345678"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_wa_lowercase(self):
        bio = "wa:0812345678"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_wa_mixed_case(self):
        bio = "Wa: 0812345678"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_number_embedded_in_sentence(self):
        bio = "Untuk kolaborasi silakan DM atau WA ke 0812345678 ya!"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_number_with_text_prefix_no_wa_label(self):
        bio = "Nomor: 0812345678"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "0812345678"

    def test_628_without_plus_in_bio(self):
        bio = "Hubungi di 6281234567890 untuk info lebih lanjut"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result == "6281234567890"

    def test_number_too_short_not_matched(self):
        # 081234 — hanya 6 digit setelah 08, terlalu pendek untuk pola 08[1-9][0-9]{7,10}
        bio = "Hubungi 081234"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result is None

    def test_number_starting_with_080_not_matched(self):
        # 080 bukan prefix valid Indonesia (harus 08[1-9])
        bio = "Hubungi 0801234567"
        result = self.agent.parse_bio_for_whatsapp(bio)
        assert result is None


# ---------------------------------------------------------------------------
# monitor_chat_reply — timeout edge cases
# ---------------------------------------------------------------------------


class TestMonitorChatReplyTimeout:
    @pytest.mark.asyncio
    async def test_returns_number_before_timeout(self):
        """Jika balasan ditemukan sebelum deadline, kembalikan nomor."""
        agent = _make_agent()
        agent._tiktok.get_chat_replies = AsyncMock(
            return_value=[{"text": "WA saya 0812345678"}]
        )

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await agent.monitor_chat_reply(
                "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
            )

        assert result == "0812345678"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_reply_within_timeout(self):
        """Jika tidak ada balasan sampai deadline, kembalikan None."""
        agent = _make_agent()
        agent._tiktok.get_chat_replies = AsyncMock(return_value=[])

        call_count = 0

        async def fake_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                # Simulasikan deadline terlampaui dengan patch datetime
                raise StopAsyncIteration

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with patch(
                "app.agents.whatsapp_collector_agent.datetime"
            ) as mock_dt:
                # Buat deadline sudah terlampaui setelah 2 iterasi
                now_val = datetime(2024, 1, 1, 0, 0, 0)
                deadline_val = datetime(2024, 1, 3, 0, 0, 0)  # +48 jam
                # Setelah 2 panggilan utcnow(), kembalikan waktu setelah deadline
                mock_dt.utcnow.side_effect = [
                    now_val,       # untuk hitung deadline
                    now_val,       # iterasi 1: masih sebelum deadline
                    deadline_val,  # iterasi 2: sudah melewati deadline → keluar loop
                ]
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                result = await agent.monitor_chat_reply(
                    "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
                )

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_exactly_at_48_hours(self):
        """Timeout tepat di batas 48 jam — tidak boleh ada balasan yang dikembalikan."""
        agent = _make_agent()
        agent._tiktok.get_chat_replies = AsyncMock(return_value=[])

        base_time = datetime(2024, 6, 1, 12, 0, 0)
        exactly_at_deadline = datetime(2024, 6, 3, 12, 0, 0)  # tepat +48 jam

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "app.agents.whatsapp_collector_agent.datetime"
            ) as mock_dt:
                # Saat pertama: hitung deadline; saat kedua: sudah tepat di deadline (tidak < deadline)
                mock_dt.utcnow.side_effect = [
                    base_time,
                    exactly_at_deadline,  # deadline = base + 48h; now >= deadline → keluar
                ]
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                result = await agent.monitor_chat_reply(
                    "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
                )

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_one_second_before_48_hours_still_polls(self):
        """Satu detik sebelum deadline, masih harus polling."""
        agent = _make_agent()
        agent._tiktok.get_chat_replies = AsyncMock(
            return_value=[{"text": "nomor saya 0812345678"}]
        )

        base_time = datetime(2024, 6, 1, 12, 0, 0)
        one_second_before = datetime(2024, 6, 3, 11, 59, 59)  # 1 detik sebelum deadline

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "app.agents.whatsapp_collector_agent.datetime"
            ) as mock_dt:
                mock_dt.utcnow.side_effect = [
                    base_time,
                    one_second_before,  # masih sebelum deadline → poll
                ]
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                result = await agent.monitor_chat_reply(
                    "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
                )

        assert result == "0812345678"

    @pytest.mark.asyncio
    async def test_api_error_during_polling_continues(self):
        """Error saat polling tidak menghentikan loop — lanjut ke iterasi berikutnya."""
        agent = _make_agent()
        call_count = 0

        async def flaky_replies(affiliate_id, msg_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return [{"text": "WA: 0812345678"}]

        agent._tiktok.get_chat_replies = flaky_replies

        base_time = datetime(2024, 6, 1, 12, 0, 0)
        before_deadline = datetime(2024, 6, 1, 12, 5, 0)
        before_deadline2 = datetime(2024, 6, 1, 12, 10, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "app.agents.whatsapp_collector_agent.datetime"
            ) as mock_dt:
                mock_dt.utcnow.side_effect = [
                    base_time,
                    before_deadline,
                    before_deadline2,
                ]
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                result = await agent.monitor_chat_reply(
                    "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
                )

        assert result == "0812345678"

    @pytest.mark.asyncio
    async def test_reply_without_number_continues_polling(self):
        """Balasan tanpa nomor WA tidak dianggap sukses — lanjut polling."""
        agent = _make_agent()
        call_count = 0

        async def replies_then_number(affiliate_id, msg_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [{"text": "Halo, ada yang bisa dibantu?"}]
            return [{"text": "WA saya 0812345678"}]

        agent._tiktok.get_chat_replies = replies_then_number

        base_time = datetime(2024, 6, 1, 12, 0, 0)
        t1 = datetime(2024, 6, 1, 12, 5, 0)
        t2 = datetime(2024, 6, 1, 12, 10, 0)

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch(
                "app.agents.whatsapp_collector_agent.datetime"
            ) as mock_dt:
                mock_dt.utcnow.side_effect = [base_time, t1, t2]
                mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

                result = await agent.monitor_chat_reply(
                    "aff-1", "msg-1", timeout_hours=48, _poll_interval_seconds=1
                )

        assert result == "0812345678"


# ---------------------------------------------------------------------------
# check_official_whatsapp_icon
# ---------------------------------------------------------------------------


class TestCheckOfficialWhatsappIcon:
    @pytest.mark.asyncio
    async def test_found_in_whatsapp_number_field(self):
        agent = _make_agent()
        agent._tiktok.get_affiliate_profile = AsyncMock(
            return_value={"whatsapp_number": "6281234567890"}
        )
        result = await agent.check_official_whatsapp_icon("aff-1")
        assert result == "6281234567890"

    @pytest.mark.asyncio
    async def test_found_in_social_links_whatsapp(self):
        agent = _make_agent()
        agent._tiktok.get_affiliate_profile = AsyncMock(
            return_value={"social_links": {"whatsapp": "+6281234567890"}}
        )
        result = await agent.check_official_whatsapp_icon("aff-1")
        assert result == "+6281234567890"

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        agent = _make_agent()
        agent._tiktok.get_affiliate_profile = AsyncMock(
            return_value={"name": "Influencer A", "bio": "No WA here"}
        )
        result = await agent.check_official_whatsapp_icon("aff-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_api_error_returns_none(self):
        agent = _make_agent()
        agent._tiktok.get_affiliate_profile = AsyncMock(side_effect=Exception("API error"))
        result = await agent.check_official_whatsapp_icon("aff-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_whatsapp_number_takes_priority_over_social_links(self):
        agent = _make_agent()
        agent._tiktok.get_affiliate_profile = AsyncMock(
            return_value={
                "whatsapp_number": "6281111111111",
                "social_links": {"whatsapp": "+6282222222222"},
            }
        )
        result = await agent.check_official_whatsapp_icon("aff-1")
        assert result == "6281111111111"


# ---------------------------------------------------------------------------
# collect_whatsapp_number — orkestrasi
# ---------------------------------------------------------------------------


class TestCollectWhatsappNumber:
    def _make_agent_with_mocks(
        self,
        icon_result: Optional[str] = None,
        bio_result: Optional[str] = None,
        chat_message_id: str = "msg-1",
        chat_reply_result: Optional[str] = None,
        profile_bio: str = "",
    ) -> tuple[WhatsAppCollectorAgent, list]:
        """Buat agent dengan semua metode di-mock, dan call_log untuk verifikasi urutan."""
        agent = _make_agent()
        call_log = []

        async def mock_icon(aid):
            call_log.append("icon")
            return icon_result

        async def mock_get_profile(aid):
            call_log.append("profile")
            return {"bio": profile_bio}

        async def mock_send_chat(aid):
            call_log.append("chat_send")
            return chat_message_id

        async def mock_monitor_reply(aid, msg_id, timeout_hours=48, _poll_interval_seconds=300):
            call_log.append("chat_monitor")
            return chat_reply_result

        async def mock_get_influencer_id(affiliate_id, db):
            return "inf-1"

        agent.check_official_whatsapp_icon = mock_icon
        agent._tiktok.get_affiliate_profile = mock_get_profile
        agent.send_chat_request = mock_send_chat
        agent.monitor_chat_reply = mock_monitor_reply
        agent._get_influencer_id = mock_get_influencer_id

        return agent, call_log

    @pytest.mark.asyncio
    async def test_stops_at_icon_if_successful(self):
        agent, call_log = self._make_agent_with_mocks(icon_result="+6281234567890")
        db = _make_db()

        result = await agent.collect_whatsapp_number("aff-1", db)

        assert result.status == WhatsAppCollectionStatus.COLLECTED
        assert result.method == WhatsAppCollectionMethod.OFFICIAL_ICON
        assert result.phone_number == "+6281234567890"
        assert "icon" in call_log
        assert "chat_send" not in call_log

    @pytest.mark.asyncio
    async def test_falls_through_to_bio_if_icon_fails(self):
        agent, call_log = self._make_agent_with_mocks(
            icon_result=None,
            profile_bio="Hubungi WA: 0812345678",
        )
        db = _make_db()

        result = await agent.collect_whatsapp_number("aff-1", db)

        assert result.status == WhatsAppCollectionStatus.COLLECTED
        assert result.method == WhatsAppCollectionMethod.BIO_PARSING
        assert "icon" in call_log
        assert "profile" in call_log
        assert "chat_send" not in call_log

    @pytest.mark.asyncio
    async def test_falls_through_to_chat_if_icon_and_bio_fail(self):
        agent, call_log = self._make_agent_with_mocks(
            icon_result=None,
            profile_bio="Tidak ada nomor di sini",
            chat_reply_result="0812345678",
        )
        db = _make_db()

        result = await agent.collect_whatsapp_number("aff-1", db)

        assert result.status == WhatsAppCollectionStatus.COLLECTED
        assert result.method == WhatsAppCollectionMethod.CHAT_REPLY
        assert "icon" in call_log
        assert "chat_send" in call_log
        assert "chat_monitor" in call_log

    @pytest.mark.asyncio
    async def test_marks_unavailable_if_all_methods_fail(self):
        agent, call_log = self._make_agent_with_mocks(
            icon_result=None,
            profile_bio="",
            chat_reply_result=None,
        )
        db = _make_db()

        result = await agent.collect_whatsapp_number("aff-1", db)

        assert result.status == WhatsAppCollectionStatus.UNAVAILABLE
        assert result.phone_number is None
        assert result.method is None

    @pytest.mark.asyncio
    async def test_icon_result_normalized_and_validated(self):
        """Nomor dari ikon harus dinormalisasi sebelum disimpan."""
        agent, _ = self._make_agent_with_mocks(icon_result="0812345678")
        db = _make_db()

        result = await agent.collect_whatsapp_number("aff-1", db)

        assert result.status == WhatsAppCollectionStatus.COLLECTED
        assert result.phone_number == "+62812345678"


# ---------------------------------------------------------------------------
# save_collection_record
# ---------------------------------------------------------------------------


class TestSaveCollectionRecord:
    @pytest.mark.asyncio
    async def test_valid_number_saved_successfully(self):
        agent = _make_agent()
        db = _make_db()

        record = await agent.save_collection_record(
            affiliate_id="aff-1",
            influencer_id="inf-1",
            phone_number="+6281234567890",
            method=WhatsAppCollectionMethod.BIO_PARSING,
            db=db,
        )

        assert record.phone_number == "+6281234567890"
        assert record.method == WhatsAppCollectionMethod.BIO_PARSING
        assert record.status == WhatsAppCollectionStatus.COLLECTED
        assert record.collected_at is not None
        assert record.affiliate_id == "aff-1"
        assert record.influencer_id == "inf-1"

    @pytest.mark.asyncio
    async def test_invalid_number_raises_error(self):
        agent = _make_agent()
        db = _make_db()

        with pytest.raises(InvalidPhoneNumberError):
            await agent.save_collection_record(
                affiliate_id="aff-1",
                influencer_id="inf-1",
                phone_number="invalid-number",
                method=WhatsAppCollectionMethod.BIO_PARSING,
                db=db,
            )

    @pytest.mark.asyncio
    async def test_number_without_plus62_raises_error(self):
        agent = _make_agent()
        db = _make_db()

        with pytest.raises(InvalidPhoneNumberError):
            await agent.save_collection_record(
                affiliate_id="aff-1",
                influencer_id="inf-1",
                phone_number="0812345678",  # belum dinormalisasi
                method=WhatsAppCollectionMethod.OFFICIAL_ICON,
                db=db,
            )

    @pytest.mark.asyncio
    async def test_db_execute_called(self):
        agent = _make_agent()
        db = _make_db()

        await agent.save_collection_record(
            affiliate_id="aff-1",
            influencer_id="inf-1",
            phone_number="+6281234567890",
            method=WhatsAppCollectionMethod.CHAT_REPLY,
            db=db,
        )

        # Harus ada 2 execute: INSERT record + UPDATE influencers
        assert db.execute.call_count == 2
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_collected_at_not_in_future(self):
        agent = _make_agent()
        db = _make_db()
        before = datetime.utcnow()

        record = await agent.save_collection_record(
            affiliate_id="aff-1",
            influencer_id="inf-1",
            phone_number="+6281234567890",
            method=WhatsAppCollectionMethod.OFFICIAL_ICON,
            db=db,
        )

        assert record.collected_at >= before
        assert record.collected_at <= datetime.utcnow()


# ---------------------------------------------------------------------------
# mark_unavailable
# ---------------------------------------------------------------------------


class TestMarkUnavailable:
    @pytest.mark.asyncio
    async def test_status_unavailable_saved(self):
        agent = _make_agent()
        db = _make_db()

        await agent.mark_unavailable("aff-1", "inf-1", db)

        db.execute.assert_called_once()
        db.flush.assert_called_once()

        # Verifikasi parameter yang dikirim ke DB mengandung status unavailable
        call_args = db.execute.call_args
        params = call_args[0][1]
        assert params["status"] == WhatsAppCollectionStatus.UNAVAILABLE.value
        assert params["affiliate_id"] == "aff-1"
        assert params["influencer_id"] == "inf-1"

    @pytest.mark.asyncio
    async def test_mark_unavailable_does_not_raise(self):
        agent = _make_agent()
        db = _make_db()

        # Tidak boleh raise exception
        await agent.mark_unavailable("aff-999", "inf-999", db)
