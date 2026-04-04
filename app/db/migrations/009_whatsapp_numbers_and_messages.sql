-- Migration 009: WhatsApp numbers per category + message history

-- Tabel nomor WhatsApp per kategori
CREATE TABLE IF NOT EXISTS whatsapp_numbers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100) NOT NULL,          -- e.g. 'FnB', 'Fashion', 'Skincare'
    phone_number VARCHAR(20) NOT NULL,        -- e.g. '+628123456789'
    phone_number_id VARCHAR(50),             -- Meta's phone_number_id (dari dashboard Meta)
    waba_id VARCHAR(50),                     -- WhatsApp Business Account ID
    display_name VARCHAR(100),               -- e.g. 'WA FnB Team'
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_wa_numbers_category ON whatsapp_numbers(category) WHERE is_active = TRUE;

-- Tabel history pesan
CREATE TABLE IF NOT EXISTS message_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id VARCHAR(50) NOT NULL REFERENCES influencers(id) ON DELETE CASCADE,
    affiliate_name VARCHAR(200),
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('outbound', 'inbound')),
    message_content TEXT NOT NULL,
    wa_number_id UUID REFERENCES whatsapp_numbers(id) ON DELETE SET NULL,
    from_number VARCHAR(20),
    to_number VARCHAR(20),
    status VARCHAR(20) DEFAULT 'sent' CHECK (status IN ('sent', 'delivered', 'read', 'failed')),
    template_id UUID,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_msg_history_affiliate ON message_history(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_msg_history_sent_at ON message_history(sent_at DESC);

-- Seed nomor WA default per kategori
INSERT INTO whatsapp_numbers (category, phone_number, display_name) VALUES
    ('FnB', '+6281100000001', 'WA Tim FnB'),
    ('Fashion', '+6281100000002', 'WA Tim Fashion'),
    ('Skincare', '+6281100000003', 'WA Tim Skincare'),
    ('Elektronik', '+6281100000004', 'WA Tim Elektronik'),
    ('Olahraga', '+6281100000005', 'WA Tim Olahraga'),
    ('Umum', '+6281100000000', 'WA Tim Umum')
ON CONFLICT DO NOTHING;
