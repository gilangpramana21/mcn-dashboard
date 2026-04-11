-- Migration 016: Incoming messages (pesan masuk dari affiliate)

CREATE TABLE IF NOT EXISTS incoming_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id VARCHAR(255),              -- tidak pakai FK karena tipe berbeda
    affiliate_name VARCHAR(255),
    channel VARCHAR(50) NOT NULL,           -- 'whatsapp' | 'tiktok_seller'
    message_content TEXT NOT NULL,
    from_number VARCHAR(100),
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMPTZ,
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_incoming_messages_is_read ON incoming_messages(is_read);
CREATE INDEX IF NOT EXISTS idx_incoming_messages_received_at ON incoming_messages(received_at DESC);
