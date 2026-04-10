"""Brands API — CRUD brand, SKU, dan export Excel."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import io

from app.database import get_db_session
from app.services.rbac import get_current_user
from app.services.report_export_service import (
    generate_excel1_outreach,
    generate_excel2_deal,
    generate_excel3_master_brand,
)

router = APIRouter(prefix="/brands", tags=["brands"])


# ─── Models ───────────────────────────────────────────────────────────────────

class BrandCreate(BaseModel):
    name: str
    wa_number: Optional[str] = None
    sow: Optional[str] = None
    message_template: Optional[str] = None


class BrandSKUCreate(BaseModel):
    product_name: str
    affiliate_link: Optional[str] = None
    price: int = 0


class DealRecordCreate(BaseModel):
    affiliate_id: Optional[str] = None
    brand_id: str
    username: Optional[str] = None
    link_acc: Optional[str] = None
    follower_count: int = 0
    contact_wa: Optional[str] = None
    pic: Optional[str] = None
    avg_gmv_per_month: int = 0
    gmv_per_buyer: int = 0
    update_status: Optional[str] = None
    respon_status: Optional[str] = None
    speed_status: Optional[str] = None
    result_status: Optional[str] = None
    status_sempel: Optional[str] = None
    link_video: Optional[str] = None
    total_vt: int = 0
    note_deal: Optional[str] = None
    note_dari_rara: Optional[str] = None
    id_pesanan: Optional[str] = None
    no_va_co_sampel: Optional[str] = None
    status_payment_sampel: Optional[str] = None
    gmv_week1_after_join: int = 0
    gmv_week2_after_join: int = 0
    gmv_week3_after_join: int = 0
    gmv_week4_after_join: int = 0
    gmv_perbulan_after_join: int = 0


# ─── Brand CRUD ───────────────────────────────────────────────────────────────

@router.get("")
async def list_brands(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(text("""
        SELECT b.id, b.name, b.wa_number, b.sow, b.message_template, b.is_active,
               COUNT(bs.id) as sku_count
        FROM brands b
        LEFT JOIN brand_skus bs ON b.id = bs.brand_id AND bs.is_active = TRUE
        WHERE b.is_active = TRUE
        GROUP BY b.id
        ORDER BY b.name
    """))
    rows = result.mappings().all()
    return [dict(r) for r in rows]


@router.post("")
async def create_brand(
    body: BrandCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(text("""
        INSERT INTO brands (name, wa_number, sow, message_template)
        VALUES (:name, :wa, :sow, :template)
        RETURNING id, name
    """), {"name": body.name, "wa": body.wa_number, "sow": body.sow, "template": body.message_template})
    row = result.mappings().first()
    await db.commit()
    return dict(row)


@router.get("/{brand_id}/skus")
async def list_brand_skus(
    brand_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(text("""
        SELECT id, brand_id, product_name, affiliate_link, price, is_active
        FROM brand_skus WHERE brand_id = :brand_id AND is_active = TRUE
        ORDER BY product_name
    """), {"brand_id": brand_id})
    return [dict(r) for r in result.mappings().all()]


@router.post("/{brand_id}/skus")
async def add_brand_sku(
    brand_id: str,
    body: BrandSKUCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    result = await db.execute(text("""
        INSERT INTO brand_skus (brand_id, product_name, affiliate_link, price)
        VALUES (:brand_id, :name, :link, :price)
        RETURNING id, product_name
    """), {"brand_id": brand_id, "name": body.product_name, "link": body.affiliate_link, "price": body.price})
    row = result.mappings().first()
    await db.commit()
    return dict(row)


# ─── Deal Records ─────────────────────────────────────────────────────────────

@router.post("/deals")
async def create_deal_record(
    body: DealRecordCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    await db.execute(text("""
        INSERT INTO deal_records (
            affiliate_id, brand_id, username, link_acc, follower_count, contact_wa,
            pic, avg_gmv_per_month, gmv_per_buyer, update_status, respon_status,
            speed_status, result_status, status_sempel, link_video, total_vt,
            note_deal, note_dari_rara, id_pesanan, no_va_co_sampel,
            status_payment_sampel, gmv_week1_after_join, gmv_week2_after_join,
            gmv_week3_after_join, gmv_week4_after_join, gmv_perbulan_after_join
        ) VALUES (
            :affiliate_id, :brand_id, :username, :link_acc, :follower_count, :contact_wa,
            :pic, :avg_gmv, :gmv_buyer, :update_status, :respon_status,
            :speed_status, :result_status, :status_sempel, :link_video, :total_vt,
            :note_deal, :note_rara, :id_pesanan, :no_va,
            :status_payment, :week1, :week2, :week3, :week4, :perbulan
        )
    """), {
        "affiliate_id": body.affiliate_id, "brand_id": body.brand_id,
        "username": body.username, "link_acc": body.link_acc,
        "follower_count": body.follower_count, "contact_wa": body.contact_wa,
        "pic": body.pic, "avg_gmv": body.avg_gmv_per_month,
        "gmv_buyer": body.gmv_per_buyer, "update_status": body.update_status,
        "respon_status": body.respon_status, "speed_status": body.speed_status,
        "result_status": body.result_status, "status_sempel": body.status_sempel,
        "link_video": body.link_video, "total_vt": body.total_vt,
        "note_deal": body.note_deal, "note_rara": body.note_dari_rara,
        "id_pesanan": body.id_pesanan, "no_va": body.no_va_co_sampel,
        "status_payment": body.status_payment_sampel,
        "week1": body.gmv_week1_after_join, "week2": body.gmv_week2_after_join,
        "week3": body.gmv_week3_after_join, "week4": body.gmv_week4_after_join,
        "perbulan": body.gmv_perbulan_after_join,
    })
    await db.commit()
    return {"status": "created"}


# ─── Export Excel ─────────────────────────────────────────────────────────────

@router.get("/export/outreach")
async def export_excel1_outreach(
    brand_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    data = await generate_excel1_outreach(db, brand_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=database_outreach.xlsx"}
    )


@router.get("/export/deal")
async def export_excel2_deal(
    brand_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    data = await generate_excel2_deal(db, brand_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=database_deal.xlsx"}
    )


@router.get("/export/master-brand")
async def export_excel3_master_brand(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    data = await generate_excel3_master_brand(db)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=master_brand.xlsx"}
    )
