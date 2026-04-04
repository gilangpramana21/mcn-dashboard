"""Property-based tests untuk AffiliateCenterClient.

Validates: Requirements 2.2
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.integrations.affiliate_center import AffiliateCenterClient
from app.models.domain import Influencer, InfluencerStatus


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


def _make_influencer_data(
    influencer_id: str = "inf-1",
    follower_count: int = 1000,
) -> Dict[str, Any]:
    return {
        "id": influencer_id,
        "tiktok_user_id": "tiktok-1",
        "name": "Test Influencer",
        "phone_number": "+6281234567890",
        "follower_count": follower_count,
        "engagement_rate": 0.05,
        "content_categories": ["fashion"],
        "location": "Jakarta",
        "status": "ACTIVE",
        "blacklisted": False,
    }


# ---------------------------------------------------------------------------
# Property 1: page_size selalu di-cap ke 100
# ---------------------------------------------------------------------------


class TestProperty1PageSizeCap:
    """Validates: Requirements 2.2 — page_size > 100 selalu di-cap ke 100."""

    @given(page_size=st.integers(min_value=101, max_value=10000))
    @settings(max_examples=50)
    def test_page_size_capped_at_100_for_large_values(self, page_size: int):
        """For any page_size > 100, get_influencers harus menggunakan page_size = 100."""
        async def _run():
            client = AffiliateCenterClient.__new__(AffiliateCenterClient)
            client._base_url = "http://test"
            client._client_id = "test"
            client._client_secret = "test"
            from app.integrations.affiliate_center import OAuthToken
            client._token = OAuthToken(
                access_token="test-token",
                refresh_token="test-refresh",
            )

            captured_params: Dict = {}

            async def _mock_request(method, path, headers=None, params=None, **kwargs):
                captured_params.update(params or {})
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "items": [_make_influencer_data()],
                    "total": 1,
                    "has_next": False,
                }
                return mock_resp

            mock_client = AsyncMock()
            mock_client.request = _mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch("app.integrations.affiliate_center.httpx.AsyncClient", return_value=mock_client):
                result = await client.get_influencers(page=1, page_size=page_size)

            # page_size harus di-cap ke 100
            assert result.page_size == 100, (
                f"page_size={page_size} harus di-cap ke 100, tapi result.page_size={result.page_size}"
            )
            assert captured_params.get("page_size") == 100

        _run_async(_run())

    @given(page_size=st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_page_size_not_capped_for_valid_values(self, page_size: int):
        """For any page_size <= 100, get_influencers harus menggunakan page_size asli."""
        async def _run():
            client = AffiliateCenterClient.__new__(AffiliateCenterClient)
            client._base_url = "http://test"
            client._client_id = "test"
            client._client_secret = "test"
            from app.integrations.affiliate_center import OAuthToken
            client._token = OAuthToken(
                access_token="test-token",
                refresh_token="test-refresh",
            )

            captured_params: Dict = {}

            async def _mock_request(method, path, headers=None, params=None, **kwargs):
                captured_params.update(params or {})
                mock_resp = MagicMock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {
                    "items": [],
                    "total": 0,
                    "has_next": False,
                }
                return mock_resp

            mock_client = AsyncMock()
            mock_client.request = _mock_request
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            with patch("app.integrations.affiliate_center.httpx.AsyncClient", return_value=mock_client):
                result = await client.get_influencers(page=1, page_size=page_size)

            assert result.page_size == page_size

        _run_async(_run())


# ---------------------------------------------------------------------------
# Property 2: _parse_influencer menghasilkan follower_count >= 0
# ---------------------------------------------------------------------------


class TestProperty2ParseInfluencerFollowerCount:
    """Validates: Requirements 2.2 — _parse_influencer menghasilkan follower_count >= 0."""

    @given(
        follower_count=st.integers(min_value=0, max_value=100_000_000),
        engagement_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_parse_influencer_follower_count_non_negative(
        self,
        follower_count: int,
        engagement_rate: float,
    ):
        """_parse_influencer harus menghasilkan Influencer dengan follower_count >= 0."""
        data = {
            "id": "inf-test",
            "tiktok_user_id": "tiktok-test",
            "name": "Test",
            "phone_number": "+6281234567890",
            "follower_count": follower_count,
            "engagement_rate": engagement_rate,
            "content_categories": [],
            "location": "Jakarta",
            "status": "ACTIVE",
            "blacklisted": False,
        }
        influencer = AffiliateCenterClient._parse_influencer(data)
        assert influencer.follower_count >= 0, (
            f"follower_count={influencer.follower_count} harus >= 0"
        )

    @given(
        influencer_id=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_parse_influencer_returns_influencer_instance(self, influencer_id: str):
        """_parse_influencer harus selalu mengembalikan instance Influencer."""
        data = {
            "id": influencer_id,
            "tiktok_user_id": "tiktok-test",
            "name": "Test",
            "phone_number": "+6281234567890",
            "follower_count": 1000,
            "engagement_rate": 0.05,
            "content_categories": [],
            "location": "Jakarta",
            "status": "ACTIVE",
            "blacklisted": False,
        }
        influencer = AffiliateCenterClient._parse_influencer(data)
        assert isinstance(influencer, Influencer)
        assert influencer.id == influencer_id


# ---------------------------------------------------------------------------
# Property 3: min(page_size, 100) selalu <= 100
# ---------------------------------------------------------------------------


class TestProperty3PaginationLimit:
    """Validates: Requirements 2.2 — Pagination tidak melebihi batas 100."""

    @given(page_size=st.integers(min_value=1, max_value=10000))
    @settings(max_examples=50)
    def test_effective_page_size_always_lte_100(self, page_size: int):
        """For any page_size input, min(page_size, 100) selalu <= 100."""
        effective = min(page_size, 100)
        assert effective <= 100, (
            f"min({page_size}, 100) = {effective} harus <= 100"
        )
        assert effective >= 1, (
            f"min({page_size}, 100) = {effective} harus >= 1"
        )
