# Implementation Plan: Analytics Platform

## Overview

This implementation plan converts the Analytics Platform design into actionable coding tasks. The platform extends the TikTok Influencer Marketing Agent with comprehensive analytics capabilities including 5 API endpoints, 4 frontend pages, database migrations, caching layer, and creator score calculation service.

The implementation follows an incremental approach: database layer → backend services → API endpoints → frontend components → integration and testing.

## Tasks

- [x] 1. Database schema and migrations
  - [x] 1.1 Create migration for products table
    - Create `app/db/migrations/005_analytics_products.sql`
    - Define products table with columns: id (UUID), tiktok_product_id (VARCHAR UNIQUE), name (VARCHAR), price (NUMERIC), category (VARCHAR), image_url (TEXT), shop_name (VARCHAR), is_active (BOOLEAN), created_at, updated_at
    - Add indexes: idx_products_category, idx_products_active
    - Add unique constraint on tiktok_product_id
    - _Requirements: 1.1, 1.2, 1.3, 19.1, 19.7_
  
  - [ ]* 1.2 Write property test for products table constraints
    - **Property 1: Product ID Uniqueness**
    - **Validates: Requirements 1.2**
  
  - [x] 1.3 Create migration for content_videos table
    - Create `app/db/migrations/006_analytics_content_videos.sql`
    - Define content_videos table with columns: id (UUID), tiktok_video_id (VARCHAR UNIQUE), creator_id (VARCHAR FK), product_id (UUID FK), title (TEXT), views (BIGINT), likes (BIGINT), comments (BIGINT), shares (BIGINT), gmv_generated (NUMERIC), buyers (INT), posted_at (TIMESTAMPTZ), created_at
    - Add foreign key constraints: creator_id → influencers.id, product_id → products.id ON DELETE SET NULL
    - Add indexes: idx_content_videos_creator, idx_content_videos_product, idx_content_videos_posted, idx_content_videos_gmv
    - _Requirements: 2.1, 2.2, 2.3, 19.2, 19.3, 19.4, 19.5, 19.6_
  
  - [ ]* 1.4 Write property test for content_videos constraints
    - **Property 2: Non-Negative Validation**
    - **Property 4: Referential Integrity**
    - **Validates: Requirements 1.3, 2.2, 2.3, 16.2**
  
  - [x] 1.5 Create migration to extend influencers table
    - Create `app/db/migrations/007_analytics_influencer_extensions.sql`
    - Add columns to influencers: creator_role (VARCHAR DEFAULT 'influencer'), creator_score (NUMERIC DEFAULT 0), estimated_revenue (NUMERIC DEFAULT 0), avg_views (BIGINT DEFAULT 0)
    - Add indexes: idx_influencers_creator_role, idx_influencers_creator_score
    - _Requirements: 4.2, 4.3, 4.4_
  
  - [ ]* 1.6 Write unit tests for database migrations
    - Test migration execution without errors
    - Test rollback functionality
    - Test index creation
    - _Requirements: 19.1, 19.2, 19.3_

- [x] 2. Domain models and validation
  - [x] 2.1 Add Product and ContentVideo models to domain.py
    - Add Product dataclass with fields: id, tiktok_product_id, name, price, category, image_url, shop_name, is_active, created_at, updated_at
    - Add ContentVideo dataclass with fields: id, tiktok_video_id, creator_id, product_id, title, views, likes, comments, shares, gmv_generated, buyers, posted_at, created_at
    - _Requirements: 1.1, 2.1_
  
  - [x] 2.2 Implement validation functions for Product
    - Create `app/services/analytics_validation.py`
    - Implement validate_product() function: check price >= 0, tiktok_product_id not empty, category is valid
    - Raise HTTPException with descriptive error for invalid data
    - _Requirements: 1.3, 16.1_
  
  - [x] 2.3 Implement validation functions for ContentVideo
    - Implement validate_content_video() function: check all metrics >= 0, posted_at not in future, creator_id and product_id exist
    - Implement validate_gmv_limit() function: check GMV <= 10 billion
    - _Requirements: 2.2, 2.4, 16.2, 16.4, 16.5_
  
  - [ ]* 2.4 Write property test for validation functions
    - **Property 2: Non-Negative Validation**
    - **Property 3: Future Timestamp Rejection**
    - **Property 24: Invalid Input Rejection**
    - **Validates: Requirements 1.3, 2.2, 2.4, 16.1, 16.2, 16.4, 16.5**

