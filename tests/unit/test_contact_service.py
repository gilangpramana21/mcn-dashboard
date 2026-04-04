"""Unit tests for contact_service."""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.contact_service import get_contact_channel, send_contact_message


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db_with_phone(phone_number: Optional[str]) -> AsyncMock:
    """Buat mock DB yang mengembalikan row dengan phone_number tertentu."""
    db = AsyncMock()

    # fetchone() untuk query phone_number
    row_mock = MagicMock()
    row_mock.__getitem__ = lambda self, idx: [None, phone_number][idx]
    row_mock.__iter__ = lambda self: iter([None, phone_number])

    # Untuk query yang hanya mengambil phone_number (1 kolom)
    row_single = MagicMock()
    row_single.__getitem__ = lambda self, idx: phone_number

    result_mock = MagicMock()
    result_mock.fetchone = MagicMock(return_value=row_mock if phone_number is not None else None)

    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()
    return db


def _make_db_no_row() -> AsyncMock:
    """Buat mock DB yang tidak mengembalikan row (affiliate tidak ditemukan)."""
    db = AsyncMock()
    result_mock = MagicMock()
    result_mock.fetchone = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()
    return db


# ---------------------------------------------------------------------------
# Tests: get_contact_channel
# ---------------------------------------------------------------------------


class TestGetContactChannel:
    @pytest.mark.asyncio
    async def test_returns_whatsapp_when_phone_number_exists(self):
        """Kembalikan 'whatsapp' jika phone_number tersimpan di DB."""
        db = AsyncMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: "+6281234567890"
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        channel = await get_contact_channel("affiliate-1", db)

        assert channel == "whatsapp"

    @pytest.mark.asyncio
    async def test_returns_seller_center_chat_when_no_phone_number(self):
        """Kembalikan 'seller_center_chat' jika phone_number NULL di DB."""
        db = AsyncMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: None
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        channel = await get_contact_channel("affiliate-2", db)

        assert channel == "seller_center_chat"

    @pytest.mark.asyncio
    async def test_returns_seller_center_chat_when_affiliate_not_found(self):
        """Kembalikan 'seller_center_chat' jika affiliate tidak ada di DB."""
        db = _make_db_no_row()

        channel = await get_contact_channel("nonexistent", db)

        assert channel == "seller_center_chat"

    @pytest.mark.asyncio
    async def test_queries_db_with_affiliate_id(self):
        """Pastikan DB di-query dengan affiliate_id yang benar."""
        db = AsyncMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: "+6281234567890"
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        await get_contact_channel("aff-xyz", db)

        db.execute.assert_called_once()
        call_args = db.execute.call_args
        # Pastikan affiliate_id diteruskan sebagai parameter
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        assert "aff-xyz" in str(params)


# ---------------------------------------------------------------------------
# Tests: send_contact_message
# ---------------------------------------------------------------------------


