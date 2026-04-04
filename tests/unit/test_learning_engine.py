"""Unit tests for LearningEngine."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.learning_engine import LearningEngine
from app.models.domain import (
    CampaignOutcome,
    ModelType,
    ModelVersion,
    SelectionCriteria,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db() -> AsyncMock:
    """Buat mock AsyncSession."""
    db = AsyncMock()
    db.flush = AsyncMock()
    return db


def _make_execute_result(rows: List[Dict[str, Any]]) -> MagicMock:
    """Buat mock result dari db.execute() dengan rows tertentu."""
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.all.return_value = rows
    mock_mappings.first.return_value = rows[0] if rows else None
    mock_result.mappings.return_value = mock_mappings
    return mock_result


def _make_execute_result_first(row: Optional[Dict[str, Any]]) -> MagicMock:
    """Buat mock result dari db.execute() untuk query yang menggunakan .first()."""
    mock_result = MagicMock()
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = row
    mock_mappings.all.return_value = [row] if row else []
    mock_result.mappings.return_value = mock_mappings
    return mock_result


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Tests: record_campaign_outcome
# ---------------------------------------------------------------------------


class TestRecordCampaignOutcome:
    @pytest.mark.asyncio
    async def test_record_saves_outcomes_to_db(self):
        """record_campaign_outcome harus menyimpan CampaignOutcome ke DB."""
        engine = LearningEngine()
        db = _make_db()

        # Mock invitations query
        inv_rows = [
            {"influencer_id": "inf-1", "status": "SENT"},
            {"influencer_id": "inf-2", "status": "ACCEPTED"},
        ]
        # Mock metrics query
        metrics_rows = [
            {
                "influencer_id": "inf-1",
                "total_gmv": 500000.0,
                "avg_conversion_rate": 0.05,
                "content_count": 3,
            },
            {
                "influencer_id": "inf-2",
                "total_gmv": 1200000.0,
                "avg_conversion_rate": 0.08,
                "content_count": 5,
            },
        ]

        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # invitations query
                return _make_execute_result(inv_rows)
            elif call_count == 2:
                # metrics query
                return _make_execute_result(metrics_rows)
            else:
                # INSERT queries
                return MagicMock()

        db.execute = _execute

        await engine.record_campaign_outcome("camp-1", db)

        # flush harus dipanggil
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_skips_if_no_invitations(self):
        """record_campaign_outcome harus skip jika tidak ada undangan."""
        engine = LearningEngine()
        db = _make_db()

        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            return _make_execute_result([])

        db.execute = _execute

        await engine.record_campaign_outcome("camp-empty", db)

        # flush tidak dipanggil karena tidak ada data
        db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_record_marks_accepted_correctly(self):
        """Influencer dengan status ACCEPTED harus ditandai accepted=True."""
        engine = LearningEngine()
        db = _make_db()

        inv_rows = [
            {"influencer_id": "inf-1", "status": "ACCEPTED"},
            {"influencer_id": "inf-2", "status": "PENDING"},
        ]

        inserted_params: List[dict] = []
        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_execute_result(inv_rows)
            elif call_count == 2:
                return _make_execute_result([])
            else:
                if params and "accepted" in params:
                    inserted_params.append(dict(params))
                return MagicMock()

        db.execute = _execute

        await engine.record_campaign_outcome("camp-1", db)

        # Verifikasi accepted flag
        accepted_map = {p["influencer_id"]: p["accepted"] for p in inserted_params}
        assert accepted_map.get("inf-1") is True
        assert accepted_map.get("inf-2") is False


# ---------------------------------------------------------------------------
# Tests: retrain_selection_model
# ---------------------------------------------------------------------------


class TestRetrainSelectionModel:
    @pytest.mark.asyncio
    async def test_retrain_creates_new_model_version(self):
        """retrain_selection_model harus membuat ModelVersion baru."""
        engine = LearningEngine()
        db = _make_db()

        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 2})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first({"accuracy_after": 0.75})
            elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                return _make_execute_result([
                    {
                        "influencer_id": "inf-1",
                        "avg_gmv": 500000.0,
                        "avg_conversion_rate": 0.05,
                        "campaign_count": 3,
                    }
                ])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_selection_model(db)

        assert isinstance(result, ModelVersion)
        assert result.model_type == ModelType.SELECTION
        assert result.version == 2

    @pytest.mark.asyncio
    async def test_retrain_version_monotonically_increases(self):
        """Version harus bertambah monoton: versi baru > versi sebelumnya."""
        engine = LearningEngine()
        db = _make_db()

        # Simulasi versi sebelumnya adalah 5
        async def _execute(query, params=None):
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 6})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first({"accuracy_after": 0.80})
            elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                return _make_execute_result([
                    {
                        "influencer_id": "inf-1",
                        "avg_gmv": 1000000.0,
                        "avg_conversion_rate": 0.10,
                        "campaign_count": 5,
                    }
                ])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_selection_model(db)

        assert result.version == 6
        assert result.version > 5  # monoton meningkat

    @pytest.mark.asyncio
    async def test_retrain_first_version_has_no_accuracy_before(self):
        """Versi pertama harus memiliki accuracy_before = None."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 1})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                # Tidak ada versi sebelumnya
                return _make_execute_result_first(None)
            elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                return _make_execute_result([])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_selection_model(db)

        assert result.version == 1
        assert result.accuracy_before is None


