"""Sender Agent — kirim undangan massal via WhatsApp API dengan rate limiting."""

from __future__ import annotations

import re
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Deque, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import BlacklistViolationError, ValidationError
from app.integrations.whatsapp_api import WhatsAppAPIClient
from app.models.domain import Influencer, InvitationStatus, MessageTemplate
from app.services.blacklist_service import BlacklistService
from app.services.template_service import TemplateService

_VAR_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class InvitationReport:
    """Laporan ringkasan hasil pengiriman undangan massal."""

    campaign_id: str
    total_sent: int
    total_failed: int
    total_pending: int
    total_processed: int


# ---------------------------------------------------------------------------
# SenderAgent
# ---------------------------------------------------------------------------


class SenderAgent:
    """Mengelola pengiriman undangan massal dengan rate limiting sliding window."""

    # Rate limit: maks 100 undangan per 60 detik
    _RATE_LIMIT: int = 100
    _RATE_WINDOW_SECONDS: float = 60.0

    def __init__(
        self,
        blacklist_service: BlacklistService,
        whatsapp_client: Optional[WhatsAppAPIClient] = None,
        redis: Optional[object] = None,
    ) -> None:
        self._blacklist = blacklist_service
        self._whatsapp = whatsapp_client or WhatsAppAPIClient()
        self._redis = redis
        # Sliding window: timestamps pengiriman (monotonic)
        self._send_timestamps: Deque[float] = deque()

    # ------------------------------------------------------------------
    # Substitusi variabel template
    # ------------------------------------------------------------------

    def _substitute_variables(
        self,
        template: MessageTemplate,
        influencer: Influencer,
        campaign_id: str,
    ) -> str:
        """Substitusi semua {{variable}} dalam template.content.

        Prioritas: data influencer/kampanye > default_values template.
        Raises ValidationError jika ada placeholder yang tersisa.
        """
        dynamic: dict[str, str] = {
            **template.default_values,
            "name": influencer.name,
            "campaign": campaign_id,
        }

        def _replace(match: re.Match) -> str:  # type: ignore[type-arg]
            key = match.group(1)
            return dynamic.get(key, match.group(0))

        rendered = _VAR_PATTERN.sub(_replace, template.content)

        remaining = _VAR_PATTERN.findall(rendered)
        if remaining:
            raise ValidationError(
                f"Placeholder berikut belum tersubstitusi: {', '.join(remaining)}"
            )

        return rendered

    # ------------------------------------------------------------------
    # Rate limiting (sliding window)
    # ------------------------------------------------------------------

    def _prune_window(self, now: float) -> None:
        """Hapus timestamps yang sudah di luar window 60 detik."""
        cutoff = now - self._RATE_WINDOW_SECONDS
        while self._send_timestamps and self._send_timestamps[0] <= cutoff:
            self._send_timestamps.popleft()

    def _count_in_window(self, now: float) -> int:
        self._prune_window(now)
        return len(self._send_timestamps)

    async def _wait_for_rate_limit(self) -> None:
        """Tunggu jika sudah mencapai batas 100 undangan/menit."""
        import asyncio

        while True:
            now = time.monotonic()
            self._prune_window(now)
            if len(self._send_timestamps) < self._RATE_LIMIT:
                break
            # Hitung berapa lama harus menunggu agar window bergeser
            oldest = self._send_timestamps[0]
            wait_seconds = self._RATE_WINDOW_SECONDS - (now - oldest) + 0.01
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)

    def _record_send(self) -> None:
        """Catat timestamp pengiriman ke sliding window."""
        self._send_timestamps.append(time.monotonic())

    # ------------------------------------------------------------------
    # send_single_invitation
    # ------------------------------------------------------------------

    async def send_single_invitation(
        self,
        influencer: Influencer,
        template_id: str,
        campaign_id: str,
        db: AsyncSession,
        scheduled_at: Optional[datetime] = None,
    ) -> str:
        """Kirim satu undangan ke influencer.

        - Ambil template dari DB.
        - Substitusi variabel.
        - Cek blacklist (raise BlacklistViolationError jika blacklisted).
        - Jika scheduled_at diisi, simpan dengan status SCHEDULED tanpa kirim.
        - Kirim via WhatsApp API.
        - Catat status + timestamp ke tabel invitations.
        - Kembalikan invitation_id.
        """
        # Cek blacklist
        if influencer.blacklisted or await self._blacklist.is_blacklisted(influencer.id):
            raise BlacklistViolationError(
                f"Influencer {influencer.id} ({influencer.name}) ada dalam daftar hitam."
            )

        # Ambil template
        template_svc = TemplateService(db)
        template = await template_svc.get(template_id)

        # Substitusi variabel
        message_content = self._substitute_variables(template, influencer, campaign_id)

        invitation_id = str(uuid.uuid4())
        now = _now_utc()

        # Jika dijadwalkan, simpan dengan status SCHEDULED
        if scheduled_at is not None:
            await self._save_invitation(
                db=db,
                invitation_id=invitation_id,
                campaign_id=campaign_id,
                influencer_id=influencer.id,
                template_id=template_id,
                message_content=message_content,
                status=InvitationStatus.SCHEDULED,
                sent_at=None,
                scheduled_at=scheduled_at,
                error_message=None,
                whatsapp_message_id=None,
                now=now,
            )
            return invitation_id

        # Kirim via WhatsApp API
        try:
            result = await self._whatsapp.send_message(
                phone_number=influencer.phone_number,
                message=message_content,
            )
            self._record_send()
            await self._save_invitation(
                db=db,
                invitation_id=invitation_id,
                campaign_id=campaign_id,
                influencer_id=influencer.id,
                template_id=template_id,
                message_content=message_content,
                status=InvitationStatus.SENT,
                sent_at=now,
                scheduled_at=None,
                error_message=None,
                whatsapp_message_id=result.message_id,
                now=now,
            )
            # Publish event
            await self._publish_event(campaign_id, influencer.id, InvitationStatus.SENT)
        except BlacklistViolationError:
            raise
        except Exception as exc:
            await self._save_invitation(
                db=db,
                invitation_id=invitation_id,
                campaign_id=campaign_id,
                influencer_id=influencer.id,
                template_id=template_id,
                message_content=message_content,
                status=InvitationStatus.FAILED,
                sent_at=None,
                scheduled_at=None,
                error_message=str(exc),
                whatsapp_message_id=None,
                now=now,
            )
            await self._publish_event(campaign_id, influencer.id, InvitationStatus.FAILED)
            raise

        return invitation_id

    # ------------------------------------------------------------------
    # send_bulk_invitations
    # ------------------------------------------------------------------

    async def send_bulk_invitations(
        self,
        influencers: List[Influencer],
        template_id: str,
        campaign_id: str,
        db: AsyncSession,
        scheduled_at: Optional[datetime] = None,
    ) -> InvitationReport:
        """Kirim undangan massal ke daftar influencer.

        - Rate limiting: maks 100 undangan/menit (sliding window).
        - Jika satu influencer gagal, catat FAILED dan lanjutkan.
        - Kembalikan InvitationReport.
        """
        total_sent = 0
        total_failed = 0
        total_pending = 0

        for influencer in influencers:
            # Rate limiting hanya untuk pengiriman langsung (bukan scheduled)
            if scheduled_at is None:
                await self._wait_for_rate_limit()

            try:
                await self.send_single_invitation(
                    influencer=influencer,
                    template_id=template_id,
                    campaign_id=campaign_id,
                    db=db,
                    scheduled_at=scheduled_at,
                )
                if scheduled_at is not None:
                    total_pending += 1
                else:
                    total_sent += 1
            except BlacklistViolationError:
                total_failed += 1
            except Exception:
                total_failed += 1

        # Publish bulk event ke Redis Streams
        await self._publish_bulk_event(campaign_id, total_sent, total_failed, total_pending)

        return InvitationReport(
            campaign_id=campaign_id,
            total_sent=total_sent,
            total_failed=total_failed,
            total_pending=total_pending,
            total_processed=len(influencers),
        )

    # ------------------------------------------------------------------
    # generate_invitation_report
    # ------------------------------------------------------------------

    async def generate_invitation_report(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> InvitationReport:
        """Query tabel invitations untuk campaign_id dan hitung totals."""
        result = await db.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (WHERE status = 'SENT')       AS total_sent,
                    COUNT(*) FILTER (WHERE status = 'FAILED')     AS total_failed,
                    COUNT(*) FILTER (WHERE status IN ('PENDING', 'SCHEDULED')) AS total_pending,
                    COUNT(*)                                        AS total_processed
                FROM invitations
                WHERE campaign_id = :campaign_id
                """
            ),
            {"campaign_id": campaign_id},
        )
        row = result.mappings().first()
        if row is None:
            return InvitationReport(
                campaign_id=campaign_id,
                total_sent=0,
                total_failed=0,
                total_pending=0,
                total_processed=0,
            )

        return InvitationReport(
            campaign_id=campaign_id,
            total_sent=int(row["total_sent"] or 0),
            total_failed=int(row["total_failed"] or 0),
            total_pending=int(row["total_pending"] or 0),
            total_processed=int(row["total_processed"] or 0),
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _save_invitation(
        self,
        db: AsyncSession,
        invitation_id: str,
        campaign_id: str,
        influencer_id: str,
        template_id: str,
        message_content: str,
        status: InvitationStatus,
        sent_at: Optional[datetime],
        scheduled_at: Optional[datetime],
        error_message: Optional[str],
        whatsapp_message_id: Optional[str],
        now: datetime,
    ) -> None:
        await db.execute(
            text(
                """
                INSERT INTO invitations
                    (id, campaign_id, influencer_id, template_id, message_content,
                     status, sent_at, scheduled_at, error_message, whatsapp_message_id,
                     created_at, updated_at)
                VALUES
                    (:id, :campaign_id, :influencer_id, :template_id, :message_content,
                     :status, :sent_at, :scheduled_at, :error_message, :whatsapp_message_id,
                     :now, :now)
                """
            ),
            {
                "id": invitation_id,
                "campaign_id": campaign_id,
                "influencer_id": influencer_id,
                "template_id": template_id,
                "message_content": message_content,
                "status": status.value,
                "sent_at": sent_at,
                "scheduled_at": scheduled_at,
                "error_message": error_message,
                "whatsapp_message_id": whatsapp_message_id,
                "now": now,
            },
        )
        await db.flush()

    async def _publish_event(
        self,
        campaign_id: str,
        influencer_id: str,
        status: InvitationStatus,
    ) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.xadd(
                "agent:events",
                {
                    "type": "invitation_sent",
                    "campaign_id": campaign_id,
                    "influencer_id": influencer_id,
                    "status": status.value,
                },
            )
        except Exception:
            pass

    async def _publish_bulk_event(
        self,
        campaign_id: str,
        total_sent: int,
        total_failed: int,
        total_pending: int,
    ) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.xadd(
                "agent:events",
                {
                    "type": "bulk_invitations_sent",
                    "campaign_id": campaign_id,
                    "total_sent": str(total_sent),
                    "total_failed": str(total_failed),
                    "total_pending": str(total_pending),
                },
            )
        except Exception:
            pass
