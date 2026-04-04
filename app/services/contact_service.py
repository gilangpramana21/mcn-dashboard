"""Contact Service — menentukan kanal kontak dan mengirim pesan ke affiliate."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.whatsapp_collector_agent import WhatsAppCollectorAgent
from app.integrations.tiktok_api import TikTokAPIClient
from app.integrations.whatsapp_api import MessageResult, WhatsAppAPIClient


async def get_contact_channel(affiliate_id: str, db: AsyncSession) -> str:
    """Kembalikan 'whatsapp' jika phone_number tersimpan di DB, 'seller_center_chat' jika tidak.

    Pencarian dilakukan berdasarkan tiktok_user_id (affiliate_id) pada tabel influencers.
    """
    result = await db.execute(
        text(
            "SELECT phone_number FROM influencers WHERE tiktok_user_id = :affiliate_id LIMIT 1"
        ),
        {"affiliate_id": affiliate_id},
    )
    row = result.fetchone()
    if row and row[0]:
        return "whatsapp"
    return "seller_center_chat"


async def send_contact_message(
    affiliate_id: str,
    message: str,
    db: AsyncSession,
    whatsapp_client: Optional[WhatsAppAPIClient] = None,
) -> dict:
    """Kirim pesan ke affiliate melalui kanal yang sesuai.

    - Jika phone_number ada di DB → kirim via WhatsApp API.
    - Jika tidak → trigger WhatsAppCollectorAgent.collect_whatsapp_number()
      dan kirim pesan via chat Seller Center.

    Kembalikan dict dengan keys: channel, status, message_id (optional).
    """
    # Ambil phone_number dari DB
    result = await db.execute(
        text(
            "SELECT id, phone_number FROM influencers WHERE tiktok_user_id = :affiliate_id LIMIT 1"
        ),
        {"affiliate_id": affiliate_id},
    )
    row = result.fetchone()
    phone_number: Optional[str] = row[1] if row else None

    if phone_number:
        # Kirim via WhatsApp API
        client = whatsapp_client or WhatsAppAPIClient()
        msg_result: MessageResult = await client.send_message(phone_number, message)
        return {
            "channel": "whatsapp",
            "status": msg_result.status.value,
            "message_id": msg_result.message_id,
        }
    else:
        # Trigger WhatsApp collection dan kirim via Seller Center chat
        collector = WhatsAppCollectorAgent()
        collection_result = await collector.collect_whatsapp_number(affiliate_id, db)

        if collection_result.phone_number:
            # Nomor berhasil dikumpulkan — kirim via WhatsApp
            client = whatsapp_client or WhatsAppAPIClient()
            msg_result = await client.send_message(collection_result.phone_number, message)
            return {
                "channel": "whatsapp",
                "status": msg_result.status.value,
                "message_id": msg_result.message_id,
            }
        else:
            # Nomor tidak tersedia — kirim via Seller Center chat
            tiktok_client = TikTokAPIClient()
            chat_message_id = await tiktok_client.send_seller_center_chat(affiliate_id, message)
            return {
                "channel": "seller_center_chat",
                "status": "sent",
                "message_id": chat_message_id,
            }
