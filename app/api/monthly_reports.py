"""Monthly Reports API."""
from __future__ import annotations
from datetime import date
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user
from app.services.monthly_report_service import (
    calculate_metrics,
    generate_ai_insights,
    get_top_performers,
)

router = APIRouter(prefix="/monthly-reports", tags=["monthly-reports"])


class MonthlyReportCreate(BaseModel):
    brand_id: str
    batch_name: str
    period_start: date
    period_end: date
    gmv_previous: int = 0
    # Optional overrides
    total_products_sold: int = 0
    total_orders_settled: int = 0
    # Editable insights
    insight_key_metrics: Optional[str] = None
    insight_affiliate: Optional[str] = None
    insight_funnel: Optional[str] = None
    insight_gmv: Optional[str] = None
    insight_product: Optional[str] = None
    insight_gap: Optional[str] = None
    insight_strategic: Optional[str] = None
    next_plan: Optional[str] = None
    kesimpulan: Optional[str] = None


class MonthlyReportUpdate(BaseModel):
    batch_name: Optional[str] = None
    insight_key_metrics: Optional[str] = None
    insight_affiliate: Optional[str] = None
    insight_funnel: Optional[str] = None
    insight_gmv: Optional[str] = None
    insight_product: Optional[str] = None
    insight_gap: Optional[str] = None
    insight_strategic: Optional[str] = None
    next_plan: Optional[str] = None
    kesimpulan: Optional[str] = None
    total_products_sold: Optional[int] = None
    total_orders_settled: Optional[int] = None
    gmv_previous: Optional[int] = None


@router.get("/preview")
async def preview_metrics(
    brand_id: str = Query(...),
    period_start: date = Query(...),
    period_end: date = Query(...),
    gmv_previous: int = Query(0),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Preview kalkulasi otomatis + AI insights sebelum disimpan."""
    # Get brand name
    brand_result = await db.execute(
        text("SELECT name FROM brands WHERE id = :id"), {"id": brand_id}
    )
    brand = brand_result.mappings().first()
    brand_name = brand["name"] if brand else "Brand"

    metrics = await calculate_metrics(db, brand_id, period_start, period_end, gmv_previous)
    top_performers = await get_top_performers(db, brand_id, period_start, period_end)
    insights = generate_ai_insights(metrics, brand_name, "Preview", top_performers)

    return {
        "metrics": metrics,
        "top_performers": top_performers,
        "insights": insights,
    }


@router.post("")
async def create_monthly_report(
    body: MonthlyReportCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Buat monthly report baru — kalkulasi otomatis + simpan insights."""
    brand_result = await db.execute(
        text("SELECT name FROM brands WHERE id = :id"), {"id": body.brand_id}
    )
    brand = brand_result.mappings().first()
    brand_name = brand["name"] if brand else "Brand"

    metrics = await calculate_metrics(
        db, body.brand_id, body.period_start, body.period_end, body.gmv_previous
    )
    metrics["total_products_sold"] = body.total_products_sold
    metrics["total_orders_settled"] = body.total_orders_settled

    top_performers = await get_top_performers(db, body.brand_id, body.period_start, body.period_end)
    ai_insights = generate_ai_insights(metrics, brand_name, body.batch_name, top_performers)

    # User-provided insights override AI
    final_insights = {
        k: getattr(body, k) or v
        for k, v in ai_insights.items()
    }

    result = await db.execute(text("""
        INSERT INTO monthly_reports (
            brand_id, batch_name, period_start, period_end,
            total_deal, total_uploaded, total_not_uploaded, total_videos,
            total_generate_sales, gmv_current, gmv_previous, gmv_video, gmv_live,
            total_products_sold, total_orders_settled,
            insight_key_metrics, insight_affiliate, insight_funnel, insight_gmv,
            insight_product, insight_gap, insight_strategic, next_plan, kesimpulan
        ) VALUES (
            :brand_id, :batch_name, :period_start, :period_end,
            :total_deal, :total_uploaded, :total_not_uploaded, :total_videos,
            :total_generate_sales, :gmv_current, :gmv_previous, :gmv_video, :gmv_live,
            :total_products_sold, :total_orders_settled,
            :insight_key_metrics, :insight_affiliate, :insight_funnel, :insight_gmv,
            :insight_product, :insight_gap, :insight_strategic, :next_plan, :kesimpulan
        ) RETURNING id
    """), {
        "brand_id": body.brand_id,
        "batch_name": body.batch_name,
        "period_start": body.period_start,
        "period_end": body.period_end,
        **{k: metrics.get(k, 0) for k in [
            "total_deal", "total_uploaded", "total_not_uploaded", "total_videos",
            "total_generate_sales", "gmv_current", "gmv_previous", "gmv_video", "gmv_live",
            "total_products_sold", "total_orders_settled",
        ]},
        **final_insights,
    })
    row = result.mappings().first()
    await db.commit()
    return {"id": str(row["id"]), "status": "created"}


@router.get("")
async def list_monthly_reports(
    brand_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    where = "WHERE mr.brand_id = :brand_id" if brand_id else ""
    result = await db.execute(text(f"""
        SELECT mr.id, mr.brand_id, b.name as brand_name, mr.batch_name,
               mr.period_start, mr.period_end,
               mr.total_deal, mr.total_uploaded, mr.total_generate_sales,
               mr.gmv_current, mr.gmv_previous, mr.created_at
        FROM monthly_reports mr
        JOIN brands b ON mr.brand_id = b.id
        {where}
        ORDER BY mr.period_start DESC
    """), {"brand_id": brand_id} if brand_id else {})
    return [dict(r) for r in result.mappings().all()]


@router.get("/{report_id}")
async def get_monthly_report(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(text("""
        SELECT mr.*, b.name as brand_name
        FROM monthly_reports mr
        JOIN brands b ON mr.brand_id = b.id
        WHERE mr.id = :id
    """), {"id": report_id})
    row = result.mappings().first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Report tidak ditemukan")

    # Top performers
    top = await get_top_performers(
        db, str(row["brand_id"]), row["period_start"], row["period_end"]
    )
    data = dict(row)
    data["top_performers"] = top
    return data


@router.patch("/{report_id}")
async def update_monthly_report(
    report_id: str,
    body: MonthlyReportUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Update insights (editable oleh user)."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        return {"status": "no changes"}

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["id"] = report_id
    updates["updated_at"] = date.today()

    await db.execute(text(f"""
        UPDATE monthly_reports SET {set_clause}, updated_at = NOW()
        WHERE id = :id
    """), updates)
    await db.commit()
    return {"status": "updated"}


from fastapi.responses import StreamingResponse
import io
from app.services.report_export_service import generate_excel_monthly_report


@router.get("/{report_id}/export")
async def export_monthly_report_excel(
    report_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    data = await generate_excel_monthly_report(db, report_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=monthly_report_{report_id}.xlsx"}
    )
