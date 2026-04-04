"""Classifier Agent — klasifikasikan umpan balik influencer menggunakan NLP/AI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nlp_client import NLPClassifierClient
from app.models.domain import FeedbackCategory, InfluencerFeedback, InfluencerStatus


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ClassificationResult:
    feedback_id: str
    category: FeedbackCategory
    confidence_score: float
    requires_manual_review: bool


@dataclass
class ClassificationSummary:
    campaign_id: str
    total: int
    accepted: int
    rejected: int
    needs_more_info: int
    no_response: int
    pending_manual_review: int


# ---------------------------------------------------------------------------
# ClassifierAgent
# ---------------------------------------------------------------------------


class ClassifierAgent:
    """Mengklasifikasikan umpan balik influencer menggunakan NLP/AI (OpenAI) dengan fallback keyword."""

    def __init__(self, redis: Optional[object] = None) -> None:
        self._redis = redis
        self._nlp = NLPClassifierClient()

    # ------------------------------------------------------------------
    # classify_feedback
    # ------------------------------------------------------------------

    async def classify_feedback(
        self,
        feedback: InfluencerFeedback,
        db: AsyncSession,
    ) -> ClassificationResult:
        """Klasifikasikan raw_message ke salah satu FeedbackCategory.

        Langkah:
        1. Jika raw_message kosong/None → NO_RESPONSE, confidence=1.0
        2. Hitung jumlah keyword yang cocok per kategori
        3. Pilih kategori dengan jumlah keyword terbanyak
        4. Hitung confidence_score = matched / total_keywords_in_category (normalized)
        5. Set requires_manual_review jika NEEDS_MORE_INFO atau confidence < 0.8
        6. Jika REJECTED → update status influencer di DB
        7. Simpan hasil ke tabel influencer_feedback
        8. Publish event ke Redis Streams
        """
        raw = feedback.raw_message

        # --- Gunakan NLP client (AI atau keyword fallback) ---
        nlp_result = await self._nlp.classify(raw or "")
        category = nlp_result.category
        confidence_score = nlp_result.confidence_score
        requires_manual_review = bool(
            category == FeedbackCategory.NEEDS_MORE_INFO
            or confidence_score < 0.8
        )

        # --- Update status influencer jika REJECTED ---
        if category == FeedbackCategory.REJECTED:
            await self._update_influencer_status(feedback.influencer_id, InfluencerStatus.REJECTED, db)

        # --- Simpan hasil klasifikasi ke DB ---
        classified_at = datetime.now(timezone.utc)
        await self._save_classification(
            feedback_id=feedback.id,
            category=category,
            confidence_score=confidence_score,
            requires_manual_review=requires_manual_review,
            classified_at=classified_at,
            db=db,
        )

        # --- Publish event ke Redis Streams ---
        await self._publish_event(
            feedback_id=feedback.id,
            campaign_id=feedback.campaign_id,
            influencer_id=feedback.influencer_id,
            category=category,
        )

        return ClassificationResult(
            feedback_id=feedback.id,
            category=category,
            confidence_score=confidence_score,
            requires_manual_review=requires_manual_review,
        )

    # ------------------------------------------------------------------
    # get_classification_summary
    # ------------------------------------------------------------------

    async def get_classification_summary(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> ClassificationSummary:
        """Query tabel influencer_feedback dan hitung distribusi per kategori."""
        result = await db.execute(
            text(
                """
                SELECT
                    classification,
                    COUNT(*) AS cnt
                FROM influencer_feedback
                WHERE campaign_id = :campaign_id
                  AND classification IS NOT NULL
                GROUP BY classification
                """
            ),
            {"campaign_id": campaign_id},
        )
        rows = result.mappings().all()

        counts = {
            FeedbackCategory.ACCEPTED: 0,
            FeedbackCategory.REJECTED: 0,
            FeedbackCategory.NEEDS_MORE_INFO: 0,
            FeedbackCategory.NO_RESPONSE: 0,
        }

        for row in rows:
            raw_cat = row["classification"]
            cnt = int(row["cnt"] or 0)
            try:
                cat = FeedbackCategory(raw_cat)
                counts[cat] += cnt
            except ValueError:
                pass

        # Hitung pending_manual_review
        mr_result = await db.execute(
            text(
                """
                SELECT COUNT(*) AS cnt
                FROM influencer_feedback
                WHERE campaign_id = :campaign_id
                  AND classification IS NOT NULL
                  AND requires_manual_review = TRUE
                """
            ),
            {"campaign_id": campaign_id},
        )
        mr_row = mr_result.mappings().first()
        pending_manual_review = int((mr_row["cnt"] if mr_row else 0) or 0)

        total = sum(counts.values())

        return ClassificationSummary(
            campaign_id=campaign_id,
            total=total,
            accepted=counts[FeedbackCategory.ACCEPTED],
            rejected=counts[FeedbackCategory.REJECTED],
            needs_more_info=counts[FeedbackCategory.NEEDS_MORE_INFO],
            no_response=counts[FeedbackCategory.NO_RESPONSE],
            pending_manual_review=pending_manual_review,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _update_influencer_status(
        self,
        influencer_id: str,
        status: InfluencerStatus,
        db: AsyncSession,
    ) -> None:
        await db.execute(
            text(
                "UPDATE influencers SET status = :status WHERE id = :influencer_id"
            ),
            {"status": status.value, "influencer_id": influencer_id},
        )
        await db.flush()

    async def _save_classification(
        self,
        feedback_id: str,
        category: FeedbackCategory,
        confidence_score: float,
        requires_manual_review: bool,
        classified_at: datetime,
        db: AsyncSession,
    ) -> None:
        await db.execute(
            text(
                """
                UPDATE influencer_feedback
                SET
                    classification        = :classification,
                    confidence_score      = :confidence_score,
                    requires_manual_review = :requires_manual_review,
                    classified_at         = :classified_at
                WHERE id = :feedback_id
                """
            ),
            {
                "feedback_id": feedback_id,
                "classification": category.value,
                "confidence_score": confidence_score,
                "requires_manual_review": requires_manual_review,
                "classified_at": classified_at,
            },
        )
        await db.flush()

    async def _publish_event(
        self,
        feedback_id: str,
        campaign_id: str,
        influencer_id: str,
        category: FeedbackCategory,
    ) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.xadd(
                "agent:events",
                {
                    "type": "feedback_classified",
                    "feedback_id": feedback_id,
                    "campaign_id": campaign_id,
                    "influencer_id": influencer_id,
                    "category": category.value,
                },
            )
        except Exception:
            pass
