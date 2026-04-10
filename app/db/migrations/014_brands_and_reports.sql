-- Migration 014: Brands, Brand SKUs, dan kolom tambahan untuk report system

-- Tabel brands (Master Brand - Excel 3)
CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    wa_number VARCHAR(50),           -- No WA yang dipakai untuk brand ini
    sow TEXT,                        -- Statement of Work (sistem, minimal GMV, kategori, dll)
    message_template TEXT,           -- Template pesan WA untuk brand ini
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tabel brand_skus (SKU per brand, bisa lebih dari 1)
CREATE TABLE IF NOT EXISTS brand_skus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    affiliate_link TEXT,
    price BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tambah kolom baru ke tabel influencers untuk tracking outreach (Excel 1)
ALTER TABLE influencers
    ADD COLUMN IF NOT EXISTS pic VARCHAR(100),
    ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES brands(id),
    ADD COLUMN IF NOT EXISTS avg_gmv_per_month BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gmv_per_buyer BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS update_status VARCHAR(100),
    ADD COLUMN IF NOT EXISTS respon_status VARCHAR(100),
    ADD COLUMN IF NOT EXISTS speed_status VARCHAR(50),
    ADD COLUMN IF NOT EXISTS result_status VARCHAR(50),
    ADD COLUMN IF NOT EXISTS sampel_gratis VARCHAR(50),
    ADD COLUMN IF NOT EXISTS note TEXT,
    ADD COLUMN IF NOT EXISTS id_pesanan VARCHAR(100),
    ADD COLUMN IF NOT EXISTS no_va_co_sampel VARCHAR(100),
    ADD COLUMN IF NOT EXISTS status_payment_sampel VARCHAR(100),
    ADD COLUMN IF NOT EXISTS gmv_week1_after_join BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gmv_week2_after_join BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gmv_week3_after_join BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gmv_week4_after_join BIGINT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS gmv_perbulan_after_join BIGINT DEFAULT 0;

-- Tabel deal_records (Excel 2 - Database Deal per brand)
CREATE TABLE IF NOT EXISTS deal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id UUID REFERENCES influencers(id),
    brand_id UUID REFERENCES brands(id),
    tanggal DATE DEFAULT CURRENT_DATE,
    username VARCHAR(255),
    link_acc TEXT,
    follower_count INTEGER DEFAULT 0,
    contact_wa VARCHAR(50),
    pic VARCHAR(100),
    avg_gmv_per_month BIGINT DEFAULT 0,
    gmv_per_buyer BIGINT DEFAULT 0,
    update_status VARCHAR(100),
    respon_status VARCHAR(100),
    speed_status VARCHAR(50),
    result_status VARCHAR(50),
    status_sempel VARCHAR(100),
    link_video TEXT,
    total_vt INTEGER DEFAULT 0,
    note_deal TEXT,
    note_dari_rara TEXT,
    id_pesanan VARCHAR(100),
    no_va_co_sampel VARCHAR(100),
    status_payment_sampel VARCHAR(100),
    gmv_week1_after_join BIGINT DEFAULT 0,
    gmv_week2_after_join BIGINT DEFAULT 0,
    gmv_week3_after_join BIGINT DEFAULT 0,
    gmv_week4_after_join BIGINT DEFAULT 0,
    gmv_perbulan_after_join BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index untuk performa query
CREATE INDEX IF NOT EXISTS idx_deal_records_brand_id ON deal_records(brand_id);
CREATE INDEX IF NOT EXISTS idx_deal_records_affiliate_id ON deal_records(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_influencers_brand_id ON influencers(brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_skus_brand_id ON brand_skus(brand_id);
