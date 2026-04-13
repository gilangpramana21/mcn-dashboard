"""TikTok Shop API — OAuth, agent run, token management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/tiktok-shop", tags=["tiktok-shop"])

# Alias router untuk backward compatibility dengan redirect URI /tiktok/callback
router_alias = APIRouter(prefix="/tiktok", tags=["tiktok-shop"])


# ─── Models ───────────────────────────────────────────────────────────────────

class OAuthCallbackRequest(BaseModel):
    auth_code: str
    shop_id: Optional[str] = None


class AgentRunRequest(BaseModel):
    keyword: str = ""
    min_followers: int = 1000
    max_followers: int = 0
    categories: List[str] = []
    max_creators: int = 50
    auto_send_message: bool = True
    wa_request_message: str = ""
    product_ids: List[str] = []
    commission_rate: float = 15.0


class TokenInfo(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    shop_id: Optional[str] = None
    shop_name: Optional[str] = None
    shop_cipher: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_active_token(db: AsyncSession) -> Optional[str]:
    """Ambil access_token aktif dari database."""
    result = await db.execute(text("""
        SELECT access_token FROM tiktok_shop_tokens
        WHERE expires_at > NOW()
        ORDER BY created_at DESC LIMIT 1
    """))
    row = result.mappings().first()
    return row["access_token"] if row else None


async def _get_active_token_with_cipher(db: AsyncSession) -> tuple[Optional[str], Optional[str]]:
    """Ambil access_token dan shop_cipher aktif dari database."""
    result = await db.execute(text("""
        SELECT access_token, shop_cipher FROM tiktok_shop_tokens
        WHERE expires_at > NOW()
        ORDER BY created_at DESC LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return None, None
    return row["access_token"], row.get("shop_cipher")


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/callback")
@router_alias.get("/callback")
async def oauth_callback_get(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Handle redirect dari TikTok OAuth — tukar code dengan token."""
    from app.integrations.tiktok_shop_api import TikTokShopOAuth
    import uuid

    oauth = TikTokShopOAuth()
    try:
        token_data = await oauth.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal tukar token: {str(e)}")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = int(token_data.get("access_token_expire_in", 3600))

    await db.execute(text("""
        INSERT INTO tiktok_shop_tokens (access_token, refresh_token, expires_at, shop_id)
        VALUES (:access_token, :refresh_token,
                NOW() + (:expires * INTERVAL '1 second'), :shop_id)
    """), {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires_in,
        "shop_id": token_data.get("seller_id"),
    })
    await db.commit()

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/agent?oauth=success")
@router.get("/auth-url")
async def get_auth_url(
    redirect_uri: str = Query(..., description="URL callback setelah seller authorize"),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Generate URL untuk seller authorize app TikTok Shop."""
    from app.integrations.tiktok_shop_api import TikTokShopOAuth
    oauth = TikTokShopOAuth()
    url = oauth.get_auth_url(redirect_uri=redirect_uri)
    return {"auth_url": url}


@router.post("/oauth/callback")
async def oauth_callback(
    body: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """Tukar auth_code dengan access_token dan simpan ke database. Tidak butuh auth."""
    from app.integrations.tiktok_shop_api import TikTokShopOAuth
    import uuid

    oauth = TikTokShopOAuth()
    try:
        token_data = await oauth.exchange_code(body.auth_code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = int(token_data.get("access_token_expire_in", 3600))

    # Simpan token ke DB
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS tiktok_shop_tokens (
            id TEXT PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT,
            expires_at TIMESTAMPTZ,
            shop_id TEXT,
            shop_name TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    await db.execute(text("""
        INSERT INTO tiktok_shop_tokens (id, access_token, refresh_token, expires_at, shop_id)
        VALUES (:id, :access_token, :refresh_token,
                NOW() + (:expires * INTERVAL '1 second'), :shop_id)
    """), {
        "id": str(uuid.uuid4()),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires": expires_in,
        "shop_id": body.shop_id,
    })
    await db.commit()

    return {
        "status": "authorized",
        "expires_in": expires_in,
        "message": "Token berhasil disimpan. Sekarang bisa jalankan agent.",
    }


@router.post("/token/manual")
async def save_token_manual(
    body: TokenInfo,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Simpan access_token secara manual (untuk testing atau token dari Seller Center)."""
    import uuid

    await db.execute(text("""
        INSERT INTO tiktok_shop_tokens (id, access_token, refresh_token, expires_at, shop_id, shop_name, shop_cipher)
        VALUES (:id, :access_token, :refresh_token,
                NOW() + (:expires * INTERVAL '1 second'), :shop_id, :shop_name, :shop_cipher)
    """), {
        "id": str(uuid.uuid4()),
        "access_token": body.access_token,
        "refresh_token": body.refresh_token,
        "expires": body.expires_in,
        "shop_id": body.shop_id,
        "shop_name": body.shop_name,
        "shop_cipher": body.shop_cipher,
    })
    await db.commit()

    return {"status": "saved", "message": "Token tersimpan. Agent siap dijalankan."}


@router.get("/token/status")
async def token_status(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Cek status token TikTok Shop."""
    result = await db.execute(text("""
        SELECT access_token, expires_at, shop_id, shop_name, shop_cipher, created_at
        FROM tiktok_shop_tokens
        ORDER BY created_at DESC LIMIT 1
    """))
    row = result.mappings().first()

    if not row:
        return {"status": "no_token", "message": "Belum ada token. Lakukan OAuth terlebih dahulu."}

    from datetime import datetime, timezone
    expires_at = row["expires_at"]
    is_valid = expires_at and expires_at > datetime.now(timezone.utc)

    return {
        "status": "valid" if is_valid else "expired",
        "expires_at": expires_at.isoformat() if expires_at else None,
        "shop_id": row["shop_id"],
        "shop_name": row["shop_name"],
        "has_cipher": bool(row.get("shop_cipher")),
        "has_token": True,
    }


@router.post("/token/fetch-cipher")
async def fetch_shop_cipher(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Auto-fetch shop_cipher dari TikTok API menggunakan access_token yang ada.
    shop_cipher diperlukan untuk semua API call versi 202309+.
    """
    from app.integrations.tiktok_shop_api import TikTokShopClient

    access_token = await _get_active_token(db)
    if not access_token:
        raise HTTPException(status_code=401, detail="Tidak ada token aktif.")

    client = TikTokShopClient(access_token=access_token)
    try:
        shop_data = await client.get_authorized_shop()
        shops = shop_data.get("shops", shop_data.get("list", []))
        if not shops:
            return {"status": "no_shops", "message": "Tidak ada shop yang ditemukan."}

        # Ambil cipher dari shop pertama
        shop = shops[0]
        cipher = shop.get("cipher", "")
        shop_id = shop.get("id", "")
        shop_name = shop.get("name", "")

        if cipher:
            await db.execute(text("""
                UPDATE tiktok_shop_tokens
                SET shop_cipher = :cipher, shop_id = :shop_id, shop_name = :shop_name
                WHERE expires_at > NOW()
            """), {"cipher": cipher, "shop_id": shop_id, "shop_name": shop_name})
            await db.commit()

        return {
            "status": "ok",
            "shop_id": shop_id,
            "shop_name": shop_name,
            "cipher_saved": bool(cipher),
            "shops": shops,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal ambil shop cipher: {str(e)}")


@router.post("/agent/run")
async def run_agent(
    body: AgentRunRequest,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Jalankan TikTok Shop Agent:
    1. Cari creator berdasarkan filter
    2. Simpan ke database
    3. Kirim pesan TikTok chat minta nomor WA
    """
    from app.agents.tiktok_shop_agent import TikTokShopAgent, AgentRunConfig

    # Ambil token aktif
    access_token, shop_cipher = await _get_active_token_with_cipher(db)
    if not access_token:
        raise HTTPException(
            status_code=401,
            detail="Tidak ada token TikTok Shop yang aktif. Lakukan OAuth atau input token manual dulu.",
        )

    config = AgentRunConfig(
        keyword=body.keyword,
        min_followers=body.min_followers,
        max_followers=body.max_followers,
        categories=body.categories,
        max_creators=body.max_creators,
        auto_send_message=body.auto_send_message,
        wa_request_message=body.wa_request_message or "",
        product_ids=body.product_ids,
        commission_rate=body.commission_rate,
    )

    agent = TikTokShopAgent(access_token=access_token, shop_cipher=shop_cipher or "", db=db)
    result = await agent.run(config)

    return {
        "found": result.found,
        "new_saved": result.new_saved,
        "already_exists": result.already_exists,
        "messages_sent": result.messages_sent,
        "errors": result.errors[:10],  # max 10 error ditampilkan
        "creators": result.creators[:20],  # preview 20 creator pertama
    }


@router.get("/agent/history")
async def agent_history(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Riwayat pesan yang dikirim agent via TikTok Chat."""
    result = await db.execute(text("""
        SELECT mh.affiliate_name, mh.to_number AS tiktok_id,
               mh.message_content, mh.status, mh.sent_at,
               i.follower_count, i.has_whatsapp
        FROM message_history mh
        LEFT JOIN influencers i ON i.id = mh.affiliate_id
        WHERE mh.from_number = 'TikTok Chat'
        ORDER BY mh.sent_at DESC
        LIMIT :limit
    """), {"limit": limit})

    rows = result.mappings().all()
    return {
        "total": len(rows),
        "messages": [
            {
                "name": row["affiliate_name"],
                "tiktok_id": row["tiktok_id"],
                "message": row["message_content"][:100] + "..." if len(row["message_content"]) > 100 else row["message_content"],
                "status": row["status"],
                "sent_at": row["sent_at"].isoformat() if row["sent_at"] else "",
                "has_whatsapp": bool(row["has_whatsapp"]),
                "followers": row["follower_count"],
            }
            for row in rows
        ],
    }


@router.get("/data/fetch")
async def fetch_basic_data(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Ambil data dasar dari TikTok Shop yang tersedia:
    - List kolaborasi yang sudah ada
    - List produk toko
    Tanpa search creator (tidak tersedia di Custom App).
    """
    from app.integrations.tiktok_shop_api import TikTokShopClient

    access_token, shop_cipher = await _get_active_token_with_cipher(db)
    if not access_token:
        raise HTTPException(status_code=401, detail="Tidak ada token aktif. Lakukan OAuth dulu.")

    client = TikTokShopClient(access_token=access_token, shop_cipher=shop_cipher or "")
    results: Dict[str, Any] = {
        "collaborations": {"data": [], "error": None},
        "products": {"data": [], "error": None},
        "creators": {"data": [], "error": None},
    }

    # 1. List kolaborasi
    try:
        collab_data = await client.list_collaborations(page_size=20)
        results["collaborations"]["data"] = collab_data.get("collaborations", collab_data.get("list", []))
    except Exception as e:
        results["collaborations"]["error"] = str(e)

    # 2. List produk
    try:
        product_data = await client.get_shop_products(page_size=20)
        results["products"]["data"] = product_data.get("products", product_data.get("list", []))
    except Exception as e:
        results["products"]["error"] = str(e)

    # 3. List kreator yang pernah kolaborasi
    try:
        creator_data = await client.get_collaboration_creators(page_size=20)
        results["creators"]["data"] = creator_data.get("creators", creator_data.get("list", []))
    except Exception as e:
        results["creators"]["error"] = str(e)

    return results
