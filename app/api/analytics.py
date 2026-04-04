"""Analytics API — Creator Intelligence, Content, Product, Revenue Insights."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.services.rbac import get_current_user

router = APIRouter(prefix="/analytics", tags=["analytics"])

# ─── Response Models ──────────────────────────────────────────────────────────

class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int

class OverviewData(BaseModel):
    total_gmv: float
    total_views: int
    total_creators: int
    global_conversion_rate: float
    total_buyers: int
    top_creator_name: Optional[str]
    top_creator_revenue: float
    top_product_name: Optional[str]
    top_product_gmv: float

class OverviewResponse(BaseModel):
    data: OverviewData
    meta: Dict[str, Any]

class CreatorIntelligenceItem(BaseModel):
    id: str
    name: str
    follower_count: int
    engagement_rate: float
    avg_views: int
    estimated_revenue: float
    creator_score: float
    creator_role: str
    creator_type: str
    has_whatsapp: bool
    location: str
    content_categories: List[str]
    video_count: int
    total_gmv: float
    total_views: int

class CreatorsResponse(BaseModel):
    data: List[CreatorIntelligenceItem]
    meta: PaginationMeta

class ContentItem(BaseModel):
    id: str
    tiktok_video_id: str
    creator_name: str
    creator_id: str
    product_name: Optional[str]
    views: int
    likes: int
    comments: int
    shares: int
    engagement_rate: float
    velocity: float
    gmv_generated: float
    buyers: int
    conversion_rate: float
    posted_at: str

class ContentResponse(BaseModel):
    data: List[ContentItem]
    meta: PaginationMeta

class ProductItem(BaseModel):
    id: str
    name: str
    price: float
    category: Optional[str]
    total_gmv: float
    total_buyers: int
    total_creators: int
    conversion_rate: float
    revenue: float
    shop_name: Optional[str]

class ProductsResponse(BaseModel):
    data: List[ProductItem]
    meta: PaginationMeta

class RevenueInsightItem(BaseModel):
    creator_id: str
    creator_name: str
    product_id: Optional[str]
    product_name: Optional[str]
    revenue: float
    gmv: float
    buyers: int
    conversion_rate: float
    video_count: int

class RevenueResponse(BaseModel):
    data: List[RevenueInsightItem]
    meta: PaginationMeta

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _parse_categories(raw: Any) -> List[str]:
    import json
    if raw is None: return []
    if isinstance(raw, list): return raw
    if isinstance(raw, str):
        try: return json.loads(raw)
        except: return [raw] if raw else []
    return []

# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> OverviewResponse:
    """KPI global platform."""
    from app.services.cache_service import get_cached_analytics, set_cached_analytics
    
    # Check cache first
    cache_params = {}
    cached_data = await get_cached_analytics("overview", cache_params)
    if cached_data:
        return OverviewResponse(**cached_data)
    
    # Total GMV, views, buyers dari content_videos
    kpi = await db.execute(text("""
        SELECT
            COALESCE(SUM(gmv_generated), 0) AS total_gmv,
            COALESCE(SUM(views), 0) AS total_views,
            COALESCE(SUM(buyers), 0) AS total_buyers
        FROM content_videos
    """))
    kpi_row = kpi.mappings().first()
    total_gmv = float(kpi_row["total_gmv"] or 0)
    total_views = int(kpi_row["total_views"] or 0)
    total_buyers = int(kpi_row["total_buyers"] or 0)
    global_cr = (total_buyers / total_views * 100) if total_views > 0 else 0.0

    # Total creators
    creators_count = await db.execute(text("SELECT COUNT(*) FROM influencers WHERE status = 'ACTIVE'"))
    total_creators = int(creators_count.scalar() or 0)

    # Top creator by revenue
    top_creator = await db.execute(text("""
        SELECT i.name, COALESCE(SUM(cv.gmv_generated), 0) AS revenue
        FROM influencers i
        LEFT JOIN content_videos cv ON cv.creator_id = i.id
        GROUP BY i.id, i.name
        ORDER BY revenue DESC LIMIT 1
    """))
    tc_row = top_creator.mappings().first()

    # Top product by GMV
    top_product = await db.execute(text("""
        SELECT p.name, COALESCE(SUM(cv.gmv_generated), 0) AS gmv
        FROM products p
        LEFT JOIN content_videos cv ON cv.product_id = p.id
        GROUP BY p.id, p.name
        ORDER BY gmv DESC LIMIT 1
    """))
    tp_row = top_product.mappings().first()

    overview_data = OverviewData(
        total_gmv=total_gmv,
        total_views=total_views,
        total_creators=total_creators,
        global_conversion_rate=round(global_cr, 2),
        total_buyers=total_buyers,
        top_creator_name=tc_row["name"] if tc_row else None,
        top_creator_revenue=float(tc_row["revenue"]) if tc_row else 0.0,
        top_product_name=tp_row["name"] if tp_row else None,
        top_product_gmv=float(tp_row["gmv"]) if tp_row else 0.0,
    )
    
    response_data = OverviewResponse(
        data=overview_data,
        meta={}
    )
    
    # Cache the response with 5-minute TTL
    await set_cached_analytics("overview", cache_params, response_data.model_dump(), ttl=300)
    
    return response_data


@router.get("/creators", response_model=CreatorsResponse)
async def get_creator_intelligence(
    sort_by: str = Query("score", description="score|revenue|followers|engagement|views"),
    role: Optional[str] = Query(None, description="influencer|affiliator|hybrid"),
    creator_type: Optional[str] = Query(None, description="influencer|affiliator|hybrid"),
    min_followers: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> CreatorsResponse:
    """Creator Intelligence with score, role, and revenue."""
    from app.services.cache_service import get_cached_analytics, set_cached_analytics
    from app.services.creator_score_service import calculate_creator_score, classify_creator_role
    
    # Check cache first
    cache_params = {
        "sort_by": sort_by,
        "role": role,
        "creator_type": creator_type,
        "min_followers": min_followers,
        "page": page,
        "page_size": page_size,
    }
    cached_data = await get_cached_analytics("creators", cache_params)
    if cached_data:
        return CreatorsResponse(**cached_data)
    
    conditions = ["i.status = 'ACTIVE'"]
    params: Dict[str, Any] = {}

    if role:
        conditions.append("i.creator_role = :role")
        params["role"] = role
    if creator_type:
        conditions.append("i.creator_type = :creator_type")
        params["creator_type"] = creator_type
    if min_followers:
        conditions.append("i.follower_count >= :min_followers")
        params["min_followers"] = min_followers

    where = f"WHERE {' AND '.join(conditions)}"

    # Get total count for pagination
    count_result = await db.execute(text(f"""
        SELECT COUNT(DISTINCT i.id)
        FROM influencers i
        {where}
    """), params)
    total_items = int(count_result.scalar() or 0)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    order_map = {
        "score": "creator_score DESC",
        "revenue": "total_gmv DESC",
        "followers": "i.follower_count DESC",
        "engagement": "i.engagement_rate DESC",
        "views": "total_views DESC",
    }
    order = order_map.get(sort_by, "creator_score DESC")

    # First, get all creators with their aggregated data
    result = await db.execute(text(f"""
        SELECT
            i.id, i.name, i.follower_count, i.engagement_rate,
            i.avg_views, i.estimated_revenue, i.creator_score,
            i.creator_role, i.creator_type, i.has_whatsapp, i.location,
            i.content_categories,
            COUNT(cv.id) AS video_count,
            COALESCE(SUM(cv.gmv_generated), 0) AS total_gmv,
            COALESCE(SUM(cv.views), 0) AS total_views
        FROM influencers i
        LEFT JOIN content_videos cv ON cv.creator_id = i.id
        {where}
        GROUP BY i.id, i.name, i.follower_count, i.engagement_rate,
                 i.avg_views, i.estimated_revenue, i.creator_score,
                 i.creator_role, i.creator_type, i.has_whatsapp, i.location, i.content_categories
    """), params)

    rows = result.mappings().all()
    
    # Calculate max values for normalization
    max_gmv = max((float(row["total_gmv"] or 0) for row in rows), default=1.0)
    max_engagement = max((float(row["engagement_rate"] or 0) for row in rows), default=1.0)
    max_video_count = max((int(row["video_count"] or 0) for row in rows), default=1)
    
    # Ambil semua GMV per video sekaligus (satu query, bukan N query)
    creator_ids = [str(row["id"]) for row in rows]
    creator_gmv_lists: Dict[str, list] = {cid: [] for cid in creator_ids}
    
    if creator_ids:
        placeholders = ", ".join(f":cid_{i}" for i in range(len(creator_ids)))
        gmv_params = {f"cid_{i}": cid for i, cid in enumerate(creator_ids)}
        gmv_all = await db.execute(text(f"""
            SELECT creator_id, gmv_generated
            FROM content_videos
            WHERE creator_id IN ({placeholders})
        """), gmv_params)
        for gmv_row in gmv_all.fetchall():
            cid = str(gmv_row[0])
            if cid in creator_gmv_lists:
                creator_gmv_lists[cid].append(float(gmv_row[1] or 0))
    
    # Calculate max consistency
    all_consistencies = []
    for cid, gmv_list in creator_gmv_lists.items():
        if gmv_list:
            from app.services.creator_score_service import calculate_consistency
            consistency = calculate_consistency(gmv_list)
            all_consistencies.append(consistency)
    max_consistency = max(all_consistencies, default=1.0)
    
    # Now calculate scores and build response items
    items = []
    for row in rows:
        creator_id = str(row["id"])
        total_gmv = float(row["total_gmv"] or 0)
        total_views = int(row["total_views"] or 0)
        video_count = int(row["video_count"] or 0)
        avg_engagement_rate = float(row["engagement_rate"] or 0)
        
        # Get GMV per video list for this creator
        gmv_per_video_list = creator_gmv_lists.get(creator_id, [])
        
        # Recalculate creator score using creator_score_service
        score = calculate_creator_score(
            total_gmv=total_gmv,
            avg_engagement_rate=avg_engagement_rate,
            video_count=video_count,
            gmv_per_video_list=gmv_per_video_list,
            max_gmv=max_gmv,
            max_engagement=max_engagement,
            max_video_count=max_video_count,
            max_consistency=max_consistency,
        )
        
        # Auto-classify creator_role based on score
        role_val = classify_creator_role(score)

        items.append(CreatorIntelligenceItem(
            id=creator_id,
            name=row["name"],
            follower_count=int(row["follower_count"] or 0),
            engagement_rate=avg_engagement_rate,
            avg_views=int(row["avg_views"] or 0),
            estimated_revenue=total_gmv,
            creator_score=score,
            creator_role=role_val,
            creator_type=row["creator_type"] or "influencer",
            has_whatsapp=bool(row["has_whatsapp"]),
            location=row["location"] or "",
            content_categories=_parse_categories(row["content_categories"]),
            video_count=video_count,
            total_gmv=total_gmv,
            total_views=total_views,
        ))
    
    # Apply sorting after score calculation
    sort_key_map = {
        "score": lambda x: x.creator_score,
        "revenue": lambda x: x.total_gmv,
        "followers": lambda x: x.follower_count,
        "engagement": lambda x: x.engagement_rate,
        "views": lambda x: x.total_views,
    }
    sort_key = sort_key_map.get(sort_by, lambda x: x.creator_score)
    items.sort(key=sort_key, reverse=True)
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]
    
    response_data = CreatorsResponse(
        data=paginated_items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
    
    # Cache the response with 5-minute TTL
    await set_cached_analytics("creators", cache_params, response_data.model_dump(), ttl=300)
    
    return response_data


@router.get("/content", response_model=ContentResponse)
async def get_content_analytics(
    sort_by: str = Query("views", description="views|gmv|engagement|velocity"),
    creator_id: Optional[str] = Query(None),
    product_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> ContentResponse:
    """Content Analytics per video."""
    from app.services.cache_service import get_cached_analytics, set_cached_analytics
    
    # Check cache first
    cache_params = {
        "sort_by": sort_by,
        "creator_id": creator_id,
        "product_id": product_id,
        "page": page,
        "page_size": page_size,
    }
    cached_data = await get_cached_analytics("content", cache_params)
    if cached_data:
        return ContentResponse(**cached_data)
    
    conditions = []
    params: Dict[str, Any] = {}

    if creator_id:
        conditions.append("cv.creator_id = :creator_id")
        params["creator_id"] = creator_id
    if product_id:
        conditions.append("cv.product_id = :product_id")
        params["product_id"] = product_id

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # Get total count for pagination
    count_result = await db.execute(text(f"""
        SELECT COUNT(*)
        FROM content_videos cv
        {where}
    """), params)
    total_items = int(count_result.scalar() or 0)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    order_map = {
        "views": "cv.views DESC",
        "gmv": "cv.gmv_generated DESC",
        "engagement": "engagement_rate DESC",
        "velocity": "velocity DESC",
    }
    order = order_map.get(sort_by, "cv.views DESC")

    # Calculate offset for pagination
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(text(f"""
        SELECT
            cv.id, cv.tiktok_video_id, cv.creator_id,
            i.name AS creator_name,
            p.name AS product_name,
            cv.views, cv.likes, cv.comments, cv.shares,
            cv.gmv_generated, cv.buyers, cv.posted_at,
            CASE WHEN cv.views > 0
                THEN (cv.likes + cv.comments + cv.shares)::float / cv.views * 100
                ELSE 0 END AS engagement_rate,
            CASE WHEN EXTRACT(EPOCH FROM (NOW() - cv.posted_at)) / 3600 > 0
                THEN cv.views::float / (EXTRACT(EPOCH FROM (NOW() - cv.posted_at)) / 3600)
                ELSE 0 END AS velocity,
            CASE WHEN cv.views > 0
                THEN cv.buyers::float / cv.views * 100
                ELSE 0 END AS conversion_rate
        FROM content_videos cv
        JOIN influencers i ON i.id = cv.creator_id
        LEFT JOIN products p ON p.id = cv.product_id
        {where}
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """), params)

    rows = result.mappings().all()
    items = [
        ContentItem(
            id=str(row["id"]),
            tiktok_video_id=row["tiktok_video_id"],
            creator_name=row["creator_name"],
            creator_id=str(row["creator_id"]),
            product_name=row["product_name"],
            views=int(row["views"] or 0),
            likes=int(row["likes"] or 0),
            comments=int(row["comments"] or 0),
            shares=int(row["shares"] or 0),
            engagement_rate=round(float(row["engagement_rate"] or 0), 2),
            velocity=round(float(row["velocity"] or 0), 1),
            gmv_generated=float(row["gmv_generated"] or 0),
            buyers=int(row["buyers"] or 0),
            conversion_rate=round(float(row["conversion_rate"] or 0), 2),
            posted_at=row["posted_at"].isoformat() if row["posted_at"] else "",
        )
        for row in rows
    ]
    
    response_data = ContentResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
    
    # Cache the response with 5-minute TTL
    await set_cached_analytics("content", cache_params, response_data.model_dump(), ttl=300)
    
    return response_data


@router.get("/products", response_model=ProductsResponse)
async def get_product_analytics(
    sort_by: str = Query("gmv", description="gmv|buyers|creators|conversion"),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> ProductsResponse:
    """Product Analytics."""
    from app.services.cache_service import get_cached_analytics, set_cached_analytics
    
    # Check cache first
    cache_params = {
        "sort_by": sort_by,
        "category": category,
        "page": page,
        "page_size": page_size,
    }
    cached_data = await get_cached_analytics("products", cache_params)
    if cached_data:
        return ProductsResponse(**cached_data)
    
    conditions = ["p.is_active = TRUE"]
    params: Dict[str, Any] = {}

    if category:
        conditions.append("p.category = :category")
        params["category"] = category

    where = f"WHERE {' AND '.join(conditions)}"

    # Get total count for pagination
    count_result = await db.execute(text(f"""
        SELECT COUNT(*)
        FROM products p
        {where}
    """), params)
    total_items = int(count_result.scalar() or 0)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    order_map = {
        "gmv": "total_gmv DESC",
        "buyers": "total_buyers DESC",
        "creators": "total_creators DESC",
        "conversion": "conversion_rate DESC",
    }
    order = order_map.get(sort_by, "total_gmv DESC")

    # Calculate offset for pagination
    offset = (page - 1) * page_size
    params["limit"] = page_size
    params["offset"] = offset

    result = await db.execute(text(f"""
        SELECT
            p.id, p.name, p.price, p.category, p.shop_name,
            COALESCE(SUM(cv.gmv_generated), 0) AS total_gmv,
            COALESCE(SUM(cv.buyers), 0) AS total_buyers,
            COUNT(DISTINCT cv.creator_id) AS total_creators,
            CASE WHEN SUM(cv.views) > 0
                THEN SUM(cv.buyers)::float / SUM(cv.views) * 100
                ELSE 0 END AS conversion_rate
        FROM products p
        LEFT JOIN content_videos cv ON cv.product_id = p.id
        {where}
        GROUP BY p.id, p.name, p.price, p.category, p.shop_name
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """), params)

    rows = result.mappings().all()
    items = [
        ProductItem(
            id=str(row["id"]),
            name=row["name"],
            price=float(row["price"] or 0),
            category=row["category"],
            shop_name=row["shop_name"],
            total_gmv=float(row["total_gmv"] or 0),
            total_buyers=int(row["total_buyers"] or 0),
            total_creators=int(row["total_creators"] or 0),
            conversion_rate=round(float(row["conversion_rate"] or 0), 2),
            revenue=float(row["total_buyers"] or 0) * float(row["price"] or 0),
        )
        for row in rows
    ]
    
    response_data = ProductsResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
    
    # Cache the response with 5-minute TTL
    await set_cached_analytics("products", cache_params, response_data.model_dump(), ttl=300)
    
    return response_data


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue_insights(
    sort_by: str = Query("revenue", description="revenue|conversion|buyers"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> RevenueResponse:
    """Revenue Insights — Creator × Product × Revenue."""
    from app.services.cache_service import get_cached_analytics, set_cached_analytics
    
    # Check cache first
    cache_params = {
        "sort_by": sort_by,
        "page": page,
        "page_size": page_size,
    }
    cached_data = await get_cached_analytics("revenue", cache_params)
    if cached_data:
        return RevenueResponse(**cached_data)
    
    # Get total count for pagination
    count_result = await db.execute(text("""
        SELECT COUNT(*)
        FROM (
            SELECT i.id, p.id
            FROM influencers i
            JOIN content_videos cv ON cv.creator_id = i.id
            LEFT JOIN products p ON p.id = cv.product_id
            GROUP BY i.id, p.id
        ) AS subq
    """))
    total_items = int(count_result.scalar() or 0)
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 1

    order_map = {
        "revenue": "revenue DESC",
        "conversion": "conversion_rate DESC",
        "buyers": "total_buyers DESC",
    }
    order = order_map.get(sort_by, "revenue DESC")

    # Calculate offset for pagination
    offset = (page - 1) * page_size

    result = await db.execute(text(f"""
        SELECT
            i.id AS creator_id, i.name AS creator_name,
            p.id AS product_id, p.name AS product_name,
            COALESCE(SUM(cv.gmv_generated), 0) AS revenue,
            COALESCE(SUM(cv.gmv_generated), 0) AS gmv,
            COALESCE(SUM(cv.buyers), 0) AS total_buyers,
            COUNT(cv.id) AS video_count,
            CASE WHEN SUM(cv.views) > 0
                THEN SUM(cv.buyers)::float / SUM(cv.views) * 100
                ELSE 0 END AS conversion_rate
        FROM influencers i
        JOIN content_videos cv ON cv.creator_id = i.id
        LEFT JOIN products p ON p.id = cv.product_id
        GROUP BY i.id, i.name, p.id, p.name
        ORDER BY {order}
        LIMIT :limit OFFSET :offset
    """), {"limit": page_size, "offset": offset})

    rows = result.mappings().all()
    items = [
        RevenueInsightItem(
            creator_id=str(row["creator_id"]),
            creator_name=row["creator_name"],
            product_id=str(row["product_id"]) if row["product_id"] else None,
            product_name=row["product_name"],
            revenue=float(row["revenue"] or 0),
            gmv=float(row["gmv"] or 0),
            buyers=int(row["total_buyers"] or 0),
            conversion_rate=round(float(row["conversion_rate"] or 0), 2),
            video_count=int(row["video_count"] or 0),
        )
        for row in rows
    ]
    
    response_data = RevenueResponse(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
    
    # Cache the response with 5-minute TTL
    await set_cached_analytics("revenue", cache_params, response_data.model_dump(), ttl=300)
    
    return response_data


# ─── Affiliate Detail Analytics ───────────────────────────────────────────────

class AffiliateSalesData(BaseModel):
    gmv: float
    products_sold: int
    gpm: float
    gmv_per_buyer_min: float
    gmv_per_buyer_max: float
    gmv_by_channel: List[Dict[str, Any]]
    gmv_by_category: List[Dict[str, Any]]

class AffiliateCollabData(BaseModel):
    likelihood_pct: int
    avg_commission_rate: Optional[float]
    products: int
    brand_collabs: int
    price_min: float
    price_max: float

class AffiliateTrendPoint(BaseModel):
    date: str
    value: float

class AffiliateFollowerData(BaseModel):
    gender: List[Dict[str, Any]]
    age: List[Dict[str, Any]]
    top_locations: List[Dict[str, Any]]


@router.get("/affiliate/{affiliate_id}/sales")
async def get_affiliate_sales(
    affiliate_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Sales metrics untuk satu affiliator."""
    result = await db.execute(text("""
        SELECT
            COALESCE(SUM(cv.gmv_generated), 0) AS total_gmv,
            COALESCE(SUM(cv.buyers), 0) AS total_buyers,
            COUNT(cv.id) AS video_count,
            COALESCE(AVG(cv.gmv_generated), 0) AS avg_gmv_per_video,
            COALESCE(MIN(CASE WHEN cv.buyers > 0 THEN cv.gmv_generated / cv.buyers END), 0) AS gmv_per_buyer_min,
            COALESCE(MAX(CASE WHEN cv.buyers > 0 THEN cv.gmv_generated / cv.buyers END), 0) AS gmv_per_buyer_max
        FROM content_videos cv
        WHERE cv.creator_id = :id
    """), {"id": affiliate_id})
    row = result.mappings().first()

    total_gmv = float(row["total_gmv"] or 0)
    total_buyers = int(row["total_buyers"] or 0)
    avg_gmv = float(row["avg_gmv_per_video"] or 0)
    gpm = total_gmv / max(1, total_buyers)

    # GMV by channel (mock: mostly video)
    gmv_by_channel = [
        {"name": "Video", "value": 98.72, "color": "#14b8a6"},
        {"name": "Kartu produk", "value": 1.28, "color": "#f59e0b"},
    ]

    # GMV by category from products
    cat_result = await db.execute(text("""
        SELECT p.category, COALESCE(SUM(cv.gmv_generated), 0) AS cat_gmv
        FROM content_videos cv
        JOIN products p ON p.id = cv.product_id
        WHERE cv.creator_id = :id AND p.category IS NOT NULL
        GROUP BY p.category
        ORDER BY cat_gmv DESC
        LIMIT 5
    """), {"id": affiliate_id})
    cat_rows = cat_result.mappings().all()

    colors = ["#14b8a6", "#f59e0b", "#3b82f6", "#8b5cf6", "#ec4899"]
    total_cat_gmv = sum(float(r["cat_gmv"]) for r in cat_rows) or 1
    gmv_by_category = [
        {
            "name": r["category"],
            "value": round(float(r["cat_gmv"]) / total_cat_gmv * 100, 2),
            "color": colors[i % len(colors)],
        }
        for i, r in enumerate(cat_rows)
    ]
    if not gmv_by_category:
        gmv_by_category = [{"name": "Lainnya", "value": 100.0, "color": "#14b8a6"}]

    return {
        "gmv": total_gmv,
        "products_sold": total_buyers,
        "gpm": round(gpm),
        "gmv_per_buyer_min": float(row["gmv_per_buyer_min"] or 0),
        "gmv_per_buyer_max": float(row["gmv_per_buyer_max"] or 0),
        "gmv_by_channel": gmv_by_channel,
        "gmv_by_category": gmv_by_category,
    }


