"""Unit tests for SelectorAgent."""

from __future__ import annotations

from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.selector_agent import SelectionResult, SelectorAgent
from app.models.domain import (
    CriteriaWeights,
    Influencer,
    InfluencerStatus,
    SelectionCriteria,
)
from app.services.blacklist_service import BlacklistService


# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------


def _make_influencer(
    id: str = "inf-1",
    follower_count: int = 50_000,
    engagement_rate: float = 0.05,
    content_categories: Optional[List[str]] = None,
    location: str = "Jakarta",
    blacklisted: bool = False,
) -> Influencer:
    return Influencer(
        id=id,
        tiktok_user_id=f"tt-{id}",
        name=f"Influencer {id}",
        phone_number="+6281234567890",
        follower_count=follower_count,
        engagement_rate=engagement_rate,
        content_categories=content_categories or ["fashion"],
        location=location,
        blacklisted=blacklisted,
    )


def _make_criteria(
    min_followers: Optional[int] = None,
    max_followers: Optional[int] = None,
    min_engagement_rate: Optional[float] = None,
    content_categories: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    weights: Optional[CriteriaWeights] = None,
) -> SelectionCriteria:
    return SelectionCriteria(
        id="crit-1",
        name="Test Criteria",
        min_followers=min_followers,
        max_followers=max_followers,
        min_engagement_rate=min_engagement_rate,
        content_categories=content_categories,
        locations=locations,
        criteria_weights=weights or CriteriaWeights(),
    )


def _make_blacklist_service(is_blacklisted: bool = False) -> BlacklistService:
    svc = MagicMock(spec=BlacklistService)
    svc.is_blacklisted = AsyncMock(return_value=is_blacklisted)
    return svc


