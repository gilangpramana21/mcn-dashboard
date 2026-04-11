-- Migration 015: Monthly Reports per brand

CREATE TABLE IF NOT EXISTS monthly_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    batch_name VARCHAR(100) NOT NULL,       -- e.g. "Batch 5"
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    -- Key Metrics (auto-calculated, can be overridden)
    total_deal INTEGER DEFAULT 0,
    total_uploaded INTEGER DEFAULT 0,
    total_not_uploaded INTEGER DEFAULT 0,
    total_videos INTEGER DEFAULT 0,
    total_generate_sales INTEGER DEFAULT 0,
    gmv_current BIGINT DEFAULT 0,
    gmv_previous BIGINT DEFAULT 0,
    gmv_video BIGINT DEFAULT 0,
    gmv_live BIGINT DEFAULT 0,
    total_products_sold INTEGER DEFAULT 0,
    total_orders_settled INTEGER DEFAULT 0,

    -- AI-generated insights (editable)
    insight_key_metrics TEXT,
    insight_affiliate TEXT,
    insight_funnel TEXT,
    insight_gmv TEXT,
    insight_product TEXT,
    insight_gap TEXT,
    insight_strategic TEXT,
    next_plan TEXT,
    kesimpulan TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monthly_reports_brand_id ON monthly_reports(brand_id);
CREATE INDEX IF NOT EXISTS idx_monthly_reports_period ON monthly_reports(period_start, period_end);
