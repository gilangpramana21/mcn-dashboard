# Design Document: Analytics Platform

## Overview

The Analytics Platform extends the TikTok Influencer Marketing Agent with comprehensive analytics capabilities to measure, monitor, and optimize influencer marketing campaign performance. The platform aggregates data from multiple sources (content videos, products, creators, and transactions) to generate actionable business insights.

The system provides five core analytics endpoints (overview, creators, content, products, revenue) and four dedicated frontend pages (Creator Intelligence, Content Analytics, Product Analytics, Revenue Insights) that enable marketing teams to understand campaign ROI, identify high-performing creators and products, analyze content trends, and make data-driven decisions.

Key design principles:
- Query optimization through strategic indexing and aggregation
- Redis caching for frequently accessed analytics data
- Consistent API response format across all endpoints
- Real-time data aggregation with sub-3-second response times
- Seamless integration with existing influencer management system

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Dashboard   │  │   Creator    │  │   Content    │          │
│  │   (Updated)  │  │ Intelligence │  │  Analytics   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │   Product    │  │   Revenue    │                            │
│  │  Analytics   │  │   Insights   │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer                                │
│  /api/v1/analytics/overview                                     │
│  /api/v1/analytics/creators                                     │
│  /api/v1/analytics/content                                      │
│  /api/v1/analytics/products                                     │
│  /api/v1/analytics/revenue                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
         ┌──────────────────┐  ┌──────────────────┐
         │  Redis Cache     │  │  PostgreSQL DB   │
         │  (5 min TTL)     │  │                  │
         └──────────────────┘  └──────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
            │  influencers │   │   products   │   │content_videos│
            └──────────────┘   └──────────────┘   └──────────────┘
```

### Data Flow

1. **Request Flow**: Frontend → API endpoint → Cache check → Database query → Response
2. **Cache Strategy**: Cache hit returns immediately; cache miss triggers DB query and cache update
3. **Aggregation**: Complex analytics computed via SQL JOINs and GROUP BY operations
4. **Real-time Updates**: Cache TTL of 5 minutes ensures fresh data without excessive DB load

## Components and Interfaces

### Database Schema

#### Products Table

```sql
CREATE TABLE products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tiktok_product_id   VARCHAR(255) UNIQUE NOT NULL,
    name                VARCHAR(500) NOT NULL,
    price               NUMERIC(18, 2) NOT NULL DEFAULT 0,
    category            VARCHAR(100),
    image_url           TEXT,
    shop_name           VARCHAR(255),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_products_active ON products(is_active);
```

**Field Descriptions**:
- `tiktok_product_id`: Unique identifier from TikTok platform
- `price`: Product price in Rupiah (18 digits, 2 decimal places)
- `category`: Product category for filtering and grouping
- `is_active`: Soft delete flag for product lifecycle management

#### Content Videos Table

```sql
CREATE TABLE content_videos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tiktok_video_id VARCHAR(255) UNIQUE NOT NULL,
    creator_id      VARCHAR(255) NOT NULL REFERENCES influencers(id),
    product_id      UUID REFERENCES products(id),
    title           TEXT,
    views           BIGINT NOT NULL DEFAULT 0,
    likes           BIGINT NOT NULL DEFAULT 0,
    comments        BIGINT NOT NULL DEFAULT 0,
    shares          BIGINT NOT NULL DEFAULT 0,
    gmv_generated   NUMERIC(18, 2) NOT NULL DEFAULT 0,
    buyers          INT NOT NULL DEFAULT 0,
    posted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_content_videos_creator ON content_videos(creator_id);
CREATE INDEX idx_content_videos_product ON content_videos(product_id);
CREATE INDEX idx_content_videos_posted ON content_videos(posted_at DESC);
CREATE INDEX idx_content_videos_gmv ON content_videos(gmv_generated DESC);
```

**Field Descriptions**:
- `creator_id`: Foreign key to influencers table
- `product_id`: Foreign key to products table (nullable for non-product content)
- `gmv_generated`: Gross Merchandise Value in Rupiah
- `buyers`: Number of unique buyers from this video

**Index Strategy**:
- `creator_id`: Optimizes creator-based filtering and aggregation
- `product_id`: Optimizes product-based filtering and aggregation
- `posted_at DESC`: Optimizes time-based sorting and filtering
- `gmv_generated DESC`: Optimizes revenue-based sorting

#### Influencers Table Extensions

```sql
ALTER TABLE influencers
    ADD COLUMN creator_role VARCHAR(20) NOT NULL DEFAULT 'influencer',
    ADD COLUMN creator_score NUMERIC(10, 4) NOT NULL DEFAULT 0,
    ADD COLUMN estimated_revenue NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN avg_views BIGINT NOT NULL DEFAULT 0;

