"""Report Service — generate campaign reports and export in CSV/Excel/PDF."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class CampaignReportData:
    campaign_id: str
    total_influencers: int
    acceptance_rate: float          # 0.0 – 1.0
    total_views: int
    total_gmv: float
    cost_per_conversion: float
    generated_at: datetime = field(default_factory=_now_utc)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ReportService:
    """Generates campaign performance reports and exports them."""

    # ------------------------------------------------------------------
    # Core report generation
    # ------------------------------------------------------------------

    async def generate_campaign_report(
        self,
        campaign_id: str,
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[str]] = None,
        status: Optional[str] = None,
    ) -> CampaignReportData:
        """Query campaigns, invitations, and content_metrics to build a report."""

        # --- total influencers invited ---
        inv_result = await db.execute(
            text("SELECT COUNT(*) AS cnt FROM invitations WHERE campaign_id = :cid"),
            {"cid": campaign_id},
        )
        inv_row = inv_result.mappings().first()
        total_influencers: int = int(inv_row["cnt"]) if inv_row else 0

        # --- acceptance rate (DELIVERED / total) ---
        acc_result = await db.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM invitations "
                "WHERE campaign_id = :cid AND status = 'DELIVERED'"
            ),
            {"cid": campaign_id},
        )
        acc_row = acc_result.mappings().first()
        accepted: int = int(acc_row["cnt"]) if acc_row else 0
        acceptance_rate: float = (accepted / total_influencers) if total_influencers > 0 else 0.0

        # --- content metrics aggregation ---
        metrics_result = await db.execute(
            text(
                "SELECT COALESCE(SUM(views), 0) AS total_views, "
                "       COALESCE(SUM(gmv_generated), 0) AS total_gmv, "
                "       COALESCE(AVG(conversion_rate), 0) AS avg_conversion "
                "FROM content_metrics WHERE campaign_id = :cid"
            ),
            {"cid": campaign_id},
        )
        metrics_row = metrics_result.mappings().first()
        total_views: int = int(metrics_row["total_views"]) if metrics_row else 0
        total_gmv: float = float(metrics_row["total_gmv"]) if metrics_row else 0.0
        avg_conversion: float = float(metrics_row["avg_conversion"]) if metrics_row else 0.0

        # --- cost per conversion ---
        cost_per_conversion: float = (total_gmv / avg_conversion) if avg_conversion > 0 else 0.0

        return CampaignReportData(
            campaign_id=campaign_id,
            total_influencers=total_influencers,
            acceptance_rate=acceptance_rate,
            total_views=total_views,
            total_gmv=total_gmv,
            cost_per_conversion=cost_per_conversion,
            generated_at=_now_utc(),
        )

    # ------------------------------------------------------------------
    # Export helpers
    # ------------------------------------------------------------------

    async def export_csv(self, campaign_id: str, db: AsyncSession) -> str:
        """Return a CSV string of the campaign report. Jika campaign_id='all', ekspor semua."""
        reports = await self._get_reports(campaign_id, db)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "campaign_id", "total_influencers", "acceptance_rate",
            "total_views", "total_gmv", "cost_per_conversion", "generated_at",
        ])
        for report in reports:
            writer.writerow([
                report.campaign_id,
                report.total_influencers,
                f"{report.acceptance_rate:.2%}",
                report.total_views,
                report.total_gmv,
                report.cost_per_conversion,
                report.generated_at.isoformat(),
            ])
        return output.getvalue()

    async def export_excel(self, campaign_id: str, db: AsyncSession) -> bytes:
        """Return Excel bytes. Jika campaign_id='all', ekspor semua kampanye."""
        import openpyxl  # type: ignore

        reports = await self._get_reports(campaign_id, db)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Laporan Kampanye"

        headers = [
            "ID Kampanye", "Total Influencer", "Tingkat Penerimaan",
            "Total Views", "Total GMV (Rp)", "Biaya per Konversi", "Dibuat",
        ]
        ws.append(headers)
        for report in reports:
            ws.append([
                report.campaign_id,
                report.total_influencers,
                f"{report.acceptance_rate:.2%}",
                report.total_views,
                report.total_gmv,
                report.cost_per_conversion,
                report.generated_at.isoformat(),
            ])

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def export_pdf(self, campaign_id: str, db: AsyncSession) -> bytes:
        """Return PDF bytes. Jika campaign_id='all', ekspor semua kampanye."""
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore

        reports = await self._get_reports(campaign_id, db)

        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 50, "Laporan Performa Kampanye")

        c.setFont("Helvetica", 10)
        y = height - 80
        for report in reports:
            if y < 100:
                c.showPage()
                y = height - 50
            c.setFont("Helvetica-Bold", 11)
            c.drawString(50, y, f"Kampanye: {report.campaign_id}")
            y -= 16
            c.setFont("Helvetica", 10)
            lines = [
                f"  Total Influencer : {report.total_influencers}",
                f"  Tingkat Penerimaan: {report.acceptance_rate:.2%}",
                f"  Total Views      : {report.total_views}",
                f"  Total GMV        : Rp {report.total_gmv:,.0f}",
                f"  Dibuat           : {report.generated_at.isoformat()}",
            ]
            for line in lines:
                c.drawString(50, y, line)
                y -= 14
            y -= 10

        c.save()
        return buf.getvalue()

    async def _get_reports(self, campaign_id: str, db: AsyncSession) -> List[CampaignReportData]:
        """Ambil satu atau semua laporan kampanye."""
        if campaign_id != "all":
            return [await self.generate_campaign_report(campaign_id, db)]

        # Ambil semua campaign_id dari DB
        result = await db.execute(
            text("SELECT id FROM campaigns ORDER BY created_at DESC")
        )
        rows = result.mappings().all()
        reports = []
        for row in rows:
            try:
                report = await self.generate_campaign_report(str(row["id"]), db)
                reports.append(report)
            except Exception:
                continue
        return reports
