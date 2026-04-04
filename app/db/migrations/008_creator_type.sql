-- Migration 008: Add creator_type column to influencers table
-- creator_type: influencer | affiliator | hybrid

ALTER TABLE influencers
ADD COLUMN IF NOT EXISTS creator_type VARCHAR(20) DEFAULT 'influencer';

-- Set default values based on existing data
UPDATE influencers SET creator_type = 'influencer' WHERE creator_type IS NULL;

-- Add index for filtering
CREATE INDEX IF NOT EXISTS idx_influencers_creator_type ON influencers(creator_type);
