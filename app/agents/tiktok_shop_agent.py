"""TikTok Shop Agent — otomatis cari affiliator, kirim pesan, simpan ke DB.

Alur kerja:
1. Search creator di TikTok Shop Marketplace berdasarkan filter
2. Simpan creator baru ke database (influencers table)
3. Kirim pesan chat TikTok minta nomor WhatsApp
4. Catat semua aktivitas ke message_history
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tiktok_shop_api import TikTokShopClient
from app.services.message_learning_service import MessageLearningService

logger = logging.getLogger(__name__)


@dataclass
class AgentRunConfig:
    """Konfigurasi satu run agent."""
    keyword: str = ""
    min_followers: int = 1000
    max_followers: int = 0
    categories: List[str] = field(default_factory=list)
    max_creators: int = 50
    wa_request_message: str = (
        "Halo {{nama_creator}}! 👋\n\n"
        "Kami dari MCN tertarik untuk berkolaborasi dengan kamu. "
        "Boleh minta nomor WhatsApp kamu untuk diskusi lebih lanjut? 😊"
    )
    auto_send_message: bool = True
    product_ids: List[str] = field(default_factory=list)
    commission_rate: float = 15.0


@dataclass
class AgentRunResult:
    """Hasil satu run agent."""
    found: int = 0
    new_saved: int = 0
    already_exists: int = 0
    messages_sent: int = 0
    errors: List[str] = field(default_factory=list)
    creators: List[Dict[str, Any]] = field(default_factory=list)


class TikTokShopAgent:
    """
    Agent yang berjalan otomatis untuk:
    1. Cari creator di TikTok Shop
    2. Simpan ke database
    3. Kirim pesan minta nomor WA
    """

    def __init__(self, access_token: str, db: AsyncSession) -> None:
        self._client = TikTokShopClient(access_token)
        self._db = db
        self._msg_learning = MessageLearningService(db)

    async def run(self, config: AgentRunConfig) -> AgentRunResult:
        """Jalankan agent dengan konfigurasi yang diberikan."""
        result = AgentRunResult()

        # Ambil variasi pesan terbaik dari learning service
        wa_message = config.wa_request_message
        variation_id = None
        try:
            wa_message, variation_id = await self._msg_learning.get_best_variation(
                template_type="request_whatsapp"
            )
        except Exception:
            # Fallback ke template dari DB
            tmpl_result = await self._db.execute(text("""
                SELECT content FROM message_templates
                WHERE message_type = 'request_whatsapp' AND is_active = TRUE
                LIMIT 1
            """))
            tmpl_row = tmpl_result.mappings().first()
            if tmpl_row:
                wa_message = tmpl_row["content"]

        # Search creators
        page_token = ""
        fetched = 0

        while fetched < config.max_creators:
            batch_size = min(20, config.max_creators - fetched)
            try:
                search_result = await self._client.search_creators(
                    keyword=config.keyword,
                    min_followers=config.min_followers,
                    max_followers=config.max_followers,
                    categories=config.categories if config.categories else None,
                    page_size=batch_size,
                    page_token=page_token,
                )
            except Exception as e:
                result.errors.append(f"Search error: {str(e)[:100]}")
                break

            creators = search_result.get("creators", [])
            if not creators:
                break

            result.found += len(creators)
            fetched += len(creators)

            for creator in creators:
                creator_result = await self._process_creator(
                    creator=creator,
                    wa_message=wa_message,
                    config=config,
                    variation_id=variation_id,
                )
                if creator_result["is_new"]:
                    result.new_saved += 1
                else:
                    result.already_exists += 1
                if creator_result["message_sent"]:
                    result.messages_sent += 1
                if creator_result.get("error"):
                    result.errors.append(creator_result["error"])
                result.creators.append(creator_result)

            # Next page
            page_token = search_result.get("next_page_token", "")
            if not page_token:
                break

        await self._db.commit()
        logger.info(
            "TikTokShopAgent selesai: found=%d, new=%d, messages=%d",
            result.found, result.new_saved, result.messages_sent,
        )
        return result

    async def _process_creator(
        self,
        creator: Dict[str, Any],
        wa_message: str,
        config: AgentRunConfig,
        variation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Proses satu creator: simpan ke DB dan kirim pesan."""
        creator_id = str(creator.get("creator_id", ""))
        name = creator.get("creator_name", "") or creator.get("nickname", "")
        username = creator.get("creator_username", "") or creator.get("unique_id", "")
        followers = int(creator.get("follower_count", 0))
        engagement = float(creator.get("engagement_rate", 0))
        categories = creator.get("creator_categories", []) or []
        location = creator.get("region", "") or ""

        if not name:
            return {"is_new": False, "message_sent": False, "error": "Creator tanpa nama dilewati"}

        # Cek apakah sudah ada di DB (prioritaskan match berdasarkan tiktok_creator_id)
        existing = await self._db.execute(text("""
            SELECT id, phone_number FROM influencers
            WHERE tiktok_creator_id = :creator_id
               OR tiktok_user_id = :tiktok_user_id
               OR LOWER(name) = :name
            LIMIT 1
        """), {
            "creator_id": creator_id or "",
            "tiktok_user_id": username or creator_id or "",
            "name": name.lower(),
        })
        existing_row = existing.mappings().first()

        affiliate_db_id = None
        is_new = False

        if existing_row:
            affiliate_db_id = str(existing_row["id"])
            # Jika sudah punya WA, skip kirim pesan
            if existing_row.get("phone_number"):
                return {
                    "is_new": False,
                    "message_sent": False,
                    "creator_id": creator_id,
                    "name": name,
                }
        else:
            # Insert baru
            affiliate_db_id = str(uuid.uuid4())
            try:
                await self._db.execute(text("""
                    INSERT INTO influencers
                        (id, name, tiktok_user_id, tiktok_creator_id, follower_count,
                         engagement_rate, content_categories, location, has_whatsapp,
                         status, creator_type, data_source, tiktok_synced_at,
                         created_at, updated_at)
                    VALUES
                        (:id, :name, :tiktok_user_id, :tiktok_creator_id, :followers,
                         :engagement, cast(:categories as jsonb), :location, FALSE,
                         'ACTIVE', 'affiliator', 'tiktok_shop_search', NOW(),
                         NOW(), NOW())
                """), {
                    "id": affiliate_db_id,
                    "name": name,
                    "tiktok_user_id": username or creator_id,
                    "tiktok_creator_id": creator_id or None,
                    "followers": followers,
                    "engagement": engagement,
                    "categories": json.dumps(categories if isinstance(categories, list) else []),
                    "location": location,
                })
                is_new = True
            except Exception as e:
                return {"is_new": False, "message_sent": False, "error": f"{name}: {str(e)[:80]}"}

        # Kirim pesan jika dikonfigurasi
        message_sent = False
        if config.auto_send_message and affiliate_db_id:
            personalized_msg = wa_message.replace("{{nama_creator}}", name).replace("{{nama_influencer}}", name)

            # Coba kirim via TikTok Shop API
            tiktok_msg_id = None
            if creator_id:
                try:
                    chat_result = await self._client.send_chat_message(
                        creator_id=creator_id,
                        message=personalized_msg,
                    )
                    tiktok_msg_id = chat_result.get("message_id", "")
                    message_sent = True
                    # Catat bahwa variasi ini sudah dikirim
                    await self._msg_learning.record_sent(variation_id)
                except Exception as e:
                    logger.warning("Gagal kirim chat ke %s: %s", name, e)

            # Catat ke message_history (baik berhasil maupun tidak)
            try:
                await self._db.execute(text("""
                    INSERT INTO message_history
                        (id, affiliate_id, affiliate_name, direction, message_content,
                         from_number, to_number, status, sent_at, variation_id)
                    VALUES
                        (:id, :affiliate_id, :affiliate_name, 'outbound', :content,
                         'TikTok Chat', :tiktok_id, :status, NOW(), :variation_id)
                """), {
                    "id": tiktok_msg_id or str(uuid.uuid4()),
                    "affiliate_id": affiliate_db_id,
                    "affiliate_name": name,
                    "content": personalized_msg,
                    "tiktok_id": creator_id or username,
                    "status": "sent" if message_sent else "failed",
                    "variation_id": variation_id,
                })
            except Exception as e:
                logger.warning("Gagal catat message_history untuk %s: %s", name, e)

        return {
            "is_new": is_new,
            "message_sent": message_sent,
            "creator_id": creator_id,
            "name": name,
            "followers": followers,
        }
