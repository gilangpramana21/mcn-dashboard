-- Migration 003: Tambah message_type dan channel ke message_templates

ALTER TABLE message_templates
    ADD COLUMN IF NOT EXISTS message_type VARCHAR(50) NOT NULL DEFAULT 'campaign_invitation',
    ADD COLUMN IF NOT EXISTS channel      VARCHAR(20) NOT NULL DEFAULT 'whatsapp';

-- message_type values:
--   campaign_invitation  - Undangan bergabung kampanye (via WhatsApp)
--   request_whatsapp     - Minta nomor WA (via TikTok Seller Center chat)
--   followup             - Follow-up untuk yang belum merespons (via WhatsApp)
--   product_brief        - Kirim brief/detail produk (via WhatsApp)
--   broadcast            - Pengumuman umum (via WhatsApp)
--   custom               - Pesan kustom bebas

-- channel values:
--   whatsapp             - Dikirim via WhatsApp API
--   tiktok_chat          - Dikirim via TikTok Seller Center chat

CREATE INDEX IF NOT EXISTS idx_templates_message_type ON message_templates(message_type);
