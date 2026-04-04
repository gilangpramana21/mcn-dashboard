"""Unit tests for integration clients."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.exceptions import AffiliateCenterError, TikTokAPIError, TokenExpiredError, WhatsAppAPIError
from app.integrations.affiliate_center import AffiliateCenterClient, OAuthToken, PaginatedResult
from app.integrations.tiktok_api import CircuitBreaker, TikTokAPIClient, VideoMetrics
from app.integrations.whatsapp_api import MessageResult, MessageStatus, WhatsAppAPIClient


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    def test_initially_closed(self):
        cb = CircuitBreaker(max_failures=5, window_seconds=60, reset_seconds=30)
        assert not cb.is_open()

    def test_opens_after_max_failures(self):
        cb = CircuitBreaker(max_failures=3, window_seconds=60, reset_seconds=30)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open()

    def test_does_not_open_before_max_failures(self):
        cb = CircuitBreaker(max_failures=5, window_seconds=60, reset_seconds=30)
        for _ in range(4):
            cb.record_failure()
        assert not cb.is_open()

    def test_resets_after_cooldown(self):
        cb = CircuitBreaker(max_failures=3, window_seconds=60, reset_seconds=0.01)
        for _ in range(3):
            cb.record_failure()
        assert cb.is_open()
        time.sleep(0.05)
        assert not cb.is_open()

    def test_success_does_not_open(self):
        cb = CircuitBreaker(max_failures=3, window_seconds=60, reset_seconds=30)
        cb.record_success()
        assert not cb.is_open()

    def test_failures_outside_window_dont_count(self):
        # Only 2 failures (below threshold=3), then window expires — circuit stays closed
        cb = CircuitBreaker(max_failures=3, window_seconds=0.05, reset_seconds=30)
        for _ in range(2):
            cb.record_failure()
        time.sleep(0.1)
        # After window expires, old failures are pruned — adding one more shouldn't open
        cb.record_failure()
        assert not cb.is_open()


# ---------------------------------------------------------------------------
# AffiliateCenterClient tests
# ---------------------------------------------------------------------------


def _make_token() -> OAuthToken:
    return OAuthToken(access_token="acc", refresh_token="ref")


def _mock_response(status_code: int, json_data: dict) -> httpx.Response:
    response = MagicMock(spec=httpx.Response)
    response.status_code = status_code
    response.json.return_value = json_data
    response.text = str(json_data)
    return response


class TestAffiliateCenterClient:
    @pytest.mark.asyncio
    async def test_authenticate_stores_token(self):
        client = AffiliateCenterClient()
        mock_resp = _mock_response(200, {
            "access_token": "tok123",
            "refresh_token": "ref456",
            "token_type": "Bearer",
            "expires_in": 3600,
        })
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            token = await client.authenticate()
        assert token.access_token == "tok123"
        assert client._token is token

    @pytest.mark.asyncio
    async def test_authenticate_raises_on_error(self):
        from tenacity import RetryError
        client = AffiliateCenterClient()
        mock_resp = _mock_response(401, {"error": "unauthorized"})
        # Patch asyncio.sleep to skip tenacity wait delays
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
                with pytest.raises((AffiliateCenterError, RetryError)):
                    await client.authenticate()

    @pytest.mark.asyncio
    async def test_refresh_token_updates_stored_token(self):
        client = AffiliateCenterClient()
        old_token = _make_token()
        mock_resp = _mock_response(200, {
            "access_token": "new_acc",
            "refresh_token": "new_ref",
            "token_type": "Bearer",
            "expires_in": 3600,
        })
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
            new_token = await client.refresh_token(old_token)
        assert new_token.access_token == "new_acc"

    @pytest.mark.asyncio
    async def test_refresh_token_raises_token_expired_on_error(self):
        from tenacity import RetryError
        client = AffiliateCenterClient()
        old_token = _make_token()
        mock_resp = _mock_response(400, {"error": "invalid_grant"})
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp):
                with pytest.raises((TokenExpiredError, RetryError)):
                    await client.refresh_token(old_token)

    @pytest.mark.asyncio
    async def test_get_influencers_caps_page_size_at_100(self):
        client = AffiliateCenterClient()
        client._token = _make_token()
        captured_params = {}

        async def fake_request(method, path, headers=None, params=None, **kwargs):
            captured_params.update(params or {})
            return _mock_response(200, {"items": [], "total": 0, "has_next": False})

        with patch.object(client, "_request_with_token_refresh", side_effect=fake_request):
            result = await client.get_influencers(page=1, page_size=200)

        assert captured_params["page_size"] == 100
        assert isinstance(result, PaginatedResult)

    @pytest.mark.asyncio
    async def test_get_influencers_returns_paginated_result(self):
        client = AffiliateCenterClient()
        client._token = _make_token()
        influencer_data = {
            "id": "inf1",
            "tiktok_user_id": "ttu1",
            "name": "Test User",
            "phone_number": "+6281234567890",
            "follower_count": 10000,
            "engagement_rate": 0.05,
            "content_categories": ["fashion"],
            "location": "Jakarta",
        }

        async def fake_request(method, path, **kwargs):
            return _mock_response(200, {"items": [influencer_data], "total": 1, "has_next": False})

        with patch.object(client, "_request_with_token_refresh", side_effect=fake_request):
            result = await client.get_influencers(page=1)

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].name == "Test User"


# ---------------------------------------------------------------------------
# TikTokAPIClient tests
# ---------------------------------------------------------------------------


class TestTikTokAPIClient:
    @pytest.mark.asyncio
    async def test_get_video_metrics_returns_metrics(self):
        client = TikTokAPIClient()
        mock_resp = _mock_response(200, {
            "data": {
                "videos": [{
                    "view_count": 1000,
                    "like_count": 200,
                    "comment_count": 50,
                    "share_count": 30,
                }]
            }
        })
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_resp):
            metrics = await client.get_video_metrics("vid123")
        assert isinstance(metrics, VideoMetrics)
        assert metrics.views == 1000
        assert metrics.likes == 200
        assert metrics.comments == 50
        assert metrics.shares == 30

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        client = TikTokAPIClient()
        # Force circuit open
        for _ in range(5):
            client._circuit_breaker.record_failure()
        with pytest.raises(TikTokAPIError, match="Circuit breaker"):
            await client.get_video_metrics("vid123")

    @pytest.mark.asyncio
    async def test_api_error_records_failure(self):
        client = TikTokAPIClient()
        mock_resp = _mock_response(500, {"error": "server error"})
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(TikTokAPIError):
                await client.get_video_metrics("vid123")
        assert len(client._circuit_breaker._failure_timestamps) == 1

    @pytest.mark.asyncio
    async def test_send_seller_center_chat_returns_message_id(self):
        client = TikTokAPIClient()
        mock_resp = _mock_response(200, {"data": {"message_id": "msg_abc"}})
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_resp):
            msg_id = await client.send_seller_center_chat("aff1", "Hello!")
        assert msg_id == "msg_abc"

    @pytest.mark.asyncio
    async def test_get_chat_replies_returns_list(self):
        client = TikTokAPIClient()
        mock_resp = _mock_response(200, {"data": {"messages": [{"id": "r1", "text": "Hi"}]}})
        with patch.object(client, "_request", new_callable=AsyncMock, return_value=mock_resp):
            replies = await client.get_chat_replies("aff1", "msg_abc")
        assert len(replies) == 1
        assert replies[0]["text"] == "Hi"


# ---------------------------------------------------------------------------
# WhatsAppAPIClient tests
# ---------------------------------------------------------------------------


class TestWhatsAppAPIClient:
    @pytest.mark.asyncio
    async def test_send_message_returns_result(self):
        """Test send_message returns MessageResult."""
        client = WhatsAppAPIClient()
        mock_result = MessageResult(
            message_id="wa_123",
            status=MessageStatus.QUEUED,
            phone_number="+6281234567890",
        )
        with patch.object(client._multi_client, "send_text_message", new_callable=AsyncMock, return_value=mock_result):
            # Set a fake phone_number_id so it doesn't take the fallback path
            client._default_phone_number_id = "fake_phone_id"
            result = await client.send_message("+6281234567890", "Hello!")
        assert isinstance(result, MessageResult)
        assert result.message_id == "wa_123"
        assert result.status == MessageStatus.QUEUED
        assert result.phone_number == "+6281234567890"

    @pytest.mark.asyncio
    async def test_get_message_status_returns_status(self):
        """Test get_message_status returns MessageStatus."""
        client = WhatsAppAPIClient()
        with patch.object(client._multi_client, "get_message_status", new_callable=AsyncMock, return_value=MessageStatus.DELIVERED):
            status = await client.get_message_status("wa_123")
        assert status == MessageStatus.DELIVERED

    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_when_open(self):
        """Test that circuit breaker in multi_client rejects when open."""
        client = WhatsAppAPIClient()
        client._default_phone_number_id = "fake_phone_id"
        # Force circuit breaker open on the multi_client
        for _ in range(5):
            client._multi_client._circuit_breaker.record_failure()
        with pytest.raises(WhatsAppAPIError):
            await client.send_message("+6281234567890", "test")

    @pytest.mark.asyncio
    async def test_send_message_no_phone_id_returns_mock(self):
        """Test that missing phone_number_id returns mock result without raising."""
        client = WhatsAppAPIClient()
        client._default_phone_number_id = ""  # No config
        result = await client.send_message("+6281234567890", "test")
        assert isinstance(result, MessageResult)
        assert result.status == MessageStatus.SENT
