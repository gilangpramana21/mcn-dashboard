-- Migration 002: Extended influencer fields for advanced filtering
-- Tambah kolom untuk kategori pengiriman, metode penjualan, dan status undangan

ALTER TABLE influencers
    ADD COLUMN IF NOT EXISTS delivery_categories TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS sales_methods       TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS has_whatsapp        BOOLEAN NOT NULL DEFAULT FALSE;

-- Update has_whatsapp berdasarkan phone_number yang sudah ada
UPDATE influencers SET has_whatsapp = TRUE WHERE phone_number IS NOT NULL AND phone_number != '';

-- Index untuk filter baru
CREATE INDEX IF NOT EXISTS idx_influencers_has_whatsapp ON influencers(has_whatsapp);
CREATE INDEX IF NOT EXISTS idx_influencers_name ON influencers(name);
