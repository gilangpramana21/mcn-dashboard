-- Migration 012: Message learning - track which message variations get replies

-- Add tracking columns to message_templates
ALTER TABLE message_templates
    ADD COLUMN IF NOT EXISTS send_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reply_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS reply_rate FLOAT DEFAULT 0.0;

-- Message variations table - multiple versions of same template
CREATE TABLE IF NOT EXISTS message_variations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES message_templates(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    send_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    reply_rate FLOAT DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track which variation was used per message
ALTER TABLE message_history
    ADD COLUMN IF NOT EXISTS variation_id UUID REFERENCES message_variations(id);

GRANT ALL ON message_variations TO mcn_user;