def _make_agent(is_blacklisted: bool = False) -> SelectorAgent:
    return SelectorAgent(
        blacklist_service=_make_blacklist_service(is_blacklisted),
        redis=None,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent() -> SelectorAgent:
    return _make_agent()


# ---------------------------------------------------------------------------
# select_influencers — filter tests
# ---------------------------------------------------------------------------


class TestSelectInfluencersFilters:
    @pytest.mark.asyncio
    async def test_filter_min_followers_excludes_below(self, agent):
        influencers = [
            _make_influencer("inf-1", follower_count=5_000),
            _make_influencer("inf-2", follower_count=20_000),
        ]
        criteria = _make_criteria(min_followers=10_000)

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-1" not in ids
        assert "inf-2" in ids

    @pytest.mark.asyncio
    async def test_filter_max_followers_excludes_above(self, agent):
        influencers = [
            _make_influencer("inf-1", follower_count=5_000),
            _make_influencer("inf-2", follower_count=200_000),
        ]
        criteria = _make_criteria(max_followers=100_000)

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-1" in ids
        assert "inf-2" not in ids

    @pytest.mark.asyncio
    async def test_filter_min_engagement_rate_excludes_below(self, agent):
        influencers = [
            _make_influencer("inf-1", engagement_rate=0.01),
            _make_influencer("inf-2", engagement_rate=0.08),
        ]
        criteria = _make_criteria(min_engagement_rate=0.05)

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-1" not in ids
        assert "inf-2" in ids

    @pytest.mark.asyncio
    async def test_filter_content_categories_any_match(self, agent):
        influencers = [
            _make_influencer("inf-1", content_categories=["fashion", "beauty"]),
            _make_influencer("inf-2", content_categories=["gaming"]),
        ]
        criteria = _make_criteria(content_categories=["beauty", "lifestyle"])

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-1" in ids
        assert "inf-2" not in ids

    @pytest.mark.asyncio
    async def test_filter_locations_any_match(self, agent):
        influencers = [
            _make_influencer("inf-1", location="Jakarta"),
            _make_influencer("inf-2", location="Surabaya"),
        ]
        criteria = _make_criteria(locations=["Jakarta", "Bandung"])

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-1" in ids
        assert "inf-2" not in ids

    @pytest.mark.asyncio
    async def test_no_criteria_returns_all_non_blacklisted(self, agent):
        influencers = [
            _make_influencer("inf-1"),
            _make_influencer("inf-2"),
        ]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 2

    @pytest.mark.asyncio
    async def test_results_sorted_by_score_descending(self, agent):
        influencers = [
            _make_influencer("inf-low", follower_count=1_000, engagement_rate=0.01),
            _make_influencer("inf-high", follower_count=1_000_000, engagement_rate=0.5),
        ]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.influencers[0].id == "inf-high"
        assert result.influencers[1].id == "inf-low"

    @pytest.mark.asyncio
    async def test_category_filter_case_insensitive(self, agent):
        influencers = [
            _make_influencer("inf-1", content_categories=["Fashion"]),
        ]
        criteria = _make_criteria(content_categories=["fashion"])

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_location_filter_case_insensitive(self, agent):
        influencers = [
            _make_influencer("inf-1", location="JAKARTA"),
        ]
        criteria = _make_criteria(locations=["jakarta"])

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 1


# ---------------------------------------------------------------------------
# select_influencers — blacklist exclusion
# ---------------------------------------------------------------------------


class TestSelectInfluencersBlacklist:
    @pytest.mark.asyncio
    async def test_blacklisted_flag_on_influencer_excludes(self):
        agent = _make_agent(is_blacklisted=False)
        influencers = [
            _make_influencer("inf-bl", blacklisted=True),
            _make_influencer("inf-ok"),
        ]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-bl" not in ids
        assert "inf-ok" in ids

    @pytest.mark.asyncio
    async def test_blacklist_service_check_excludes(self):
        """Influencer not flagged locally but blacklisted in DB is excluded."""
        bl_svc = MagicMock(spec=BlacklistService)

        async def _is_blacklisted(inf_id: str) -> bool:
            return inf_id == "inf-db-bl"

        bl_svc.is_blacklisted = _is_blacklisted
        agent = SelectorAgent(blacklist_service=bl_svc, redis=None)

        influencers = [
            _make_influencer("inf-db-bl"),
            _make_influencer("inf-ok"),
        ]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert "inf-db-bl" not in ids
        assert "inf-ok" in ids

    @pytest.mark.asyncio
    async def test_all_blacklisted_returns_empty_with_suggestion(self):
        agent = _make_agent(is_blacklisted=True)
        influencers = [_make_influencer("inf-1"), _make_influencer("inf-2")]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 0
        assert result.suggestion is not None


# ---------------------------------------------------------------------------
# select_influencers — empty result suggestion
# ---------------------------------------------------------------------------


class TestSelectInfluencersEmptyResult:
    @pytest.mark.asyncio
    async def test_empty_result_returns_suggestion(self, agent):
        influencers = [_make_influencer("inf-1", follower_count=100)]
        criteria = _make_criteria(min_followers=1_000_000)

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 0
        assert result.suggestion is not None
        assert len(result.suggestion) > 0

    @pytest.mark.asyncio
    async def test_empty_dataset_returns_suggestion(self, agent):
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", [])

        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_non_empty_result_has_no_suggestion(self, agent):
        influencers = [_make_influencer("inf-1")]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 1
        assert result.suggestion is None


# ---------------------------------------------------------------------------
# calculate_relevance_score
# ---------------------------------------------------------------------------


class TestCalculateRelevanceScore:
    @pytest.mark.asyncio
    async def test_score_in_range_zero_to_one(self, agent):
        influencer = _make_influencer(follower_count=500_000, engagement_rate=0.1)
        criteria = _make_criteria()

        score = await agent.calculate_relevance_score(influencer, criteria)

        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_score_is_deterministic(self, agent):
        influencer = _make_influencer(follower_count=200_000, engagement_rate=0.07)
        criteria = _make_criteria(
            content_categories=["fashion"],
            locations=["Jakarta"],
        )

        score1 = await agent.calculate_relevance_score(influencer, criteria)
        score2 = await agent.calculate_relevance_score(influencer, criteria)

        assert score1 == score2

    @pytest.mark.asyncio
    async def test_higher_followers_gives_higher_score(self, agent):
        criteria = _make_criteria()
        low = _make_influencer("low", follower_count=1_000, engagement_rate=0.0)
        high = _make_influencer("high", follower_count=5_000_000, engagement_rate=0.0)

        score_low = await agent.calculate_relevance_score(low, criteria)
        score_high = await agent.calculate_relevance_score(high, criteria)

        assert score_high > score_low

    @pytest.mark.asyncio
    async def test_category_match_increases_score(self, agent):
        criteria = _make_criteria(content_categories=["fashion"])
        match = _make_influencer("match", content_categories=["fashion"])
        no_match = _make_influencer("no", content_categories=["gaming"])

        score_match = await agent.calculate_relevance_score(match, criteria)
        score_no = await agent.calculate_relevance_score(no_match, criteria)

        assert score_match > score_no

    @pytest.mark.asyncio
    async def test_location_match_increases_score(self, agent):
        criteria = _make_criteria(locations=["Jakarta"])
        match = _make_influencer("match", location="Jakarta")
        no_match = _make_influencer("no", location="Surabaya")

        score_match = await agent.calculate_relevance_score(match, criteria)
        score_no = await agent.calculate_relevance_score(no_match, criteria)

        assert score_match > score_no

    @pytest.mark.asyncio
    async def test_score_clamped_at_one_for_extreme_values(self, agent):
        """Weights summing to > 1.0 should still produce score ≤ 1.0."""
        weights = CriteriaWeights(
            follower_count=0.5,
            engagement_rate=0.5,
            category_match=0.5,
            location_match=0.5,
        )
        criteria = _make_criteria(
            content_categories=["fashion"],
            locations=["Jakarta"],
            weights=weights,
        )
        influencer = _make_influencer(
            follower_count=10_000_000,
            engagement_rate=1.0,
            content_categories=["fashion"],
            location="Jakarta",
        )

        score = await agent.calculate_relevance_score(influencer, criteria)

        assert score <= 1.0

    @pytest.mark.asyncio
    async def test_score_zero_for_zero_engagement_and_followers(self, agent):
        influencer = _make_influencer(follower_count=0, engagement_rate=0.0)
        criteria = _make_criteria(
            content_categories=["gaming"],  # no match
            locations=["Bali"],             # no match
        )
        # Override influencer categories/location to ensure no match
        influencer.content_categories = ["fashion"]
        influencer.location = "Jakarta"

        score = await agent.calculate_relevance_score(influencer, criteria)

        assert score == 0.0

    @pytest.mark.asyncio
    async def test_no_category_filter_gives_full_category_score(self, agent):
        """When criteria has no content_categories, category component = 1.0."""
        weights = CriteriaWeights(
            follower_count=0.0,
            engagement_rate=0.0,
            category_match=1.0,
            location_match=0.0,
        )
        criteria = _make_criteria(content_categories=None, weights=weights)
        influencer = _make_influencer(content_categories=["anything"])

        score = await agent.calculate_relevance_score(influencer, criteria)

        assert score == 1.0

    @pytest.mark.asyncio
    async def test_no_location_filter_gives_full_location_score(self, agent):
        """When criteria has no locations, location component = 1.0."""
        weights = CriteriaWeights(
            follower_count=0.0,
            engagement_rate=0.0,
            category_match=0.0,
            location_match=1.0,
        )
        criteria = _make_criteria(locations=None, weights=weights)
        influencer = _make_influencer(location="Anywhere")

        score = await agent.calculate_relevance_score(influencer, criteria)

        assert score == 1.0


# ---------------------------------------------------------------------------
# save_criteria_template
# ---------------------------------------------------------------------------


class TestSaveCriteriaTemplate:
    def _make_db(self) -> AsyncMock:
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock())
        db.flush = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_returns_criteria_with_is_template_true(self, agent):
        db = self._make_db()
        criteria = _make_criteria(min_followers=10_000)

        saved = await agent.save_criteria_template(criteria, db)

        assert saved.is_template is True

    @pytest.mark.asyncio
    async def test_preserves_criteria_fields(self, agent):
        db = self._make_db()
        criteria = SelectionCriteria(
            id="crit-tmpl",
            name="My Template",
            min_followers=5_000,
            max_followers=500_000,
            min_engagement_rate=0.03,
            content_categories=["beauty", "lifestyle"],
            locations=["Jakarta", "Bandung"],
            criteria_weights=CriteriaWeights(
                follower_count=0.25,
                engagement_rate=0.45,
                category_match=0.2,
                location_match=0.1,
            ),
        )

        saved = await agent.save_criteria_template(criteria, db)

        assert saved.name == "My Template"
        assert saved.min_followers == 5_000
        assert saved.max_followers == 500_000
        assert saved.min_engagement_rate == 0.03
        assert saved.content_categories == ["beauty", "lifestyle"]
        assert saved.locations == ["Jakarta", "Bandung"]

    @pytest.mark.asyncio
    async def test_calls_db_execute_and_flush(self, agent):
        db = self._make_db()
        criteria = _make_criteria()

        await agent.save_criteria_template(criteria, db)

        db.execute.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_existing_id_when_provided(self, agent):
        db = self._make_db()
        criteria = SelectionCriteria(id="fixed-id", name="Fixed")

        saved = await agent.save_criteria_template(criteria, db)

        assert saved.id == "fixed-id"

    @pytest.mark.asyncio
    async def test_generates_id_when_empty(self, agent):
        db = self._make_db()
        criteria = SelectionCriteria(id="", name="No ID")

        saved = await agent.save_criteria_template(criteria, db)

        # Should generate a UUID (36 chars)
        assert len(saved.id) == 36


