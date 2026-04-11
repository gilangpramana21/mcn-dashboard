"""Message History & WhatsApp Numbers API."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])


# ─── Models ───────────────────────────────────────────────────────────────────

class MessageItem(BaseModel):
    id: str
    affiliate_id: str
    affiliate_name: str
    direction: str  # outbound | inbound
    message_content: str
    from_number: Optional[str]
    to_number: Optional[str]
    status: str
    sent_at: str
    wa_category: Optional[str] = None


class ConversationSummary(BaseModel):
    affiliate_id: str
    affiliate_name: str
    last_message: str
    last_message_at: str
    message_count: int
    unread_count: int
    wa_category: Optional[str] = None
    has_whatsapp: bool


class WhatsAppNumber(BaseModel):
    id: str
    category: str
    phone_number: str
    display_name: Optional[str]
    is_active: bool


class SendMessageRequest(BaseModel):
    affiliate_id: str
    message_content: str
    template_id: Optional[str] = None


class BlastPreviewRequest(BaseModel):
    wa_category: Optional[str] = None  # None = semua kategori


class BlastSendRequest(BaseModel):
    wa_category: Optional[str] = None
    message_content: str
    template_id: Optional[str] = None


class BlastRecipient(BaseModel):
    affiliate_id: str
    affiliate_name: str
    phone_number: Optional[str]
    wa_category: str


class BlastResult(BaseModel):
    total: int
    sent: int
    failed: int
    skipped: int  # tidak punya nomor HP
    recipients: List[BlastRecipient]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_category_from_categories(categories: List[str]) -> str:
    """Map content categories to WA number category."""
    category_map = {
        # Beauty
        'Kecantikan': 'Kecantikan',
        'Perawatan Kulit': 'Kecantikan',
        'Perawatan Rambut': 'Kecantikan',
        'Parfum & Wewangian': 'Kecantikan',
        # Fashion
        'Fashion Wanita': 'Fashion',
        'Fashion Pria': 'Fashion',
        'Fashion Anak': 'Fashion',
        'Tas & Dompet': 'Fashion',
        'Sepatu': 'Fashion',
        'Aksesoris': 'Fashion',
        # Food
        'Makanan & Minuman': 'FnB',
        'Makanan Ringan': 'FnB',
        'Minuman': 'FnB',
        'Suplemen & Vitamin': 'FnB',
        # Electronics
        'Elektronik': 'Elektronik',
        'Handphone & Aksesoris': 'Elektronik',
        'Komputer & Laptop': 'Elektronik',
        'Kamera': 'Elektronik',
        # Sports
        'Olahraga & Outdoor': 'Olahraga',
        'Alat Fitness': 'Olahraga',
        # Home
        'Rumah & Dekorasi': 'Umum',
        'Peralatan Dapur': 'Umum',
        'Perlengkapan Tidur': 'Umum',
        # Others
        'Ibu & Bayi': 'Umum',
        'Mainan Anak': 'Umum',
        'Otomotif & Aksesoris': 'Umum',
        'Hewan Peliharaan': 'Umum',
        'Gaming': 'Umum',
        'Buku & Alat Tulis': 'Umum',
        # Legacy mapping
        'Kecantikan & Perawatan': 'Kecantikan',
        'Skincare': 'Kecantikan',
        'Kuliner & Resep': 'FnB',
        'Elektronik & Gadget': 'Elektronik',
        'Kesehatan & Suplemen': 'Olahraga',
    }
    for cat in categories:
        if cat in category_map:
            return category_map[cat]
    return 'Umum'


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/conversations", response_model=List[ConversationSummary])
async def get_conversations(
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[ConversationSummary]:
    """Daftar semua percakapan (gabungan inbound + outbound, satu per affiliate)."""
    import json

    search_filter = "WHERE LOWER(affiliate_name) LIKE :search" if search else ""
    params: Dict[str, Any] = {}
    if search:
        params["search"] = f"%{search.lower()}%"

    # Gabungkan incoming_messages (inbound) + message_history (outbound)
    result = await db.execute(text(f"""
        WITH all_messages AS (
            SELECT
                COALESCE(affiliate_id, affiliate_name) AS aff_key,
                affiliate_name,
                message_content,
                received_at AS msg_at,
                CASE WHEN is_read = FALSE THEN 1 ELSE 0 END AS is_unread
            FROM incoming_messages
            UNION ALL
            SELECT
                affiliate_id AS aff_key,
                affiliate_name,
                message_content,
                sent_at AS msg_at,
                0 AS is_unread
            FROM message_history
        )
        SELECT
            aff_key AS affiliate_id,
            affiliate_name,
            COUNT(*) AS message_count,
            MAX(msg_at) AS last_message_at,
            (SELECT message_content FROM all_messages am2
             WHERE am2.aff_key = am.aff_key
             ORDER BY am2.msg_at DESC LIMIT 1) AS last_message,
            SUM(is_unread) AS unread_count
        FROM all_messages am
        {search_filter}
        GROUP BY aff_key, affiliate_name
        ORDER BY MAX(msg_at) DESC
    """), params)

    rows = result.mappings().all()
    items = []
    for row in rows:
        # Coba ambil content_categories dari influencers berdasarkan affiliate_id
        cats: List[str] = []
        try:
            aff_result = await db.execute(text(
                "SELECT content_categories FROM influencers WHERE id = :id OR name = :name LIMIT 1"
            ), {"id": str(row["affiliate_id"]), "name": row["affiliate_name"]})
            aff_row = aff_result.mappings().first()
            if aff_row and aff_row["content_categories"]:
                raw = aff_row["content_categories"]
                if isinstance(raw, str):
                    try:
                        cats = json.loads(raw)
                    except Exception:
                        cats = []
                elif isinstance(raw, list):
                    cats = raw
        except Exception:
            pass
        wa_cat = _get_category_from_categories(cats)
        items.append(ConversationSummary(
            affiliate_id=str(row["affiliate_id"]),
            affiliate_name=row["affiliate_name"] or "",
            last_message=row["last_message"] or "",
            last_message_at=row["last_message_at"].isoformat() if row["last_message_at"] else "",
            message_count=int(row["message_count"] or 0),
            unread_count=int(row["unread_count"] or 0),
            wa_category=wa_cat,
            has_whatsapp=False,
        ))
    return items


@router.get("/history/{affiliate_id}", response_model=List[MessageItem])
async def get_message_history(
    affiliate_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[MessageItem]:
    """History pesan dengan affiliate tertentu (inbound + outbound)."""
    offset = (page - 1) * page_size
    result = await db.execute(text("""
        SELECT * FROM (
            SELECT
                id::text AS id,
                COALESCE(affiliate_id, affiliate_name) AS affiliate_id,
                affiliate_name,
                'inbound' AS direction,
                message_content,
                from_number,
                NULL::varchar AS to_number,
                CASE WHEN is_read THEN 'read' ELSE 'delivered' END AS status,
                received_at AS sent_at,
                channel AS wa_category
            FROM incoming_messages
            WHERE affiliate_name = :affiliate_id OR affiliate_id = :affiliate_id
            UNION ALL
            SELECT
                id::text AS id,
                affiliate_id,
                affiliate_name,
                direction,
                message_content,
                from_number,
                to_number,
                status,
                sent_at,
                NULL::varchar AS wa_category
            FROM message_history
            WHERE affiliate_id = :affiliate_id OR affiliate_name = :affiliate_id
        ) combined
        ORDER BY sent_at ASC
        LIMIT :limit OFFSET :offset
    """), {"affiliate_id": affiliate_id, "limit": page_size, "offset": offset})
    rows = result.mappings().all()
    return [
        MessageItem(
            id=str(row["id"]),
            affiliate_id=str(row["affiliate_id"]),
            affiliate_name=row["affiliate_name"] or "",
            direction=row["direction"],
            message_content=row["message_content"],
            from_number=row["from_number"],
            to_number=row["to_number"],
            status=row["status"],
            sent_at=row["sent_at"].isoformat() if row["sent_at"] else "",
            wa_category=row["wa_category"],
        )
        for row in rows
    ]


@router.post("/send")
async def send_message(
    body: SendMessageRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Kirim pesan ke affiliate — otomatis pilih nomor WA berdasarkan kategori."""
    import json
    import uuid

    # Ambil data affiliate
    aff_result = await db.execute(text("""
        SELECT id, name, phone_number, content_categories FROM influencers
        WHERE id = :id
    """), {"id": body.affiliate_id})
    aff = aff_result.mappings().first()
    if not aff:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Affiliate tidak ditemukan")

    # Tentukan kategori WA
    cats = aff["content_categories"] or []
    if isinstance(cats, str):
        try:
            cats = json.loads(cats)
        except Exception:
            cats = []
    wa_category = _get_category_from_categories(cats)

    # Ambil nomor WA yang sesuai kategori
    wa_result = await db.execute(text("""
        SELECT id, phone_number, display_name, phone_number_id FROM whatsapp_numbers
        WHERE category = :cat AND is_active = TRUE
        LIMIT 1
    """), {"cat": wa_category})
    wa_row = wa_result.mappings().first()

    # Fallback ke Umum jika kategori tidak ada
    if not wa_row:
        wa_result = await db.execute(text("""
            SELECT id, phone_number, display_name, phone_number_id FROM whatsapp_numbers
            WHERE category = 'Umum' AND is_active = TRUE LIMIT 1
        """))
        wa_row = wa_result.mappings().first()

    wa_number_id = str(wa_row["id"]) if wa_row else None
    from_number = wa_row["phone_number"] if wa_row else None
    phone_number_id = wa_row.get("phone_number_id") if wa_row else None
    to_number = aff["phone_number"]

    # Simpan ke history
    msg_id = str(uuid.uuid4())

    # Kirim via Meta Cloud API jika phone_number_id tersedia
    if phone_number_id and to_number:
        try:
            from app.integrations.whatsapp_api import WhatsAppMultiClient
            wa_client = WhatsAppMultiClient()
            result = await wa_client.send_text_message(
                phone_number_id=phone_number_id,
                to_phone=to_number,
                message=body.message_content,
            )
            if result.message_id:
                msg_id = result.message_id
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning("Gagal kirim WA: %s", e)
    await db.execute(text("""
        INSERT INTO message_history
            (id, affiliate_id, affiliate_name, direction, message_content,
             wa_number_id, from_number, to_number, status, template_id)
        VALUES
            (:id, :affiliate_id, :affiliate_name, 'outbound', :content,
             :wa_number_id, :from_number, :to_number, 'sent', :template_id)
    """), {
        "id": msg_id,
        "affiliate_id": body.affiliate_id,
        "affiliate_name": aff["name"],
        "content": body.message_content,
        "wa_number_id": wa_number_id,
        "from_number": from_number,
        "to_number": to_number,
        "template_id": body.template_id,
    })
    await db.commit()

    return {
        "id": msg_id,
        "status": "sent",
        "from_number": from_number,
        "to_number": to_number,
        "wa_category": wa_category,
    }


