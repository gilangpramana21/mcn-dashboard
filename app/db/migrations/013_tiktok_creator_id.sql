-- Migration 013: Add TikTok Shop creator ID and data source tracking
-- Required for TikTok Shop Partner Center Go Live Review compliance.
-- Reviewers need to verify that creator data is synchronized from TikTok Shop
-- by seeing the official creator_id from TikTok Shop API in the system.

ALTER TABLE influencers
    ADD COLUMN IF NOT EXISTS tiktok_creator_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS data_source       VARCHAR(50)  NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS tiktok_synced_at  TIMESTAMPTZ;

-- tiktok_creator_id: official creator_id from TikTok Shop Affiliate Creator Search API
-- data_source: 'tiktok_shop_search' | 'manual' | 'affiliate_center'
-- tiktok_synced_at: timestamp when this record was last synced from TikTok Shop

COMMENT ON COLUMN influencers.tiktok_creator_id IS 'Official creator_id from TikTok Shop Affiliate Creator Search API';
COMMENT ON COLUMN influencers.data_source       IS 'Origin of this record: tiktok_shop_search | manual | affiliate_center';
COMMENT ON COLUMN influencers.tiktok_synced_at  IS 'Timestamp of last sync from TikTok Shop API';

CREATE INDEX IF NOT EXISTS idx_influencers_tiktok_creator_id
    ON influencers(tiktok_creator_id)
    WHERE tiktok_creator_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_influencers_data_source
    ON influencers(data_source);
