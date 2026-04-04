"""Agent Orchestrator — koordinasi semua agen dan manajemen state kampanye."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.classifier_agent import ClassifierAgent
from app.agents.learning_engine import LearningEngine
from app.agents.monitor_agent import MonitorAgent
from app.agents.selector_agent import SelectorAgent
from app.agents.sender_agent import SenderAgent
from app.exceptions import ValidationError
from app.integrations.affiliate_center import AffiliateCenterClient
from app.models.domain import Campaign, CampaignStatus, InfluencerFeedback, SelectionCriteria

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class CampaignResult:
    """Hasil dari start_campaign()."""

    campaign_id: str
    status: CampaignStatus
    influencers_selected: int
    invitations_sent: int
    invitations_failed: int


# ---------------------------------------------------------------------------
# AgentOrchestrator
# ---------------------------------------------------------------------------


class AgentOrchestrator:
    """Mengkoordinasikan semua agen dan mengelola state kampanye."""

    def __init__(
        self,
        selector_agent: SelectorAgent,
        sender_agent: SenderAgent,
        monitor_agent: MonitorAgent,
        classifier_agent: ClassifierAgent,
        affiliate_client: Optional[AffiliateCenterClient] = None,
        redis: Optional[object] = None,
        learning_engine: Optional[LearningEngine] = None,
    ) -> None:
        self._selector = selector_agent
        self._sender = sender_agent
        self._monitor = monitor_agent
        self._classifier = classifier_agent
        self._affiliate_client = affiliate_client or AffiliateCenterClient()
        self._redis = redis
        self._learning_engine = learning_engine

    # ------------------------------------------------------------------
    # start_campaign
    # ------------------------------------------------------------------

    async def start_campaign(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> CampaignResult:
        """Orkestrasi urutan start kampanye:

        1. Ambil data kampanye dari DB
        2. Ambil daftar influencer dari Affiliate Center
        3. Panggil SelectorAgent.select_influencers()
        4. Panggil SenderAgent.send_bulk_invitations()
        5. Panggil MonitorAgent.start_monitoring()
        6. Update status kampanye menjadi ACTIVE
        7. Kembalikan CampaignResult
        """
        # 1. Ambil data kampanye dari DB
        campaign = await self._get_campaign(campaign_id, db)
        if campaign is None:
            raise ValidationError(f"Kampanye dengan id '{campaign_id}' tidak ditemukan.")

        # 2. Ambil daftar influencer dari Affiliate Center
        influencers = []
        try:
            result = await self._affiliate_client.get_influencers(page=1, page_size=100)
            influencers = result.items
        except Exception as exc:
            logger.warning("Gagal mengambil influencer dari Affiliate Center: %s", exc)

        # 3. Ambil criteria dari DB dan panggil SelectorAgent
        criteria = await self._get_selection_criteria(campaign.selection_criteria_id, db)
        selection_result = await self._selector.select_influencers(
            criteria=criteria,
            campaign_id=campaign_id,
            influencers=influencers,
        )
        selected_influencers = selection_result.influencers

        # 4. Kirim undangan massal
        invitation_report = await self._sender.send_bulk_invitations(
            influencers=selected_influencers,
            template_id=campaign.template_id,
            campaign_id=campaign_id,
            db=db,
        )

        # 5. Mulai monitoring
        await self._monitor.start_monitoring(campaign_id=campaign_id, db=db)

        # 6. Update status kampanye menjadi ACTIVE
        await self._update_campaign_status(campaign_id, CampaignStatus.ACTIVE, db)

        # 7. Kembalikan CampaignResult
        return CampaignResult(
            campaign_id=campaign_id,
            status=CampaignStatus.ACTIVE,
            influencers_selected=selection_result.total_found,
            invitations_sent=invitation_report.total_sent,
            invitations_failed=invitation_report.total_failed,
        )

    # ------------------------------------------------------------------
    # stop_campaign
    # ------------------------------------------------------------------

    async def stop_campaign(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> None:
        """Hentikan monitoring, update status kampanye menjadi COMPLETED,
        dan panggil LearningEngine.record_campaign_outcome() jika tersedia.
        Jadwalkan retraining sebagai background task setelah record selesai.
        """
        import asyncio

        # Hentikan monitoring
        self._monitor.stop_monitoring(campaign_id)

        # Update status kampanye menjadi COMPLETED
        await self._update_campaign_status(campaign_id, CampaignStatus.COMPLETED, db)

        # Panggil LearningEngine jika tersedia
        learning_engine = getattr(self, "_learning_engine", None)
        if learning_engine is not None:
            try:
                await learning_engine.record_campaign_outcome(campaign_id, db)
                # Jadwalkan retraining sebagai background task (tidak memblokir)
                asyncio.create_task(
                    self._run_retraining(learning_engine, db)
                )
            except Exception as exc:
                logger.warning("LearningEngine.record_campaign_outcome gagal: %s", exc)

    async def _run_retraining(
        self,
        learning_engine: "LearningEngine",
        db: AsyncSession,
    ) -> None:
        """Jalankan retraining selection dan classifier model sebagai background task."""
        try:
            await learning_engine.retrain_selection_model(db)
        except Exception as exc:
            logger.warning("retrain_selection_model gagal: %s", exc)
        try:
            await learning_engine.retrain_classifier_model(db)
        except Exception as exc:
            logger.warning("retrain_classifier_model gagal: %s", exc)

    # ------------------------------------------------------------------
    # get_campaign_status
    # ------------------------------------------------------------------

    async def get_campaign_status(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> CampaignStatus:
        """Ambil status kampanye dari DB."""
        campaign = await self._get_campaign(campaign_id, db)
        if campaign is None:
            raise ValidationError(f"Kampanye dengan id '{campaign_id}' tidak ditemukan.")
        return campaign.status

    # ------------------------------------------------------------------
    # handle_agent_event
    # ------------------------------------------------------------------

    async def handle_agent_event(
        self,
        event: Dict[str, Any],
        db: AsyncSession,
    ) -> None:
        """Proses event dari Redis Streams.

        - "feedback_received" → panggil ClassifierAgent.classify_feedback()
        - "content_non_compliant" → log notifikasi
        """
        event_type = event.get("type", "")

        if event_type == "feedback_received":
            feedback_data = event.get("feedback")
            if feedback_data is not None and isinstance(feedback_data, InfluencerFeedback):
                try:
                    await self._classifier.classify_feedback(feedback=feedback_data, db=db)
                except Exception as exc:
                    logger.error("Gagal mengklasifikasikan feedback: %s", exc)

        elif event_type == "content_non_compliant":
            campaign_id = event.get("campaign_id", "")
            influencer_id = event.get("influencer_id", "")
            video_id = event.get("video_id", "")
            logger.warning(
                "Konten tidak sesuai panduan — campaign_id=%s, influencer_id=%s, video_id=%s",
                campaign_id,
                influencer_id,
                video_id,
            )

        else:
            logger.debug("Event tidak dikenal: %s", event_type)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_campaign(
        self,
        campaign_id: str,
        db: AsyncSession,
    ) -> Optional[Campaign]:
        """Ambil kampanye dari DB berdasarkan id."""
        import json
        from datetime import datetime

        from app.models.domain import CampaignSettings

        result = await db.execute(
            text("SELECT * FROM campaigns WHERE id = :id"),
            {"id": campaign_id},
        )
        row = result.mappings().first()
        if row is None:
            return None

        settings_raw = row.get("settings") or {}
        if isinstance(settings_raw, str):
            settings_raw = json.loads(settings_raw)

        settings = CampaignSettings(
            max_invitations_per_minute=settings_raw.get("max_invitations_per_minute", 100),
            monitoring_interval_minutes=settings_raw.get("monitoring_interval_minutes", 30),
            compliance_check_enabled=settings_raw.get("compliance_check_enabled", True),
            alert_thresholds=settings_raw.get("alert_thresholds", {}),
        )

        return Campaign(
            id=str(row["id"]),
            name=row["name"],
            description=row.get("description", ""),
            status=CampaignStatus(row["status"]),
            selection_criteria_id=str(row["selection_criteria_id"]),
            template_id=str(row["template_id"]),
            start_date=row["start_date"],
            end_date=row["end_date"],
            created_by=str(row["created_by"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            settings=settings,
        )

    async def _get_selection_criteria(
        self,
        criteria_id: str,
        db: AsyncSession,
    ) -> SelectionCriteria:
        """Ambil SelectionCriteria dari DB."""
        import json

        from app.models.domain import CriteriaWeights

        result = await db.execute(
            text("SELECT * FROM selection_criteria WHERE id = :id"),
            {"id": criteria_id},
        )
        row = result.mappings().first()
        if row is None:
            # Kembalikan criteria default jika tidak ditemukan
            return SelectionCriteria(id=criteria_id, name="Default")

        content_categories = row.get("content_categories") or []
        if isinstance(content_categories, str):
            content_categories = json.loads(content_categories)

        locations = row.get("locations") or []
        if isinstance(locations, str):
            locations = json.loads(locations)

        weights = CriteriaWeights(
            follower_count=float(row.get("weight_follower_count") or 0.3),
            engagement_rate=float(row.get("weight_engagement_rate") or 0.4),
            category_match=float(row.get("weight_category_match") or 0.2),
            location_match=float(row.get("weight_location_match") or 0.1),
        )

        return SelectionCriteria(
            id=str(row["id"]),
            name=row.get("name", ""),
            min_followers=row.get("min_followers"),
            max_followers=row.get("max_followers"),
            min_engagement_rate=row.get("min_engagement_rate"),
            content_categories=list(content_categories) if content_categories else None,
            locations=list(locations) if locations else None,
            criteria_weights=weights,
            is_template=bool(row.get("is_template", False)),
        )

    async def _update_campaign_status(
        self,
        campaign_id: str,
        status: CampaignStatus,
        db: AsyncSession,
    ) -> None:
        """Update status kampanye di DB."""
        from datetime import datetime, timezone

        await db.execute(
            text(
                """
                UPDATE campaigns
                SET status = :status, updated_at = :now
                WHERE id = :id
                """
            ),
            {
                "status": status.value,
                "now": datetime.now(timezone.utc),
                "id": campaign_id,
            },
        )
        await db.flush()
