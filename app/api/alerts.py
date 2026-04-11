"""Alerts API — notifikasi bisnis untuk dashboard."""
from __future__ import annotations
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("")
async def get_alerts(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[Dict]:
    """Ambil semua alert bisnis aktif."""
    alerts = []

    # 1. Creator belum upload video (deal_records dengan link_video kosong)
    result = await db.execute(text("""
        SELECT b.name as brand_name, COUNT(*) as count
        FROM deal_records dr
        JOIN brands b ON dr.brand_id = b.id
        WHERE (dr.link_video IS NULL OR dr.link_video = '')
          AND dr.tanggal >= CURRENT_DATE - INTERVAL '30 days'
        GROUP BY b.name
        ORDER BY count DESC
        LIMIT 5
    """))
    rows = result.fetchall()
    for row in rows:
        if row[1] > 0:
            alerts.append({
                "type": "warning",
                "category": "upload",
                "title": f"{row[1]} creator belum upload",
                "message": f"Brand {row[0]} — {row[1]} creator belum upload video dalam 30 hari terakhir",
                "brand": row[0],
                "count": row[1],
            })

    # 2. Affiliator tanpa nomor WA (has_whatsapp = false, status ACTIVE)
    result2 = await db.execute(text("""
        SELECT COUNT(*) FROM influencers
        WHERE has_whatsapp = FALSE AND status = 'ACTIVE'
    """))
    no_wa_count = result2.scalar() or 0
    if no_wa_count > 0:
        alerts.append({
            "type": "info",
            "category": "whatsapp",
            "title": f"{no_wa_count} affiliator belum ada nomor WA",
            "message": f"{no_wa_count} affiliator aktif belum memiliki nomor WhatsApp",
            "count": no_wa_count,
        })

    # 3. Brand tanpa SKU
    result3 = await db.execute(text("""
        SELECT b.name FROM brands b
        LEFT JOIN brand_skus bs ON b.id = bs.brand_id AND bs.is_active = TRUE
        WHERE b.is_active = TRUE AND bs.id IS NULL
    """))
    brands_no_sku = [r[0] for r in result3.fetchall()]
    if brands_no_sku:
        alerts.append({
            "type": "warning",
            "category": "sku",
            "title": f"{len(brands_no_sku)} brand tanpa SKU",
            "message": f"Brand berikut belum memiliki SKU: {', '.join(brands_no_sku[:3])}{'...' if len(brands_no_sku) > 3 else ''}",
            "count": len(brands_no_sku),
        })

    # 4. Deal records tanpa GMV (result_status = deal tapi gmv = 0)
    result4 = await db.execute(text("""
        SELECT COUNT(*) FROM deal_records
        WHERE result_status ILIKE '%deal%'
          AND gmv_perbulan_after_join = 0
          AND tanggal >= CURRENT_DATE - INTERVAL '30 days'
    """))
    deal_no_gmv = result4.scalar() or 0
    if deal_no_gmv > 0:
        alerts.append({
            "type": "info",
            "category": "gmv",
            "title": f"{deal_no_gmv} deal belum ada data GMV",
            "message": f"{deal_no_gmv} deal dalam 30 hari terakhir belum diisi data GMV",
            "count": deal_no_gmv,
        })

    return alerts