CREATE INDEX idx_influencers_creator_role ON influencers(creator_role);
CREATE INDEX idx_influencers_creator_score ON influencers(creator_score DESC);
```

**New Fields**:
- `creator_role`: Classification (influencer | affiliator | hybrid)
- `creator_score`: Composite performance score (0-1 range)
- `estimated_revenue`: Cached total GMV for performance
- `avg_views`: Cached average views per video

### API Endpoints

#### 1. GET /api/v1/analytics/overview

**Purpose**: Global KPI dashboard metrics

**Response Schema**:
```typescript
{
  total_gmv: number,
  total_views: number,
  total_creators: number,
  global_conversion_rate: number,
  total_buyers: number,
  top_creator_name: string | null,
  top_creator_revenue: number,
  top_product_name: string | null,
  top_product_gmv: number
}
```

**Query Strategy**:
```sql
-- Aggregated KPIs from content_videos
SELECT
    COALESCE(SUM(gmv_generated), 0) AS total_gmv,
    COALESCE(SUM(views), 0) AS total_views,
    COALESCE(SUM(buyers), 0) AS total_buyers
FROM content_videos;

-- Top creator by revenue
SELECT i.name, COALESCE(SUM(cv.gmv_generated), 0) AS revenue
FROM influencers i
LEFT JOIN content_videos cv ON cv.creator_id = i.id
GROUP BY i.id, i.name
ORDER BY revenue DESC LIMIT 1;

-- Top product by GMV
SELECT p.name, COALESCE(SUM(cv.gmv_generated), 0) AS gmv
FROM products p
LEFT JOIN content_videos cv ON cv.product_id = p.id
GROUP BY p.id, p.name
ORDER BY gmv DESC LIMIT 1;
```

**Performance Target**: < 3 seconds for 100,000 videos

#### 2. GET /api/v1/analytics/creators

**Purpose**: Creator intelligence with performance metrics

**Query Parameters**:
- `sort_by`: score | revenue | followers | engagement | views (default: score)
- `role`: influencer | affiliator | hybrid (optional filter)
- `min_followers`: minimum follower count (optional filter)
- `limit`: result limit (default: 50, max: 200)

**Response Schema**:
```typescript
{
  id: string,
  name: string,
  follower_count: number,
  engagement_rate: number,
  avg_views: number,
  estimated_revenue: number,
  creator_score: number,
  creator_role: string,
  has_whatsapp: boolean,
  location: string,
  content_categories: string[],
  video_count: number,
  total_gmv: number,
  total_views: number
}[]
```

**Query Strategy**:
```sql
SELECT
    i.id, i.name, i.follower_count, i.engagement_rate,
    i.avg_views, i.estimated_revenue, i.creator_score,
    i.creator_role, i.has_whatsapp, i.location,
    i.content_categories,
    COUNT(cv.id) AS video_count,
    COALESCE(SUM(cv.gmv_generated), 0) AS total_gmv,
    COALESCE(SUM(cv.views), 0) AS total_views