- [x] 3. Creator score calculation service
  - [x] 3.1 Implement creator score calculation algorithm
    - Create `app/services/creator_score_service.py`
    - Implement calculate_creator_score() function with formula: (0.4 × normalized_gmv) + (0.3 × normalized_engagement) + (0.2 × normalized_consistency) + (0.1 × normalized_video_count)
    - Implement min-max normalization helper: normalize_value(value, max_value) → [0, 1]
    - Implement consistency calculation: calculate_consistency(gmv_per_video_list) using standard deviation
    - _Requirements: 4.3, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6_
  
  - [ ]* 3.2 Write property test for creator score formula
    - **Property 7: Creator Score Formula**
    - **Property 8: Creator Score Bounds**
    - **Property 10: Min-Max Normalization Range**
    - **Validates: Requirements 4.3, 14.1, 14.2, 14.3, 14.5, 14.6**
  
  - [x] 3.3 Implement creator role classification
    - Implement classify_creator_role(score) function: Superstar (>= 0.8), Rising Star (0.6-0.8), Consistent Performer (0.4-0.6), Underperformer (< 0.4)
    - _Requirements: 4.4_
  
  - [ ]* 3.4 Write property test for creator role classification
    - **Property 9: Creator Role Classification**
    - **Validates: Requirements 4.4**
  
  - [ ]* 3.5 Write unit tests for edge cases
    - Test creator with zero videos
    - Test creator with single video
    - Test dataset with all same values
    - _Requirements: 14.6, 17.3_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Analytics calculation helpers
  - [x] 5.1 Implement engagement rate calculation
    - Create `app/services/analytics_calculations.py`
    - Implement calculate_engagement_rate(likes, comments, shares, views) → float
    - Handle division by zero: return 0.0 when views = 0
    - _Requirements: 5.3, 16.3_
  
  - [ ]* 5.2 Write property test for engagement rate
    - **Property 11: Engagement Rate Calculation**
    - **Property 13: Zero Views Edge Case**
    - **Validates: Requirements 5.3, 16.3**
  
  - [x] 5.3 Implement conversion rate calculation
    - Implement calculate_conversion_rate(buyers, views) → float
    - Handle division by zero: return 0.0 when views = 0
    - _Requirements: 5.4, 16.3_
  
  - [ ]* 5.4 Write property test for conversion rate
    - **Property 12: Conversion Rate Calculation**
    - **Property 13: Zero Views Edge Case**
    - **Validates: Requirements 5.4, 16.3**
  
  - [x] 5.5 Implement velocity calculation
    - Implement calculate_velocity(views, posted_at) → float
    - Calculate hours since posted, return views / hours
    - Handle edge case: return 0 if hours <= 0
    - _Requirements: 5.3_

- [x] 6. Redis caching layer
  - [x] 6.1 Implement Redis cache service
    - Create `app/services/cache_service.py`
    - Implement get_cached_analytics(endpoint, params) → Optional[dict]
    - Implement set_cached_analytics(endpoint, params, data, ttl=300)
    - Implement cache key generation: f"analytics:{endpoint}:{hash(params)}"
    - Handle Redis connection failures gracefully (log warning, continue without cache)
    - _Requirements: 15.4_
  
  - [ ]* 6.2 Write property test for cache consistency
    - **Property 22: Cache Consistency**
    - **Validates: Requirements 15.4**
  
  - [ ]* 6.3 Write unit tests for cache service
    - Test cache hit scenario
    - Test cache miss scenario
    - Test Redis connection failure handling
    - Test TTL expiration
    - _Requirements: 15.4_

