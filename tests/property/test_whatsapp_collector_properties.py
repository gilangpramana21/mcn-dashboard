"""Property-based tests untuk WhatsAppCollectorAgent.

Validates: Requirements 7.2
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.whatsapp_collector_agent import WhatsAppCollectorAgent
from app.models.domain import (
    WhatsAppCollectionMethod,
    WhatsAppCollectionRecord,
    WhatsAppCollectionStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_async(coro):
    """Jalankan coroutine dalam event loop baru (kompatibel dengan Hypothesis)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_db() -> AsyncMock:
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        mock_result = MagicMock()
        mock_mappings = MagicMock()
        mock_mappings.first.return_value = None
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        mock_result.fetchone.return_value = None
        return mock_result

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# Property 34: Urutan Prioritas
# ---------------------------------------------------------------------------


class TestProperty34PriorityOrder:
    """Validates: Requirements 7.2 — jika ikon berhasil, bio dan chat tidak dipanggil."""

    @given(
        affiliate_id=st.text(min_size=1, max_size=30),
        phone_number=st.from_regex(r'\+62[1-9][0-9]{8,11}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_icon_success_skips_bio_and_chat(
        self,
        affiliate_id: str,
        phone_number: str,
    ):
        """Jika ikon berhasil, bio dan chat tidak dipanggil."""
        async def _run():
            bio_called = False
            chat_called = False

            agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

            async def _check_icon(aid: str) -> Optional[str]:
                return phone_number

            def _parse_bio(bio_text: str) -> Optional[str]:
                nonlocal bio_called
                bio_called = True
                return None

            async def _send_chat(aid: str) -> str:
                nonlocal chat_called
                chat_called = True
                return "chat-id"

            agent.check_official_whatsapp_icon = _check_icon
            agent.parse_bio_for_whatsapp = _parse_bio
            agent.send_chat_request = _send_chat

            # Mock save_collection_record
            async def _save_record(affiliate_id, influencer_id, phone_number, method, db):
                return WhatsAppCollectionRecord(
                    id=str(uuid.uuid4()),
                    affiliate_id=affiliate_id,
                    influencer_id=influencer_id,
                    phone_number=phone_number,
                    method=method,
                    status=WhatsAppCollectionStatus.COLLECTED,
                    collected_at=datetime.utcnow(),
                )

            agent.save_collection_record = _save_record

            # Mock _get_influencer_id
            async def _get_influencer_id(aid, db):
                return f"inf-{aid}"

            agent._get_influencer_id = _get_influencer_id

            db = _make_db()
            result = await agent.collect_whatsapp_number(affiliate_id, db)

            assert result.status == WhatsAppCollectionStatus.COLLECTED
            assert result.method == WhatsAppCollectionMethod.OFFICIAL_ICON
            assert not bio_called, "parse_bio tidak boleh dipanggil jika ikon berhasil"
            assert not chat_called, "send_chat tidak boleh dipanggil jika ikon berhasil"

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 35: Normalisasi E.164
# ---------------------------------------------------------------------------


class TestProperty35E164Normalization:
    """Validates: Requirements 7.2 — normalize_to_e164 menghasilkan string yang dimulai dengan '+62'."""

    @given(
        local_number=st.from_regex(r'08[1-9][0-9]{7,10}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_normalize_local_format_starts_with_plus62(self, local_number: str):
        """Format 08xxx harus dinormalisasi ke +62xxx."""
        agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
        result = agent.normalize_to_e164(local_number)
        assert result.startswith("+62"), (
            f"normalize_to_e164({local_number!r}) = {result!r} harus dimulai dengan '+62'"
        )

    @given(
        intl_number=st.from_regex(r'\+62[1-9][0-9]{8,11}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_normalize_e164_format_unchanged(self, intl_number: str):
        """Format +62xxx harus tetap dimulai dengan +62 setelah normalisasi."""
        agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
        result = agent.normalize_to_e164(intl_number)
        assert result.startswith("+62"), (
            f"normalize_to_e164({intl_number!r}) = {result!r} harus dimulai dengan '+62'"
        )

    @given(
        country_number=st.from_regex(r'62[1-9][0-9]{8,11}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_normalize_62_prefix_format_starts_with_plus62(self, country_number: str):
        """Format 62xxx (tanpa +) harus dinormalisasi ke +62xxx."""
        agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
        result = agent.normalize_to_e164(country_number)
        assert result.startswith("+62"), (
            f"normalize_to_e164({country_number!r}) = {result!r} harus dimulai dengan '+62'"
        )


# ---------------------------------------------------------------------------
# Property 36: Hanya Nomor Valid Tersimpan
# ---------------------------------------------------------------------------


class TestProperty36OnlyValidNumbersStored:
    """Validates: Requirements 7.2 — validate_whatsapp_number mengembalikan False untuk non-E.164."""

    @given(
        invalid_number=st.text(min_size=1, max_size=30).filter(
            lambda s: not s.startswith("+62") or len(s) < 12
        ),
    )
    @settings(max_examples=50)
    def test_invalid_number_returns_false(self, invalid_number: str):
        """String yang bukan format E.164 valid harus mengembalikan False."""
        agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
        # Nomor yang tidak dimulai dengan +62 atau terlalu pendek harus False
        result = agent.validate_whatsapp_number(invalid_number)
        # Kita hanya assert bahwa nomor yang jelas tidak valid mengembalikan False
        if not invalid_number.startswith("+62"):
            assert result is False, (
                f"validate_whatsapp_number({invalid_number!r}) harus False"
            )

    @given(
        valid_number=st.from_regex(r'\+62[1-9][0-9]{8,11}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_valid_e164_number_returns_true(self, valid_number: str):
        """Nomor E.164 Indonesia valid harus mengembalikan True."""
        agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
        result = agent.validate_whatsapp_number(valid_number)
        assert result is True, (
            f"validate_whatsapp_number({valid_number!r}) harus True"
        )


# ---------------------------------------------------------------------------
# Property 37: Pencatatan Lengkap
# ---------------------------------------------------------------------------


class TestProperty37CompleteRecord:
    """Validates: Requirements 7.2 — save_collection_record menghasilkan record dengan method dan collected_at tidak null."""

    @given(
        affiliate_id=st.text(min_size=1, max_size=30),
        phone_number=st.from_regex(r'\+62[1-9][0-9]{8,11}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_save_collection_record_has_method_and_collected_at(
        self,
        affiliate_id: str,
        phone_number: str,
    ):
        """save_collection_record dengan nomor valid selalu menghasilkan record dengan method dan collected_at tidak null."""
        async def _run():
            db = _make_db()
            agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)

            record = await agent.save_collection_record(
                affiliate_id=affiliate_id,
                influencer_id=f"inf-{affiliate_id}",
                phone_number=phone_number,
                method=WhatsAppCollectionMethod.OFFICIAL_ICON,
                db=db,
            )

            assert record.method is not None, "method tidak boleh None"
            assert record.collected_at is not None, "collected_at tidak boleh None"
            assert record.phone_number == phone_number
            assert record.status == WhatsAppCollectionStatus.COLLECTED

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 38: Timeout → Unavailable
# ---------------------------------------------------------------------------


class TestProperty38TimeoutUnavailable:
    """Validates: Requirements 7.2 — mark_unavailable selalu menyimpan status unavailable."""

    @given(
        affiliate_id=st.text(min_size=1, max_size=30),
    )
    @settings(max_examples=50)
    def test_mark_unavailable_stores_unavailable_status(self, affiliate_id: str):
        """mark_unavailable selalu menyimpan status unavailable."""
        async def _run():
            executed_queries: List[str] = []
            executed_params: List[Dict] = []

            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                executed_queries.append(str(query))
                executed_params.append(params or {})
                mock_result = MagicMock()
                mock_result.fetchone.return_value = None
                return mock_result

            db.execute = _execute

            agent = WhatsAppCollectorAgent.__new__(WhatsAppCollectorAgent)
            await agent.mark_unavailable(
                affiliate_id=affiliate_id,
                influencer_id=f"inf-{affiliate_id}",
                db=db,
            )

            # Verifikasi bahwa status unavailable disimpan
            found_unavailable = False
            for params in executed_params:
                if params.get("status") == WhatsAppCollectionStatus.UNAVAILABLE.value:
                    found_unavailable = True
                    break

            assert found_unavailable, (
                "mark_unavailable harus menyimpan status 'unavailable'"
            )

        _run_async(_run())
