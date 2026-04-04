"""Affiliate Center Indonesia API client."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Generic, List, Optional, TypeVar

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import get_settings
from app.exceptions import AffiliateCenterError, TokenExpiredError
from app.models.domain import Influencer

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Helper dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    expires_at: Optional[datetime] = None


@dataclass
class PaginatedResult(Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool = False


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class AffiliateCenterClient:
    """Async HTTP client for the Affiliate Center Indonesia API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.AFFILIATE_CENTER_API_URL
        self._client_id = settings.AFFILIATE_CENTER_CLIENT_ID
        self._client_secret = settings.AFFILIATE_CENTER_CLIENT_SECRET
        self._token: Optional[OAuthToken] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, timeout=30.0)

    def _auth_headers(self) -> Dict[str, str]:
        if self._token is None:
            raise AffiliateCenterError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self._token.access_token}"}

    async def _request_with_token_refresh(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Execute a request; on 401 refresh token and retry once."""
        async with self._make_client() as client:
            response = await client.request(
                method, path, headers=self._auth_headers(), **kwargs
            )
            if response.status_code == 401:
                # Refresh and retry once
                if self._token is None:
                    raise TokenExpiredError("Token expired and no token available to refresh.")
                self._token = await self.refresh_token(self._token)
                response = await client.request(
                    method, path, headers=self._auth_headers(), **kwargs
                )
            if response.status_code >= 400:
                raise AffiliateCenterError(
                    f"Affiliate Center API error {response.status_code}: {response.text}"
                )
            return response

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def authenticate(self) -> OAuthToken:
        """POST /oauth/token — obtain OAuth token using client credentials."""
        async with self._make_client() as client:
            response = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            if response.status_code >= 400:
                raise AffiliateCenterError(
                    f"Authentication failed {response.status_code}: {response.text}"
                )
            data = response.json()
            token = OAuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
            )
            self._token = token
            return token

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def refresh_token(self, token: OAuthToken) -> OAuthToken:
        """POST /oauth/token — refresh an existing OAuth token."""
        async with self._make_client() as client:
            response = await client.post(
                "/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": token.refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
            )
            if response.status_code >= 400:
                raise TokenExpiredError(
                    f"Token refresh failed {response.status_code}: {response.text}"
                )
            data = response.json()
            new_token = OAuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", token.refresh_token),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
            )
            self._token = new_token
            return new_token

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def get_influencers(
        self,
        page: int,
        page_size: int = 100,
        filters: Optional[Dict] = None,
    ) -> PaginatedResult[Influencer]:
        """GET /influencers — fetch a paginated page of influencers (max 100/page)."""
        page_size = min(page_size, 100)
        params: Dict = {"page": page, "page_size": page_size}
        if filters:
            params.update(filters)

        response = await self._request_with_token_refresh("GET", "/influencers", params=params)
        data = response.json()

        items = [self._parse_influencer(item) for item in data.get("items", [])]
        return PaginatedResult(
            items=items,
            total=data.get("total", len(items)),
            page=page,
            page_size=page_size,
            has_next=data.get("has_next", False),
        )

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(5))
    async def sync_influencer_data(self, since: datetime) -> List[Influencer]:
        """Fetch all influencers updated since `since` by iterating all pages."""
        all_influencers: List[Influencer] = []
        page = 1
        while True:
            result = await self.get_influencers(
                page=page,
                page_size=100,
                filters={"updated_since": since.isoformat()},
            )
            all_influencers.extend(result.items)
            if not result.has_next:
                break
            page += 1
        return all_influencers

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_influencer(data: Dict) -> Influencer:
        from app.models.domain import InfluencerStatus

        return Influencer(
            id=data["id"],
            tiktok_user_id=data.get("tiktok_user_id", ""),
            name=data.get("name", ""),
            phone_number=data.get("phone_number", ""),
            follower_count=int(data.get("follower_count", 0)),
            engagement_rate=float(data.get("engagement_rate", 0.0)),
            content_categories=data.get("content_categories", []),
            location=data.get("location", ""),
            relevance_score=data.get("relevance_score"),
            status=InfluencerStatus(data.get("status", InfluencerStatus.ACTIVE)),
            blacklisted=bool(data.get("blacklisted", False)),
            blacklist_reason=data.get("blacklist_reason"),
        )
