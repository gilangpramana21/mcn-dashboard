"""TikTok Shop Open API client — Affiliate APIs.

Dokumentasi: https://partner.tiktokshop.com/docv2/page/affiliate
Auth: OAuth 2.0 dengan App Key + App Secret
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.exceptions import TikTokAPIError
from app.integrations.tiktok_api import CircuitBreaker

logger = logging.getLogger(__name__)

TIKTOK_SHOP_BASE = "https://open-api.tiktokglobalshop.com"


class TikTokShopClient:
    """
    Client untuk TikTok Shop Open API (Affiliate APIs).

    Cara kerja:
    1. Seller authorize app via OAuth → dapat access_token
    2. Pakai access_token untuk semua request
    3. Setiap request di-sign dengan HMAC-SHA256

    Referensi: https://partner.tiktokshop.com/docv2/page/affiliate
    """

    def __init__(self, access_token: str) -> None:
        settings = get_settings()
        self._app_key = settings.TIKTOK_APP_KEY
        self._app_secret = settings.TIKTOK_APP_SECRET
        self._access_token = access_token
        self._circuit_breaker = CircuitBreaker(max_failures=5, window_seconds=60.0, reset_seconds=30.0)

    def _sign_request(self, path: str, params: Dict[str, Any], body: str = "") -> str:
        """Generate HMAC-SHA256 signature untuk TikTok Shop API."""
        timestamp = str(int(time.time()))
        # Sort params
        sorted_params = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        # String to sign: app_secret + path + sorted_params + body + timestamp
        sign_str = f"{self._app_secret}{path}{sorted_params}{body}{timestamp}"
        signature = hmac.new(
            self._app_secret.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        return signature, timestamp

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=TIKTOK_SHOP_BASE,
            headers={
                "Content-Type": "application/json",
                "x-tts-access-token": self._access_token,
            },
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if self._circuit_breaker.is_open():
            raise TikTokAPIError("Circuit breaker terbuka — TikTok Shop API ditolak sementara.")

        params = params or {}
        params["app_key"] = self._app_key

        import json as json_lib
        body_str = json_lib.dumps(json) if json else ""
        signature, timestamp = self._sign_request(path, params, body_str)
        params["sign"] = signature
        params["timestamp"] = timestamp

        try:
            async with self._make_client() as client:
                response = await client.request(method, path, params=params, json=json)

            data = response.json()
            code = data.get("code", 0)

            if response.status_code >= 400 or code not in (0, 200):
                self._circuit_breaker.record_failure()
                msg = data.get("message", response.text)
                raise TikTokAPIError(f"TikTok Shop API error {code}: {msg}")

            self._circuit_breaker.record_success()
            return data.get("data", {})

        except TikTokAPIError:
            raise
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise TikTokAPIError(f"Request gagal: {exc}") from exc

    # ──────────────────────────────────────────────────────────────────
    # Creator / Affiliator Search
    # ──────────────────────────────────────────────────────────────────

    async def search_creators(
        self,
        keyword: str = "",
        min_followers: int = 0,
        max_followers: int = 0,
        categories: Optional[List[str]] = None,
        page_size: int = 20,
        page_token: str = "",
    ) -> Dict[str, Any]:
        """
        Cari creator/affiliator di TikTok Shop Marketplace.

        Returns:
            {
                "creators": [...],
                "next_page_token": "...",
                "total_count": 123
            }
        """
        params: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        body: Dict[str, Any] = {}
        if keyword:
            body["keyword"] = keyword
        if min_followers:
            body["follower_count_min"] = min_followers
        if max_followers:
            body["follower_count_max"] = max_followers
        if categories:
            body["creator_categories"] = categories

        result = await self._request(
            "POST",
            "/api/v2/affiliate/creator/search",
            params=params,
            json=body,
        )
        return result

    async def get_creator_detail(self, creator_id: str) -> Dict[str, Any]:
        """Ambil detail lengkap satu creator."""
        result = await self._request(
            "GET",
            "/api/v2/affiliate/creator/detail",
            params={"creator_id": creator_id},
        )
        return result

    # ──────────────────────────────────────────────────────────────────
    # Targeted Collaboration (Undangan)
    # ──────────────────────────────────────────────────────────────────

    async def create_targeted_collaboration(
        self,
        creator_id: str,
        product_ids: List[str],
        commission_rate: float,
        message: str = "",
    ) -> Dict[str, Any]:
        """
        Kirim undangan kolaborasi targeted ke creator.
        Ini adalah cara resmi TikTok untuk 'menghubungi' creator via Seller Center.

        Args:
            creator_id: ID creator dari search result
            product_ids: Daftar produk yang ingin dipromosikan
            commission_rate: Komisi dalam persen (misal 15.0 = 15%)
            message: Pesan personal ke creator
        """
        body = {
            "creator_id": creator_id,
            "product_ids": product_ids,
            "commission_rate": commission_rate,
            "collaboration_message": message,
        }
        result = await self._request(
            "POST",
            "/api/v2/affiliate/collaboration/targeted/create",
            json=body,
        )
        return result

    async def list_collaborations(
        self,
        status: str = "",
        page_size: int = 20,
        page_token: str = "",
    ) -> Dict[str, Any]:
        """Daftar semua kolaborasi (pending, accepted, rejected)."""
        params: Dict[str, Any] = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token
        if status:
            params["status"] = status

        result = await self._request(
            "GET",
            "/api/v2/affiliate/collaboration/list",
            params=params,
        )
        return result

    # ──────────────────────────────────────────────────────────────────
    # Chat / Pesan
    # ──────────────────────────────────────────────────────────────────

    async def send_chat_message(
        self,
        creator_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """
        Kirim pesan chat ke creator via Seller Center.
        Dipakai untuk minta nomor WhatsApp.
        """
        body = {
            "creator_id": creator_id,
            "message": message,
            "message_type": "TEXT",
        }
        result = await self._request(
            "POST",
            "/api/v2/affiliate/chat/send",
            json=body,
        )
        return result

    async def get_chat_messages(
        self,
        creator_id: str,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Ambil history chat dengan creator."""
        result = await self._request(
            "GET",
            "/api/v2/affiliate/chat/messages",
            params={"creator_id": creator_id, "page_size": page_size},
        )
        return result


