"""Reports API router."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.domain import UserRole
from app.services.rbac import get_current_user, require_role
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class CampaignReportResponse(BaseModel):
    campaign_id: str
    total_influencers: int
    acceptance_rate: float
    total_views: int
    total_gmv: float
    cost_per_conversion: float
    generated_at: str


class ExportReportRequest(BaseModel):
    campaign_id: Optional[str] = None  # None = ekspor semua kampanye
    format: str = "csv"  # csv | excel | pdf
    start_date: Optional[str] = None
    end_date: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/campaigns", response_model=List[CampaignReportResponse])
async def list_campaign_reports(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[CampaignReportResponse]:
    """Laporan semua kampanye."""
    from sqlalchemy import text

    result = await db.execute(text("SELECT id FROM campaigns ORDER BY created_at DESC"))
    rows = result.mappings().all()

    svc = ReportService()
    reports = []
    for row in rows:
        try:
            report = await svc.generate_campaign_report(str(row["id"]), db)
            reports.append(
                CampaignReportResponse(
                    campaign_id=report.campaign_id,
                    total_influencers=report.total_influencers,
                    acceptance_rate=report.acceptance_rate,
                    total_views=report.total_views,
                    total_gmv=report.total_gmv,
                    cost_per_conversion=report.cost_per_conversion,
                    generated_at=report.generated_at.isoformat(),
                )
            )
        except Exception:
            continue
    return reports


@router.post("/export")
async def export_report(
    body: ExportReportRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Response:
    """Ekspor laporan kampanye dalam format csv, excel, atau pdf."""
    svc = ReportService()
    fmt = body.format.lower()

    # Jika tidak ada campaign_id, ekspor semua kampanye
    campaign_id = body.campaign_id or "all"

    if fmt == "csv":
        content = await svc.export_csv(campaign_id, db)
        return Response(
            content=content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=laporan-kampanye.csv"
            },
        )
    elif fmt == "excel":
        content = await svc.export_excel(campaign_id, db)
        return Response(
            content=content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=laporan-kampanye.xlsx"
            },
        )
    elif fmt == "pdf":
        content = await svc.export_pdf(campaign_id, db)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=laporan-kampanye.pdf"
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Format tidak didukung: '{fmt}'. Gunakan csv, excel, atau pdf.",
        )