@router.get("/wa-numbers", response_model=List[WhatsAppNumber])
async def get_wa_numbers(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[WhatsAppNumber]:
    """Daftar semua nomor WhatsApp per kategori."""
    result = await db.execute(text("""
        SELECT id, category, phone_number, display_name, is_active
        FROM whatsapp_numbers ORDER BY category
    """))
    rows = result.mappings().all()
    return [
        WhatsAppNumber(
            id=str(row["id"]),
            category=row["category"],
            phone_number=row["phone_number"],
            display_name=row["display_name"],
            is_active=bool(row["is_active"]),
        )
        for row in rows
    ]


@router.put("/wa-numbers/{number_id}")
async def update_wa_number(
    number_id: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update nomor WhatsApp untuk kategori tertentu."""
    await db.execute(text("""
        UPDATE whatsapp_numbers
        SET phone_number = :phone, display_name = :name, updated_at = NOW()
        WHERE id = :id
    """), {
        "phone": body.get("phone_number"),
        "name": body.get("display_name"),
        "id": number_id,
    })
    await db.commit()
    return {"status": "updated"}


@router.post("/blast/preview", response_model=List[BlastRecipient])
async def blast_preview(
    body: BlastPreviewRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> List[BlastRecipient]:
    """Preview daftar penerima blast sebelum kirim."""
    import json

    # Ambil semua affiliate yang punya nomor HP
    result = await db.execute(text("""
        SELECT id, name, phone_number, content_categories
        FROM influencers
        WHERE phone_number IS NOT NULL AND phone_number != ''
        ORDER BY name
    """))
    rows = result.mappings().all()

    recipients = []
    for row in rows:
        cats = row["content_categories"] or []
        if isinstance(cats, str):
            try:
                cats = json.loads(cats)
            except Exception:
                cats = []
        wa_cat = _get_category_from_categories(cats)

        # Filter by kategori jika ditentukan
        if body.wa_category and wa_cat != body.wa_category:
            continue

        recipients.append(BlastRecipient(
            affiliate_id=str(row["id"]),
            affiliate_name=row["name"],
            phone_number=row["phone_number"],
            wa_category=wa_cat,
        ))

    return recipients


@router.post("/blast/send", response_model=BlastResult)
async def blast_send(
    body: BlastSendRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> BlastResult:
    """Kirim pesan massal ke semua affiliate berdasarkan kategori WA."""
    import json
    import uuid

    # Ambil semua affiliate yang punya nomor HP
    result = await db.execute(text("""
        SELECT id, name, phone_number, content_categories
        FROM influencers
        WHERE phone_number IS NOT NULL AND phone_number != ''
        ORDER BY name
    """))
    rows = result.mappings().all()

    # Ambil semua WA numbers sekaligus
    wa_result = await db.execute(text("""
        SELECT category, id, phone_number, phone_number_id
        FROM whatsapp_numbers WHERE is_active = TRUE
    """))
    wa_map: Dict[str, Any] = {}
    for wa in wa_result.mappings().all():
        wa_map[wa["category"]] = dict(wa)

    sent = 0
    failed = 0
    skipped = 0
    recipients: List[BlastRecipient] = []

    for row in rows:
        cats = row["content_categories"] or []
        if isinstance(cats, str):
            try:
                cats = json.loads(cats)
            except Exception:
                cats = []
        wa_cat = _get_category_from_categories(cats)

        # Filter by kategori jika ditentukan
        if body.wa_category and wa_cat != body.wa_category:
            continue

        to_number = row["phone_number"]
        if not to_number:
            skipped += 1
            continue

        recipients.append(BlastRecipient(
            affiliate_id=str(row["id"]),
            affiliate_name=row["name"],
            phone_number=to_number,
            wa_category=wa_cat,
        ))

        # Pilih WA number yang sesuai kategori
        wa_row = wa_map.get(wa_cat) or wa_map.get("Umum")
        wa_number_id = str(wa_row["id"]) if wa_row else None
        from_number = wa_row["phone_number"] if wa_row else None
        phone_number_id = wa_row.get("phone_number_id") if wa_row else None

        msg_id = str(uuid.uuid4())
        msg_status = "sent"

        # Kirim via Meta Cloud API jika phone_number_id tersedia
        if phone_number_id and to_number:
            try:
                from app.integrations.whatsapp_api import WhatsAppMultiClient
                wa_client = WhatsAppMultiClient()
                result_wa = await wa_client.send_text_message(
                    phone_number_id=phone_number_id,
                    to_phone=to_number,
                    message=body.message_content,
                )
                if result_wa.message_id:
                    msg_id = result_wa.message_id
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Blast gagal ke %s: %s", to_number, e)
                msg_status = "failed"
                failed += 1

        if msg_status == "sent":
            sent += 1

        # Simpan ke history
        try:
            await db.execute(text("""
                INSERT INTO message_history
                    (id, affiliate_id, affiliate_name, direction, message_content,
                     wa_number_id, from_number, to_number, status, template_id)
                VALUES
                    (:id, :affiliate_id, :affiliate_name, 'outbound', :content,
                     :wa_number_id, :from_number, :to_number, :status, :template_id)
            """), {
                "id": msg_id,
                "affiliate_id": str(row["id"]),
                "affiliate_name": row["name"],
                "content": body.message_content,
                "wa_number_id": wa_number_id,
                "from_number": from_number,
                "to_number": to_number,
                "status": msg_status,
                "template_id": body.template_id,
            })
        except Exception:
            pass

    await db.commit()

    return BlastResult(
        total=len(recipients),
        sent=sent,
        failed=failed,
        skipped=skipped,
        recipients=recipients,
    )
