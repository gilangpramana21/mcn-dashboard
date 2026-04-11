"""Inbox API — pesan masuk dari affiliate (WhatsApp & TikTok Seller)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/inbox", tags=["inbox"])


class SimulateMessageRequest(BaseModel):
    affiliate_name: str
    channel: str  # 'whatsapp' | 'tiktok_seller'
    message_content: str
    from_number: Optional[str] = None
    affiliate_id: Optional[str] = None


@router.get("/affiliates-with-wa")
async def get_affiliates_for_simulate(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict]:
    """Ambil daftar affiliator untuk dropdown simulasi."""
    result = await db.execute(text("""
        SELECT id, name, tiktok_user_id, phone_number, has_whatsapp
        FROM influencers
        ORDER BY has_whatsapp DESC, name ASC
        LIMIT 100
    """))
    return [dict(r) for r in result.mappings().all()]


@router.post("/simulate")
async def simulate_incoming_message(
    body: SimulateMessageRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Simulasi pesan masuk dari affiliate."""
    await db.execute(text("""
        INSERT INTO incoming_messages
            (affiliate_id, affiliate_name, channel, message_content, from_number)
        VALUES
            (:affiliate_id, :affiliate_name, :channel, :message_content, :from_number)
    """), {
        "affiliate_id": body.affiliate_id,
        "affiliate_name": body.affiliate_name,
        "channel": body.channel,
        "message_content": body.message_content,
        "from_number": body.from_number,
    })
    await db.commit()
    return {"status": "message_received", "channel": body.channel}


@router.get("/unread-count")
async def get_unread_count(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, int]:
    """Jumlah pesan belum dibaca."""
    result = await db.execute(text(
        "SELECT COUNT(*) FROM incoming_messages WHERE is_read = FALSE"
    ))
    count = result.scalar() or 0
    return {"count": int(count)}


@router.get("")
async def list_inbox(
    limit: int = 20,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict]:
    """Daftar pesan masuk terbaru."""
    result = await db.execute(text("""
        SELECT id, affiliate_id, affiliate_name, channel,
               message_content, from_number, is_read, received_at
        FROM incoming_messages
        ORDER BY received_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.patch("/{message_id}/read")
async def mark_as_read(
    message_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Tandai pesan sebagai sudah dibaca."""
    await db.execute(text("""
        UPDATE incoming_messages
        SET is_read = TRUE, read_at = NOW()
        WHERE id = :id
    """), {"id": message_id})
    await db.commit()
    return {"status": "read"}


@router.patch("/read-all")
async def mark_all_read(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Tandai semua pesan sebagai sudah dibaca."""
    await db.execute(text(
        "UPDATE incoming_messages SET is_read = TRUE, read_at = NOW() WHERE is_read = FALSE"
    ))
    await db.commit()
    return {"status": "all_read"}
