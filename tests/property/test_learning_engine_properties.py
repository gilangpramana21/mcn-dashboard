"""Property-based tests untuk LearningEngine.

Validates: Requirements 13.1, 13.2, 13.4, 13.5, 13.6
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

from app.agents.learning_engine import LearningEngine
from app.models.domain import ModelType, ModelVersion, SelectionCriteria


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
    return db


def _make_execute_result(rows: List[Dict[str, Any]]) -> MagicMock:
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = rows
    mock_mappings.first.return_value = rows[0] if rows else None
    mock_result.mappings.return_value = mock_mappings
    return mock_result


def _make_execute_result_first(row: Optional[Dict[str, Any]]) -> MagicMock:
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = row
    mock_mappings.all.return_value = [row] if row else []
    mock_result.mappings.return_value = mock_mappings
    return mock_result


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_retrain_db(next_version: int, prev_accuracy: Optional[float] = None) -> AsyncMock:
    """Buat mock DB yang mengembalikan next_version tertentu untuk retrain."""
    db = _make_db()

    async def _execute(query, params=None):
        q = str(query)
        if "COALESCE(MAX(version)" in q:
            return _make_execute_result_first({"next_version": next_version})
        elif "accuracy_after" in q and "ORDER BY version DESC" in q:
            if prev_accuracy is not None:
                return _make_execute_result_first({"accuracy_after": prev_accuracy})
            return _make_execute_result_first(None)
        elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
            return _make_execute_result([])
        elif "influencer_feedback" in q:
            return _make_execute_result([])
        else:
            return MagicMock()

    db.execute = _execute
    return db


# ---------------------------------------------------------------------------
# Property 43: Versi Model Bertambah Monoton
# Feature: tiktok-influencer-marketing-agent, Property 43: Versi Model Bertambah Monoton
# ---------------------------------------------------------------------------


class TestProperty43VersionMonotonicallyIncreases:
    """Validates: Requirements 13.1, 13.4"""

    @given(
        versions=st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=2,
            max_size=10,
        ).filter(lambda vs: all(vs[i] < vs[i + 1] for i in range(len(vs) - 1)))
    )
    @settings(max_examples=50)
    def test_selection_model_version_monotonically_increases(self, versions: List[int]):
        """For any sequence of retrain calls, setiap versi baru harus > versi sebelumnya."""
        async def _run():
            engine = LearningEngine()
            collected_versions: List[int] = []

            for next_ver in versions:
                db = _make_retrain_db(next_version=next_ver)
                result = await engine.retrain_selection_model(db)
                collected_versions.append(result.version)

            # Verifikasi monoton meningkat
            for i in range(len(collected_versions) - 1):
                assert collected_versions[i] < collected_versions[i + 1], (
                    f"Versi tidak monoton: {collected_versions[i]} >= {collected_versions[i + 1]}"
                )

        _run_async(_run())

    @given(
        versions=st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=2,
            max_size=10,
        ).filter(lambda vs: all(vs[i] < vs[i + 1] for i in range(len(vs) - 1)))
    )
    @settings(max_examples=50)
    def test_classifier_model_version_monotonically_increases(self, versions: List[int]):
        """For any sequence of retrain calls pada classifier, versi harus monoton meningkat."""
        async def _run():
            engine = LearningEngine()
            collected_versions: List[int] = []

            for next_ver in versions:
                db = _make_retrain_db(next_version=next_ver)
                result = await engine.retrain_classifier_model(db)
                collected_versions.append(result.version)

            for i in range(len(collected_versions) - 1):
                assert collected_versions[i] < collected_versions[i + 1], (
                    f"Versi classifier tidak monoton: {collected_versions[i]} >= {collected_versions[i + 1]}"
                )

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 44: Retraining Menghasilkan ModelVersion Lengkap
# Feature: tiktok-influencer-marketing-agent, Property 44: Retraining Menghasilkan ModelVersion Lengkap
# ---------------------------------------------------------------------------


class TestProperty44RetrainingProducesCompleteModelVersion:
    """Validates: Requirements 13.1, 13.2"""

    @given(
        data_size=st.integers(min_value=0, max_value=500),
        prev_accuracy=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        next_version=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_selection_model_version_has_all_required_fields(
        self,
        data_size: int,
        prev_accuracy: Optional[float],
        next_version: int,
    ):
        """ModelVersion dari retrain_selection_model harus memiliki semua field wajib tidak null."""
        async def _run():
            engine = LearningEngine()

            async def _execute(query, params=None):
                q = str(query)
                if "COALESCE(MAX(version)" in q:
                    return _make_execute_result_first({"next_version": next_version})
                elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                    if prev_accuracy is not None:
                        return _make_execute_result_first({"accuracy_after": prev_accuracy})
                    return _make_execute_result_first(None)
                elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                    rows = [
                        {
                            "influencer_id": f"inf-{i}",
                            "avg_gmv": 100000.0,
                            "avg_conversion_rate": 0.05,
                            "campaign_count": 2,
                        }
                        for i in range(data_size)
                    ]
                    return _make_execute_result(rows)
                else:
                    return MagicMock()

            db = _make_db()
            db.execute = _execute

            result = await engine.retrain_selection_model(db)

            # Semua field wajib tidak boleh None
            assert result.id is not None, "id tidak boleh None"
            assert result.model_type is not None, "model_type tidak boleh None"
            assert result.version is not None, "version tidak boleh None"
            assert result.accuracy_after is not None, "accuracy_after tidak boleh None"
            assert result.trained_at is not None, "trained_at tidak boleh None"
            assert result.training_data_size is not None, "training_data_size tidak boleh None"

            # Tipe data harus benar
            assert isinstance(result.id, str)
            assert isinstance(result.model_type, ModelType)
            assert isinstance(result.version, int)
            assert isinstance(result.accuracy_after, float)
            assert isinstance(result.trained_at, datetime)
            assert isinstance(result.training_data_size, int)

        _run_async(_run())

    @given(
        data_size=st.integers(min_value=0, max_value=500),
        prev_accuracy=st.one_of(st.none(), st.floats(min_value=0.0, max_value=1.0, allow_nan=False)),
        next_version=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_classifier_model_version_has_all_required_fields(
        self,
        data_size: int,
        prev_accuracy: Optional[float],
        next_version: int,
    ):
        """ModelVersion dari retrain_classifier_model harus memiliki semua field wajib tidak null."""
        async def _run():
            engine = LearningEngine()

            async def _execute(query, params=None):
                q = str(query)
                if "COALESCE(MAX(version)" in q:
                    return _make_execute_result_first({"next_version": next_version})
                elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                    if prev_accuracy is not None:
                        return _make_execute_result_first({"accuracy_after": prev_accuracy})
                    return _make_execute_result_first(None)
                elif "influencer_feedback" in q:
                    rows = [
                        {
                            "classification": "Menerima",
                            "raw_message": f"pesan {i}",
                            "confidence_score": 0.9,
                        }
                        for i in range(data_size)
                    ]
                    return _make_execute_result(rows)
                else:
                    return MagicMock()

            db = _make_db()
            db.execute = _execute

            result = await engine.retrain_classifier_model(db)

            assert result.id is not None
            assert result.model_type is not None
            assert result.version is not None
            assert result.accuracy_after is not None
            assert result.trained_at is not None
            assert result.training_data_size is not None

            assert isinstance(result.id, str)
            assert isinstance(result.model_type, ModelType)
            assert isinstance(result.version, int)
            assert isinstance(result.accuracy_after, float)
            assert isinstance(result.trained_at, datetime)
            assert isinstance(result.training_data_size, int)

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 45: Confidence Score Rekomendasi dalam Rentang Valid
# Feature: tiktok-influencer-marketing-agent, Property 45: Confidence Score Rekomendasi dalam Rentang Valid
# ---------------------------------------------------------------------------


class TestProperty45ConfidenceScoreInValidRange:
    """Validates: Requirements 13.5, 13.6"""

    @given(
        campaign_count=st.integers(min_value=0, max_value=100),
        avg_conversion_rate=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_confidence_score_always_in_0_to_1(
        self,
        campaign_count: int,
        avg_conversion_rate: float,
    ):
        """For any campaign_count dalam [0, 100], confidence_score harus dalam [0.0, 1.0]."""
        async def _run():
            engine = LearningEngine()

            outcome_rows = [
                {
                    "influencer_id": "inf-test",
                    "avg_gmv": 500000.0,
                    "avg_conversion_rate": avg_conversion_rate,
                    "campaign_count": campaign_count,
                    "campaign_ids": ["camp-1"],
                }
            ]

            async def _execute(query, params=None):
                return _make_execute_result(outcome_rows)

            db = _make_db()
            db.execute = _execute

            criteria = SelectionCriteria(id="crit-1", name="Test")
            recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

            assert len(recommendations) == 1
            rec = recommendations[0]

            assert 0.0 <= rec.confidence_score <= 1.0, (
                f"confidence_score={rec.confidence_score} harus dalam [0.0, 1.0] "
                f"untuk campaign_count={campaign_count}"
            )

        _run_async(_run())

    @given(
        avg_conversion_rate=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_predicted_conversion_rate_clamped_to_0_1(self, avg_conversion_rate: float):
        """For any avg_conversion_rate dalam [0.0, 2.0], predicted_conversion_rate harus di-clamp ke [0.0, 1.0]."""
        async def _run():
            engine = LearningEngine()

            outcome_rows = [
                {
                    "influencer_id": "inf-test",
                    "avg_gmv": 100000.0,
                    "avg_conversion_rate": avg_conversion_rate,
                    "campaign_count": 5,
                    "campaign_ids": ["camp-1"],
                }
            ]

            async def _execute(query, params=None):
                return _make_execute_result(outcome_rows)

            db = _make_db()
            db.execute = _execute

            criteria = SelectionCriteria(id="crit-1", name="Test")
            recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

            assert len(recommendations) == 1
            rec = recommendations[0]

            assert 0.0 <= rec.predicted_conversion_rate <= 1.0, (
                f"predicted_conversion_rate={rec.predicted_conversion_rate} harus dalam [0.0, 1.0] "
                f"untuk avg_conversion_rate={avg_conversion_rate}"
            )

        _run_async(_run())

    @given(
        campaign_count=st.integers(min_value=0, max_value=100),
        avg_conversion_rate=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_both_scores_in_valid_range_simultaneously(
        self,
        campaign_count: int,
        avg_conversion_rate: float,
    ):
        """confidence_score dan predicted_conversion_rate keduanya harus dalam [0.0, 1.0]."""
        async def _run():
            engine = LearningEngine()

            outcome_rows = [
                {
                    "influencer_id": "inf-test",
                    "avg_gmv": 200000.0,
                    "avg_conversion_rate": avg_conversion_rate,
                    "campaign_count": campaign_count,
                    "campaign_ids": ["camp-1"],
                }
            ]

            async def _execute(query, params=None):
                return _make_execute_result(outcome_rows)

            db = _make_db()
            db.execute = _execute

            criteria = SelectionCriteria(id="crit-1", name="Test")
            recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

            for rec in recommendations:
                assert 0.0 <= rec.confidence_score <= 1.0
                assert 0.0 <= rec.predicted_conversion_rate <= 1.0

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 46: Retraining Tidak Mengubah State Kampanye Aktif
# Feature: tiktok-influencer-marketing-agent, Property 46: Retraining Tidak Mengubah State Kampanye Aktif
# ---------------------------------------------------------------------------


class TestProperty46RetrainingDoesNotAffectActiveCampaigns:
    """Validates: Requirements 13.1, 13.2"""

    @given(
        campaign_id=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"),
            min_size=1,
            max_size=36,
        ),
        next_version=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_retrain_selection_model_does_not_update_campaigns(
        self,
        campaign_id: str,
        next_version: int,
    ):
        """retrain_selection_model tidak boleh memanggil UPDATE campaigns."""
        async def _run():
            engine = LearningEngine()
            executed_queries: List[str] = []

            async def _execute(query, params=None):
                q = str(query)
                executed_queries.append(q)
                if "COALESCE(MAX(version)" in q:
                    return _make_execute_result_first({"next_version": next_version})
                elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                    return _make_execute_result_first(None)
                elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                    return _make_execute_result([])
                else:
                    return MagicMock()

            db = _make_db()
            db.execute = _execute

            await engine.retrain_selection_model(db)

            # Tidak boleh ada query UPDATE campaigns
            for q in executed_queries:
                q_lower = q.lower()
                assert not (
                    "update" in q_lower and "campaigns" in q_lower
                ), f"retrain_selection_model tidak boleh mengeksekusi UPDATE campaigns, tapi ditemukan: {q}"

        _run_async(_run())

    @given(
        campaign_id=st.text(
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"),
            min_size=1,
            max_size=36,
        ),
        next_version=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=50)
    def test_retrain_classifier_model_does_not_update_campaigns(
        self,
        campaign_id: str,
        next_version: int,
    ):
        """retrain_classifier_model tidak boleh memanggil UPDATE campaigns."""
        async def _run():
            engine = LearningEngine()
            executed_queries: List[str] = []

            async def _execute(query, params=None):
                q = str(query)
                executed_queries.append(q)
                if "COALESCE(MAX(version)" in q:
                    return _make_execute_result_first({"next_version": next_version})
                elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                    return _make_execute_result_first(None)
                elif "influencer_feedback" in q:
                    return _make_execute_result([])
                else:
                    return MagicMock()

            db = _make_db()
            db.execute = _execute

            await engine.retrain_classifier_model(db)

            for q in executed_queries:
                q_lower = q.lower()
                assert not (
                    "update" in q_lower and "campaigns" in q_lower
                ), f"retrain_classifier_model tidak boleh mengeksekusi UPDATE campaigns, tapi ditemukan: {q}"

        _run_async(_run())