FROM influencers i
LEFT JOIN content_videos cv ON cv.creator_id = i.id
WHERE i.status = 'ACTIVE'
GROUP BY i.id, [all i columns]
ORDER BY creator_score DESC
LIMIT :limit;
```

#### 3. GET /api/v1/analytics/content

**Purpose**: Video-level content performance analytics

**Query Parameters**:
- `sort_by`: views | gmv | engagement | velocity (default: views)
- `creator_id`: filter by creator (optional)
- `product_id`: filter by product (optional)
- `limit`: result limit (default: 50, max: 200)

**Response Schema**:
```typescript
{
  id: string,
  tiktok_video_id: string,
  creator_name: string,
  creator_id: string,
  product_name: string | null,
  views: number,
  likes: number,
  comments: number,
  shares: number,
  engagement_rate: number,
  velocity: number,
  gmv_generated: number,
  buyers: number,
  conversion_rate: number,
  posted_at: string
}[]
```

**Calculated Metrics**:
- `engagement_rate = ((likes + comments + shares) / views) × 100`
- `velocity = views / hours_since_posted`
- `conversion_rate = (buyers / views) × 100`

#### 4. GET /api/v1/analytics/products

**Purpose**: Product performance analytics

**Query Parameters**:
- `sort_by`: gmv | buyers | creators | conversion (default: gmv)
- `category`: filter by category (optional)
- `limit`: result limit (default: 50, max: 200)

**Response Schema**:
```typescript
{
  id: string,
  name: string,
  price: number,
  category: string | null,
  total_gmv: number,
  total_buyers: number,
  total_creators: number,
  conversion_rate: number,
  revenue: number,
  shop_name: string | null
}[]
```

**Query Strategy**:
```sql
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
WHERE p.is_active = TRUE
GROUP BY p.id, p.name, p.price, p.category, p.shop_name
ORDER BY total_gmv DESC
LIMIT :limit;
```

#### 5. GET /api/v1/analytics/revenue

**Purpose**: Revenue insights by creator-product combinations

**Query Parameters**:
- `sort_by`: revenue | conversion | buyers (default: revenue)
- `limit`: result limit (default: 100, max: 500)

**Response Schema**:
```typescript
{
  creator_id: string,
  creator_name: string,
  product_id: string | null,
  product_name: string | null,
  revenue: number,
  gmv: number,
  buyers: number,
  conversion_rate: number,
  video_count: number
}[]
```

**Query Strategy**:
```sql
SELECT
    i.id AS creator_id, i.name AS creator_name,
    p.id AS product_id, p.name AS product_name,
    COALESCE(SUM(cv.gmv_generated), 0) AS revenue,
    COALESCE(SUM(cv.buyers), 0) AS total_buyers,
    COUNT(cv.id) AS video_count,
    CASE WHEN SUM(cv.views) > 0
        THEN SUM(cv.buyers)::float / SUM(cv.views) * 100
        ELSE 0 END AS conversion_rate
FROM influencers i
JOIN content_videos cv ON cv.creator_id = i.id
LEFT JOIN products p ON p.id = cv.product_id
GROUP BY i.id, i.name, p.id, p.name
ORDER BY revenue DESC
LIMIT :limit;
```

### Frontend Components

#### Component Architecture

```
src/
├── app/
│   └── (dashboard)/
│       ├── page.tsx                    # Dashboard (updated with KPIs)
│       ├── creator-intelligence/
│       │   └── page.tsx                # Creator Intelligence page
│       ├── content-analytics/
│       │   └── page.tsx                # Content Analytics page
│       ├── product-analytics/
│       │   └── page.tsx                # Product Analytics page
│       └── revenue-insights/
│           └── page.tsx                # Revenue Insights page
├── components/
│   ├── Sidebar.tsx                     # Updated navigation
│   ├── analytics/
│   │   ├── KPICard.tsx                 # Reusable KPI display
│   │   ├── CreatorTable.tsx            # Creator intelligence table
│   │   ├── ContentTable.tsx            # Content analytics table
│   │   ├── ProductTable.tsx            # Product analytics table
│   │   └── RevenueTable.tsx            # Revenue insights table
│   └── ui/
│       ├── Badge.tsx                   # Role/status badges
│       └── DataTable.tsx               # Generic sortable table
└── hooks/
    └── useAnalytics.ts                 # Analytics data fetching hook
