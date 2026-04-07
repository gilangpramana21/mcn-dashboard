"""Affiliates API router — pencarian, detail, dan kontak affiliate."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.domain import WhatsAppCollectionStatus
from app.services.contact_service import get_contact_channel, send_contact_message
from app.services.rbac import get_current_user

router = APIRouter(prefix="/affiliates", tags=["affiliates"])

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class AffiliateCardResponse(BaseModel):
    id: str
    name: str
    photo_url: Optional[str]
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    has_whatsapp: bool


class PaginatedAffiliateResponse(BaseModel):
    items: List[AffiliateCardResponse]
    total: int
    page: int
    page_size: int


class AffiliateDetailResponse(BaseModel):
    id: str
    name: str
    photo_url: Optional[str]
    follower_count: int
    engagement_rate: float
    content_categories: List[str]
    location: str
    bio: Optional[str]
    phone_number: Optional[str]
    contact_channel: str
    whatsapp_collection_status: Optional[str]
    tiktok_profile_url: Optional[str]
    tiktok_creator_id: Optional[str]
    data_source: Optional[str]
    tiktok_synced_at: Optional[str]


class ContactRequest(BaseModel):
    message: str


class ContactResponse(BaseModel):
    channel: str
    status: str
    message_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_categories(raw: Any) -> List[str]:
    """Parse content_categories dari DB (bisa list, string JSON, atau None)."""
    import json

    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return [raw] if raw else []
    return []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/search", response_model=PaginatedAffiliateResponse)
async def search_affiliates(
    min_followers: Optional[int] = Query(None),
    max_followers: Optional[int] = Query(None),
    min_engagement_rate: Optional[float] = Query(None),
    categories: Optional[List[str]] = Query(None),
    locations: Optional[List[str]] = Query(None),
    # Filter baru
    name: Optional[str] = Query(None, description="Cari berdasarkan nama (partial match)"),
    delivery_categories: Optional[str] = Query(None, description="Comma-separated delivery categories"),
    sales_methods: Optional[str] = Query(None, description="Comma-separated sales methods"),
    has_whatsapp: Optional[bool] = Query(None),
    invitation_status: Optional[str] = Query(None, description="invited|accepted|not_invited"),
    sort_by: Optional[str] = Query(None, description="relevance_desc|followers_desc|engagement_desc|newest"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PaginatedAffiliateResponse:
    """Cari affiliate dengan filter lengkap dan pagination."""
    conditions = []
    params: Dict[str, Any] = {}

    if name:
        conditions.append("LOWER(name) LIKE :name")
        params["name"] = f"%{name.lower()}%"

    if min_followers is not None:
        conditions.append("follower_count >= :min_followers")
        params["min_followers"] = min_followers

    if max_followers is not None:
        conditions.append("follower_count <= :max_followers")
        params["max_followers"] = max_followers

    if min_engagement_rate is not None:
        conditions.append("engagement_rate >= :min_engagement_rate")
        params["min_engagement_rate"] = min_engagement_rate

    if has_whatsapp is not None:
        conditions.append("has_whatsapp = :has_whatsapp")
        params["has_whatsapp"] = has_whatsapp

    if locations:
        placeholders = ", ".join(f":loc_{i}" for i in range(len(locations)))
        conditions.append(f"location IN ({placeholders})")
        for i, loc in enumerate(locations):
            params[f"loc_{i}"] = loc

    # Filter kategori kreator langsung di SQL
    if categories:
        cat_conditions = []
        for i, cat in enumerate(categories):
            cat_conditions.append(f"content_categories::text ILIKE :cat_{i}")
            params[f"cat_{i}"] = f"%{cat}%"
        conditions.append(f"({' OR '.join(cat_conditions)})")

    # Filter delivery_categories di SQL
    if delivery_categories:
        delivery_list = [d.strip() for d in delivery_categories.split(',') if d.strip()]
        if delivery_list:
            del_conditions = []
            for i, d in enumerate(delivery_list):
                del_conditions.append(f"delivery_categories::text ILIKE :del_{i}")
                params[f"del_{i}"] = f"%{d}%"
            conditions.append(f"({' OR '.join(del_conditions)})")

    # Filter sales_methods di SQL
    if sales_methods:
        sales_list = [s.strip() for s in sales_methods.split(',') if s.strip()]
        if sales_list:
            sm_conditions = []
            for i, s in enumerate(sales_list):
                sm_conditions.append(f"sales_methods::text ILIKE :sm_{i}")
                params[f"sm_{i}"] = f"%{s}%"
            conditions.append(f"({' OR '.join(sm_conditions)})")

    # Filter status undangan
    if invitation_status == "invited":
        conditions.append("status IN ('INVITED', 'ACCEPTED', 'REJECTED')")
    elif invitation_status == "accepted":
        conditions.append("status = 'ACCEPTED'")
    elif invitation_status == "not_invited":
        conditions.append("status = 'ACTIVE'")

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Sorting
    order_map = {
        "followers_desc": "follower_count DESC",
        "engagement_desc": "engagement_rate DESC",
        "newest": "created_at DESC",
        "relevance_desc": "relevance_score DESC NULLS LAST, follower_count DESC",
    }
    order_clause = f"ORDER BY {order_map.get(sort_by or '', 'follower_count DESC')}"

    # Count total
    count_result = await db.execute(
        text(f"SELECT COUNT(*) FROM influencers {where_clause}"),
        params,
    )
    total: int = count_result.scalar() or 0

    # Fetch page
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    rows_result = await db.execute(
        text(
            f"""
            SELECT id, name, follower_count, engagement_rate,
                   content_categories, location, phone_number, has_whatsapp,
                   delivery_categories, sales_methods, status
            FROM influencers
            {where_clause}
            {order_clause}
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    rows = rows_result.mappings().all()

    items: List[AffiliateCardResponse] = []
    for row in rows:
        cats = _parse_categories(row.get("content_categories"))
        items.append(
            AffiliateCardResponse(
                id=str(row["id"]),
                name=row["name"],
                photo_url=None,
                follower_count=row["follower_count"],
                engagement_rate=float(row["engagement_rate"]),
                content_categories=cats,
                location=row.get("location") or "",
                has_whatsapp=bool(row.get("has_whatsapp") or row.get("phone_number")),
            )
        )

    return PaginatedAffiliateResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{affiliate_id}", response_model=AffiliateDetailResponse)