- [x] 7. Analytics API - Overview endpoint
  - [x] 7.1 Implement GET /api/v1/analytics/overview
    - Update `app/api/analytics.py`
    - Implement overview endpoint with OverviewResponse model
    - Query total_gmv, total_views, total_buyers from content_videos
    - Calculate global_conversion_rate = (total_buyers / total_views) × 100
    - Query total_creators from influencers WHERE status = 'ACTIVE'
    - Query top_creator by revenue (SUM gmv_generated GROUP BY creator)
    - Query top_product by GMV (SUM gmv_generated GROUP BY product)
    - Integrate cache layer with 5-minute TTL
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 15.4_
  
  - [ ]* 7.2 Write property test for overview calculations
    - **Property 5: Global Conversion Rate Calculation**
    - **Property 6: Top Entity Selection**
    - **Validates: Requirements 3.3, 3.5, 3.6**
  
  - [ ]* 7.3 Write unit tests for overview endpoint
    - Test with empty dataset
    - Test with single creator and product
    - Test with multiple creators and products
    - Test response format
    - _Requirements: 3.1, 3.2, 17.1, 17.2_

- [x] 8. Analytics API - Creators endpoint
  - [x] 8.1 Implement GET /api/v1/analytics/creators
    - Implement creators endpoint with CreatorIntelligenceItem response model
    - Support query parameters: sort_by (score|revenue|followers|engagement|views), role, min_followers, limit
    - Query influencers with LEFT JOIN content_videos, GROUP BY creator
    - Calculate video_count, total_gmv, total_views per creator
    - Recalculate creator_score using creator_score_service
    - Auto-classify creator_role based on score
    - Filter out BLACKLISTED creators
    - Apply sorting and pagination
    - Integrate cache layer
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 20.3_
  
  - [ ]* 8.2 Write property test for creators endpoint
    - **Property 18: Sorting Consistency**
    - **Property 19: Filtering Correctness**
    - **Property 20: Pagination Correctness**
    - **Property 23: Blacklist Exclusion**
    - **Validates: Requirements 4.5, 4.6, 4.7, 20.3**
  
  - [ ]* 8.3 Write unit tests for creators endpoint
    - Test sorting by each field
    - Test filtering by role and min_followers
    - Test pagination with various limits
    - Test blacklist exclusion
    - _Requirements: 4.5, 4.6, 4.7, 20.3_

- [x] 9. Analytics API - Content endpoint
  - [x] 9.1 Implement GET /api/v1/analytics/content
    - Implement content endpoint with ContentItem response model
    - Support query parameters: sort_by (views|gmv|engagement|velocity), creator_id, product_id, limit
    - Query content_videos with JOIN influencers and LEFT JOIN products
    - Calculate engagement_rate, velocity, conversion_rate in SQL
    - Apply filtering by creator_id and product_id
    - Apply sorting and pagination
    - Integrate cache layer
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7_
  
  - [ ]* 9.2 Write property test for content endpoint
    - **Property 18: Sorting Consistency**
    - **Property 19: Filtering Correctness**
    - **Property 20: Pagination Correctness**
    - **Validates: Requirements 5.5, 5.6, 5.7**
  
  - [ ]* 9.3 Write unit tests for content endpoint
    - Test sorting by each field
    - Test filtering by creator and product
    - Test pagination
    - Test calculated metrics accuracy
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 5.7_

- [x] 10. Analytics API - Products endpoint
  - [x] 10.1 Implement GET /api/v1/analytics/products
    - Implement products endpoint with ProductItem response model
    - Support query parameters: sort_by (gmv|buyers|creators|conversion), category, limit
    - Query products with LEFT JOIN content_videos, GROUP BY product
    - Calculate total_gmv, total_buyers, total_creators, conversion_rate
    - Filter by category and is_active = TRUE
    - Apply sorting and pagination
    - Integrate cache layer
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_
  
  - [ ]* 10.2 Write property test for products endpoint
    - **Property 14: Product Aggregation Counts**
    - **Property 15: Average Conversion Rate**
    - **Property 18: Sorting Consistency**
    - **Property 19: Filtering Correctness**
    - **Property 20: Pagination Correctness**
    - **Validates: Requirements 6.3, 6.4, 6.5, 6.6, 6.7, 6.8**
  
  - [ ]* 10.3 Write unit tests for products endpoint
    - Test aggregation calculations
    - Test sorting by each field
    - Test filtering by category
    - Test pagination
    - _Requirements: 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

