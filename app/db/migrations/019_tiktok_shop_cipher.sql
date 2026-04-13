-- Migration 019: Tambah shop_cipher ke tiktok_shop_tokens
ALTER TABLE tiktok_shop_tokens ADD COLUMN IF NOT EXISTS shop_cipher TEXT;
