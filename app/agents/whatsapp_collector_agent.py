"""WhatsApp Collector Agent — mengumpulkan nomor WhatsApp affiliate melalui tiga metode bertingkat."""

from __future__ import annotations

import asyncio
import re
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InvalidPhoneNumberError
from app.integrations.tiktok_api import TikTokAPIClient
from app.models.domain import (
    WhatsAppCollectionMethod,
    WhatsAppCollectionRecord,
    WhatsAppCollectionResult,
    WhatsAppCollectionStatus,
)

# ---------------------------------------------------------------------------
# Regex patterns untuk deteksi nomor WA dalam teks bio
# ---------------------------------------------------------------------------

# Urutan penting: pola lebih spesifik dulu
_WA_PATTERNS = [
    # wa.me/628xxx
    re.compile(r'wa\.me/(628[1-9][0-9]{7,10})', re.IGNORECASE),
    # +628xxx
    re.compile(r'(\+628[1-9][0-9]{7,10})'),
    # WA: 08xxx  /  WA:08xxx  /  WA 08xxx
    re.compile(r'WA\s*:?\s*(08[1-9][0-9]{7,10})', re.IGNORECASE),
    # 628xxx (tanpa +)
    re.compile(r'\b(628[1-9][0-9]{7,10})\b'),
    # 08xxx
    re.compile(r'\b(08[1-9][0-9]{7,10})\b'),
]

# Regex validasi E.164 Indonesia
_E164_PATTERN = re.compile(r'^\+62[1-9][0-9]{8,11}$')


