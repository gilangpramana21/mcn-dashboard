-- =============================================================================
-- Migration 006: Analytics Content Videos Table
-- TikTok Influencer Marketing Agent - Analytics Platform
-- =============================================================================

-- Enable UUID generation (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- content_videos
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_videos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tiktok_video_id VARCHAR(255) UNIQUE NOT NULL,
    creator_id      VARCHAR(255) NOT NULL REFERENCES influencers(id),
    product_id      UUID REFERENCES products(id) ON DELETE SET NULL,
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

-- =============================================================================
-- Indexes
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_content_videos_creator ON content_videos(creator_id);
CREATE INDEX IF NOT EXISTS idx_content_videos_product ON content_videos(product_id);
CREATE INDEX IF NOT EXISTS idx_content_videos_posted ON content_videos(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_videos_gmv ON content_videos(gmv_generated DESC);

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE content_videos IS 'TikTok video content created by influencers to promote products';
COMMENT ON COLUMN content_videos.id IS 'Internal UUID primary key';
COMMENT ON COLUMN content_videos.tiktok_video_id IS 'Unique identifier from TikTok platform';
COMMENT ON COLUMN content_videos.creator_id IS 'Foreign key to influencers table';
COMMENT ON COLUMN content_videos.product_id IS 'Foreign key to products table (nullable for non-product content)';
COMMENT ON COLUMN content_videos.title IS 'Video title/caption';
COMMENT ON COLUMN content_videos.views IS 'Total view count';
COMMENT ON COLUMN content_videos.likes IS 'Total like count';
COMMENT ON COLUMN content_videos.comments IS 'Total comment count';
COMMENT ON COLUMN content_videos.shares IS 'Total share count';
COMMENT ON COLUMN content_videos.gmv_generated IS 'Gross Merchandise Value in Rupiah generated from this video';
COMMENT ON COLUMN content_videos.buyers IS 'Number of unique buyers from this video';
COMMENT ON COLUMN content_videos.posted_at IS 'Timestamp when video was posted on TikTok';
COMMENT ON COLUMN content_videos.created_at IS 'Timestamp when record was created in database';
