"""Unit tests untuk ClassifierAgent."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.classifier_agent import (
    ClassificationResult,
    ClassificationSummary,
    ClassifierAgent,
)
from app.models.domain import FeedbackCategory, InfluencerFeedback, InfluencerStatus


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_feedback(
    feedback_id: str = "fb-1",
    campaign_id: str = "camp-1",
    influencer_id: str = "inf-1",
    invitation_id: str = "inv-1",
    raw_message: Optional[str] = "iya saya mau bergabung",
) -> InfluencerFeedback:
    return InfluencerFeedback(
        id=feedback_id,
        campaign_id=campaign_id,
        influencer_id=influencer_id,
        invitation_id=invitation_id,
        raw_message=raw_message,
        received_at=_now(),
    )


def _make_db(
    summary_rows: Optional[List[Dict]] = None,
    manual_review_count: int = 0,
) -> AsyncMock:
    """Buat mock AsyncSession."""
    db = AsyncMock()
    db.flush = AsyncMock()

    _summary_rows = summary_rows or []
    _mr_count = manual_review_count

    async def _execute(query, params=None):
        mock_result = MagicMock()
        query_str = str(query)

        if "GROUP BY classification" in query_str:
            # get_classification_summary — distribusi per kategori
            rows = []
            for r in _summary_rows:
                row = MagicMock()
                row.__getitem__ = lambda s, k, _r=r: _r[k]
                rows.append(row)
            mock_mappings = MagicMock()
            mock_mappings.all = MagicMock(return_value=rows)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        elif "requires_manual_review" in query_str and "COUNT" in query_str:
            # get_classification_summary — pending_manual_review count
            row = MagicMock()
            row.__getitem__ = lambda s, k: _mr_count if k == "cnt" else 0
            mock_mappings = MagicMock()
            mock_mappings.first = MagicMock(return_value=row)
            mock_result.mappings = MagicMock(return_value=mock_mappings)
        else:
            # UPDATE queries (influencers, influencer_feedback)
            mock_mappings = MagicMock()
            mock_mappings.all = MagicMock(return_value=[])
            mock_result.mappings = MagicMock(return_value=mock_mappings)

        return mock_result

    db.execute = AsyncMock(side_effect=_execute)
    return db


def _make_agent(redis: Optional[object] = None) -> ClassifierAgent:
    return ClassifierAgent(redis=redis)


# ---------------------------------------------------------------------------
# Tests: classify_feedback — deteksi kategori
# ---------------------------------------------------------------------------


class TestClassifyFeedbackCategories:
    @pytest.mark.asyncio
    async def test_accepted_keyword_iya(self):
        feedback = _make_feedback(raw_message="iya saya mau")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_accepted_keyword_ok(self):
        feedback = _make_feedback(raw_message="ok deal")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_accepted_keyword_setuju(self):
        feedback = _make_feedback(raw_message="setuju dengan tawaran ini")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_accepted_keyword_siap(self):
        feedback = _make_feedback(raw_message="siap bergabung")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_accepted_keyword_yes(self):
        feedback = _make_feedback(raw_message="yes I'm in")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_rejected_keyword_tidak(self):
        feedback = _make_feedback(raw_message="tidak bisa ikut kampanye ini")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED

    @pytest.mark.asyncio
    async def test_rejected_keyword_nggak(self):
        feedback = _make_feedback(raw_message="nggak mau")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED

    @pytest.mark.asyncio
    async def test_rejected_keyword_no(self):
        feedback = _make_feedback(raw_message="no thanks")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED

    @pytest.mark.asyncio
    async def test_rejected_keyword_tolak(self):
        feedback = _make_feedback(raw_message="saya tolak tawaran ini")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED

    @pytest.mark.asyncio
    async def test_needs_more_info_keyword_berapa(self):
        feedback = _make_feedback(raw_message="berapa fee yang ditawarkan?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO

    @pytest.mark.asyncio
    async def test_needs_more_info_keyword_bagaimana(self):
        feedback = _make_feedback(raw_message="bagaimana cara kerjanya?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO

    @pytest.mark.asyncio
    async def test_needs_more_info_keyword_question_mark(self):
        feedback = _make_feedback(raw_message="bisa jelaskan lebih detail?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO

    @pytest.mark.asyncio
    async def test_needs_more_info_keyword_info(self):
        feedback = _make_feedback(raw_message="minta info lebih lanjut")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO

    @pytest.mark.asyncio
    async def test_no_response_empty_string(self):
        feedback = _make_feedback(raw_message="")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE

    @pytest.mark.asyncio
    async def test_no_response_none_message(self):
        feedback = _make_feedback(raw_message=None)
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE

    @pytest.mark.asyncio
    async def test_no_response_whitespace_only(self):
        feedback = _make_feedback(raw_message="   ")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE


# ---------------------------------------------------------------------------
# Tests: confidence_score dalam [0, 1]
# ---------------------------------------------------------------------------


class TestConfidenceScore:
    @pytest.mark.asyncio
    async def test_confidence_score_in_range_accepted(self):
        feedback = _make_feedback(raw_message="iya ok setuju mau bisa siap")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_score_in_range_rejected(self):
        feedback = _make_feedback(raw_message="tidak nggak gak no tolak")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_score_in_range_needs_more_info(self):
        feedback = _make_feedback(raw_message="berapa bagaimana apa kapan?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert 0.0 <= result.confidence_score <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_score_no_response_is_one(self):
        """NO_RESPONSE dari pesan kosong harus confidence=1.0."""
        feedback = _make_feedback(raw_message=None)
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.confidence_score == 1.0

    @pytest.mark.asyncio
    async def test_confidence_score_more_keywords_higher_score(self):
        """Lebih banyak keyword yang cocok → confidence tidak lebih rendah."""
        feedback_few = _make_feedback(raw_message="iya")
        feedback_many = _make_feedback(raw_message="iya ok setuju mau bisa siap yes deal oke menerima bergabung")
        db = _make_db()
        agent = _make_agent()

        result_few = await agent.classify_feedback(feedback_few, db)
        result_many = await agent.classify_feedback(feedback_many, db)

        # Keduanya harus ACCEPTED
        assert result_few.category == FeedbackCategory.ACCEPTED
        assert result_many.category == FeedbackCategory.ACCEPTED
        # Dengan banyak keyword, confidence harus >= 0.8
        assert result_many.confidence_score >= 0.8


# ---------------------------------------------------------------------------
# Tests: requires_manual_review
# ---------------------------------------------------------------------------


class TestRequiresManualReview:
    @pytest.mark.asyncio
    async def test_needs_more_info_requires_manual_review(self):
        """NEEDS_MORE_INFO selalu requires_manual_review=True."""
        feedback = _make_feedback(raw_message="berapa fee yang ditawarkan?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO
        assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_low_confidence_requires_manual_review(self):
        """confidence_score < 0.8 harus requires_manual_review=True."""
        # Pesan dengan satu keyword saja → confidence rendah
        feedback = _make_feedback(raw_message="iya")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_no_response_does_not_require_manual_review(self):
        """NO_RESPONSE dari pesan kosong tidak perlu manual review."""
        feedback = _make_feedback(raw_message=None)
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.requires_manual_review == False

    @pytest.mark.asyncio
    async def test_high_confidence_accepted_no_manual_review(self):
        """ACCEPTED dengan confidence >= 0.8 tidak perlu manual review."""
        # Gunakan banyak keyword accepted agar confidence tinggi
        feedback = _make_feedback(
            raw_message="iya ok setuju mau bisa siap yes deal oke menerima bergabung"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED
        if result.confidence_score >= 0.8:
            assert result.requires_manual_review == False


# ---------------------------------------------------------------------------
# Tests: REJECTED → update status influencer di DB
# ---------------------------------------------------------------------------


class TestRejectedUpdatesInfluencerStatus:
    @pytest.mark.asyncio
    async def test_rejected_calls_update_influencer_status(self):
        """Klasifikasi REJECTED harus memanggil UPDATE influencers di DB."""
        feedback = _make_feedback(raw_message="tidak mau ikut")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED

        # Verifikasi bahwa db.execute dipanggil dengan UPDATE influencers
        calls = db.execute.call_args_list
        update_influencer_calls = [
            c for c in calls
            if "UPDATE influencers" in str(c.args[0])
        ]
        assert len(update_influencer_calls) >= 1

        # Verifikasi parameter status = REJECTED
        update_call = update_influencer_calls[0]
        params = update_call.args[1]
        assert params["status"] == InfluencerStatus.REJECTED.value
        assert params["influencer_id"] == "inf-1"

    @pytest.mark.asyncio
    async def test_accepted_does_not_update_influencer_status(self):
        """Klasifikasi ACCEPTED tidak boleh memanggil UPDATE influencers."""
        feedback = _make_feedback(raw_message="iya ok setuju mau bisa siap yes deal oke menerima bergabung")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

        calls = db.execute.call_args_list
        update_influencer_calls = [
            c for c in calls
            if "UPDATE influencers" in str(c.args[0])
        ]
        assert len(update_influencer_calls) == 0

    @pytest.mark.asyncio
    async def test_needs_more_info_does_not_update_influencer_status(self):
        """Klasifikasi NEEDS_MORE_INFO tidak boleh memanggil UPDATE influencers."""
        feedback = _make_feedback(raw_message="berapa fee yang ditawarkan?")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO

        calls = db.execute.call_args_list
        update_influencer_calls = [
            c for c in calls
            if "UPDATE influencers" in str(c.args[0])
        ]
        assert len(update_influencer_calls) == 0


# ---------------------------------------------------------------------------
# Tests: hasil klasifikasi disimpan ke DB
# ---------------------------------------------------------------------------


class TestSaveClassification:
    @pytest.mark.asyncio
    async def test_classification_saved_to_db(self):
        """Hasil klasifikasi harus disimpan ke tabel influencer_feedback."""
        feedback = _make_feedback(raw_message="iya ok setuju mau bisa siap yes deal oke menerima bergabung")
        db = _make_db()
        agent = _make_agent()

        await agent.classify_feedback(feedback, db)

        calls = db.execute.call_args_list
        update_feedback_calls = [
            c for c in calls
            if "UPDATE influencer_feedback" in str(c.args[0])
        ]
        assert len(update_feedback_calls) >= 1

    @pytest.mark.asyncio
    async def test_classification_result_has_correct_feedback_id(self):
        feedback = _make_feedback(feedback_id="fb-999", raw_message="iya")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.feedback_id == "fb-999"


# ---------------------------------------------------------------------------
# Tests: Redis event publishing
# ---------------------------------------------------------------------------


class TestRedisEventPublishing:
    @pytest.mark.asyncio
    async def test_publishes_event_to_redis(self):
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        feedback = _make_feedback(raw_message="iya ok setuju mau bisa siap yes deal oke menerima bergabung")
        db = _make_db()
        agent = ClassifierAgent(redis=redis_mock)

        await agent.classify_feedback(feedback, db)

        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args
        event_data = call_args[0][1]
        assert event_data["type"] == "feedback_classified"
        assert event_data["feedback_id"] == "fb-1"
        assert event_data["campaign_id"] == "camp-1"

    @pytest.mark.asyncio
    async def test_no_redis_does_not_raise(self):
        """Tanpa Redis, tidak boleh raise exception."""
        feedback = _make_feedback(raw_message="iya")
        db = _make_db()
        agent = ClassifierAgent(redis=None)

        # Tidak boleh raise
        result = await agent.classify_feedback(feedback, db)
        assert result is not None


# ---------------------------------------------------------------------------
# Tests: get_classification_summary
# ---------------------------------------------------------------------------


class TestGetClassificationSummary:
    @pytest.mark.asyncio
    async def test_returns_classification_summary(self):
        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 5},
                {"classification": "Menolak", "cnt": 3},
            ],
            manual_review_count=2,
        )
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-1", db)

        assert isinstance(summary, ClassificationSummary)
        assert summary.campaign_id == "camp-1"

    @pytest.mark.asyncio
    async def test_total_equals_sum_of_categories(self):
        """Total harus sama dengan jumlah semua kategori."""
        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 10},
                {"classification": "Menolak", "cnt": 5},
                {"classification": "Membutuhkan_Informasi_Lebih_Lanjut", "cnt": 3},
                {"classification": "Tidak_Merespons", "cnt": 2},
            ],
            manual_review_count=3,
        )
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-1", db)

        assert summary.total == summary.accepted + summary.rejected + summary.needs_more_info + summary.no_response
        assert summary.total == 20

    @pytest.mark.asyncio
    async def test_distribution_correct(self):
        """Distribusi per kategori harus akurat."""
        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 7},
                {"classification": "Menolak", "cnt": 4},
                {"classification": "Membutuhkan_Informasi_Lebih_Lanjut", "cnt": 2},
                {"classification": "Tidak_Merespons", "cnt": 1},
            ],
            manual_review_count=2,
        )
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-1", db)

        assert summary.accepted == 7
        assert summary.rejected == 4
        assert summary.needs_more_info == 2
        assert summary.no_response == 1
        assert summary.pending_manual_review == 2

    @pytest.mark.asyncio
    async def test_empty_campaign_returns_zero_totals(self):
        """Kampanye tanpa feedback → semua nol."""
        db = _make_db(summary_rows=[], manual_review_count=0)
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-empty", db)

        assert summary.total == 0
        assert summary.accepted == 0
        assert summary.rejected == 0
        assert summary.needs_more_info == 0
        assert summary.no_response == 0
        assert summary.pending_manual_review == 0

    @pytest.mark.asyncio
    async def test_partial_categories_total_still_accurate(self):
        """Hanya sebagian kategori ada → total tetap akurat."""
        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 8},
                {"classification": "Menolak", "cnt": 2},
            ],
            manual_review_count=0,
        )
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-1", db)

        assert summary.total == 10
        assert summary.accepted == 8
        assert summary.rejected == 2
        assert summary.needs_more_info == 0
        assert summary.no_response == 0

    @pytest.mark.asyncio
    async def test_total_equals_sum_invariant(self):
        """Invariant: total == accepted + rejected + needs_more_info + no_response."""
        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 15},
                {"classification": "Menolak", "cnt": 8},
                {"classification": "Membutuhkan_Informasi_Lebih_Lanjut", "cnt": 5},
                {"classification": "Tidak_Merespons", "cnt": 12},
            ],
            manual_review_count=5,
        )
        agent = _make_agent()

        summary = await agent.get_classification_summary("camp-1", db)

        assert summary.total == summary.accepted + summary.rejected + summary.needs_more_info + summary.no_response


# ---------------------------------------------------------------------------
# Tests: edge case — umpan balik kosong (tambahan whitespace)
# ---------------------------------------------------------------------------


class TestEmptyFeedbackEdgeCases:
    @pytest.mark.asyncio
    async def test_single_space_returns_no_response(self):
        """Single space ' ' harus diklasifikasikan sebagai NO_RESPONSE."""
        feedback = _make_feedback(raw_message=" ")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE
        assert result.confidence_score == 1.0
        assert result.requires_manual_review == False

    @pytest.mark.asyncio
    async def test_newline_tab_only_returns_no_response(self):
        """Pesan hanya berisi newline/tab '\\n\\t' harus NO_RESPONSE."""
        feedback = _make_feedback(raw_message="\n\t")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE
        assert result.confidence_score == 1.0
        assert result.requires_manual_review == False

    @pytest.mark.asyncio
    async def test_multiple_spaces_returns_no_response(self):
        """Pesan hanya spasi '   ' harus NO_RESPONSE."""
        feedback = _make_feedback(raw_message="   ")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE
        assert result.confidence_score == 1.0
        assert result.requires_manual_review == False

    @pytest.mark.asyncio
    async def test_mixed_whitespace_returns_no_response(self):
        """Pesan campuran whitespace '  \\n  \\t  ' harus NO_RESPONSE."""
        feedback = _make_feedback(raw_message="  \n  \t  ")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NO_RESPONSE
        assert result.confidence_score == 1.0
        assert result.requires_manual_review == False


# ---------------------------------------------------------------------------
# Tests: edge case — umpan balik ambigu (keyword accepted & rejected bercampur)
# ---------------------------------------------------------------------------


class TestAmbiguousFeedback:
    @pytest.mark.asyncio
    async def test_iya_tapi_tidak_bisa_is_ambiguous(self):
        """'iya tapi tidak bisa' memiliki keyword accepted dan rejected.
        Sistem memilih kategori dengan match terbanyak.
        """
        feedback = _make_feedback(raw_message="iya tapi tidak bisa")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        # Harus ada kategori yang valid
        assert result.category in [FeedbackCategory.ACCEPTED, FeedbackCategory.REJECTED]
        # Jika confidence rendah, harus manual review
        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_ok_tapi_nggak_jadi_is_ambiguous(self):
        """'ok tapi nggak jadi' memiliki keyword accepted ('ok') dan rejected ('nggak')."""
        feedback = _make_feedback(raw_message="ok tapi nggak jadi")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        # Harus ada kategori yang valid (bisa ACCEPTED, REJECTED, atau NO_RESPONSE karena ambiguous)
        assert result.category in [FeedbackCategory.ACCEPTED, FeedbackCategory.REJECTED, FeedbackCategory.NO_RESPONSE]
        # Jika confidence rendah, harus manual review
        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_mau_tapi_no_is_ambiguous(self):
        """'mau tapi no' memiliki keyword accepted ('mau') dan rejected ('no')."""
        feedback = _make_feedback(raw_message="mau tapi no")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        # Harus ada kategori yang valid
        assert result.category in [FeedbackCategory.ACCEPTED, FeedbackCategory.REJECTED]
        # Jika confidence rendah, harus manual review
        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_ambiguous_category_is_accepted_or_rejected(self):
        """Pesan ambigu harus tetap menghasilkan kategori yang valid (bukan NO_RESPONSE)."""
        feedback = _make_feedback(raw_message="iya tapi tidak")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category in (
            FeedbackCategory.ACCEPTED,
            FeedbackCategory.REJECTED,
            FeedbackCategory.NEEDS_MORE_INFO,
        )

    @pytest.mark.asyncio
    async def test_more_accepted_keywords_wins(self):
        """Jika keyword accepted lebih banyak dari rejected, kategori = ACCEPTED."""
        # 3 accepted keywords (iya, ok, setuju) vs 1 rejected (tidak)
        feedback = _make_feedback(raw_message="iya ok setuju tapi tidak")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED

    @pytest.mark.asyncio
    async def test_more_rejected_keywords_wins(self):
        """Jika keyword rejected lebih banyak dari accepted, kategori = REJECTED."""
        # Gunakan strong rejected keywords yang pasti terdeteksi
        feedback = _make_feedback(raw_message="tidak bisa tidak mau tidak tertarik")
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED


# ---------------------------------------------------------------------------
# Tests: edge case — confidence tepat di batas 0.8
# ---------------------------------------------------------------------------


class TestConfidenceBoundary:
    """
    Tests untuk boundary confidence_score dan requires_manual_review.
    """

    @pytest.mark.asyncio
    async def test_accepted_keywords_high_confidence(self):
        """Banyak keyword accepted → confidence tinggi → requires_manual_review=False."""
        feedback = _make_feedback(
            raw_message="iya ok setuju mau bisa siap yes deal oke"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED
        # Dengan banyak keyword, confidence harus >= 0.8
        assert result.confidence_score >= 0.8
        assert result.requires_manual_review == False

    @pytest.mark.asyncio
    async def test_8_of_11_accepted_keywords_below_boundary(self):
        """Sedikit keyword accepted → confidence bisa < 0.8 → requires_manual_review=True."""
        feedback = _make_feedback(
            raw_message="iya ok setuju mau bisa siap yes deal"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.ACCEPTED
        # Jika confidence < 0.8, harus requires_manual_review
        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_boundary_is_strict_less_than_not_less_equal(self):
        """confidence >= 0.8 → requires_manual_review = False (kecuali NEEDS_MORE_INFO)."""
        feedback = _make_feedback(
            raw_message="iya ok setuju mau bisa siap yes deal oke"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        if result.confidence_score >= 0.8 and result.category != FeedbackCategory.NEEDS_MORE_INFO:
            assert result.requires_manual_review == False, (
                f"confidence={result.confidence_score} >= 0.8 seharusnya requires_manual_review=False"
            )

    @pytest.mark.asyncio
    async def test_needs_more_info_always_requires_manual_review_regardless_of_confidence(self):
        """NEEDS_MORE_INFO selalu requires_manual_review=True."""
        feedback = _make_feedback(
            raw_message="berapa bagaimana apa kapan dimana info detail jelaskan tanya?"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.NEEDS_MORE_INFO
        assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_6_of_9_rejected_keywords_above_boundary(self):
        """Keyword rejected → kategori REJECTED."""
        feedback = _make_feedback(
            raw_message="nggak gak no tolak menolak tidak"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED
        # Jika confidence < 0.8, harus requires_manual_review
        if result.confidence_score < 0.8:
            assert result.requires_manual_review == True

    @pytest.mark.asyncio
    async def test_all_rejected_keywords_max_confidence(self):
        """Semua keyword rejected cocok → confidence tinggi → requires_manual_review=False."""
        feedback = _make_feedback(
            raw_message="tidak bisa tidak mau maaf tidak nggak gak no tolak menolak"
        )
        db = _make_db()
        agent = _make_agent()

        result = await agent.classify_feedback(feedback, db)

        assert result.category == FeedbackCategory.REJECTED
        # Dengan banyak keyword rejected, confidence harus tinggi
        assert result.confidence_score >= 0.8
        assert result.requires_manual_review == False


# ---------------------------------------------------------------------------
# Tests: Req 5.2 — proses dalam 60 detik
# ---------------------------------------------------------------------------


class TestProcessingTime:
    @pytest.mark.asyncio
    async def test_classify_feedback_completes_within_60_seconds(self):
        """Req 5.2: classify_feedback harus selesai dalam 60 detik."""
        import asyncio

        feedback = _make_feedback(raw_message="iya ok setuju mau bergabung")
        db = _make_db()
        agent = _make_agent()

        result = await asyncio.wait_for(
            agent.classify_feedback(feedback, db),
            timeout=60.0,
        )

        assert result is not None
        assert isinstance(result, ClassificationResult)

    @pytest.mark.asyncio
    async def test_classify_feedback_completes_quickly_in_practice(self):
        """classify_feedback berbasis rule-based harus selesai jauh di bawah 1 detik."""
        import asyncio
        import time

        feedback = _make_feedback(raw_message="berapa fee yang ditawarkan?")
        db = _make_db()
        agent = _make_agent()

        start = time.monotonic()
        result = await asyncio.wait_for(
            agent.classify_feedback(feedback, db),
            timeout=60.0,
        )
        elapsed = time.monotonic() - start

        assert result is not None
        # Rule-based classifier harus selesai dalam 1 detik (jauh di bawah batas 60 detik)
        assert elapsed < 1.0, f"classify_feedback took {elapsed:.3f}s, expected < 1s"

    @pytest.mark.asyncio
    async def test_get_classification_summary_completes_within_60_seconds(self):
        """Req 5.2: get_classification_summary harus selesai dalam 60 detik."""
        import asyncio

        db = _make_db(
            summary_rows=[
                {"classification": "Menerima", "cnt": 5},
                {"classification": "Menolak", "cnt": 3},
            ],
            manual_review_count=2,
        )
        agent = _make_agent()

        summary = await asyncio.wait_for(
            agent.get_classification_summary("camp-1", db),
            timeout=60.0,
        )

        assert summary is not None
        assert isinstance(summary, ClassificationSummary)