class WhatsAppCollectorAgent:
    """Mengumpulkan nomor WhatsApp affiliate melalui tiga metode bertingkat:
    1. Ikon resmi TikTok Seller Center
    2. Parsing teks bio
    3. Pesan chat otomatis
    """

    def __init__(self, tiktok_client: Optional[TikTokAPIClient] = None) -> None:
        self._tiktok = tiktok_client or TikTokAPIClient()

    # ------------------------------------------------------------------
    # Normalisasi & Validasi
    # ------------------------------------------------------------------

    def normalize_to_e164(self, raw_number: str) -> str:
        """Normalisasi berbagai format nomor Indonesia ke E.164 (+62xxx).

        Mendukung: 08xxx, +628xxx, 628xxx, wa.me/628xxx, WA: 08xxx, WA:08xxx, WA 08xxx
        """
        # Ekstrak bagian nomor dari wa.me/...
        wa_me_match = re.search(r'wa\.me/(\d+)', raw_number, re.IGNORECASE)
        if wa_me_match:
            digits = wa_me_match.group(1)
        else:
            # Hapus semua karakter non-digit
            digits = re.sub(r'\D', '', raw_number)

        # Normalisasi prefix
        if digits.startswith('62'):
            digits = digits[2:]
        elif digits.startswith('0'):
            digits = digits[1:]

        return f'+62{digits}'

    def validate_whatsapp_number(self, phone_number: str) -> bool:
        """Validasi format E.164 Indonesia: harus match ^\\+62[1-9][0-9]{8,11}$"""
        return bool(_E164_PATTERN.match(phone_number))

    # ------------------------------------------------------------------
    # Metode 1: Ikon Resmi
    # ------------------------------------------------------------------

    async def check_official_whatsapp_icon(self, affiliate_id: str) -> Optional[str]:
        """Periksa ikon/tombol WhatsApp resmi di profil affiliate via TikTok API.

        Return nomor raw jika ditemukan, None jika tidak.
        """
        try:
            profile = await self._tiktok.get_affiliate_profile(affiliate_id)
        except Exception:
            return None

        # Cari field "whatsapp_number" langsung
        number = profile.get('whatsapp_number')
        if number:
            return str(number)

        # Cari di "social_links.whatsapp"
        social_links = profile.get('social_links', {})
        if isinstance(social_links, dict):
            number = social_links.get('whatsapp')
            if number:
                return str(number)

        return None

    # ------------------------------------------------------------------
    # Metode 2: Parsing Bio
    # ------------------------------------------------------------------

    def parse_bio_for_whatsapp(self, bio_text: str) -> Optional[str]:
        """Gunakan regex untuk mendeteksi pola nomor WA dalam teks bio.

        Return nomor raw pertama yang ditemukan, atau None.
        """
        if not bio_text:
            return None

        for pattern in _WA_PATTERNS:
            match = pattern.search(bio_text)
            if match:
                return match.group(1)

        return None

    # ------------------------------------------------------------------
    # Metode 3: Chat
    # ------------------------------------------------------------------

    async def send_chat_request(self, affiliate_id: str) -> str:
        """Kirim pesan otomatis via TikTok Seller Center chat.

        Return chat_message_id.
        """
        message = (
            "Halo! Kami ingin mengundang Anda bergabung dalam kampanye kami. "
            "Boleh kami minta nomor WhatsApp Anda?"
        )
        chat_message_id = await self._tiktok.send_seller_center_chat(affiliate_id, message)
        return chat_message_id

    async def monitor_chat_reply(
        self,
        affiliate_id: str,
        chat_message_id: str,
        timeout_hours: int = 48,
        _poll_interval_seconds: int = 300,
    ) -> Optional[str]:
        """Poll balasan chat setiap _poll_interval_seconds detik.

        Return nomor raw dari balasan jika ditemukan dalam timeout, None jika tidak.
        """
        deadline = datetime.utcnow() + timedelta(hours=timeout_hours)

        while datetime.utcnow() < deadline:
            try:
                replies = await self._tiktok.get_chat_replies(affiliate_id, chat_message_id)
            except Exception:
                replies = []

            for reply in replies:
                text_content = reply.get('text') or reply.get('message') or ''
                number = self.parse_bio_for_whatsapp(text_content)
                if number:
                    return number

            await asyncio.sleep(_poll_interval_seconds)

        return None

    # ------------------------------------------------------------------
    # Orkestrasi utama
    # ------------------------------------------------------------------

    async def collect_whatsapp_number(
        self,
        affiliate_id: str,
        db: AsyncSession,
    ) -> WhatsAppCollectionResult:
        """Orkestrasi tiga metode secara berurutan: ikon → bio → chat.

        Berhenti di metode pertama yang berhasil.
        """
        # Dapatkan influencer_id dari DB berdasarkan affiliate_id
        influencer_id = await self._get_influencer_id(affiliate_id, db)

        # --- Metode 1: Ikon resmi ---
        raw_number = await self.check_official_whatsapp_icon(affiliate_id)
        if raw_number:
            normalized = self.normalize_to_e164(raw_number)
            if self.validate_whatsapp_number(normalized):
                record = await self.save_collection_record(
                    affiliate_id=affiliate_id,
                    influencer_id=influencer_id,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.OFFICIAL_ICON,
                    db=db,
                )
                return WhatsAppCollectionResult(
                    affiliate_id=affiliate_id,
                    status=WhatsAppCollectionStatus.COLLECTED,
                    record=record,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.OFFICIAL_ICON,
                )

        # --- Metode 2: Parsing bio ---
        try:
            profile = await self._tiktok.get_affiliate_profile(affiliate_id)
            bio_text = profile.get('bio') or profile.get('description') or ''
        except Exception:
            bio_text = ''

        raw_number = self.parse_bio_for_whatsapp(bio_text)
        if raw_number:
            normalized = self.normalize_to_e164(raw_number)
            if self.validate_whatsapp_number(normalized):
                record = await self.save_collection_record(
                    affiliate_id=affiliate_id,
                    influencer_id=influencer_id,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.BIO_PARSING,
                    db=db,
                )
                return WhatsAppCollectionResult(
                    affiliate_id=affiliate_id,
                    status=WhatsAppCollectionStatus.COLLECTED,
                    record=record,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.BIO_PARSING,
                )

        # --- Metode 3: Chat ---
        try:
            chat_message_id = await self.send_chat_request(affiliate_id)
            raw_number = await self.monitor_chat_reply(affiliate_id, chat_message_id)
        except Exception:
            raw_number = None
            chat_message_id = None

        if raw_number:
            normalized = self.normalize_to_e164(raw_number)
            if self.validate_whatsapp_number(normalized):
                record = await self.save_collection_record(
                    affiliate_id=affiliate_id,
                    influencer_id=influencer_id,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.CHAT_REPLY,
                    db=db,
                )
                return WhatsAppCollectionResult(
                    affiliate_id=affiliate_id,
                    status=WhatsAppCollectionStatus.COLLECTED,
                    record=record,
                    phone_number=normalized,
                    method=WhatsAppCollectionMethod.CHAT_REPLY,
                )

        # --- Semua metode gagal ---
        await self.mark_unavailable(affiliate_id, influencer_id, db)
        unavailable_record = WhatsAppCollectionRecord(
            id=str(uuid.uuid4()),
            affiliate_id=affiliate_id,
            influencer_id=influencer_id,
            status=WhatsAppCollectionStatus.UNAVAILABLE,
        )
        return WhatsAppCollectionResult(
            affiliate_id=affiliate_id,
            status=WhatsAppCollectionStatus.UNAVAILABLE,
            record=unavailable_record,
            phone_number=None,
            method=None,
        )

    # ------------------------------------------------------------------
    # Persistensi
    # ------------------------------------------------------------------

    async def save_collection_record(
        self,
        affiliate_id: str,
        influencer_id: str,
        phone_number: str,
        method: WhatsAppCollectionMethod,
        db: AsyncSession,
    ) -> WhatsAppCollectionRecord:
        """Validate nomor, INSERT ke whatsapp_collection_records, UPDATE influencers.phone_number."""
        if not self.validate_whatsapp_number(phone_number):
            raise InvalidPhoneNumberError(
                f"Nomor telepon tidak valid: {phone_number!r}. "
                "Harus dalam format E.164 Indonesia (+62 diikuti 9-12 digit)."
            )

        record_id = str(uuid.uuid4())
        now = datetime.utcnow()

        await db.execute(
            text(
                """
                INSERT INTO whatsapp_collection_records
                    (id, affiliate_id, influencer_id, phone_number, method, status,
                     collected_at, created_at, updated_at)
                VALUES
                    (:id, :affiliate_id, :influencer_id, :phone_number, :method, :status,
                     :collected_at, :created_at, :updated_at)
                ON CONFLICT (affiliate_id) DO UPDATE
                SET phone_number = EXCLUDED.phone_number,
                    method       = EXCLUDED.method,
                    status       = EXCLUDED.status,
                    collected_at = EXCLUDED.collected_at,
                    updated_at   = EXCLUDED.updated_at
                """
            ),
            {
                "id": record_id,
                "affiliate_id": affiliate_id,
                "influencer_id": influencer_id,
                "phone_number": phone_number,
                "method": method.value,
                "status": WhatsAppCollectionStatus.COLLECTED.value,
                "collected_at": now,
                "created_at": now,
                "updated_at": now,
            },
        )

        # Update phone_number di tabel influencers
        await db.execute(
            text(
                "UPDATE influencers SET phone_number = :phone_number WHERE id = :influencer_id"
            ),
            {"phone_number": phone_number, "influencer_id": influencer_id},
        )

        await db.flush()

        return WhatsAppCollectionRecord(
            id=record_id,
            affiliate_id=affiliate_id,
            influencer_id=influencer_id,
            phone_number=phone_number,
            method=method,
            status=WhatsAppCollectionStatus.COLLECTED,
            collected_at=now,
            created_at=now,
            updated_at=now,
        )

    async def mark_unavailable(
        self,
        affiliate_id: str,
        influencer_id: str,
        db: AsyncSession,
    ) -> None:
        """INSERT/UPDATE whatsapp_collection_records dengan status=unavailable."""
        record_id = str(uuid.uuid4())
        now = datetime.utcnow()

        await db.execute(
            text(
                """
                INSERT INTO whatsapp_collection_records
                    (id, affiliate_id, influencer_id, status, created_at, updated_at)
                VALUES
                    (:id, :affiliate_id, :influencer_id, :status, :created_at, :updated_at)
                ON CONFLICT (affiliate_id) DO UPDATE
                SET status     = EXCLUDED.status,
                    updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": record_id,
                "affiliate_id": affiliate_id,
                "influencer_id": influencer_id,
                "status": WhatsAppCollectionStatus.UNAVAILABLE.value,
                "created_at": now,
                "updated_at": now,
            },
        )
        await db.flush()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_influencer_id(self, affiliate_id: str, db: AsyncSession) -> str:
        """Ambil influencer_id dari DB berdasarkan affiliate_id (tiktok_user_id).

        Jika tidak ditemukan, kembalikan affiliate_id sebagai fallback.
        """
        try:
            result = await db.execute(
                text("SELECT id FROM influencers WHERE tiktok_user_id = :affiliate_id LIMIT 1"),
                {"affiliate_id": affiliate_id},
            )
            row = result.fetchone()
            if row:
                return str(row[0])
        except Exception:
            pass
        return affiliate_id