```

#### Sidebar Navigation Structure

```typescript
const NAV_SECTIONS = [
  {
    label: 'Analytics',
    items: [
      { href: '/', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/creator-intelligence', label: 'Creator Intelligence', icon: Users },
      { href: '/content-analytics', label: 'Content Analytics', icon: Play },
      { href: '/product-analytics', label: 'Product Analytics', icon: ShoppingBag },
      { href: '/revenue-insights', label: 'Revenue Insights', icon: DollarSign },
    ],
  },
  {
    label: 'Outreach',
    items: [
      { href: '/affiliates', label: 'Cari Affiliasi', icon: Search },
      { href: '/influencers', label: 'Influencer', icon: Users },
      { href: '/campaigns', label: 'Kampanye', icon: Megaphone },
      { href: '/templates', label: 'Template Pesan', icon: FileText },
      { href: '/blacklist', label: 'Daftar Hitam', icon: Ban },
    ],
  },
  {
    label: 'AI & Laporan',
    items: [
      { href: '/learning', label: 'AI Learning', icon: Brain },
      { href: '/reports', label: 'Laporan', icon: BarChart3 },
    ],
  },
]
```

#### State Management Approach

Using React Server Components with client-side data fetching:

```typescript
// useAnalytics.ts
export function useAnalytics<T>(endpoint: string, params?: Record<string, any>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        const response = await apiClient.get(`/analytics/${endpoint}`, { params })
        setData(response.data)
      } catch (err) {
        setError(err as Error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [endpoint, JSON.stringify(params)])

  return { data, loading, error, refetch: () => fetchData() }
}
```

#### Data Fetching Patterns

1. **Initial Load**: Server-side data fetching for SEO and performance
2. **Client-side Updates**: React hooks for filtering, sorting, pagination
3. **Optimistic Updates**: Immediate UI feedback with background revalidation
4. **Error Boundaries**: Graceful error handling with retry mechanisms

## Data Models

### Creator Score Calculation Algorithm

The creator score is a composite metric (0-1 range) that evaluates overall creator performance:

```
creator_score = (0.4 × normalized_gmv) + 
                (0.3 × normalized_engagement) + 
                (0.2 × normalized_consistency) + 
                (0.1 × normalized_video_count)
```

**Component Calculations**:

1. **Normalized GMV** (40% weight):
```python
normalized_gmv = min(total_gmv / max_gmv_in_dataset, 1.0)
```

2. **Normalized Engagement** (30% weight):
```python
normalized_engagement = min(avg_engagement_rate / max_engagement_in_dataset, 1.0)
```

3. **Normalized Consistency** (20% weight):
```python
std_dev = standard_deviation(gmv_per_video)
consistency = 1 / (1 + std_dev)
normalized_consistency = min(consistency / max_consistency_in_dataset, 1.0)
```

4. **Normalized Video Count** (10% weight):
```python
normalized_video_count = min(video_count / max_video_count_in_dataset, 1.0)
```

**Creator Role Classification**:
- Superstar: score >= 0.8
- Rising Star: 0.6 <= score < 0.8
- Consistent Performer: 0.4 <= score < 0.6
- Underperformer: score < 0.4

### Data Aggregation Patterns

#### Pattern 1: Single-Table Aggregation
Used for simple metrics from one table:
```sql
SELECT COUNT(*), SUM(gmv_generated), AVG(views)
FROM content_videos
WHERE posted_at >= :start_date;
```

#### Pattern 2: Join-Based Aggregation
Used for cross-table analytics:
```sql
SELECT i.name, COUNT(cv.id), SUM(cv.gmv_generated)
FROM influencers i
LEFT JOIN content_videos cv ON cv.creator_id = i.id
GROUP BY i.id, i.name;
```

#### Pattern 3: Nested Aggregation
Used for complex calculations:
```sql
WITH creator_stats AS (
    SELECT creator_id, 
           AVG(gmv_generated) as avg_gmv,
           STDDEV(gmv_generated) as std_gmv
    FROM content_videos
    GROUP BY creator_id
)
SELECT * FROM creator_stats WHERE std_gmv < 1000000;
```

### Caching Strategy with Redis

**Cache Key Pattern**: `analytics:{endpoint}:{hash(params)}`

**Implementation**:
```python
async def get_cached_analytics(endpoint: str, params: dict) -> Optional[dict]:
    cache_key = f"analytics:{endpoint}:{hash(json.dumps(params, sort_keys=True))}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)
    return None

async def set_cached_analytics(endpoint: str, params: dict, data: dict):
    cache_key = f"analytics:{endpoint}:{hash(json.dumps(params, sort_keys=True))}"
    await redis.setex(cache_key, 300, json.dumps(data))  # 5 min TTL
```

**Cache Invalidation**:
- Time-based: 5-minute TTL for all analytics data
- Event-based: Clear cache on content_videos or products table updates
- Manual: Admin endpoint to clear analytics cache


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property Reflection

After analyzing all acceptance criteria, I identified several areas of redundancy:

1. **Pagination properties** (4.7, 5.7, 6.8, 7.6): All endpoints use the same pagination mechanism, so one comprehensive property covers all
2. **Sorting properties** (4.5, 5.5, 6.6, 7.4): All endpoints use similar sorting logic, can be combined into one property with parameterization
3. **Filtering properties** (4.6, 5.6, 6.7, 7.5): Similar filtering mechanisms across endpoints
4. **Normalization properties** (14.2, 14.3, 14.5): All use min-max normalization to [0,1], can be combined
5. **Response format properties** (18.1, 18.2, 18.3, 18.4, 18.5): All about consistent API response structure

The following properties represent the unique, non-redundant validation requirements:

### Property 1: Product ID Uniqueness

*For any* two product records, if they have the same tiktok_product_id, then they must be the same product (same database ID).

**Validates: Requirements 1.2**

### Property 2: Non-Negative Validation

*For any* product or content video record, all numeric fields (price, views, likes, comments, shares, gmv_generated, buyers) must be non-negative values.

**Validates: Requirements 1.3, 2.2**

### Property 3: Future Timestamp Rejection

*For any* content video record with a posted_at timestamp, if the timestamp is in the future, then the system must reject the record with a validation error.

**Validates: Requirements 2.4**

### Property 4: Referential Integrity

*For any* content video record, the creator_id must reference a valid influencer record, and if product_id is not null, it must reference a valid product record.

**Validates: Requirements 2.3, 16.2**

### Property 5: Global Conversion Rate Calculation

*For any* dataset of content videos, the global_conversion_rate must equal (total_buyers / total_views) × 100, where total_buyers and total_views are summed across all videos.

**Validates: Requirements 3.3**

### Property 6: Top Entity Selection

*For any* dataset, the top_creator must be the creator with the highest estimated_revenue, and the top_product must be the product with the highest total_gmv.

**Validates: Requirements 3.5, 3.6**

### Property 7: Creator Score Formula

*For any* creator with performance data, the creator_score must equal (0.4 × normalized_gmv) + (0.3 × normalized_engagement) + (0.2 × normalized_consistency) + (0.1 × normalized_video_count), where all normalized values are in the range [0, 1].

**Validates: Requirements 4.3, 14.1**

### Property 8: Creator Score Bounds

*For any* calculated creator_score, the value must be in the range [0, 1].

**Validates: Requirements 14.6**

### Property 9: Creator Role Classification

*For any* creator with a creator_score, the creator_role must be: "Superstar" if score >= 0.8, "Rising Star" if 0.6 <= score < 0.8, "Consistent Performer" if 0.4 <= score < 0.6, or "Underperformer" if score < 0.4.

**Validates: Requirements 4.4**

### Property 10: Min-Max Normalization Range

*For any* value normalized using min-max normalization (gmv, engagement, video_count), the result must be in the range [0, 1].

**Validates: Requirements 14.2, 14.3, 14.5**

### Property 11: Engagement Rate Calculation

*For any* content video with views > 0, the engagement_rate must equal ((likes + comments + shares) / views) × 100.

**Validates: Requirements 5.3**

### Property 12: Conversion Rate Calculation

*For any* content video with views > 0, the conversion_rate must equal (buyers / views) × 100.

**Validates: Requirements 5.4**

### Property 13: Zero Views Edge Case

*For any* content video with views = 0, the engagement_rate and conversion_rate must both be 0 without causing division errors.

**Validates: Requirements 16.3**

### Property 14: Product Aggregation Counts

*For any* product, the total_videos must equal the count of content_videos referencing that product, and total_creators must equal the count of distinct creator_ids in those videos.

**Validates: Requirements 6.3, 6.4**

### Property 15: Average Conversion Rate

*For any* product with associated videos, the avg_conversion_rate must equal the arithmetic mean of conversion_rates from all videos promoting that product.

**Validates: Requirements 6.5**

### Property 16: Revenue Contribution Percentage Sum

*For any* complete dataset of creator-product combinations, the sum of all revenue_contribution_percentage values must equal 100%.

**Validates: Requirements 7.3**

### Property 17: Revenue Contribution Calculation

*For any* creator-product combination, the revenue_contribution_percentage must equal (gmv_for_this_combination / total_gmv_all_combinations) × 100.

**Validates: Requirements 7.3**

### Property 18: Sorting Consistency

*For any* analytics endpoint with sort_by parameter, the results must be ordered according to the specified field in descending order (or ascending if specified).

**Validates: Requirements 4.5, 5.5, 6.6, 7.4**

### Property 19: Filtering Correctness

*For any* analytics endpoint with filter parameters, all returned results must satisfy the filter conditions (e.g., if min_followers=1000, all results must have follower_count >= 1000).

**Validates: Requirements 4.6, 5.6, 6.7, 7.5**

### Property 20: Pagination Correctness

*For any* analytics endpoint with limit and offset parameters, the number of returned results must not exceed limit, and results must start from the offset position in the complete dataset.

**Validates: Requirements 4.7, 5.7, 6.8, 7.6**

### Property 21: Date Range Filtering

*For any* analytics request with date_range filter, all returned content videos must have posted_at timestamps within the specified range.

**Validates: Requirements 15.3**

### Property 22: Cache Consistency

*For any* identical analytics query executed twice within the cache TTL period, both requests must return identical results.

**Validates: Requirements 15.4**

### Property 23: Blacklist Exclusion

*For any* creator analytics query, no creator with status = 'BLACKLISTED' should appear in the results.

**Validates: Requirements 20.3**

### Property 24: Invalid Input Rejection

*For any* API request with invalid data (negative price, invalid creator_id, GMV > 10 billion), the system must return HTTP 400 with a descriptive error message.

**Validates: Requirements 16.1, 16.2, 16.4, 16.5**

### Property 25: Response Format Consistency

*For any* successful analytics API response, the structure must be { "data": [...], "meta": {...} } with data as an array (never null) and snake_case field names.

**Validates: Requirements 18.1, 18.3, 18.5**

### Property 26: Pagination Metadata

*For any* paginated analytics response, the meta object must contain: page, page_size, total_items, and total_pages fields.

**Validates: Requirements 18.2**

### Property 27: Error Response Format

*For any* API error response, the structure must be { "error": { "code": string, "message": string, "details": {...} } }.

**Validates: Requirements 18.4**

### Property 28: Currency Formatting

*For any* numeric value representing Rupiah (price, GMV), the frontend must format it with "Rp" prefix and thousand separators.

**Validates: Requirements 11.3**

### Property 29: Engagement Rate Color Coding

*For any* engagement_rate value displayed in the UI, the color must be: green if >= 5%, yellow if 2-5%, gray if < 2%.

**Validates: Requirements 10.3**

### Property 30: Creator Role Badge Colors

*For any* creator_role displayed in the UI, the badge color must be: gold for Superstar, purple for Rising Star, blue for Consistent Performer, gray for Underperformer.

**Validates: Requirements 9.3**

## Error Handling

### Validation Errors

**Scenario**: Invalid input data (negative values, missing required fields, invalid references)

**Handling**:
```python
from fastapi import HTTPException

def validate_product(product_data: dict):
    if product_data.get("price", 0) < 0:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_PRICE",
                    "message": "Product price must be non-negative",
                    "details": {"field": "price", "value": product_data.get("price")}
                }
            }
        )
    if not product_data.get("tiktok_product_id"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "MISSING_PRODUCT_ID",
                    "message": "TikTok Product ID is required",
                    "details": {"field": "tiktok_product_id"}
                }
            }
        )
