-- Migration 011: TikTok Shop tokens table
CREATE TABLE IF NOT EXISTS tiktok_shop_tokens (
    id SERIAL PRIMARY KEY,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    shop_id VARCHAR(255),
    shop_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
