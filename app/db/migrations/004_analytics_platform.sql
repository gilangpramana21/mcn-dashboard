-- Migration 004: Analytics Platform — Products + Content Videos

-- ── Products ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tiktok_product_id   VARCHAR(255) UNIQUE,
    name                VARCHAR(500) NOT NULL,
    price               NUMERIC(18, 2) NOT NULL DEFAULT 0,
    category            VARCHAR(100),
    image_url           TEXT,
    shop_name           VARCHAR(255),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);

-- ── Content Videos ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS content_videos (
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

CREATE INDEX IF NOT EXISTS idx_content_videos_creator ON content_videos(creator_id);
CREATE INDEX IF NOT EXISTS idx_content_videos_product ON content_videos(product_id);
CREATE INDEX IF NOT EXISTS idx_content_videos_posted ON content_videos(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_videos_gmv ON content_videos(gmv_generated DESC);

-- ── Creator role column ───────────────────────────────────────────────────────
ALTER TABLE influencers
    ADD COLUMN IF NOT EXISTS creator_role VARCHAR(20) NOT NULL DEFAULT 'influencer',
    ADD COLUMN IF NOT EXISTS creator_score NUMERIC(10, 4) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS estimated_revenue NUMERIC(18, 2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS avg_views BIGINT NOT NULL DEFAULT 0;

-- creator_role: influencer | affiliator | hybrid

CREATE INDEX IF NOT EXISTS idx_influencers_creator_role ON influencers(creator_role);
CREATE INDEX IF NOT EXISTS idx_influencers_creator_score ON influencers(creator_score DESC);
