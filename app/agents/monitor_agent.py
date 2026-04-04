"""Monitor Agent — memantau konten TikTok influencer secara periodik."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.tiktok_api import TikTokAPIClient, TikTokContent
from app.models.domain import ContentMetrics


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InfluencerReport:
    """Laporan performa per influencer dalam kampanye."""

    influencer_id: str
    total_views: int
    total_gmv: float
    conversion_rate: float


@dataclass
class CampaignReport:
    """Laporan performa akhir kampanye."""

    campaign_id: str
    influencer_reports: List[InfluencerReport]
    total_views: int
    total_gmv: float
    total_conversion_rate: float


# ---------------------------------------------------------------------------
# Known affiliate domains for link validation
# ---------------------------------------------------------------------------

_KNOWN_AFFILIATE_DOMAINS = [
    "affiliate.tiktok.com",
    "s.tiktok.com",
    "shope.ee",
    "tokopedia.com",
    "shopee.co.id",
    "lazada.co.id",
]


# ---------------------------------------------------------------------------
# MonitorAgent
# ---------------------------------------------------------------------------


class MonitorAgent:
    """Memantau konten TikTok influencer dan menghasilkan laporan kampanye."""

    def __init__(
        self,
        tiktok_client: Optional[TikTokAPIClient] = None,
        redis: Optional[object] = None,
    ) -> None:
        self._tiktok = tiktok_client or TikTokAPIClient()
        self._redis = redis
        self._monitoring_tasks: Dict[str, asyncio.Task] = {}

    # ------------------------------------------------------------------
    # start_monitoring / stop_monitoring
    # ------------------------------------------------------------------

    async def start_monitoring(
        self,
        campaign_id: str,
        db: AsyncSession,
        _interval_seconds: int = 1800,
    ) -> None:
        """Mulai background task periodik yang memanggil check_new_content."""
        if campaign_id in self._monitoring_tasks:
            existing = self._monitoring_tasks[campaign_id]
            if not existing.done():
                return  # sudah berjalan

        async def _loop() -> None:
            while True:
                try:
                    await self.check_new_content(campaign_id, db)
                except Exception:
                    pass
                await asyncio.sleep(_interval_seconds)

        task = asyncio.create_task(_loop())
        self._monitoring_tasks[campaign_id] = task

    def stop_monitoring(self, campaign_id: str) -> None:
        """Batalkan background task untuk campaign_id."""
        task = self._monitoring_tasks.get(campaign_id)
        if task and not task.done():
            task.cancel()
        self._monitoring_tasks.pop(campaign_id, None)

    # ------------------------------------------------------------------
    # check_new_content
    # ------------------------------------------------------------------

    async def check_new_content(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> List[ContentMetrics]:
        """Ambil konten baru dari semua influencer kampanye dan simpan metrik."""
        influencers = await self._get_campaign_influencers(campaign_id, db)
        results: List[ContentMetrics] = []

        for influencer_id, tiktok_user_id in influencers:
            since = datetime.fromtimestamp(0, tz=timezone.utc)
            try:
                videos = await self._tiktok.get_user_videos(tiktok_user_id, since)
            except Exception:
                continue

            for content in videos:
                try:
                    raw_metrics = await self._tiktok.get_video_metrics(content.video_id)
                except Exception:
                    continue

                # Validasi metrik tidak null/negatif
                views = max(0, raw_metrics.views or 0)
                likes = max(0, raw_metrics.likes or 0)
                comments = max(0, raw_metrics.comments or 0)
                shares = max(0, raw_metrics.shares or 0)

                has_valid_link = await self.validate_affiliate_link(content, campaign_id)
                is_compliant = has_valid_link

                metrics = ContentMetrics(
                    id=str(uuid.uuid4()),
                    campaign_id=campaign_id,
                    influencer_id=influencer_id,
                    tiktok_video_id=content.video_id,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    has_valid_affiliate_link=has_valid_link,
                    gmv_generated=0.0,
                    conversion_rate=0.0,
                    recorded_at=datetime.now(timezone.utc),
                    is_compliant=is_compliant,
                )

                await self._save_content_metrics(metrics, db)

                if not is_compliant:
                    await self._publish_non_compliant_event(campaign_id, influencer_id, content.video_id)

                results.append(metrics)

        return results

    # ------------------------------------------------------------------
    # validate_affiliate_link
    # ------------------------------------------------------------------

    async def validate_affiliate_link(
        self,
        content: TikTokContent,
        campaign_id: str,
    ) -> bool:
        """Cek apakah konten mengandung tautan afiliasi yang valid untuk kampanye.

        Deterministik: True jika ada tautan yang mengandung campaign_id
        atau domain afiliasi yang dikenal.
        """
        for link in content.affiliate_links:
            if not link:
                continue
            # Cek apakah link mengandung campaign_id
            if campaign_id in link:
                return True
            # Cek domain afiliasi yang dikenal
            for domain in _KNOWN_AFFILIATE_DOMAINS:
                if domain in link:
                    return True
        return False

    # ------------------------------------------------------------------
    # generate_final_report
    # ------------------------------------------------------------------

    async def generate_final_report(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> CampaignReport:
        """Query content_metrics dan agregasi laporan per influencer."""
        result = await db.execute(
            text(
                """
                SELECT
                    influencer_id,
                    SUM(views)           AS total_views,
                    SUM(gmv_generated)   AS total_gmv,
                    AVG(conversion_rate) AS avg_conversion_rate
                FROM content_metrics
                WHERE campaign_id = :campaign_id
                GROUP BY influencer_id
                """
            ),
            {"campaign_id": campaign_id},
        )
        rows = result.mappings().all()

        influencer_reports: List[InfluencerReport] = []
        total_views = 0
        total_gmv = 0.0
        total_conversion_sum = 0.0

        for row in rows:
            inf_views = int(row["total_views"] or 0)
            inf_gmv = float(row["total_gmv"] or 0.0)
            inf_cr = float(row["avg_conversion_rate"] or 0.0)

            influencer_reports.append(
                InfluencerReport(
                    influencer_id=row["influencer_id"],
                    total_views=inf_views,
                    total_gmv=inf_gmv,
                    conversion_rate=inf_cr,
                )
            )
            total_views += inf_views
            total_gmv += inf_gmv
            total_conversion_sum += inf_cr

        n = len(influencer_reports)
        total_conversion_rate = total_conversion_sum / n if n > 0 else 0.0

        return CampaignReport(
            campaign_id=campaign_id,
            influencer_reports=influencer_reports,
            total_views=total_views,
            total_gmv=total_gmv,
            total_conversion_rate=total_conversion_rate,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_campaign_influencers(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> List[tuple]:
        """Ambil daftar (influencer_id, tiktok_user_id) yang berpartisipasi."""
        result = await db.execute(
            text(
                """
                SELECT DISTINCT i.id AS influencer_id, i.tiktok_user_id
                FROM influencers i
                JOIN invitations inv ON inv.influencer_id = i.id
                WHERE inv.campaign_id = :campaign_id
                  AND inv.status = 'SENT'
                """
            ),
            {"campaign_id": campaign_id},
        )
        rows = result.mappings().all()
        return [(row["influencer_id"], row["tiktok_user_id"]) for row in rows]

    async def _save_content_metrics(
        self,
        metrics: ContentMetrics,
        db: AsyncSession,
    ) -> None:
        await db.execute(
            text(
                """
                INSERT INTO content_metrics
                    (id, campaign_id, influencer_id, tiktok_video_id,
                     views, likes, comments, shares,
                     has_valid_affiliate_link, gmv_generated, conversion_rate,
                     recorded_at, is_compliant)
                VALUES
                    (:id, :campaign_id, :influencer_id, :tiktok_video_id,
                     :views, :likes, :comments, :shares,
                     :has_valid_affiliate_link, :gmv_generated, :conversion_rate,
                     :recorded_at, :is_compliant)
                """
            ),
            {
                "id": metrics.id,
                "campaign_id": metrics.campaign_id,
                "influencer_id": metrics.influencer_id,
                "tiktok_video_id": metrics.tiktok_video_id,
                "views": metrics.views,
                "likes": metrics.likes,
                "comments": metrics.comments,
                "shares": metrics.shares,
                "has_valid_affiliate_link": metrics.has_valid_affiliate_link,
                "gmv_generated": metrics.gmv_generated,
                "conversion_rate": metrics.conversion_rate,
                "recorded_at": metrics.recorded_at,
                "is_compliant": metrics.is_compliant,
            },
        )
        await db.flush()

    async def _publish_non_compliant_event(
        self,
        campaign_id: str,
        influencer_id: str,
        video_id: str,
    ) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.xadd(
                "agent:events",
                {
                    "type": "content_non_compliant",
                    "campaign_id": campaign_id,
                    "influencer_id": influencer_id,
                    "video_id": video_id,
                },
            )
        except Exception:
            pass