- [x] 11. Analytics API - Revenue endpoint
  - [x] 11.1 Implement GET /api/v1/analytics/revenue
    - Implement revenue endpoint with RevenueInsightItem response model
    - Support query parameters: sort_by (revenue|conversion|buyers), limit
    - Query influencers JOIN content_videos LEFT JOIN products, GROUP BY creator, product
    - Calculate revenue, gmv, buyers, video_count, conversion_rate per combination
    - Apply sorting and pagination
    - Integrate cache layer
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_
  
  - [ ]* 11.2 Write property test for revenue endpoint
    - **Property 16: Revenue Contribution Percentage Sum**
    - **Property 17: Revenue Contribution Calculation**
    - **Property 18: Sorting Consistency**
    - **Property 19: Filtering Correctness**
    - **Property 20: Pagination Correctness**
    - **Validates: Requirements 7.3, 7.4, 7.5, 7.6**
  
  - [ ]* 11.3 Write unit tests for revenue endpoint
    - Test revenue contribution calculation
    - Test sorting by each field
    - Test filtering
    - Test pagination
    - _Requirements: 7.3, 7.4, 7.5, 7.6_

- [x] 12. Checkpoint - Ensure all backend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. API response format standardization
  - [x] 13.1 Implement consistent response format
    - Update all analytics endpoints to return { "data": [...], "meta": {...} } structure
    - Implement pagination metadata: page, page_size, total_items, total_pages
    - Ensure empty lists return [] not null
    - Use snake_case for all field names
    - _Requirements: 18.1, 18.2, 18.3, 18.5_
  
  - [x] 13.2 Implement error response format
    - Create error response helper in `app/exceptions.py`
    - Standardize error format: { "error": { "code": str, "message": str, "details": {...} } }
    - _Requirements: 18.4_
  
  - [ ]* 13.3 Write property test for response format
    - **Property 25: Response Format Consistency**
    - **Property 26: Pagination Metadata**
    - **Property 27: Error Response Format**
    - **Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5**

- [x] 14. Frontend - useAnalytics hook
  - [x] 14.1 Create useAnalytics custom hook
    - Create `dashboard/src/hooks/useAnalytics.ts`
    - Implement generic hook: useAnalytics<T>(endpoint, params)
    - Return { data, loading, error, refetch }
    - Handle loading states, error states, and data fetching
    - Use apiClient.get() for API calls
    - _Requirements: 8.2, 8.3, 8.4_
  
  - [ ]* 14.2 Write unit tests for useAnalytics hook
    - Test successful data fetch
    - Test loading state transitions
    - Test error handling
    - Test refetch functionality
    - _Requirements: 8.2, 8.3, 8.4_

- [x] 15. Frontend - Update Sidebar navigation
  - [x] 15.1 Update Sidebar component with Analytics section
    - Update `dashboard/src/components/Sidebar.tsx`
    - Add Analytics section with items: Dashboard, Creator Intelligence, Content Analytics, Product Analytics, Revenue Insights
    - Ensure proper icons: LayoutDashboard, Users, Play, ShoppingBag, DollarSign
    - Maintain existing Outreach and AI & Laporan sections
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6_
  
  - [ ]* 15.2 Write component test for Sidebar
    - Test all menu items render correctly
    - Test active state highlighting
    - Test navigation on click
    - _Requirements: 13.5, 13.6_