```

### Database Errors

**Scenario**: Foreign key violations, unique constraint violations, connection failures

**Handling**:
```python
from sqlalchemy.exc import IntegrityError, DBAPIError

async def create_content_video(video_data: dict, db: AsyncSession):
    try:
        video = ContentVideo(**video_data)
        db.add(video)
        await db.commit()
        return video
    except IntegrityError as e:
        await db.rollback()
        if "foreign key" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error": {
                        "code": "INVALID_REFERENCE",
                        "message": "Referenced creator or product does not exist",
                        "details": {"constraint": str(e)}
                    }
                }
            )
        elif "unique" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "code": "DUPLICATE_VIDEO",
                        "message": "Video with this TikTok ID already exists",
                        "details": {"constraint": str(e)}
                    }
                }
            )
    except DBAPIError as e:
        await db.rollback()
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Database operation failed",
                    "details": {"error": str(e)}
                }
            }
        )
```

### Division by Zero

**Scenario**: Calculating rates when views = 0

**Handling**:
```python
def calculate_engagement_rate(likes: int, comments: int, shares: int, views: int) -> float:
    if views == 0:
        return 0.0
    return ((likes + comments + shares) / views) * 100

def calculate_conversion_rate(buyers: int, views: int) -> float:
    if views == 0:
        return 0.0
    return (buyers / views) * 100
