"""WhatsApp Business API client — Meta Cloud API, multi-number support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings
from app.exceptions import WhatsAppAPIError
from app.integrations.tiktok_api import CircuitBreaker

logger = logging.getLogger(__name__)

# Meta Cloud API base URL
META_API_BASE = "https://graph.facebook.com/v19.0"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class MessageResult:
    message_id: str
    status: MessageStatus
    phone_number: str
    from_phone_number_id: str = ""
    error: Optional[str] = None


@dataclass
class PhoneNumberConfig:
    """Konfigurasi satu nomor WhatsApp Business."""
    phone_number_id: str      # Meta's phone_number_id (dari dashboard Meta)
    display_phone: str        # Nomor tampilan e.g. +6281100000001
    category: str             # FnB, Fashion, Skincare, dll
    display_name: str = ""


# ---------------------------------------------------------------------------
# Multi-Number WhatsApp Client
# ---------------------------------------------------------------------------


class WhatsAppMultiClient:
    """
    Satu API key Meta, banyak nomor WA.
    Setiap nomor punya phone_number_id berbeda tapi pakai token yang sama.
    
    Cara kerja Meta Cloud API:
    POST https://graph.facebook.com/v19.0/{phone_number_id}/messages
    Authorization: Bearer {WHATSAPP_API_TOKEN}
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.WHATSAPP_API_TOKEN
        self._circuit_breaker = CircuitBreaker(
            max_failures=5,
            window_seconds=60.0,
            reset_seconds=30.0,
        )

    def _make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=META_API_BASE,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        if self._circuit_breaker.is_open():
            raise WhatsAppAPIError("Circuit breaker terbuka — request WhatsApp ditolak sementara.")
        try:
            async with self._make_client() as client:
                response = await client.request(method, path, **kwargs)
            if response.status_code >= 400:
                self._circuit_breaker.record_failure()
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                raise WhatsAppAPIError(f"Meta API error {response.status_code}: {error_msg}")
            self._circuit_breaker.record_success()
            return response
        except WhatsAppAPIError:
            raise
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise WhatsAppAPIError(f"Request gagal: {exc}") from exc

    # ------------------------------------------------------------------
    # Kirim pesan teks biasa
    # ------------------------------------------------------------------

    async def send_text_message(
        self,
        phone_number_id: str,
        to_phone: str,
        message: str,
    ) -> MessageResult:
        """
        Kirim pesan teks ke nomor tujuan menggunakan phone_number_id tertentu.
        
        Args:
            phone_number_id: ID nomor pengirim dari Meta (bukan nomor HP)
            to_phone: Nomor tujuan format internasional tanpa + (e.g. 6281234567890)
            message: Isi pesan
        """
        to_clean = to_phone.lstrip("+").replace("-", "").replace(" ", "")
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_clean,
            "type": "text",
            "text": {"preview_url": False, "body": message},
        }

        response = await self._request("POST", f"/{phone_number_id}/messages", json=payload)
        data = response.json()

        msg_id = ""
        if "messages" in data and data["messages"]:
            msg_id = data["messages"][0].get("id", "")

        logger.info("Pesan terkirim via phone_number_id=%s ke %s, msg_id=%s", phone_number_id, to_clean, msg_id)

        return MessageResult(
            message_id=msg_id,
            status=MessageStatus.SENT,
            phone_number=to_phone,
            from_phone_number_id=phone_number_id,
        )

    # ------------------------------------------------------------------
    # Kirim pesan template (wajib untuk pesan pertama ke nomor baru)
    # ------------------------------------------------------------------

    async def send_template_message(
        self,
        phone_number_id: str,
        to_phone: str,
        template_name: str,
        language_code: str = "id",
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> MessageResult:
        """
        Kirim template message yang sudah diapprove Meta.
        Wajib dipakai untuk pesan pertama ke nomor yang belum pernah chat.
        
        Args:
            phone_number_id: ID nomor pengirim dari Meta
            to_phone: Nomor tujuan
            template_name: Nama template yang sudah diapprove (e.g. 'undangan_kolaborasi')
            language_code: Kode bahasa template (default: 'id' untuk Indonesia)
            components: Parameter template (opsional)
        """
        to_clean = to_phone.lstrip("+").replace("-", "").replace(" ", "")

        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": to_clean,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        response = await self._request("POST", f"/{phone_number_id}/messages", json=payload)
        data = response.json()

        msg_id = ""
        if "messages" in data and data["messages"]:
            msg_id = data["messages"][0].get("id", "")

        logger.info("Template '%s' terkirim via phone_number_id=%s ke %s", template_name, phone_number_id, to_clean)

        return MessageResult(
            message_id=msg_id,
            status=MessageStatus.SENT,
            phone_number=to_phone,
            from_phone_number_id=phone_number_id,
        )

    # ------------------------------------------------------------------
    # Cek status pesan
    # ------------------------------------------------------------------

    async def get_message_status(self, message_id: str) -> MessageStatus:
        """Cek status pengiriman pesan."""
        response = await self._request("GET", f"/{message_id}")
        data = response.json()
        status_str = data.get("status", "sent")
        try:
            return MessageStatus(status_str)
        except ValueError:
            return MessageStatus.SENT

    # ------------------------------------------------------------------
    # Ambil daftar nomor terdaftar di Business Account
    # ------------------------------------------------------------------

    async def list_phone_numbers(self, waba_id: str) -> List[Dict[str, Any]]:
        """
        Ambil semua nomor WA yang terdaftar di WhatsApp Business Account.
        
        Args:
            waba_id: WhatsApp Business Account ID dari Meta
        """
        response = await self._request(
            "GET",
            f"/{waba_id}/phone_numbers",
            params={"fields": "id,display_phone_number,verified_name,status"},
        )
        data = response.json()
        return data.get("data", [])

    # ------------------------------------------------------------------
    # Mark as read
    # ------------------------------------------------------------------

    async def mark_as_read(self, phone_number_id: str, message_id: str) -> bool:
        """Tandai pesan masuk sebagai sudah dibaca."""
        try:
            await self._request(
                "POST",
                f"/{phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
            return True
        except WhatsAppAPIError:
            return False


# ---------------------------------------------------------------------------
# Backward-compatible single client (untuk kode lama)
# ---------------------------------------------------------------------------


class WhatsAppAPIClient:
    """
    Legacy client — wrapper di atas WhatsAppMultiClient.
    Pakai phone_number_id dari config untuk backward compatibility.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._multi_client = WhatsAppMultiClient()
        # Default phone_number_id dari env (untuk backward compat)
        self._default_phone_number_id = getattr(settings, "WHATSAPP_PHONE_NUMBER_ID", "")

    async def send_message(self, phone_number: str, message: str) -> MessageResult:
        if not self._default_phone_number_id:
            # Fallback: log warning, return mock result
            logger.warning("WHATSAPP_PHONE_NUMBER_ID tidak dikonfigurasi, pesan tidak terkirim ke %s", phone_number)
            return MessageResult(
                message_id="mock_" + phone_number,
                status=MessageStatus.SENT,
                phone_number=phone_number,
            )
        return await self._multi_client.send_text_message(
            phone_number_id=self._default_phone_number_id,
            to_phone=phone_number,
            message=message,
        )

    async def get_message_status(self, message_id: str) -> MessageStatus:
        return await self._multi_client.get_message_status(message_id)