# ---------------------------------------------------------------------------
# Redis event publishing
# ---------------------------------------------------------------------------


class TestRedisEventPublishing:
    @pytest.mark.asyncio
    async def test_publishes_event_when_redis_configured(self):
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock()

        bl_svc = _make_blacklist_service(is_blacklisted=False)
        agent = SelectorAgent(blacklist_service=bl_svc, redis=redis_mock)

        influencers = [_make_influencer("inf-1")]
        criteria = _make_criteria()

        await agent.select_influencers(criteria, "camp-42", influencers)

        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args
        assert call_args[0][0] == "agent:events"
        event_data = call_args[0][1]
        assert event_data["type"] == "influencers_selected"
        assert event_data["campaign_id"] == "camp-42"
        assert event_data["count"] == "1"

    @pytest.mark.asyncio
    async def test_no_error_when_redis_not_configured(self, agent):
        """Agent with redis=None should not raise."""
        influencers = [_make_influencer("inf-1")]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_redis_error_does_not_break_selection(self):
        redis_mock = AsyncMock()
        redis_mock.xadd = AsyncMock(side_effect=Exception("Redis down"))

        bl_svc = _make_blacklist_service(is_blacklisted=False)
        agent = SelectorAgent(blacklist_service=bl_svc, redis=redis_mock)

        influencers = [_make_influencer("inf-1")]
        criteria = _make_criteria()

        result = await agent.select_influencers(criteria, "camp-1", influencers)

        # Selection result should still be valid despite Redis failure
        assert result.total_found == 1