class TestSendContactMessage:
    @pytest.mark.asyncio
    async def test_routes_to_whatsapp_when_phone_number_exists(self):
        """Kirim via WhatsApp jika phone_number ada di DB."""
        from app.integrations.whatsapp_api import MessageResult, MessageStatus

        db = AsyncMock()
        row = MagicMock()
        # row[0] = influencer_id, row[1] = phone_number
        row.__getitem__ = lambda self, idx: ("inf-1" if idx == 0 else "+6281234567890")
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        mock_wa_client = AsyncMock()
        mock_wa_client.send_message = AsyncMock(
            return_value=MessageResult(
                message_id="msg-123",
                status=MessageStatus.SENT,
                phone_number="+6281234567890",
            )
        )

        result = await send_contact_message(
            "affiliate-1", "Halo!", db, whatsapp_client=mock_wa_client
        )

        assert result["channel"] == "whatsapp"
        assert result["status"] == "sent"
        assert result["message_id"] == "msg-123"
        mock_wa_client.send_message.assert_called_once_with("+6281234567890", "Halo!")

    @pytest.mark.asyncio
    async def test_routes_to_seller_center_when_no_phone_number_and_collection_fails(self):
        """Kirim via Seller Center chat jika phone_number tidak ada dan koleksi gagal."""
        db = AsyncMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: None  # phone_number = None
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        from app.models.domain import (
            WhatsAppCollectionRecord,
            WhatsAppCollectionResult,
            WhatsAppCollectionStatus,
        )

        mock_collection_result = WhatsAppCollectionResult(
            affiliate_id="affiliate-2",
            status=WhatsAppCollectionStatus.UNAVAILABLE,
            record=WhatsAppCollectionRecord(
                id="rec-1",
                affiliate_id="affiliate-2",
                influencer_id="inf-2",
                status=WhatsAppCollectionStatus.UNAVAILABLE,
            ),
            phone_number=None,
        )

        with patch(
            "app.services.contact_service.WhatsAppCollectorAgent"
        ) as MockCollector, patch(
            "app.services.contact_service.TikTokAPIClient"
        ) as MockTikTok:
            mock_collector_instance = AsyncMock()
            mock_collector_instance.collect_whatsapp_number = AsyncMock(
                return_value=mock_collection_result
            )
            MockCollector.return_value = mock_collector_instance

            mock_tiktok_instance = AsyncMock()
            mock_tiktok_instance.send_seller_center_chat = AsyncMock(
                return_value="chat-msg-456"
            )
            MockTikTok.return_value = mock_tiktok_instance

            result = await send_contact_message("affiliate-2", "Halo!", db)

        assert result["channel"] == "seller_center_chat"
        assert result["status"] == "sent"
        assert result["message_id"] == "chat-msg-456"

    @pytest.mark.asyncio
    async def test_routes_to_whatsapp_after_successful_collection(self):
        """Kirim via WhatsApp jika koleksi nomor berhasil."""
        from app.integrations.whatsapp_api import MessageResult, MessageStatus
        from app.models.domain import (
            WhatsAppCollectionMethod,
            WhatsAppCollectionRecord,
            WhatsAppCollectionResult,
            WhatsAppCollectionStatus,
        )

        db = AsyncMock()
        row = MagicMock()
        row.__getitem__ = lambda self, idx: None  # phone_number awalnya None
        result_mock = MagicMock()
        result_mock.fetchone = MagicMock(return_value=row)
        db.execute = AsyncMock(return_value=result_mock)

        mock_collection_result = WhatsAppCollectionResult(
            affiliate_id="affiliate-3",
            status=WhatsAppCollectionStatus.COLLECTED,
            record=WhatsAppCollectionRecord(
                id="rec-2",
                affiliate_id="affiliate-3",
                influencer_id="inf-3",
                status=WhatsAppCollectionStatus.COLLECTED,
                phone_number="+6289876543210",
            ),
            phone_number="+6289876543210",
            method=WhatsAppCollectionMethod.BIO_PARSING,
        )

        mock_wa_client = AsyncMock()
        mock_wa_client.send_message = AsyncMock(
            return_value=MessageResult(
                message_id="msg-789",
                status=MessageStatus.SENT,
                phone_number="+6289876543210",
            )
        )

        with patch("app.services.contact_service.WhatsAppCollectorAgent") as MockCollector:
            mock_collector_instance = AsyncMock()
            mock_collector_instance.collect_whatsapp_number = AsyncMock(
                return_value=mock_collection_result
            )
            MockCollector.return_value = mock_collector_instance

            result = await send_contact_message(
                "affiliate-3", "Halo!", db, whatsapp_client=mock_wa_client
            )

        assert result["channel"] == "whatsapp"
        assert result["status"] == "sent"
        assert result["message_id"] == "msg-789"
        mock_wa_client.send_message.assert_called_once_with("+6289876543210", "Halo!")

    @pytest.mark.asyncio
    async def test_send_contact_message_no_row_routes_to_seller_center(self):
        """Jika affiliate tidak ditemukan di DB, routing ke seller_center_chat."""
        db = _make_db_no_row()

        from app.models.domain import (
            WhatsAppCollectionRecord,
            WhatsAppCollectionResult,
            WhatsAppCollectionStatus,
        )

        mock_collection_result = WhatsAppCollectionResult(
            affiliate_id="unknown",
            status=WhatsAppCollectionStatus.UNAVAILABLE,
            record=WhatsAppCollectionRecord(
                id="rec-x",
                affiliate_id="unknown",
                influencer_id="unknown",
                status=WhatsAppCollectionStatus.UNAVAILABLE,
            ),
            phone_number=None,
        )

        with patch(
            "app.services.contact_service.WhatsAppCollectorAgent"
        ) as MockCollector, patch(
            "app.services.contact_service.TikTokAPIClient"
        ) as MockTikTok:
            mock_collector_instance = AsyncMock()
            mock_collector_instance.collect_whatsapp_number = AsyncMock(
                return_value=mock_collection_result
            )
            MockCollector.return_value = mock_collector_instance

            mock_tiktok_instance = AsyncMock()
            mock_tiktok_instance.send_seller_center_chat = AsyncMock(
                return_value="chat-msg-999"
            )
            MockTikTok.return_value = mock_tiktok_instance

            result = await send_contact_message("unknown", "Halo!", db)

        assert result["channel"] == "seller_center_chat"