# ---------------------------------------------------------------------------
# Tests: retrain_classifier_model
# ---------------------------------------------------------------------------


class TestRetrainClassifierModel:
    @pytest.mark.asyncio
    async def test_retrain_classifier_creates_model_version(self):
        """retrain_classifier_model harus membuat ModelVersion baru."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 3})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first({"accuracy_after": 0.82})
            elif "influencer_feedback" in q:
                return _make_execute_result([
                    {
                        "classification": "Menerima",
                        "raw_message": "iya saya mau bergabung",
                        "confidence_score": 0.95,
                    },
                    {
                        "classification": "Menolak",
                        "raw_message": "maaf tidak bisa",
                        "confidence_score": 0.90,
                    },
                ])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_classifier_model(db)

        assert isinstance(result, ModelVersion)
        assert result.model_type == ModelType.CLASSIFIER
        assert result.version == 3


# ---------------------------------------------------------------------------
# Tests: get_influencer_recommendations
# ---------------------------------------------------------------------------


class TestGetInfluencerRecommendations:
    @pytest.mark.asyncio
    async def test_confidence_score_in_valid_range(self):
        """confidence_score harus dalam [0.0, 1.0]."""
        engine = LearningEngine()
        db = _make_db()

        outcome_rows = [
            {
                "influencer_id": "inf-1",
                "avg_gmv": 500000.0,
                "avg_conversion_rate": 0.05,
                "campaign_count": 3,
                "campaign_ids": ["camp-1", "camp-2", "camp-3"],
            },
            {
                "influencer_id": "inf-2",
                "avg_gmv": 1200000.0,
                "avg_conversion_rate": 0.08,
                "campaign_count": 15,  # lebih dari 10, confidence harus di-clamp ke 1.0
                "campaign_ids": ["camp-1"],
            },
        ]

        async def _execute(query, params=None):
            return _make_execute_result(outcome_rows)

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

        assert len(recommendations) == 2
        for rec in recommendations:
            assert 0.0 <= rec.confidence_score <= 1.0, (
                f"confidence_score {rec.confidence_score} harus dalam [0.0, 1.0]"
            )
            assert 0.0 <= rec.predicted_conversion_rate <= 1.0, (
                f"predicted_conversion_rate {rec.predicted_conversion_rate} harus dalam [0.0, 1.0]"
            )

    @pytest.mark.asyncio
    async def test_confidence_clamped_at_1_for_many_campaigns(self):
        """confidence_score tidak boleh melebihi 1.0 meski campaign_count > 10."""
        engine = LearningEngine()
        db = _make_db()

        outcome_rows = [
            {
                "influencer_id": "inf-1",
                "avg_gmv": 2000000.0,
                "avg_conversion_rate": 0.12,
                "campaign_count": 50,  # jauh di atas 10
                "campaign_ids": ["camp-1"],
            },
        ]

        async def _execute(query, params=None):
            return _make_execute_result(outcome_rows)

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

        assert len(recommendations) == 1
        assert recommendations[0].confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_returns_empty_if_no_outcomes(self):
        """Harus mengembalikan list kosong jika tidak ada data outcome."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            return _make_execute_result([])

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

        assert recommendations == []

    @pytest.mark.asyncio
    async def test_respects_top_n_limit(self):
        """Harus mengembalikan maksimal top_n rekomendasi."""
        engine = LearningEngine()
        db = _make_db()

        outcome_rows = [
            {
                "influencer_id": f"inf-{i}",
                "avg_gmv": float(i * 100000),
                "avg_conversion_rate": 0.05,
                "campaign_count": 2,
                "campaign_ids": ["camp-1"],
            }
            for i in range(1, 11)  # 10 influencer
        ]

        async def _execute(query, params=None):
            return _make_execute_result(outcome_rows)

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        recommendations = await engine.get_influencer_recommendations(criteria, top_n=3, db=db)

        assert len(recommendations) <= 3


