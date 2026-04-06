"""Message Learning Service — pilih variasi pesan terbaik berdasarkan reply rate."""

from __future__ import annotations

import random
import logging
from typing import Optional, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MessageLearningService:
    """
    Memilih variasi pesan yang paling efektif berdasarkan reply rate.
    
    Cara kerja:
    - Simpan beberapa variasi pesan per template
    - Track berapa kali setiap variasi dikirim dan dibalas
    - Pilih variasi dengan weighted random (reply rate lebih tinggi = lebih sering dipilih)
    - Setelah cukup data, otomatis prefer variasi terbaik
    """

    EXPLORATION_RATE = 0.2  # 20% waktu coba variasi random (explore)

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_best_variation(
        self,
        template_type: str = "request_whatsapp",
        affiliator_name: str = "",
        affiliator_category: str = "",
    ) -> Tuple[str, Optional[str]]:
        """
        Pilih variasi pesan terbaik untuk dikirim.
        
        Returns:
            (message_content, variation_id) — variation_id None jika pakai template langsung
        """
        # Ambil semua variasi aktif
        result = await self._db.execute(text("""
            SELECT mv.id, mv.content, mv.send_count, mv.reply_count, mv.reply_rate
            FROM message_variations mv
            JOIN message_templates mt ON mv.template_id = mt.id
            WHERE mt.message_type = :template_type
              AND mv.is_active = TRUE
              AND mt.is_active = TRUE
            ORDER BY mv.reply_rate DESC
        """), {"template_type": template_type})
        variations = result.mappings().all()

        if not variations:
            # Fallback ke template utama
            tmpl = await self._db.execute(text("""
                SELECT content FROM message_templates
                WHERE message_type = :template_type AND is_active = TRUE
                LIMIT 1
            """), {"template_type": template_type})
            row = tmpl.mappings().first()
            content = row["content"] if row else self._default_message()
            return self._personalize(content, affiliator_name, affiliator_category), None

        # Exploration vs exploitation
        if random.random() < self.EXPLORATION_RATE or len(variations) == 1:
            # Explore: pilih random
            chosen = random.choice(variations)
        else:
            # Exploit: weighted random berdasarkan reply_rate
            weights = [max(v["reply_rate"], 0.01) for v in variations]
            chosen = random.choices(variations, weights=weights, k=1)[0]

        content = self._personalize(chosen["content"], affiliator_name, affiliator_category)
        return content, str(chosen["id"])

    async def record_sent(self, variation_id: Optional[str]) -> None:
        """Catat bahwa variasi ini sudah dikirim."""
        if not variation_id:
            return
        await self._db.execute(text("""
            UPDATE message_variations
            SET send_count = send_count + 1,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": variation_id})

    async def record_reply(self, variation_id: Optional[str]) -> None:
        """Catat bahwa pesan dengan variasi ini dibalas — update reply rate."""
        if not variation_id:
            return
        await self._db.execute(text("""
            UPDATE message_variations
            SET reply_count = reply_count + 1,
                reply_rate = CASE 
                    WHEN send_count > 0 THEN (reply_count + 1.0) / send_count
                    ELSE 0
                END,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": variation_id})
        await self._db.flush()
        logger.info("Reply recorded for variation %s", variation_id)

    async def add_variation(
        self,
        template_type: str,
        content: str,
    ) -> str:
        """Tambah variasi baru untuk template tertentu."""
        tmpl = await self._db.execute(text("""
            SELECT id FROM message_templates
            WHERE message_type = :template_type AND is_active = TRUE
            LIMIT 1
        """), {"template_type": template_type})
        row = tmpl.mappings().first()
        if not row:
            raise ValueError(f"Template '{template_type}' tidak ditemukan")

        result = await self._db.execute(text("""
            INSERT INTO message_variations (template_id, content)
            VALUES (:template_id, :content)
            RETURNING id
        """), {"template_id": str(row["id"]), "content": content})
        new_id = result.scalar()
        await self._db.flush()
        return str(new_id)

    async def get_variation_stats(self, template_type: str) -> list:
        """Ambil statistik semua variasi untuk template tertentu."""
        result = await self._db.execute(text("""
            SELECT mv.id, mv.content, mv.send_count, mv.reply_count, mv.reply_rate,
                   mv.is_active, mv.created_at
            FROM message_variations mv
            JOIN message_templates mt ON mv.template_id = mt.id
            WHERE mt.message_type = :template_type
            ORDER BY mv.reply_rate DESC
        """), {"template_type": template_type})
        return [dict(row) for row in result.mappings().all()]

    def _personalize(self, content: str, name: str, category: str) -> str:
        """Ganti placeholder dengan data affiliator."""
        msg = content
        if name:
            msg = msg.replace("{{nama_creator}}", name)
            msg = msg.replace("{{nama_affiliator}}", name)
            msg = msg.replace("[nama]", name)
        if category:
            msg = msg.replace("{{kategori}}", category)
            msg = msg.replace("[kategori]", category)
        return msg

    def _default_message(self) -> str:
        return (
            "Halo! 👋\n\n"
            "Kami dari tim MCN tertarik untuk kolaborasi. "
            "Boleh minta nomor WhatsApp-nya? 😊"
        )
