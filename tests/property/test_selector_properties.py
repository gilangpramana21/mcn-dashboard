"""Property-based tests untuk SelectorAgent.

Validates: Requirements 6.2
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.selector_agent import SelectorAgent
from app.models.domain import (
    CriteriaWeights,
    Influencer,
    InfluencerStatus,
    SelectionCriteria,
)
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


def _make_influencer(
    influencer_id: str,
    follower_count: int,
    engagement_rate: float,
    blacklisted: bool = False,
) -> Influencer:
    return Influencer(
        id=influencer_id,
        tiktok_user_id=f"tiktok-{influencer_id}",
        name=f"Influencer {influencer_id}",
        phone_number="+6281234567890",
        follower_count=max(0, follower_count),
        engagement_rate=max(0.0, min(1.0, engagement_rate)),
        content_categories=["fashion"],
        location="Jakarta",
        blacklisted=blacklisted,
    )


def _make_blacklist_service(blacklisted_ids: Set[str]) -> BlacklistService:
    """Buat BlacklistService dengan mock DB yang mengembalikan blacklisted_ids."""
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


# ---------------------------------------------------------------------------
# Property 4: Hasil Seleksi Memenuhi Semua Kriteria
# ---------------------------------------------------------------------------


class TestProperty4SelectionMeetsCriteria:
    """Validates: Requirements 6.2 — setiap influencer dalam hasil memenuhi semua kriteria."""

    @given(
        follower_counts=st.lists(
            st.integers(min_value=0, max_value=10_000_000),
            min_size=1,
            max_size=20,
        ),
        min_followers=st.integers(min_value=0, max_value=100_000),
        engagement_rates=st.lists(
            st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_all_selected_influencers_meet_criteria(
        self,
        follower_counts: List[int],
        min_followers: int,
        engagement_rates: List[float],
    ):
        """Setiap influencer dalam hasil seleksi harus memenuhi min_followers."""
        async def _run():
            # Pastikan panjang list sama
            n = min(len(follower_counts), len(engagement_rates))
            follower_counts_n = follower_counts[:n]
            engagement_rates_n = engagement_rates[:n]

            influencers = [
                _make_influencer(
                    influencer_id=f"inf-{i}",
                    follower_count=follower_counts_n[i],
                    engagement_rate=engagement_rates_n[i],
                )
                for i in range(n)
            ]

            blacklist_service = _make_blacklist_service(set())
            selector = SelectorAgent(blacklist_service=blacklist_service)

            criteria = SelectionCriteria(
                id="crit-1",
                name="Test",
                min_followers=min_followers,
                criteria_weights=CriteriaWeights(),
            )

            result = await selector.select_influencers(
                criteria=criteria,
                campaign_id="camp-1",
                influencers=influencers,
            )

            for inf in result.influencers:
                assert inf.follower_count >= min_followers, (
                    f"Influencer {inf.id} follower_count={inf.follower_count} "
                    f"< min_followers={min_followers}"
                )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 5: Skor Relevansi Konsisten dan Terbatas
# ---------------------------------------------------------------------------


class TestProperty5RelevanceScoreConsistentAndBounded:
    """Validates: Requirements 6.2 — score selalu dalam [0.0, 1.0] dan deterministik."""

    @given(
        follower_count=st.integers(min_value=0, max_value=10_000_000),
        engagement_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_relevance_score_in_0_to_1(
        self,
        follower_count: int,
        engagement_rate: float,
    ):
        """For any influencer dan criteria, score selalu dalam [0.0, 1.0]."""
        async def _run():
            blacklist_service = _make_blacklist_service(set())
            selector = SelectorAgent(blacklist_service=blacklist_service)

            influencer = _make_influencer(
                influencer_id="inf-test",
                follower_count=follower_count,
                engagement_rate=engagement_rate,
            )

            criteria = SelectionCriteria(
                id="crit-1",
                name="Test",
                criteria_weights=CriteriaWeights(),
            )

            score = await selector.calculate_relevance_score(influencer, criteria)

            assert 0.0 <= score <= 1.0, (
                f"score={score} harus dalam [0.0, 1.0] untuk "
                f"follower_count={follower_count}, engagement_rate={engagement_rate}"
            )

        _run_async(_run())

    @given(
        follower_count=st.integers(min_value=0, max_value=10_000_000),
        engagement_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_relevance_score_deterministic(
        self,
        follower_count: int,
        engagement_rate: float,
    ):
        """For same input, calculate_relevance_score harus menghasilkan nilai yang sama."""
        async def _run():
            blacklist_service = _make_blacklist_service(set())
            selector = SelectorAgent(blacklist_service=blacklist_service)

            influencer = _make_influencer(
                influencer_id="inf-test",
                follower_count=follower_count,
                engagement_rate=engagement_rate,
            )

            criteria = SelectionCriteria(
                id="crit-1",
                name="Test",
                criteria_weights=CriteriaWeights(),
            )

            score1 = await selector.calculate_relevance_score(influencer, criteria)
            score2 = await selector.calculate_relevance_score(influencer, criteria)

            assert score1 == score2, (
                f"Score tidak deterministik: {score1} != {score2}"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 26: Seleksi Mengecualikan Blacklist
# ---------------------------------------------------------------------------


class TestProperty26SelectionExcludesBlacklist:
    """Validates: Requirements 6.2 — tidak ada influencer blacklisted dalam hasil."""

    @given(
        influencer_count=st.integers(min_value=1, max_value=20),
        blacklist_count=st.integers(min_value=0, max_value=10),
        follower_count=st.integers(min_value=0, max_value=10_000_000),
        engagement_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_no_blacklisted_influencer_in_result(
        self,
        influencer_count: int,
        blacklist_count: int,
        follower_count: int,
        engagement_rate: float,
    ):
        """Tidak ada influencer blacklisted dalam hasil seleksi."""
        async def _run():
            actual_blacklist_count = min(blacklist_count, influencer_count)
            blacklisted_ids = {f"inf-{i}" for i in range(actual_blacklist_count)}

            influencers = [
                _make_influencer(
                    influencer_id=f"inf-{i}",
                    follower_count=follower_count,
                    engagement_rate=engagement_rate,
                    blacklisted=(f"inf-{i}" in blacklisted_ids),
                )
                for i in range(influencer_count)
            ]

            blacklist_service = _make_blacklist_service(blacklisted_ids)
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

            result_ids = {inf.id for inf in result.influencers}
            for blacklisted_id in blacklisted_ids:
                assert blacklisted_id not in result_ids, (
                    f"Influencer blacklisted {blacklisted_id!r} tidak boleh ada dalam hasil"
                )

        _run_async(_run())