# ---------------------------------------------------------------------------
# Tests: get_model_performance_history
# ---------------------------------------------------------------------------


class TestGetModelPerformanceHistory:
    @pytest.mark.asyncio
    async def test_returns_sorted_by_newest_first(self):
        """get_model_performance_history harus mengembalikan list diurutkan dari terbaru."""
        engine = LearningEngine()
        db = _make_db()

        now = _now()
        from datetime import timedelta

        rows = [
            {
                "id": str(uuid.uuid4()),
                "model_type": "SELECTION",
                "version": 3,
                "accuracy_before": 0.75,
                "accuracy_after": 0.80,
                "trained_at": now,
                "training_data_size": 100,
            },
            {
                "id": str(uuid.uuid4()),
                "model_type": "SELECTION",
                "version": 2,
                "accuracy_before": 0.70,
                "accuracy_after": 0.75,
                "trained_at": now - timedelta(days=1),
                "training_data_size": 80,
            },
            {
                "id": str(uuid.uuid4()),
                "model_type": "CLASSIFIER",
                "version": 1,
                "accuracy_before": None,
                "accuracy_after": 0.70,
                "trained_at": now - timedelta(days=2),
                "training_data_size": 50,
            },
        ]

        async def _execute(query, params=None):
            return _make_execute_result(rows)

        db.execute = _execute

        history = await engine.get_model_performance_history(db)

        assert len(history) == 3
        # Verifikasi urutan: terbaru dulu (version 3 → 2 → 1)
        assert history[0].version == 3
        assert history[1].version == 2
        assert history[2].version == 1

    @pytest.mark.asyncio
    async def test_returns_empty_if_no_versions(self):
        """Harus mengembalikan list kosong jika tidak ada model versions."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            return _make_execute_result([])

        db.execute = _execute

        history = await engine.get_model_performance_history(db)

        assert history == []

    @pytest.mark.asyncio
    async def test_model_version_fields_are_correct(self):
        """Setiap ModelVersion harus memiliki semua field yang benar."""
        engine = LearningEngine()
        db = _make_db()

        now = _now()
        version_id = str(uuid.uuid4())
        rows = [
            {
                "id": version_id,
                "model_type": "CLASSIFIER",
                "version": 5,
                "accuracy_before": 0.82,
                "accuracy_after": 0.87,
                "trained_at": now,
                "training_data_size": 200,
            }
        ]

        async def _execute(query, params=None):
            return _make_execute_result(rows)

        db.execute = _execute

        history = await engine.get_model_performance_history(db)

        assert len(history) == 1
        mv = history[0]
        assert mv.id == version_id
        assert mv.model_type == ModelType.CLASSIFIER
        assert mv.version == 5
        assert mv.accuracy_before == 0.82
        assert mv.accuracy_after == 0.87
        assert mv.training_data_size == 200


# ---------------------------------------------------------------------------
# Tests: Orchestrator integration — stop_campaign calls LearningEngine
# ---------------------------------------------------------------------------


class TestOrchestratorLearningEngineIntegration:
    @pytest.mark.asyncio
    async def test_stop_campaign_calls_record_campaign_outcome(self):
        """stop_campaign harus memanggil LearningEngine.record_campaign_outcome."""
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.classifier_agent import ClassifierAgent
        from app.agents.monitor_agent import MonitorAgent
        from app.agents.selector_agent import SelectorAgent
        from app.agents.sender_agent import SenderAgent

        selector = MagicMock(spec=SelectorAgent)
        sender = MagicMock(spec=SenderAgent)
        monitor = MagicMock(spec=MonitorAgent)
        monitor.stop_monitoring = MagicMock()
        classifier = MagicMock(spec=ClassifierAgent)

        learning_engine = MagicMock(spec=LearningEngine)
        learning_engine.record_campaign_outcome = AsyncMock()
        learning_engine.retrain_selection_model = AsyncMock(
            return_value=ModelVersion(
                id=str(uuid.uuid4()),
                model_type=ModelType.SELECTION,
                version=1,
                accuracy_after=0.75,
                trained_at=_now(),
                training_data_size=10,
            )
        )
        learning_engine.retrain_classifier_model = AsyncMock(
            return_value=ModelVersion(
                id=str(uuid.uuid4()),
                model_type=ModelType.CLASSIFIER,
                version=1,
                accuracy_after=0.80,
                trained_at=_now(),
                training_data_size=10,
            )
        )

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            learning_engine=learning_engine,
        )
        orchestrator._update_campaign_status = AsyncMock()

        db = _make_db()
        await orchestrator.stop_campaign("camp-1", db)

        learning_engine.record_campaign_outcome.assert_called_once_with("camp-1", db)

    @pytest.mark.asyncio
    async def test_stop_campaign_without_learning_engine_does_not_raise(self):
        """stop_campaign tanpa LearningEngine tidak boleh raise exception."""
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.classifier_agent import ClassifierAgent
        from app.agents.monitor_agent import MonitorAgent
        from app.agents.selector_agent import SelectorAgent
        from app.agents.sender_agent import SenderAgent

        selector = MagicMock(spec=SelectorAgent)
        sender = MagicMock(spec=SenderAgent)
        monitor = MagicMock(spec=MonitorAgent)
        monitor.stop_monitoring = MagicMock()
        classifier = MagicMock(spec=ClassifierAgent)

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
        )
        orchestrator._update_campaign_status = AsyncMock()

        db = _make_db()
        # Tidak boleh raise
        await orchestrator.stop_campaign("camp-1", db)


# ---------------------------------------------------------------------------
# Edge Case Tests: Task 17.4
# ---------------------------------------------------------------------------


class TestEdgeCaseNoOutcomeData:
    """Edge case: tidak ada data outcome — retraining dilewati / data_size = 0."""

    @pytest.mark.asyncio
    async def test_retrain_selection_skipped_when_no_outcomes(self):
        """Jika tidak ada CampaignOutcome, retrain_selection_model tetap membuat
        ModelVersion tapi dengan training_data_size = 0 (retraining dilewati)."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 1})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first(None)
            elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                # Tidak ada data outcome sama sekali
                return _make_execute_result([])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_selection_model(db)

        # ModelVersion tetap dibuat
        assert isinstance(result, ModelVersion)
        assert result.model_type == ModelType.SELECTION
        # training_data_size = 0 karena tidak ada data
        assert result.training_data_size == 0
        # accuracy_before = None karena ini versi pertama
        assert result.accuracy_before is None

    @pytest.mark.asyncio
    async def test_retrain_classifier_skipped_when_no_feedback(self):
        """Jika tidak ada data feedback, retrain_classifier_model tetap membuat
        ModelVersion tapi dengan training_data_size = 0."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 1})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first(None)
            elif "influencer_feedback" in q:
                # Tidak ada data feedback
                return _make_execute_result([])
            else:
                return MagicMock()

        db.execute = _execute

        result = await engine.retrain_classifier_model(db)

        assert isinstance(result, ModelVersion)
        assert result.model_type == ModelType.CLASSIFIER
        assert result.training_data_size == 0

    @pytest.mark.asyncio
    async def test_record_campaign_outcome_skips_when_no_invitations(self):
        """record_campaign_outcome harus skip tanpa error jika tidak ada undangan."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            # Selalu kembalikan list kosong
            return _make_execute_result([])

        db.execute = _execute

        # Tidak boleh raise exception
        await engine.record_campaign_outcome("camp-no-invitations", db)

        # flush tidak dipanggil karena tidak ada data untuk disimpan
        db.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_recommendations_empty_when_no_outcome_data(self):
        """get_influencer_recommendations harus mengembalikan [] jika tidak ada outcome."""
        engine = LearningEngine()
        db = _make_db()

        async def _execute(query, params=None):
            return _make_execute_result([])

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        result = await engine.get_influencer_recommendations(criteria, top_n=10, db=db)

        assert result == []