- [x] 16. Frontend - Update Dashboard with KPI cards
  - [x] 16.1 Create KPICard component
    - Create `dashboard/src/components/analytics/KPICard.tsx`
    - Props: title, value, icon, onClick (optional)
    - Display formatted value with loading state
    - _Requirements: 8.1_
  
  - [x] 16.2 Update Dashboard page with overview KPIs
    - Update `dashboard/src/app/(dashboard)/page.tsx`
    - Use useAnalytics('overview') to fetch KPI data
    - Display 4 KPI cards: Total GMV, Total Views, Total Creators, Global Conversion Rate
    - Format GMV as Rupiah with thousand separators
    - Add click handlers to navigate to relevant analytics pages
    - Show loading indicator while fetching
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.3_
  
  - [ ]* 16.3 Write component tests for Dashboard
    - Test KPI cards render with data
    - Test loading state
    - Test navigation on card click
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 17. Frontend - Creator Intelligence page
  - [x] 17.1 Create CreatorTable component
    - Create `dashboard/src/components/analytics/CreatorTable.tsx`
    - Display columns: name, total_videos, total_views, engagement_rate, estimated_revenue, creator_score, creator_role
    - Implement sortable columns
    - Display creator_role badges with colors: Superstar (gold), Rising Star (purple), Consistent Performer (blue), Underperformer (gray)
    - _Requirements: 9.1, 9.3_
  
  - [x] 17.2 Create Creator Intelligence page
    - Update `dashboard/src/app/(dashboard)/creator-intelligence/page.tsx`
    - Use useAnalytics('creators', params) to fetch data
    - Implement sorting controls (dropdown or column headers)
    - Implement filtering by creator_role (dropdown)
    - Implement pagination controls
    - Display CreatorTable with fetched data
    - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.6_
  
  - [ ]* 17.3 Write property test for creator role badge colors
    - **Property 30: Creator Role Badge Colors**
    - **Validates: Requirements 9.3**
  
  - [ ]* 17.4 Write component tests for Creator Intelligence page
    - Test table renders with data
    - Test sorting functionality
    - Test filtering functionality
    - Test pagination
    - _Requirements: 9.4, 9.5, 9.6_

- [x] 18. Frontend - Content Analytics page
  - [x] 18.1 Create ContentTable component
    - Create `dashboard/src/components/analytics/ContentTable.tsx`
    - Display columns: creator_name, product_name, views, engagement_rate, gmv_generated, conversion_rate, posted_at
    - Implement sortable columns
    - Display engagement_rate with color coding: green (>= 5%), yellow (2-5%), gray (< 2%)
    - Format GMV as Rupiah
    - _Requirements: 10.1, 10.3, 11.3_
  
  - [x] 18.2 Create Content Analytics page
    - Update `dashboard/src/app/(dashboard)/content-analytics/page.tsx`
    - Use useAnalytics('content', params) to fetch data
    - Implement sorting controls
    - Implement filtering by creator and product (dropdowns)
    - Implement pagination controls
    - Display ContentTable with fetched data
    - _Requirements: 10.1, 10.2, 10.4, 10.5, 10.6_
  
  - [ ]* 18.3 Write property test for engagement rate color coding
    - **Property 29: Engagement Rate Color Coding**
    - **Validates: Requirements 10.3**
  
  - [ ]* 18.4 Write component tests for Content Analytics page
    - Test table renders with data
    - Test sorting functionality
    - Test filtering functionality
    - Test pagination
    - Test color coding
    - _Requirements: 10.4, 10.5, 10.6_

- [x] 19. Frontend - Product Analytics page
  - [x] 19.1 Create ProductTable component
    - Create `dashboard/src/components/analytics/ProductTable.tsx`
    - Display columns: name, category, price, total_videos, total_creators, total_views, total_gmv, avg_conversion_rate, total_buyers
    - Implement sortable columns
    - Format price and GMV as Rupiah with thousand separators
    - _Requirements: 11.1, 11.3_
  
  - [x] 19.2 Create Product Analytics page
    - Update `dashboard/src/app/(dashboard)/product-analytics/page.tsx`
    - Use useAnalytics('products', params) to fetch data
    - Implement sorting controls
    - Implement filtering by category (dropdown)
    - Implement pagination controls
    - Display ProductTable with fetched data
    - _Requirements: 11.1, 11.2, 11.4, 11.5, 11.6_
  
  - [ ]* 19.3 Write property test for currency formatting
    - **Property 28: Currency Formatting**
    - **Validates: Requirements 11.3**
  
  - [ ]* 19.4 Write component tests for Product Analytics page
    - Test table renders with data
    - Test sorting functionality
    - Test filtering functionality
    - Test pagination
    - Test currency formatting
    - _Requirements: 11.4, 11.5, 11.6_

