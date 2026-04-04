-- Migration 010: Tambah wa_category ke message_templates
-- Setiap template bisa di-assign ke kategori WA tertentu (FnB, Fashion, dll)
-- NULL berarti template berlaku untuk semua kategori

ALTER TABLE message_templates
    ADD COLUMN IF NOT EXISTS wa_category VARCHAR(100) DEFAULT NULL;

COMMENT ON COLUMN message_templates.wa_category IS 
    'Kategori WA yang menggunakan template ini (FnB, Fashion, Skincare, dll). NULL = semua kategori.';

CREATE INDEX IF NOT EXISTS idx_templates_wa_category ON message_templates(wa_category);