class TestEdgeCaseAllInfluencersRejected:
    """Edge case: kampanye dengan semua influencer menolak."""

    @pytest.mark.asyncio
    async def test_record_outcome_all_rejected(self):
        """Semua influencer dengan status PENDING/FAILED harus ditandai accepted=False."""
        engine = LearningEngine()
        db = _make_db()

        # Semua influencer menolak (status bukan ACCEPTED/DELIVERED/SENT)
        inv_rows = [
            {"influencer_id": "inf-1", "status": "FAILED"},
            {"influencer_id": "inf-2", "status": "PENDING"},
            {"influencer_id": "inf-3", "status": "SCHEDULED"},
        ]

        inserted_params: List[dict] = []
        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_execute_result(inv_rows)
            elif call_count == 2:
                # Tidak ada metrik (semua menolak, tidak ada konten)
                return _make_execute_result([])
            else:
                if params and "accepted" in params:
                    inserted_params.append(dict(params))
                return MagicMock()

        db.execute = _execute

        await engine.record_campaign_outcome("camp-all-rejected", db)

        # Semua harus accepted=False
        assert len(inserted_params) == 3
        for p in inserted_params:
            assert p["accepted"] is False, (
                f"Influencer {p['influencer_id']} seharusnya accepted=False"
            )

    @pytest.mark.asyncio
    async def test_record_outcome_all_rejected_gmv_is_zero(self):
        """Influencer yang menolak harus memiliki gmv_generated = 0.0."""
        engine = LearningEngine()
        db = _make_db()

        inv_rows = [
            {"influencer_id": "inf-1", "status": "FAILED"},
            {"influencer_id": "inf-2", "status": "PENDING"},
        ]

        inserted_params: List[dict] = []
        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_execute_result(inv_rows)
            elif call_count == 2:
                return _make_execute_result([])  # tidak ada metrik
            else:
                if params and "gmv_generated" in params:
                    inserted_params.append(dict(params))
                return MagicMock()

        db.execute = _execute

        await engine.record_campaign_outcome("camp-all-rejected", db)

        for p in inserted_params:
            assert p["gmv_generated"] == 0.0
            assert p["conversion_rate"] == 0.0
            assert p["content_count"] == 0

    @pytest.mark.asyncio
    async def test_recommendations_with_all_rejected_outcomes(self):
        """Rekomendasi dari kampanye di mana semua menolak harus memiliki
        predicted_gmv = 0 dan confidence_score yang valid."""
        engine = LearningEngine()
        db = _make_db()

        # Semua influencer punya GMV = 0 dan conversion_rate = 0
        outcome_rows = [
            {
                "influencer_id": "inf-1",
                "avg_gmv": 0.0,
                "avg_conversion_rate": 0.0,
                "campaign_count": 2,
                "campaign_ids": ["camp-1", "camp-2"],
            },
            {
                "influencer_id": "inf-2",
                "avg_gmv": 0.0,
                "avg_conversion_rate": 0.0,
                "campaign_count": 1,
                "campaign_ids": ["camp-1"],
            },
        ]

        async def _execute(query, params=None):
            return _make_execute_result(outcome_rows)

        db.execute = _execute

        criteria = SelectionCriteria(id="crit-1", name="Test")
        recommendations = await engine.get_influencer_recommendations(criteria, top_n=5, db=db)

        assert len(recommendations) == 2
        for rec in recommendations:
            assert rec.predicted_gmv == 0.0
            assert rec.predicted_conversion_rate == 0.0
            assert 0.0 <= rec.confidence_score <= 1.0


