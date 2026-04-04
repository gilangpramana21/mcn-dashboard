-- =============================================================================
-- Migration 005: Analytics Products Table
-- TikTok Influencer Marketing Agent - Analytics Platform
-- =============================================================================

-- Enable UUID generation (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- products
-- =============================================================================
CREATE TABLE IF NOT EXISTS products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tiktok_product_id   VARCHAR(255) UNIQUE NOT NULL,
    name                VARCHAR(500) NOT NULL,
    price               NUMERIC(18, 2) NOT NULL DEFAULT 0,
    category            VARCHAR(100),
    image_url           TEXT,
    shop_name           VARCHAR(255),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- Indexes
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);

-- =============================================================================
-- Constraints
-- =============================================================================
-- Unique constraint on tiktok_product_id (already enforced by UNIQUE in column definition)
-- This ensures no duplicate products from TikTok platform

-- =============================================================================
-- Comments
-- =============================================================================
COMMENT ON TABLE products IS 'Products promoted through influencer marketing campaigns';
COMMENT ON COLUMN products.id IS 'Internal UUID primary key';
COMMENT ON COLUMN products.tiktok_product_id IS 'Unique identifier from TikTok platform';
COMMENT ON COLUMN products.name IS 'Product name';
COMMENT ON COLUMN products.price IS 'Product price in Rupiah (18 digits, 2 decimal places)';
COMMENT ON COLUMN products.category IS 'Product category for filtering and grouping';
COMMENT ON COLUMN products.image_url IS 'URL to product image';
COMMENT ON COLUMN products.shop_name IS 'Name of the shop selling the product';
COMMENT ON COLUMN products.is_active IS 'Soft delete flag for product lifecycle management';
COMMENT ON COLUMN products.created_at IS 'Timestamp when product was created';
COMMENT ON COLUMN products.updated_at IS 'Timestamp when product was last updated';