@router.get("/affiliate/{affiliate_id}/trend")
async def get_affiliate_trend(
    affiliate_id: str,
    metric: str = Query("followers", description="gmv|products_sold|followers|views|engagement"),
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Trend data untuk satu affiliator (30 hari terakhir)."""
    if metric in ("gmv", "products_sold", "views", "engagement"):
        col_map = {
            "gmv": "SUM(cv.gmv_generated)",
            "products_sold": "SUM(cv.buyers)",
            "views": "SUM(cv.views)",
            "engagement": "AVG(CASE WHEN cv.views > 0 THEN (cv.likes + cv.comments + cv.shares)::float / cv.views * 100 ELSE 0 END)",
        }
        col = col_map[metric]
        result = await db.execute(text(f"""
            SELECT
                DATE_TRUNC('day', cv.posted_at) AS day,
                {col} AS value
            FROM content_videos cv
            WHERE cv.creator_id = :id
              AND cv.posted_at >= NOW() - INTERVAL '30 days'
            GROUP BY day
            ORDER BY day
        """), {"id": affiliate_id})
        rows = result.fetchall()
        points = [
            {
                "date": row[0].strftime("%d %b") if row[0] else "",
                "value": round(float(row[1] or 0), 2),
            }
            for row in rows
        ]
    else:
        # followers — ambil dari influencer follower_count sebagai flat line + mock growth
        result = await db.execute(text("""
            SELECT follower_count FROM influencers WHERE id = :id
        """), {"id": affiliate_id})
        row = result.fetchone()
        base = int(row[0]) if row else 1000
        import random
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        points = []
        val = max(100, base - 300)
        for i in range(30):
            d = now - timedelta(days=29 - i)
            val += random.randint(-10, 50)
            val = max(100, val)
            points.append({"date": d.strftime("%d %b"), "value": val})
        # Last point = actual follower count
        if points:
            points[-1]["value"] = base

    return {"metric": metric, "points": points}


@router.get("/affiliate/{affiliate_id}/collab")
async def get_affiliate_collab(
    affiliate_id: str,
    db: AsyncSession = Depends(get_db_session),
    _: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Collaboration metrics untuk satu affiliator."""
    result = await db.execute(text("""
        SELECT
            COUNT(DISTINCT cv.product_id) AS products,
            COUNT(DISTINCT p.shop_name) AS brand_collabs,
            COALESCE(MIN(p.price), 0) AS price_min,
            COALESCE(MAX(p.price), 0) AS price_max
        FROM content_videos cv
        LEFT JOIN products p ON p.id = cv.product_id
        WHERE cv.creator_id = :id
    """), {"id": affiliate_id})
    row = result.mappings().first()

    return {
        "likelihood_pct": 60,
        "avg_commission_rate": None,
        "products": int(row["products"] or 0),
        "brand_collabs": int(row["brand_collabs"] or 0),
        "price_min": float(row["price_min"] or 0),
        "price_max": float(row["price_max"] or 0),
    }