class TestEdgeCaseRetrainingFailure:
    """Edge case: retraining gagal di tengah jalan."""

    @pytest.mark.asyncio
    async def test_run_retraining_continues_classifier_if_selection_fails(self):
        """_run_retraining harus tetap menjalankan retrain_classifier_model
        meskipun retrain_selection_model gagal."""
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.classifier_agent import ClassifierAgent
        from app.agents.monitor_agent import MonitorAgent
        from app.agents.selector_agent import SelectorAgent
        from app.agents.sender_agent import SenderAgent

        selector = MagicMock(spec=SelectorAgent)
        sender = MagicMock(spec=SenderAgent)
        monitor = MagicMock(spec=MonitorAgent)
        monitor.stop_monitoring = MagicMock()
        classifier = MagicMock(spec=ClassifierAgent)

        learning_engine = MagicMock(spec=LearningEngine)
        learning_engine.record_campaign_outcome = AsyncMock()
        # retrain_selection_model gagal
        learning_engine.retrain_selection_model = AsyncMock(
            side_effect=RuntimeError("DB connection lost during selection retraining")
        )
        # retrain_classifier_model berhasil
        learning_engine.retrain_classifier_model = AsyncMock(
            return_value=ModelVersion(
                id=str(uuid.uuid4()),
                model_type=ModelType.CLASSIFIER,
                version=1,
                accuracy_after=0.80,
                trained_at=_now(),
                training_data_size=50,
            )
        )

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            learning_engine=learning_engine,
        )

        db = _make_db()

        # _run_retraining tidak boleh raise meskipun selection gagal
        await orchestrator._run_retraining(learning_engine, db)

        # Kedua method harus dipanggil
        learning_engine.retrain_selection_model.assert_called_once_with(db)
        learning_engine.retrain_classifier_model.assert_called_once_with(db)

    @pytest.mark.asyncio
    async def test_run_retraining_handles_classifier_failure(self):
        """_run_retraining tidak boleh raise jika retrain_classifier_model gagal."""
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.classifier_agent import ClassifierAgent
        from app.agents.monitor_agent import MonitorAgent
        from app.agents.selector_agent import SelectorAgent
        from app.agents.sender_agent import SenderAgent

        selector = MagicMock(spec=SelectorAgent)
        sender = MagicMock(spec=SenderAgent)
        monitor = MagicMock(spec=MonitorAgent)
        monitor.stop_monitoring = MagicMock()
        classifier = MagicMock(spec=ClassifierAgent)

        learning_engine = MagicMock(spec=LearningEngine)
        learning_engine.retrain_selection_model = AsyncMock(
            return_value=ModelVersion(
                id=str(uuid.uuid4()),
                model_type=ModelType.SELECTION,
                version=1,
                accuracy_after=0.75,
                trained_at=_now(),
                training_data_size=30,
            )
        )
        # classifier retraining gagal
        learning_engine.retrain_classifier_model = AsyncMock(
            side_effect=RuntimeError("OOM error during classifier retraining")
        )

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            learning_engine=learning_engine,
        )

        db = _make_db()

        # Tidak boleh raise
        await orchestrator._run_retraining(learning_engine, db)

        learning_engine.retrain_selection_model.assert_called_once_with(db)
        learning_engine.retrain_classifier_model.assert_called_once_with(db)

    @pytest.mark.asyncio
    async def test_stop_campaign_continues_if_record_outcome_fails(self):
        """stop_campaign tidak boleh raise jika record_campaign_outcome gagal."""
        from app.agents.orchestrator import AgentOrchestrator
        from app.agents.classifier_agent import ClassifierAgent
        from app.agents.monitor_agent import MonitorAgent
        from app.agents.selector_agent import SelectorAgent
        from app.agents.sender_agent import SenderAgent

        selector = MagicMock(spec=SelectorAgent)
        sender = MagicMock(spec=SenderAgent)
        monitor = MagicMock(spec=MonitorAgent)
        monitor.stop_monitoring = MagicMock()
        classifier = MagicMock(spec=ClassifierAgent)

        learning_engine = MagicMock(spec=LearningEngine)
        # record_campaign_outcome gagal
        learning_engine.record_campaign_outcome = AsyncMock(
            side_effect=Exception("Database unavailable")
        )

        orchestrator = AgentOrchestrator(
            selector_agent=selector,
            sender_agent=sender,
            monitor_agent=monitor,
            classifier_agent=classifier,
            learning_engine=learning_engine,
        )
        orchestrator._update_campaign_status = AsyncMock()

        db = _make_db()

        # stop_campaign tidak boleh raise meskipun LearningEngine gagal
        await orchestrator.stop_campaign("camp-1", db)

        # Status kampanye tetap diupdate ke COMPLETED
        orchestrator._update_campaign_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrain_selection_with_db_error_during_training(self):
        """retrain_selection_model harus menangani error DB saat training."""
        engine = LearningEngine()
        db = _make_db()

        call_count = 0

        async def _execute(query, params=None):
            nonlocal call_count
            call_count += 1
            q = str(query)
            if "COALESCE(MAX(version)" in q:
                return _make_execute_result_first({"next_version": 1})
            elif "accuracy_after" in q and "ORDER BY version DESC" in q:
                return _make_execute_result_first(None)
            elif "campaign_outcomes" in q and "GROUP BY influencer_id" in q:
                # Simulasi DB error saat mengambil data training
                raise RuntimeError("DB connection lost")
            else:
                return MagicMock()

        db.execute = _execute

        # _create_model_version menangkap error dari background task
        # dan tetap membuat ModelVersion dengan data_size = 0
        result = await engine.retrain_selection_model(db)

        # ModelVersion tetap dibuat meskipun training gagal
        assert isinstance(result, ModelVersion)
        assert result.model_type == ModelType.SELECTION
        # data_size = 0 karena training gagal
        assert result.training_data_size == 0
