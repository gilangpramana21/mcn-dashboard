"""Realtime API — Server-Sent Events untuk live dashboard updates."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/realtime", tags=["realtime"])
logger = logging.getLogger(__name__)


async def _get_live_stats(db: AsyncSession) -> Dict[str, Any]:
    """Ambil stats terkini untuk dashboard."""
    try:
        # Unread messages
        r1 = await db.execute(text(
            "SELECT COUNT(*) FROM incoming_messages WHERE is_read = FALSE"
        ))
        unread_count = int(r1.scalar() or 0)

        # Total conversations (unique affiliates with messages)
        r2 = await db.execute(text("""
            SELECT COUNT(DISTINCT affiliate_name) FROM (
                SELECT affiliate_name FROM incoming_messages WHERE affiliate_name IS NOT NULL
                UNION
                SELECT affiliate_name FROM message_history WHERE affiliate_name IS NOT NULL
            ) t
        """))
        total_conversations = int(r2.scalar() or 0)

        # Active affiliates (has_whatsapp or recent message)
        r3 = await db.execute(text(
            "SELECT COUNT(*) FROM influencers WHERE status = 'ACTIVE'"
        ))
        active_affiliates = int(r3.scalar() or 0)

        # Messages today
        r4 = await db.execute(text("""
            SELECT COUNT(*) FROM (
                SELECT id FROM incoming_messages WHERE received_at >= CURRENT_DATE
                UNION ALL
                SELECT id FROM message_history WHERE sent_at >= CURRENT_DATE
            ) t
        """))
        messages_today = int(r4.scalar() or 0)

        # Recent incoming messages (last 5)
        r5 = await db.execute(text("""
            SELECT affiliate_name, channel, message_content, received_at
            FROM incoming_messages
            ORDER BY received_at DESC
            LIMIT 5
        """))
        recent_messages = [
            {
                "affiliate_name": row[0],
                "channel": row[1],
                "message_content": row[2][:80] + "..." if row[2] and len(row[2]) > 80 else row[2],
                "received_at": row[3].isoformat() if row[3] else "",
            }
            for row in r5.fetchall()
        ]

        return {
            "unread_count": unread_count,
            "total_conversations": total_conversations,
            "active_affiliates": active_affiliates,
            "messages_today": messages_today,
            "recent_messages": recent_messages,
        }
    except Exception as e:
        logger.warning("Error getting live stats: %s", e)
        return {
            "unread_count": 0,
            "total_conversations": 0,
            "active_affiliates": 0,
            "messages_today": 0,
            "recent_messages": [],
        }


async def _event_generator(
    request: Request,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """Generate SSE events setiap 15 detik."""
    try:
        while True:
            if await request.is_disconnected():
                break

            stats = await _get_live_stats(db)
            data = json.dumps(stats)
            yield f"data: {data}\n\n"

            # Tunggu 15 detik sebelum update berikutnya
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.warning("SSE generator error: %s", e)


@router.get("/stats")
async def realtime_stats(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
):
    """SSE endpoint untuk live stats dashboard."""
    return StreamingResponse(
        _event_generator(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/stats/snapshot")
async def stats_snapshot(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Snapshot stats saat ini (non-SSE, untuk initial load)."""
    return await _get_live_stats(db)
