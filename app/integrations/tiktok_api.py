"""TikTok API client with circuit breaker."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from app.config import get_settings
from app.exceptions import TikTokAPIError


# ---------------------------------------------------------------------------
# Helper dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TikTokContent:
    video_id: str
    user_id: str
    description: str
    created_at: datetime
    share_url: str
    affiliate_links: List[str] = field(default_factory=list)


@dataclass
class VideoMetrics:
    video_id: str
    views: int
    likes: int
    comments: int
    shares: int


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Simple circuit breaker: open after `max_failures` in `window_seconds`,
    stay open for `reset_seconds`."""

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: float = 60.0,
        reset_seconds: float = 30.0,
    ) -> None:
        self._max_failures = max_failures
        self._window_seconds = window_seconds
        self._reset_seconds = reset_seconds
        self._failure_timestamps: List[float] = []
        self._open_until: Optional[float] = None

    def _prune(self) -> None:
        now = time.monotonic()
        cutoff = now - self._window_seconds
        self._failure_timestamps = [t for t in self._failure_timestamps if t >= cutoff]

    def is_open(self) -> bool:
        if self._open_until is not None:
            if time.monotonic() < self._open_until:
                return True
            # Reset after cooldown
            self._open_until = None
            self._failure_timestamps = []
        return False

    def record_failure(self) -> None:
        self._prune()
        self._failure_timestamps.append(time.monotonic())
        if len(self._failure_timestamps) >= self._max_failures:
            self._open_until = time.monotonic() + self._reset_seconds

    def record_success(self) -> None:
        self._prune()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class TikTokAPIClient:
    """Async HTTP client for the TikTok API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.TIKTOK_API_KEY
        self._circuit_breaker = CircuitBreaker(
            max_failures=5,
            window_seconds=60.0,
            reset_seconds=30.0,
        )

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="https://open.tiktokapis.com",
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._circuit_breaker.is_open():
            raise TikTokAPIError("Circuit breaker is open — TikTok API requests are temporarily rejected.")
        try:
            async with self._make_client() as client:
                response = await client.request(method, path, **kwargs)
            if response.status_code >= 400:
                self._circuit_breaker.record_failure()
                raise TikTokAPIError(
                    f"TikTok API error {response.status_code}: {response.text}"
                )
            self._circuit_breaker.record_success()
            return response
        except TikTokAPIError:
            raise
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise TikTokAPIError(f"TikTok API request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    async def get_user_videos(
        self,
        user_id: str,
        since: datetime,
    ) -> List[TikTokContent]:
        """Fetch TikTok videos for a user published since `since`."""
        response = await self._request(
            "GET",
            f"/v2/video/list/",
            params={"user_id": user_id, "since": since.isoformat()},
        )
        data = response.json()
        videos = []
        for item in data.get("data", {}).get("videos", []):
            videos.append(
                TikTokContent(
                    video_id=item["id"],
                    user_id=user_id,
                    description=item.get("description", ""),
                    created_at=datetime.fromisoformat(item["create_time"])
                    if isinstance(item.get("create_time"), str)
                    else datetime.utcfromtimestamp(item.get("create_time", 0)),
                    share_url=item.get("share_url", ""),
                    affiliate_links=item.get("affiliate_links", []),
                )
            )
        return videos

    async def get_video_metrics(self, video_id: str) -> VideoMetrics:
        """Fetch metrics (views, likes, comments, shares) for a video."""
        response = await self._request(
            "GET",
            f"/v2/video/query/",
            params={"video_id": video_id, "fields": "view_count,like_count,comment_count,share_count"},
        )
        data = response.json()
        item = data.get("data", {}).get("videos", [{}])[0]
        return VideoMetrics(
            video_id=video_id,
            views=int(item.get("view_count", 0)),
            likes=int(item.get("like_count", 0)),
            comments=int(item.get("comment_count", 0)),
            shares=int(item.get("share_count", 0)),
        )

    async def get_affiliate_profile(self, affiliate_id: str) -> Dict:
        """Fetch affiliate profile including bio and social links."""
        response = await self._request(
            "GET",
            f"/v2/user/info/",
            params={"affiliate_id": affiliate_id},
        )
        return response.json().get("data", {})

    async def send_seller_center_chat(
        self,
        affiliate_id: str,
        message: str,
    ) -> str:
        """Send a message via TikTok Seller Center chat. Returns message_id."""
        response = await self._request(
            "POST",
            "/v2/seller/chat/send/",
            json={"affiliate_id": affiliate_id, "message": message},
        )
        data = response.json()
        return data.get("data", {}).get("message_id", "")

    async def get_chat_replies(
        self,
        affiliate_id: str,
        since_message_id: str,
    ) -> List[Dict]:
        """Fetch chat replies from an affiliate since a given message_id."""
        response = await self._request(
            "GET",
            "/v2/seller/chat/replies/",
            params={"affiliate_id": affiliate_id, "since_message_id": since_message_id},
        )
        data = response.json()
        return data.get("data", {}).get("messages", [])
