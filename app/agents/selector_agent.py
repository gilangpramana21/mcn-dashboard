"""Selector Agent — filter and score influencers based on SelectionCriteria."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain import CriteriaWeights, Influencer, SelectionCriteria
from app.services.blacklist_service import BlacklistService


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class SelectionResult:
    """Result returned by SelectorAgent.select_influencers()."""

    influencers: List[Influencer]
    total_found: int
    suggestion: Optional[str] = None


# ---------------------------------------------------------------------------
# SelectorAgent
# ---------------------------------------------------------------------------


class SelectorAgent:
    """Filters influencers by criteria, scores them, and publishes events."""

    # Normalisation caps — values above these are treated as the maximum
    _FOLLOWER_CAP: int = 10_000_000  # 10 M followers → score 1.0
    _ENGAGEMENT_CAP: float = 1.0     # engagement_rate is already [0, 1]

    def __init__(
        self,
        blacklist_service: BlacklistService,
        redis: Optional[object] = None,
    ) -> None:
        self._blacklist = blacklist_service
        self._redis = redis  # redis.asyncio client (optional for unit tests)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def select_influencers(
        self,
        criteria: SelectionCriteria,
        campaign_id: str,
        influencers: List[Influencer],
    ) -> SelectionResult:
        """Filter *influencers* by *criteria*, score them, and return a SelectionResult.

        Steps:
        1. Exclude blacklisted influencers.
        2. Apply hard filters (followers, engagement_rate, categories, locations).
        3. Calculate relevance_score for each passing influencer.
        4. Sort by score descending.
        5. Publish event to Redis Streams.
        6. Return SelectionResult (with suggestion if empty).
        """
        passed: List[Influencer] = []

        for inf in influencers:
            # --- blacklist check ---
            if inf.blacklisted or await self._blacklist.is_blacklisted(inf.id):
                continue

            # --- hard filters ---
            if not self._passes_filters(inf, criteria):
                continue

            # --- score ---
            score = await self.calculate_relevance_score(inf, criteria)
            # Attach score to a copy so we don't mutate the original
            scored = Influencer(
                id=inf.id,
                tiktok_user_id=inf.tiktok_user_id,
                name=inf.name,
                phone_number=inf.phone_number,
                follower_count=inf.follower_count,
                engagement_rate=inf.engagement_rate,
                content_categories=list(inf.content_categories),
                location=inf.location,
                relevance_score=score,
                status=inf.status,
                blacklisted=inf.blacklisted,
                blacklist_reason=inf.blacklist_reason,
            )
            passed.append(scored)

        # Sort by relevance_score descending
        passed.sort(key=lambda x: x.relevance_score or 0.0, reverse=True)

        suggestion: Optional[str] = None
        if not passed:
            suggestion = (
                "Tidak ada influencer yang memenuhi kriteria saat ini. "
                "Pertimbangkan untuk melonggarkan kriteria: kurangi min_followers, "
                "turunkan min_engagement_rate, atau perluas content_categories dan locations."
            )

        # Publish event to Redis Streams (fire-and-forget; ignore if redis not configured)
        await self._publish_event(campaign_id, len(passed))

        return SelectionResult(
            influencers=passed,
            total_found=len(passed),
            suggestion=suggestion,
        )

    async def calculate_relevance_score(
        self,
        influencer: Influencer,
        criteria: SelectionCriteria,
    ) -> float:
        """Return a deterministic relevance score in [0.0, 1.0].

        Score = weighted sum of four normalised components:
          - follower_count  : normalised to [0, 1] against _FOLLOWER_CAP
          - engagement_rate : already in [0, 1]
          - category_match  : 1.0 if any category matches, else 0.0
          - location_match  : 1.0 if location matches any criteria location, else 0.0
        """
        weights: CriteriaWeights = criteria.criteria_weights

        # Follower score
        follower_score = min(influencer.follower_count / self._FOLLOWER_CAP, 1.0)

        # Engagement score
        engagement_score = min(max(influencer.engagement_rate, 0.0), 1.0)

        # Category match score
        if criteria.content_categories:
            inf_cats = {c.lower() for c in influencer.content_categories}
            crit_cats = {c.lower() for c in criteria.content_categories}
            category_score = 1.0 if inf_cats & crit_cats else 0.0
        else:
            category_score = 1.0  # no filter → full score

        # Location match score
        if criteria.locations:
            crit_locs = {loc.lower() for loc in criteria.locations}
            location_score = 1.0 if influencer.location.lower() in crit_locs else 0.0
        else:
            location_score = 1.0  # no filter → full score

        raw = (
            weights.follower_count * follower_score
            + weights.engagement_rate * engagement_score
            + weights.category_match * category_score
            + weights.location_match * location_score
        )

        # Clamp to [0.0, 1.0] to guard against weight misconfiguration
        return max(0.0, min(raw, 1.0))

    async def save_criteria_template(
        self,
        criteria: SelectionCriteria,
        db: AsyncSession,
    ) -> SelectionCriteria:
        """Persist *criteria* as a reusable template (is_template=True).

        Returns the saved SelectionCriteria with is_template=True.
        """
        import json

        template_id = criteria.id or str(uuid.uuid4())
        weights = criteria.criteria_weights

        await db.execute(
            text(
                """
                INSERT INTO selection_criteria
                    (id, name, min_followers, max_followers, min_engagement_rate,
                     content_categories, locations,
                     weight_follower_count, weight_engagement_rate,
                     weight_category_match, weight_location_match,
                     is_template)
                VALUES
                    (:id, :name, :min_followers, :max_followers, :min_engagement_rate,
                     :content_categories, :locations,
                     :weight_follower_count, :weight_engagement_rate,
                     :weight_category_match, :weight_location_match,
                     TRUE)
                ON CONFLICT (id) DO UPDATE
                SET is_template = TRUE
                """
            ),
            {
                "id": template_id,
                "name": criteria.name,
                "min_followers": criteria.min_followers,
                "max_followers": criteria.max_followers,
                "min_engagement_rate": criteria.min_engagement_rate,
                "content_categories": json.dumps(criteria.content_categories or []),
                "locations": json.dumps(criteria.locations or []),
                "weight_follower_count": weights.follower_count,
                "weight_engagement_rate": weights.engagement_rate,
                "weight_category_match": weights.category_match,
                "weight_location_match": weights.location_match,
            },
        )
        await db.flush()

        return SelectionCriteria(
            id=template_id,
            name=criteria.name,
            min_followers=criteria.min_followers,
            max_followers=criteria.max_followers,
            min_engagement_rate=criteria.min_engagement_rate,
            content_categories=criteria.content_categories,
            locations=criteria.locations,
            criteria_weights=weights,
            is_template=True,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _passes_filters(
        self,
        influencer: Influencer,
        criteria: SelectionCriteria,
    ) -> bool:
        """Return True if *influencer* satisfies all hard filters in *criteria*."""
        if criteria.min_followers is not None:
            if influencer.follower_count < criteria.min_followers:
                return False

        if criteria.max_followers is not None:
            if influencer.follower_count > criteria.max_followers:
                return False

        if criteria.min_engagement_rate is not None:
            if influencer.engagement_rate < criteria.min_engagement_rate:
                return False

        if criteria.content_categories:
            inf_cats = {c.lower() for c in influencer.content_categories}
            crit_cats = {c.lower() for c in criteria.content_categories}
            if not (inf_cats & crit_cats):
                return False

        if criteria.locations:
            crit_locs = {loc.lower() for loc in criteria.locations}
            if influencer.location.lower() not in crit_locs:
                return False

        return True

    async def _publish_event(self, campaign_id: str, count: int) -> None:
        """Publish influencers_selected event to Redis Streams."""
        if self._redis is None:
            return
        try:
            await self._redis.xadd(
                "agent:events",
                {
                    "type": "influencers_selected",
                    "campaign_id": campaign_id,
                    "count": str(count),
                },
            )
        except Exception:
            # Non-critical: do not let Redis errors break the selection flow
            pass