- [x] 20. Frontend - Revenue Insights page
  - [x] 20.1 Create RevenueTable component
    - Create `dashboard/src/components/analytics/RevenueTable.tsx`
    - Display columns: creator_name, product_name, total_videos, total_gmv, avg_conversion_rate, revenue_contribution_percentage
    - Implement sortable columns
    - Display revenue_contribution_percentage with inline bar chart visualization
    - Format GMV as Rupiah
    - _Requirements: 12.1, 12.3_
  
  - [x] 20.2 Create Revenue Insights page
    - Update `dashboard/src/app/(dashboard)/revenue-insights/page.tsx`
    - Use useAnalytics('revenue', params) to fetch data
    - Implement sorting controls
    - Implement filtering by creator and product (dropdowns)
    - Implement pagination controls
    - Display RevenueTable with fetched data
    - _Requirements: 12.1, 12.2, 12.4, 12.5, 12.6_
  
  - [ ]* 20.3 Write component tests for Revenue Insights page
    - Test table renders with data
    - Test sorting functionality
    - Test filtering functionality
    - Test pagination
    - Test bar chart visualization
    - _Requirements: 12.4, 12.5, 12.6_

- [x] 21. Checkpoint - Ensure all frontend tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 22. Integration and wiring
  - [x] 22.1 Register analytics router in main.py
    - Update `app/main.py`
    - Import and include analytics router: app.include_router(analytics.router, prefix="/api/v1")
    - Ensure RBAC middleware is applied
    - _Requirements: 20.4, 20.5_
  
  - [x] 22.2 Add Redis configuration
    - Update `app/config.py`
    - Add REDIS_URL configuration variable
    - Initialize Redis client in database.py or cache_service.py
    - _Requirements: 15.4_
  
  - [x] 22.3 Update API client types
    - Update `dashboard/src/types/api.ts`
    - Add TypeScript interfaces for all analytics response models: OverviewResponse, CreatorIntelligenceItem, ContentItem, ProductItem, RevenueInsightItem
    - _Requirements: 18.1, 18.5_
  
  - [ ]* 22.4 Write integration tests for complete workflows
    - Test end-to-end: create data → query all endpoints → verify results
    - Test cache integration: query twice, verify cache hit
    - Test error handling: invalid inputs, database errors, cache failures
    - _Requirements: 15.4, 16.1, 16.2, 16.4, 16.5_

- [x] 23. Performance optimization and final validation
  - [x] 23.1 Verify database indexes are used
    - Run EXPLAIN ANALYZE on all analytics queries
    - Ensure indexes on creator_id, product_id, posted_at, gmv_generated are utilized
    - _Requirements: 15.1, 15.2_
  
  - [x] 23.2 Performance test all endpoints
    - Test overview endpoint with 100k videos (must respond < 3 seconds)
    - Test all endpoints with pagination and filtering
    - Verify cache reduces response time
    - _Requirements: 3.4, 15.4_
  
  - [ ]* 23.3 Write property test for date range filtering
    - **Property 21: Date Range Filtering**
    - **Validates: Requirements 15.3**
  
  - [x] 23.4 Verify empty dataset handling
    - Test all endpoints with empty database
    - Verify no errors, proper default values returned
    - _Requirements: 17.1, 17.2, 17.3, 17.4_

- [x] 24. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples, edge cases, and integration points
- Backend uses Python with FastAPI, SQLAlchemy, Redis, and Hypothesis for property testing
- Frontend uses TypeScript with Next.js, React, and Vitest for testing
- All analytics endpoints use consistent response format with caching layer
- Database migrations are incremental and reversible
