"""Property-based tests untuk ClassifierAgent.

Validates: Requirements 11.2
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.classifier_agent import ClassifierAgent, ClassificationResult
from app.models.domain import FeedbackCategory, InfluencerFeedback


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
        return mock_result

    db.execute = _execute
    return db


def _make_feedback(raw_message: str) -> InfluencerFeedback:
    return InfluencerFeedback(
        id=str(uuid.uuid4()),
        campaign_id="camp-1",
        influencer_id="inf-1",
        invitation_id="inv-1",
        raw_message=raw_message,
        received_at=datetime.now(timezone.utc),
    )


_VALID_CATEGORIES = set(FeedbackCategory)


# ---------------------------------------------------------------------------
# Property 16: Kategori Valid
# ---------------------------------------------------------------------------


class TestProperty16ValidCategory:
    """Validates: Requirements 11.2 — hasil klasifikasi selalu salah satu dari 4 FeedbackCategory."""

    @given(raw_message=st.text(max_size=200))
    @settings(max_examples=50)
    def test_classification_always_valid_category(self, raw_message: str):
        """For any raw_message, hasil klasifikasi selalu salah satu dari 4 FeedbackCategory."""
        async def _run():
            db = _make_db()
            agent = ClassifierAgent()
            feedback = _make_feedback(raw_message)

            result = await agent.classify_feedback(feedback, db)

            assert result.category in _VALID_CATEGORIES, (
                f"Kategori {result.category!r} bukan salah satu dari {_VALID_CATEGORIES}"
            )
            assert isinstance(result, ClassificationResult)

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 17: Routing Manual Review
# ---------------------------------------------------------------------------


class TestProperty17ManualReviewRouting:
    """Validates: Requirements 11.2 — NEEDS_MORE_INFO atau confidence < 0.8 → requires_manual_review = True."""

    @given(raw_message=st.text(max_size=200))
    @settings(max_examples=50)
    def test_needs_more_info_requires_manual_review(self, raw_message: str):
        """Jika kategori NEEDS_MORE_INFO atau confidence < 0.8, requires_manual_review harus True."""
        async def _run():
            db = _make_db()
            agent = ClassifierAgent()
            feedback = _make_feedback(raw_message)

            result = await agent.classify_feedback(feedback, db)

            if (
                result.category == FeedbackCategory.NEEDS_MORE_INFO
                or result.confidence_score < 0.8
            ):
                assert result.requires_manual_review is True, (
                    f"requires_manual_review harus True untuk kategori={result.category}, "
                    f"confidence={result.confidence_score}"
                )

        _run_async(_run())

    @given(raw_message=st.text(max_size=200))
    @settings(max_examples=50)
    def test_confidence_score_in_valid_range(self, raw_message: str):
        """confidence_score harus selalu dalam [0.0, 1.0]."""
        async def _run():
            db = _make_db()
            agent = ClassifierAgent()
            feedback = _make_feedback(raw_message)

            result = await agent.classify_feedback(feedback, db)

            assert 0.0 <= result.confidence_score <= 1.0, (
                f"confidence_score={result.confidence_score} harus dalam [0.0, 1.0]"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 18: Konsistensi Ringkasan
# ---------------------------------------------------------------------------


class TestProperty18SummaryConsistency:
    """Validates: Requirements 11.2 — total == accepted + rejected + needs_more_info + no_response."""

    @given(
        accepted=st.integers(min_value=0, max_value=100),
        rejected=st.integers(min_value=0, max_value=100),
        needs_more_info=st.integers(min_value=0, max_value=100),
        no_response=st.integers(min_value=0, max_value=100),
    )
    @settings(max_examples=50)
    def test_summary_total_equals_sum_of_categories(
        self,
        accepted: int,
        rejected: int,
        needs_more_info: int,
        no_response: int,
    ):
        """total == accepted + rejected + needs_more_info + no_response."""
        async def _run():
            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                q = str(query)
                mock_result = MagicMock()
                mock_mappings = MagicMock()

                if "GROUP BY classification" in q:
                    rows = [
                        {"classification": FeedbackCategory.ACCEPTED.value, "cnt": accepted},
                        {"classification": FeedbackCategory.REJECTED.value, "cnt": rejected},
                        {"classification": FeedbackCategory.NEEDS_MORE_INFO.value, "cnt": needs_more_info},
                        {"classification": FeedbackCategory.NO_RESPONSE.value, "cnt": no_response},
                    ]
                    mock_mappings.all.return_value = rows
                elif "requires_manual_review" in q:
                    mock_mappings.first.return_value = {"cnt": 0}
                else:
                    mock_mappings.all.return_value = []
                    mock_mappings.first.return_value = None

                mock_result.mappings.return_value = mock_mappings
                return mock_result

            db.execute = _execute

            agent = ClassifierAgent()
            summary = await agent.get_classification_summary("camp-1", db)

            expected_total = accepted + rejected + needs_more_info + no_response
            assert summary.total == expected_total, (
                f"total={summary.total} harus == {expected_total} "
                f"(accepted={accepted} + rejected={rejected} + "
                f"needs_more_info={needs_more_info} + no_response={no_response})"
            )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 19: Update Status REJECTED
# ---------------------------------------------------------------------------


class TestProperty19RejectedStatusUpdate:
    """Validates: Requirements 11.2 — klasifikasi Menolak → UPDATE influencers dipanggil."""

    @given(
        raw_message=st.sampled_from([
            "tidak bisa",
            "tidak mau",
            "maaf tidak",
            "nggak",
            "no",
            "tolak",
        ])
    )
    @settings(max_examples=50)
    def test_rejected_classification_updates_influencer_status(self, raw_message: str):
        """Klasifikasi Menolak harus memanggil UPDATE influencers."""
        async def _run():
            executed_queries: List[str] = []

            db = AsyncMock()
            db.flush = AsyncMock()

            async def _execute(query, params=None):
                executed_queries.append(str(query))
                mock_result = MagicMock()
                mock_mappings = MagicMock()
                mock_mappings.first.return_value = None
                mock_mappings.all.return_value = []
                mock_result.mappings.return_value = mock_mappings
                return mock_result

            db.execute = _execute

            agent = ClassifierAgent()
            feedback = _make_feedback(raw_message)

            result = await agent.classify_feedback(feedback, db)

            if result.category == FeedbackCategory.REJECTED:
                # Verifikasi bahwa UPDATE influencers dipanggil
                update_influencer_called = any(
                    "UPDATE influencers" in q and "status" in q
                    for q in executed_queries
                )
                assert update_influencer_called, (
                    f"UPDATE influencers harus dipanggil untuk kategori REJECTED, "
                    f"queries: {executed_queries}"
                )

        _run_async(_run())