```

### Empty Dataset Handling

**Scenario**: Analytics queries with no matching data

**Handling**:
```python
async def get_creator_analytics(db: AsyncSession) -> List[CreatorIntelligenceItem]:
    result = await db.execute(query)
    rows = result.mappings().all()
    
    if not rows:
        return []  # Return empty array, not null
    
    # Process rows...
    return items
```

### Cache Failures

**Scenario**: Redis connection failures or cache misses

**Handling**:
```python
async def get_analytics_with_cache(endpoint: str, params: dict, db: AsyncSession):
    try:
        cached = await get_cached_analytics(endpoint, params)
        if cached:
            return cached
    except Exception as e:
        # Log cache error but continue with database query
        logger.warning(f"Cache error: {e}")
    
    # Fetch from database
    data = await fetch_from_database(endpoint, params, db)
    
    try:
        await set_cached_analytics(endpoint, params, data)
    except Exception as e:
        # Log cache set error but return data anyway
        logger.warning(f"Cache set error: {e}")
    
    return data
```

### Frontend Error Handling

**Scenario**: API request failures, network errors, loading states

**Handling**:
```typescript
export function useAnalytics<T>(endpoint: string, params?: Record<string, any>) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await apiClient.get(`/analytics/${endpoint}`, { params })
        setData(response.data)
      } catch (err) {
        setError(err as Error)
        // Show user-friendly error message
        toast.error('Failed to load analytics data. Please try again.')
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [endpoint, JSON.stringify(params)])

  return { data, loading, error, refetch: fetchData }
}
```

## Testing Strategy

### Dual Testing Approach

The analytics platform requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests**: Focus on specific examples, edge cases, and integration points
- Specific calculation examples (e.g., creator_score for known inputs)
- Edge cases (zero views, empty datasets, single-item datasets)
- API endpoint integration tests
- Database migration verification
- Frontend component rendering tests

**Property-Based Tests**: Verify universal properties across all inputs
- Calculation formulas (engagement rate, conversion rate, creator score)
- Normalization bounds (all normalized values in [0, 1])
- Sorting and filtering correctness
- Response format consistency
- Referential integrity constraints

### Property-Based Testing Configuration

**Library**: Hypothesis (Python) for backend, fast-check (TypeScript) for frontend

**Configuration**:
```python
# Backend property tests
from hypothesis import given, settings
from hypothesis import strategies as st