async def get_affiliate_detail(
    affiliate_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AffiliateDetailResponse:
    """Ambil detail lengkap affiliate dari DB."""
    result = await db.execute(
        text(
            """
            SELECT id, name, follower_count, engagement_rate,
                   content_categories, location, phone_number, tiktok_user_id,
                   tiktok_creator_id, data_source, tiktok_synced_at
            FROM influencers
            WHERE tiktok_user_id = :affiliate_id OR id::text = :affiliate_id
               OR tiktok_creator_id = :affiliate_id
            LIMIT 1
            """
        ),
        {"affiliate_id": affiliate_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Affiliate '{affiliate_id}' tidak ditemukan.",
        )

    phone_number: Optional[str] = row.get("phone_number")
    contact_channel = "whatsapp" if phone_number else "seller_center_chat"

    # Cek WhatsAppCollectionRecord untuk status pengumpulan
    wa_status: Optional[str] = None
    wa_result = await db.execute(
        text(
            """
            SELECT status FROM whatsapp_collection_records
            WHERE affiliate_id = :affiliate_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"affiliate_id": affiliate_id},
    )
    wa_row = wa_result.fetchone()
    if wa_row:
        wa_status = wa_row[0]

    tiktok_user_id = row.get("tiktok_user_id")
    tiktok_profile_url = (
        f"https://www.tiktok.com/@{tiktok_user_id}" if tiktok_user_id else None
    )

    tiktok_synced_raw = row.get("tiktok_synced_at")
    tiktok_synced_str = tiktok_synced_raw.isoformat() if tiktok_synced_raw else None

    return AffiliateDetailResponse(
        id=str(row["id"]),
        name=row["name"],
        photo_url=None,
        follower_count=row["follower_count"],
        engagement_rate=float(row["engagement_rate"]),
        content_categories=_parse_categories(row.get("content_categories")),
        location=row.get("location") or "",
        bio=None,
        phone_number=phone_number,
        contact_channel=contact_channel,
        whatsapp_collection_status=wa_status,
        tiktok_profile_url=tiktok_profile_url,
        tiktok_creator_id=row.get("tiktok_creator_id"),
        data_source=row.get("data_source"),
        tiktok_synced_at=tiktok_synced_str,
    )


@router.post("/{affiliate_id}/contact", response_model=ContactResponse)
async def contact_affiliate(
    affiliate_id: str,
    body: ContactRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ContactResponse:
    """Kirim pesan ke affiliate melalui kanal yang sesuai (WhatsApp atau Seller Center chat)."""
    try:
        result = await send_contact_message(affiliate_id, body.message, db)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Gagal mengirim pesan: {exc}",
        )

    return ContactResponse(
        channel=result["channel"],
        status=result["status"],
        message_id=result.get("message_id"),
    )


# ---------------------------------------------------------------------------
# Import CSV
# ---------------------------------------------------------------------------

class ImportAffiliateItem(BaseModel):
    name: str
    tiktok_username: Optional[str] = None
    follower_count: int = 0
    engagement_rate: float = 0.0
    content_categories: List[str] = []
    location: str = ""
    phone_number: Optional[str] = None


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[str]
    auto_sent_tiktok: int


@router.post("/import", response_model=ImportResult)
async def import_affiliates(
    body: List[ImportAffiliateItem],
    auto_send_tiktok: bool = Query(True, description="Otomatis kirim pesan TikTok chat minta nomor WA"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ImportResult:
    """Import data affiliator dari CSV. Opsional auto-send pesan TikTok chat."""
    import uuid
    import json

    imported = 0
    skipped = 0
    errors: List[str] = []
    auto_sent = 0

    # Ambil template "Minta Nomor WA" untuk auto-send
    tiktok_template_content = None
    if auto_send_tiktok:
        tmpl_result = await db.execute(text("""
            SELECT content, default_values FROM message_templates
            WHERE message_type = 'request_whatsapp' AND is_active = TRUE
            LIMIT 1
        """))
        tmpl_row = tmpl_result.mappings().first()
        if tmpl_row:
            tiktok_template_content = tmpl_row["content"]

    for item in body:
        if not item.name.strip():
            skipped += 1
            continue

        try:
            # Cek apakah sudah ada (by tiktok_username atau nama)
            check_q = "SELECT id FROM influencers WHERE "
            check_params: Dict[str, Any] = {}
            if item.tiktok_username:
                check_q += "tiktok_user_id = :tiktok_id"
                check_params["tiktok_id"] = item.tiktok_username
            else:
                check_q += "LOWER(name) = :name"
                check_params["name"] = item.name.lower().strip()

            existing = await db.execute(text(check_q), check_params)
            existing_row = existing.mappings().first()

            if existing_row:
                # Update nomor WA jika ada
                if item.phone_number:
                    await db.execute(text("""
                        UPDATE influencers
                        SET phone_number = :phone, has_whatsapp = TRUE, updated_at = NOW()
                        WHERE id = :id
                    """), {"phone": item.phone_number, "id": str(existing_row["id"])})
                skipped += 1
                continue

            # Insert baru
            new_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO influencers
                    (id, name, tiktok_user_id, follower_count, engagement_rate,
                     content_categories, location, phone_number, has_whatsapp,
                     status, created_at, updated_at)
                VALUES
                    (:id, :name, :tiktok_id, :followers, :engagement,
                     cast(:categories as jsonb), :location, :phone, :has_wa,
                     'ACTIVE', NOW(), NOW())
            """), {
                "id": new_id,
                "name": item.name.strip(),
                "tiktok_id": item.tiktok_username,
                "followers": item.follower_count,
                "engagement": item.engagement_rate,
                "categories": json.dumps(item.content_categories),
                "location": item.location,
                "phone": item.phone_number,
                "has_wa": bool(item.phone_number),
            })
            imported += 1

            # Auto-send TikTok chat jika tidak punya nomor WA
            if auto_send_tiktok and not item.phone_number and tiktok_template_content:
                msg_content = tiktok_template_content.replace(
                    "{{nama_influencer}}", item.name
                )
                msg_id = str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO message_history
                        (id, affiliate_id, affiliate_name, direction, message_content,
                         from_number, to_number, status, sent_at)
                    VALUES
                        (:id, :affiliate_id, :affiliate_name, 'outbound', :content,
                         'TikTok Chat', :tiktok_id, 'sent', NOW())
                """), {
                    "id": msg_id,
                    "affiliate_id": new_id,
                    "affiliate_name": item.name,
                    "content": msg_content,
                    "tiktok_id": item.tiktok_username or item.name,
                })
                auto_sent += 1

        except Exception as e:
            errors.append(f"{item.name}: {str(e)[:100]}")

    await db.commit()

    return ImportResult(
        imported=imported,
        skipped=skipped,
        errors=errors,
        auto_sent_tiktok=auto_sent,
    )


@router.patch("/{affiliate_id}/whatsapp")
async def update_affiliate_whatsapp(
    affiliate_id: str,
    body: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Update nomor WhatsApp affiliator. Otomatis trigger kirim pesan WA undangan."""
    import uuid

    phone = body.get("phone_number", "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Nomor WhatsApp tidak boleh kosong")

    # Update nomor WA
    await db.execute(text("""
        UPDATE influencers
        SET phone_number = :phone, has_whatsapp = TRUE, updated_at = NOW()
        WHERE id = :id
    """), {"phone": phone, "id": affiliate_id})

    # Ambil data affiliator
    aff_result = await db.execute(text("""
        SELECT id, name, content_categories FROM influencers WHERE id = :id
    """), {"id": affiliate_id})
    aff = aff_result.mappings().first()
    if not aff:
        raise HTTPException(status_code=404, detail="Affiliator tidak ditemukan")

    auto_sent = False
    if body.get("auto_send_wa", True):
        # Ambil template undangan kampanye
        import json
        cats = aff["content_categories"] or []
        if isinstance(cats, str):
            try:
                cats = json.loads(cats)
            except Exception:
                cats = []

        # Cari template yang sesuai
        tmpl_result = await db.execute(text("""
            SELECT content, default_values FROM message_templates
            WHERE message_type = 'campaign_invitation' AND is_active = TRUE
            LIMIT 1
        """))
        tmpl_row = tmpl_result.mappings().first()

        if tmpl_row:
            msg_content = tmpl_row["content"].replace("{{nama_influencer}}", aff["name"])

            # Pilih WA number berdasarkan kategori
            from app.api.messages import _get_category_from_categories
            wa_cat = _get_category_from_categories(cats)
            wa_result = await db.execute(text("""
                SELECT id, phone_number, phone_number_id FROM whatsapp_numbers
                WHERE category = :cat AND is_active = TRUE LIMIT 1
            """), {"cat": wa_cat})
            wa_row = wa_result.mappings().first()
            if not wa_row:
                wa_result = await db.execute(text("""
                    SELECT id, phone_number, phone_number_id FROM whatsapp_numbers
                    WHERE category = 'Umum' AND is_active = TRUE LIMIT 1
                """))
                wa_row = wa_result.mappings().first()

            wa_number_id = str(wa_row["id"]) if wa_row else None
            from_number = wa_row["phone_number"] if wa_row else None
            phone_number_id = wa_row.get("phone_number_id") if wa_row else None

            msg_id = str(uuid.uuid4())

            # Kirim via Meta API jika tersedia
            if phone_number_id:
                try:
                    from app.integrations.whatsapp_api import WhatsAppMultiClient
                    wa_client = WhatsAppMultiClient()
                    result_wa = await wa_client.send_text_message(
                        phone_number_id=phone_number_id,
                        to_phone=phone,
                        message=msg_content,
                    )
                    if result_wa.message_id:
                        msg_id = result_wa.message_id
                except Exception:
                    pass

            await db.execute(text("""
                INSERT INTO message_history
                    (id, affiliate_id, affiliate_name, direction, message_content,
                     wa_number_id, from_number, to_number, status, sent_at)
                VALUES
                    (:id, :affiliate_id, :affiliate_name, 'outbound', :content,
                     :wa_number_id, :from_number, :to_number, 'sent', NOW())
            """), {
                "id": msg_id,
                "affiliate_id": affiliate_id,
                "affiliate_name": aff["name"],
                "content": msg_content,
                "wa_number_id": wa_number_id,
                "from_number": from_number,
                "to_number": phone,
            })
            auto_sent = True

    await db.commit()
    return {"status": "updated", "phone_number": phone, "auto_sent_wa": auto_sent}