# ---------------------------------------------------------------------------
# Edge Cases — Task 6.3 (Requirement 2.5)
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: empty dataset, all blacklisted, no criteria match."""

    # --- Empty dataset ---

    @pytest.mark.asyncio
    async def test_empty_dataset_total_found_is_zero(self, agent):
        result = await agent.select_influencers(_make_criteria(), "camp-1", [])
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_empty_dataset_influencers_list_is_empty(self, agent):
        result = await agent.select_influencers(_make_criteria(), "camp-1", [])
        assert result.influencers == []

    @pytest.mark.asyncio
    async def test_empty_dataset_suggestion_is_not_none(self, agent):
        result = await agent.select_influencers(_make_criteria(), "camp-1", [])
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_empty_dataset_suggestion_is_non_empty_string(self, agent):
        result = await agent.select_influencers(_make_criteria(), "camp-1", [])
        assert isinstance(result.suggestion, str)
        assert len(result.suggestion.strip()) > 0

    @pytest.mark.asyncio
    async def test_empty_dataset_with_strict_criteria_still_empty(self, agent):
        """Strict criteria on empty dataset should still return empty result."""
        criteria = _make_criteria(
            min_followers=1_000_000,
            min_engagement_rate=0.5,
            content_categories=["fashion"],
            locations=["Jakarta"],
        )
        result = await agent.select_influencers(criteria, "camp-1", [])
        assert result.total_found == 0
        assert result.influencers == []

    # --- All influencers blacklisted ---

    @pytest.mark.asyncio
    async def test_all_blacklisted_via_flag_total_found_is_zero(self):
        """All influencers with blacklisted=True → empty result."""
        agent = _make_agent(is_blacklisted=False)
        influencers = [
            _make_influencer("inf-1", blacklisted=True),
            _make_influencer("inf-2", blacklisted=True),
            _make_influencer("inf-3", blacklisted=True),
        ]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_all_blacklisted_via_service_total_found_is_zero(self):
        """All influencers blacklisted in DB → empty result."""
        agent = _make_agent(is_blacklisted=True)
        influencers = [_make_influencer("inf-1"), _make_influencer("inf-2")]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_all_blacklisted_returns_suggestion(self):
        agent = _make_agent(is_blacklisted=True)
        influencers = [_make_influencer("inf-1"), _make_influencer("inf-2")]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_all_blacklisted_influencers_list_is_empty(self):
        agent = _make_agent(is_blacklisted=True)
        influencers = [_make_influencer("inf-1"), _make_influencer("inf-2")]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)
        assert result.influencers == []

    @pytest.mark.asyncio
    async def test_mixed_blacklisted_only_non_blacklisted_returned(self):
        """Only non-blacklisted influencers should appear in results."""
        bl_svc = MagicMock(spec=BlacklistService)

        async def _is_blacklisted(inf_id: str) -> bool:
            return inf_id in {"inf-1", "inf-3"}

        bl_svc.is_blacklisted = _is_blacklisted
        agent = SelectorAgent(blacklist_service=bl_svc, redis=None)

        influencers = [
            _make_influencer("inf-1"),
            _make_influencer("inf-2"),
            _make_influencer("inf-3"),
        ]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)

        ids = [i.id for i in result.influencers]
        assert ids == ["inf-2"]
        assert result.total_found == 1

    # --- No influencer meets criteria ---

    @pytest.mark.asyncio
    async def test_no_match_min_followers_too_high(self, agent):
        influencers = [
            _make_influencer("inf-1", follower_count=1_000),
            _make_influencer("inf-2", follower_count=5_000),
        ]
        criteria = _make_criteria(min_followers=1_000_000)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_no_match_max_followers_too_low(self, agent):
        influencers = [
            _make_influencer("inf-1", follower_count=500_000),
            _make_influencer("inf-2", follower_count=1_000_000),
        ]
        criteria = _make_criteria(max_followers=100)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_no_match_engagement_rate_too_high(self, agent):
        influencers = [
            _make_influencer("inf-1", engagement_rate=0.01),
            _make_influencer("inf-2", engagement_rate=0.02),
        ]
        criteria = _make_criteria(min_engagement_rate=0.99)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_no_match_category_mismatch(self, agent):
        influencers = [
            _make_influencer("inf-1", content_categories=["gaming"]),
            _make_influencer("inf-2", content_categories=["tech"]),
        ]
        criteria = _make_criteria(content_categories=["fashion", "beauty"])
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_no_match_location_mismatch(self, agent):
        influencers = [
            _make_influencer("inf-1", location="Surabaya"),
            _make_influencer("inf-2", location="Medan"),
        ]
        criteria = _make_criteria(locations=["Bali", "Yogyakarta"])
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_no_match_combined_criteria(self, agent):
        """All criteria combined result in zero matches."""
        influencers = [
            _make_influencer(
                "inf-1",
                follower_count=10_000,
                engagement_rate=0.02,
                content_categories=["gaming"],
                location="Surabaya",
            )
        ]
        criteria = _make_criteria(
            min_followers=100_000,
            min_engagement_rate=0.1,
            content_categories=["fashion"],
            locations=["Jakarta"],
        )
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 0
        assert result.suggestion is not None

    @pytest.mark.asyncio
    async def test_suggestion_mentions_relaxing_criteria(self, agent):
        """Suggestion text should hint at relaxing criteria."""
        influencers = [_make_influencer("inf-1", follower_count=100)]
        criteria = _make_criteria(min_followers=10_000_000)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        # Suggestion should contain actionable advice
        assert result.suggestion is not None
        suggestion_lower = result.suggestion.lower()
        # Should mention loosening/relaxing criteria in some form
        assert any(
            word in suggestion_lower
            for word in ["longgar", "kurangi", "perluas", "turunkan", "kriteria"]
        )

    @pytest.mark.asyncio
    async def test_boundary_exactly_at_min_followers_passes(self, agent):
        """Influencer with follower_count == min_followers should pass."""
        influencers = [_make_influencer("inf-1", follower_count=10_000)]
        criteria = _make_criteria(min_followers=10_000)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_boundary_exactly_at_max_followers_passes(self, agent):
        """Influencer with follower_count == max_followers should pass."""
        influencers = [_make_influencer("inf-1", follower_count=100_000)]
        criteria = _make_criteria(max_followers=100_000)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_boundary_exactly_at_min_engagement_passes(self, agent):
        """Influencer with engagement_rate == min_engagement_rate should pass."""
        influencers = [_make_influencer("inf-1", engagement_rate=0.05)]
        criteria = _make_criteria(min_engagement_rate=0.05)
        result = await agent.select_influencers(criteria, "camp-1", influencers)
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_single_influencer_not_blacklisted_not_filtered_returns_one(self, agent):
        """Sanity check: single valid influencer with no filters → 1 result."""
        influencers = [_make_influencer("inf-1")]
        result = await agent.select_influencers(_make_criteria(), "camp-1", influencers)
        assert result.total_found == 1
        assert result.suggestion is None