@settings(max_examples=100)
@given(
    views=st.integers(min_value=0, max_value=1_000_000),
    likes=st.integers(min_value=0, max_value=100_000),
    comments=st.integers(min_value=0, max_value=10_000),
    shares=st.integers(min_value=0, max_value=10_000),
)
def test_engagement_rate_calculation(views, likes, comments, shares):
    """
    Feature: analytics-platform, Property 11: Engagement Rate Calculation
    For any content video with views > 0, engagement_rate = ((likes + comments + shares) / views) × 100
    """
    if views > 0:
        expected = ((likes + comments + shares) / views) * 100
        actual = calculate_engagement_rate(likes, comments, shares, views)
        assert abs(actual - expected) < 0.01  # Allow for floating point precision
    else:
        actual = calculate_engagement_rate(likes, comments, shares, views)
        assert actual == 0.0
```

**Test Organization**:
```
tests/
├── unit/
│   ├── test_analytics_api.py          # Specific API endpoint tests
│   ├── test_creator_score.py          # Specific score calculation tests
│   └── test_database_migrations.py    # Migration verification
├── property/
│   ├── test_calculation_properties.py # Properties 5, 7, 11, 12, 15, 17
│   ├── test_normalization_properties.py # Properties 8, 10
│   ├── test_validation_properties.py  # Properties 1, 2, 3, 4, 24
│   ├── test_api_properties.py         # Properties 18, 19, 20, 25, 26, 27
│   └── test_filtering_properties.py   # Properties 21, 23
└── integration/
    ├── test_end_to_end_analytics.py   # Full workflow tests
    └── test_cache_integration.py      # Redis cache tests
