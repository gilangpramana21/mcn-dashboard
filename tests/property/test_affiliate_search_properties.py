"""Property-based tests untuk ContactService.

Validates: Requirements 16.3
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.services.contact_service import get_contact_channel


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


def _make_db_with_phone(phone_number: Optional[str]) -> AsyncMock:
    """Buat mock DB yang mengembalikan phone_number tertentu untuk affiliate."""
    db = AsyncMock()
    db.flush = AsyncMock()

    async def _execute(query, params=None):
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (phone_number,) if phone_number else None
        return mock_result

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# Property 40: Hasil Pencarian Memenuhi Kriteria
# ---------------------------------------------------------------------------


class TestProperty40ContactChannelCriteria:
    """Validates: Requirements 16.3 — get_contact_channel mengembalikan kanal yang benar."""

    @given(
        affiliate_id=st.text(min_size=1, max_size=50),
        phone_number=st.one_of(
            st.none(),
            st.from_regex(r'\+62[0-9]{9,12}', fullmatch=True),
        ),
    )
    @settings(max_examples=50)
    def test_contact_channel_whatsapp_if_phone_exists(
        self,
        affiliate_id: str,
        phone_number: Optional[str],
    ):
        """get_contact_channel mengembalikan 'whatsapp' jika phone_number ada, 'seller_center_chat' jika tidak."""
        async def _run():
            db = _make_db_with_phone(phone_number)
            channel = await get_contact_channel(affiliate_id, db)

            if phone_number:
                assert channel == "whatsapp", (
                    f"channel harus 'whatsapp' jika phone_number={phone_number!r} ada"
                )
            else:
                assert channel == "seller_center_chat", (
                    f"channel harus 'seller_center_chat' jika phone_number=None"
                )

        _run_async(_run())

    @given(
        affiliate_id=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_contact_channel_seller_center_when_no_phone(self, affiliate_id: str):
        """get_contact_channel mengembalikan 'seller_center_chat' jika tidak ada phone_number."""
        async def _run():
            db = _make_db_with_phone(None)
            channel = await get_contact_channel(affiliate_id, db)
            assert channel == "seller_center_chat"

        _run_async(_run())

    @given(
        affiliate_id=st.text(min_size=1, max_size=50),
        phone_number=st.from_regex(r'\+62[0-9]{9,12}', fullmatch=True),
    )
    @settings(max_examples=50)
    def test_contact_channel_whatsapp_when_phone_exists(
        self,
        affiliate_id: str,
        phone_number: str,
    ):
        """get_contact_channel mengembalikan 'whatsapp' jika phone_number ada."""
        async def _run():
            db = _make_db_with_phone(phone_number)
            channel = await get_contact_channel(affiliate_id, db)
            assert channel == "whatsapp"

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 42: Pemilihan Kanal Konsisten
# ---------------------------------------------------------------------------


class TestProperty42ContactChannelConsistent:
    """Validates: Requirements 16.3 — contact_channel selalu konsisten dengan keberadaan phone_number."""

    @given(
        affiliate_id=st.text(min_size=1, max_size=50),
        phone_number=st.one_of(
            st.none(),
            st.from_regex(r'\+62[0-9]{9,12}', fullmatch=True),
        ),
    )
    @settings(max_examples=50)
    def test_contact_channel_consistent_with_phone_number(
        self,
        affiliate_id: str,
        phone_number: Optional[str],
    ):
        """contact_channel selalu konsisten dengan keberadaan phone_number."""
        async def _run():
            db = _make_db_with_phone(phone_number)

            # Panggil dua kali — harus konsisten
            channel1 = await get_contact_channel(affiliate_id, db)
            channel2 = await get_contact_channel(affiliate_id, db)

            assert channel1 == channel2, (
                f"contact_channel tidak konsisten: {channel1} != {channel2}"
            )

            # Verifikasi konsistensi dengan keberadaan phone_number
            if phone_number:
                assert channel1 == "whatsapp"
            else:
                assert channel1 == "seller_center_chat"

        _run_async(_run())