# ──────────────────────────────────────────────────────────────────────────────
# OAuth Helper
# ──────────────────────────────────────────────────────────────────────────────

class TikTokShopOAuth:
    """Helper untuk OAuth flow TikTok Shop."""

    def __init__(self) -> None:
        settings = get_settings()
        self._app_key = settings.TIKTOK_APP_KEY
        self._app_secret = settings.TIKTOK_APP_SECRET

    def get_auth_url(self, redirect_uri: str, state: str = "") -> str:
        """Generate URL untuk seller authorize app."""
        params = f"app_key={self._app_key}&redirect_uri={redirect_uri}"
        if state:
            params += f"&state={state}"
        return f"https://auth.tiktok-shops.com/oauth/authorize?{params}"

    async def exchange_code(self, auth_code: str) -> Dict[str, Any]:
        """Tukar auth_code dengan access_token."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://auth.tiktok-shops.com/api/v2/token/get",
                params={
                    "app_key": self._app_key,
                    "app_secret": self._app_secret,
                    "auth_code": auth_code,
                    "grant_type": "authorized_code",
                },
            )
        data = response.json()
        if data.get("code") != 0:
            raise TikTokAPIError(f"OAuth error: {data.get('message')}")
        return data.get("data", {})

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access_token yang sudah expired."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://auth.tiktok-shops.com/api/v2/token/refresh",
                params={
                    "app_key": self._app_key,
                    "app_secret": self._app_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
        data = response.json()
        if data.get("code") != 0:
            raise TikTokAPIError(f"Token refresh error: {data.get('message')}")
        return data.get("data", {})
