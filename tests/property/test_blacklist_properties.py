"""Property-based tests untuk BlacklistService.

Validates: Requirements 5.2
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.exceptions import BlacklistViolationError
from app.models.domain import Influencer, InfluencerStatus
from app.services.blacklist_service import BlacklistService


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


def _make_db_with_blacklist(blacklisted_ids: set) -> AsyncMock:
    """Buat mock DB yang melacak blacklist dalam memory."""
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
        elif "INSERT INTO blacklist" in q and params:
            influencer_id = params.get("influencer_id", "")
            blacklisted_ids.add(influencer_id)
            mock_result.first.return_value = None
        else:
            mock_result.first.return_value = None

        mock_mappings.first.return_value = None
        mock_mappings.all.return_value = []
        mock_result.mappings.return_value = mock_mappings
        return mock_result

    db.execute = _execute
    return db


def _make_influencer(
    influencer_id: str,
    blacklisted: bool = False,
) -> Influencer:
    return Influencer(
        id=influencer_id,
        tiktok_user_id=f"tiktok-{influencer_id}",
        name=f"Influencer {influencer_id}",
        phone_number="+6281234567890",
        follower_count=10000,
        engagement_rate=0.05,
        content_categories=["fashion"],
        location="Jakarta",
        blacklisted=blacklisted,
    )


# ---------------------------------------------------------------------------
# Property 25: Blacklist Round-Trip
# ---------------------------------------------------------------------------


class TestProperty25BlacklistRoundTrip:
    """Validates: Requirements 5.2 — setelah add_to_blacklist, is_blacklisted harus True."""

    @given(
        influencer_id=st.text(min_size=1, max_size=50),
        reason=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=50)
    def test_add_to_blacklist_then_is_blacklisted_true(
        self,
        influencer_id: str,
        reason: str,
    ):
        """For any influencer_id dan reason, setelah add_to_blacklist, is_blacklisted harus True."""
        async def _run():
            blacklisted_ids: set = set()
            db = _make_db_with_blacklist(blacklisted_ids)
            service = BlacklistService(db)

            # Tambahkan ke blacklist
            await service.add_to_blacklist(
                influencer_id=influencer_id,
                reason=reason,
                added_by_user_id="user-1",
            )

            # Verifikasi is_blacklisted mengembalikan True
            result = await service.is_blacklisted(influencer_id)
            assert result is True, (
                f"is_blacklisted({influencer_id!r}) harus True setelah add_to_blacklist"
            )

        _run_async(_run())

    @given(
        influencer_id=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_is_blacklisted_false_before_adding(self, influencer_id: str):
        """is_blacklisted harus False sebelum add_to_blacklist dipanggil."""
        async def _run():
            blacklisted_ids: set = set()
            db = _make_db_with_blacklist(blacklisted_ids)
            service = BlacklistService(db)

            result = await service.is_blacklisted(influencer_id)
            assert result is False, (
                f"is_blacklisted({influencer_id!r}) harus False sebelum ditambahkan"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 26: Seleksi Mengecualikan Blacklist
# ---------------------------------------------------------------------------


class TestProperty26SelectionExcludesBlacklist:
    """Validates: Requirements 5.2 — select_influencers tidak mengembalikan yang blacklisted."""

    @given(
        influencer_ids=st.lists(
            st.text(min_size=1, max_size=20),
            min_size=1,
            max_size=10,
            unique=True,
        ),
        blacklist_indices=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=0,
            max_size=5,
        ),
    )
    @settings(max_examples=50)
    def test_blacklisted_influencers_excluded_from_selection(
        self,
        influencer_ids: List[str],
        blacklist_indices: List[int],
    ):
        """Influencer yang blacklisted tidak boleh ada dalam hasil seleksi."""
        from app.agents.selector_agent import SelectorAgent
        from app.models.domain import CriteriaWeights, SelectionCriteria

        async def _run():
            # Tentukan mana yang blacklisted
            valid_indices = [i for i in blacklist_indices if i < len(influencer_ids)]
            blacklisted_set = {influencer_ids[i] for i in valid_indices}

            blacklisted_ids_db: set = set(blacklisted_set)
            db = _make_db_with_blacklist(blacklisted_ids_db)
            blacklist_service = BlacklistService(db)

            # Buat influencer list
            influencers = [
                _make_influencer(
                    influencer_id=inf_id,
                    blacklisted=(inf_id in blacklisted_set),
                )
                for inf_id in influencer_ids
            ]

            selector = SelectorAgent(blacklist_service=blacklist_service)
            criteria = SelectionCriteria(
                id="crit-1",
                name="Test",
                criteria_weights=CriteriaWeights(),
            )

            result = await selector.select_influencers(
                criteria=criteria,
                campaign_id="camp-1",
                influencers=influencers,
            )

            # Tidak ada influencer blacklisted dalam hasil
            result_ids = {inf.id for inf in result.influencers}
            for blacklisted_id in blacklisted_set:
                assert blacklisted_id not in result_ids, (
                    f"Influencer blacklisted {blacklisted_id!r} tidak boleh ada dalam hasil seleksi"
                )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 27: Pengiriman Menolak Influencer Blacklist
# ---------------------------------------------------------------------------


class TestProperty27SendingRejectsBlacklistedInfluencer:
    """Validates: Requirements 5.2 — send_single_invitation raise BlacklistViolationError untuk blacklisted."""

    @given(
        influencer_id=st.text(min_size=1, max_size=50),
        reason=st.text(min_size=1, max_size=200),
    )
    @settings(max_examples=50)
    def test_send_invitation_raises_for_blacklisted_influencer(
        self,
        influencer_id: str,
        reason: str,
    ):
        """For any influencer blacklisted, send_single_invitation raise BlacklistViolationError."""
        from app.agents.sender_agent import SenderAgent

        async def _run():
            blacklisted_ids: set = {influencer_id}
            db = _make_db_with_blacklist(blacklisted_ids)
            blacklist_service = BlacklistService(db)

            sender = SenderAgent(blacklist_service=blacklist_service)

            influencer = _make_influencer(influencer_id=influencer_id, blacklisted=True)

            with pytest.raises(BlacklistViolationError):
                await sender.send_single_invitation(
                    influencer=influencer,
                    template_id="template-1",
                    campaign_id="camp-1",
                    db=db,
                )

        _run_async(_run())