```

### Unit Test Examples

```python
# tests/unit/test_creator_score.py
def test_creator_score_superstar_classification():
    """Test that high-performing creator gets Superstar role"""
    creator = {
        "total_gmv": 10_000_000,
        "avg_engagement_rate": 8.5,
        "video_count": 50,
        "gmv_per_video_std": 100_000
    }
    score = calculate_creator_score(creator, dataset_stats)
    assert score >= 0.8
    assert classify_creator_role(score) == "Superstar"

def test_creator_score_with_zero_videos():
    """Test edge case: creator with no videos"""
    creator = {
        "total_gmv": 0,
        "avg_engagement_rate": 0,
        "video_count": 0,
        "gmv_per_video_std": 0
    }
    score = calculate_creator_score(creator, dataset_stats)
    assert score == 0.0
    assert classify_creator_role(score) == "Underperformer"
```

### Frontend Testing

```typescript
// dashboard/src/hooks/__tests__/useAnalytics.test.ts
import { renderHook, waitFor } from '@testing-library/react'
import { useAnalytics } from '../useAnalytics'

describe('useAnalytics', () => {
  it('should fetch analytics data successfully', async () => {
    const { result } = renderHook(() => useAnalytics('overview'))
    
    expect(result.current.loading).toBe(true)
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    
    expect(result.current.data).toBeDefined()
    expect(result.current.error).toBeNull()
  })

  it('should handle API errors gracefully', async () => {
    // Mock API failure
    const { result } = renderHook(() => useAnalytics('invalid-endpoint'))
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })
    
    expect(result.current.error).toBeDefined()
    expect(result.current.data).toBeNull()
  })
})
```

### Integration Testing

```python
# tests/integration/test_end_to_end_analytics.py
@pytest.mark.asyncio
async def test_complete_analytics_workflow(db_session, test_client):
    """Test complete workflow: create data → query analytics → verify results"""
    # Create test data
    creator = await create_test_influencer(db_session)
    product = await create_test_product(db_session)
    videos = await create_test_videos(db_session, creator.id, product.id, count=10)
    
    # Query overview
    response = await test_client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_gmv"] > 0
    assert data["total_views"] > 0
    
    # Query creator intelligence
    response = await test_client.get("/api/v1/analytics/creators")
    assert response.status_code == 200
    creators = response.json()
    assert len(creators) > 0
    assert any(c["id"] == creator.id for c in creators)
    
    # Verify creator score calculation
    creator_data = next(c for c in creators if c["id"] == creator.id)
    assert 0 <= creator_data["creator_score"] <= 1
    assert creator_data["creator_role"] in ["Superstar", "Rising Star", "Consistent Performer", "Underperformer"]
```

### Performance Testing

```python
# tests/performance/test_analytics_performance.py
@pytest.mark.asyncio
async def test_overview_performance_with_large_dataset(db_session, test_client):
    """Test that overview endpoint responds within 3 seconds for 100k videos"""
    # Create 100k test videos
    await create_bulk_test_videos(db_session, count=100_000)
    
    import time
    start = time.time()
    response = await test_client.get("/api/v1/analytics/overview")
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 3.0  # Must respond within 3 seconds
```

### Test Coverage Goals

- Unit tests: 80% code coverage minimum
- Property tests: 100 iterations per property minimum
- Integration tests: All critical user workflows
- Performance tests: All endpoints under load
- Frontend tests: All components and hooks

