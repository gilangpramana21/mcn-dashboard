-- =============================================================================
-- Migration 001: Initial schema
-- TikTok Influencer Marketing Agent
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- users
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username                VARCHAR(100) NOT NULL UNIQUE,
    password_hash           TEXT NOT NULL,
    role                    VARCHAR(50) NOT NULL,
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts   INT NOT NULL DEFAULT 0,
    locked_until            TIMESTAMPTZ,
    last_activity_at        TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- selection_criteria
-- =============================================================================
CREATE TABLE IF NOT EXISTS selection_criteria (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    min_followers           INT,
    max_followers           INT,
    min_engagement_rate     NUMERIC(5, 4),
    content_categories      TEXT[],
    locations               TEXT[],
    weight_follower_count   NUMERIC(4, 3) NOT NULL DEFAULT 0.3,
    weight_engagement_rate  NUMERIC(4, 3) NOT NULL DEFAULT 0.4,
    weight_category_match   NUMERIC(4, 3) NOT NULL DEFAULT 0.2,
    weight_location_match   NUMERIC(4, 3) NOT NULL DEFAULT 0.1,
    is_template             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- campaigns
-- =============================================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                            VARCHAR(255) NOT NULL,
    description                     TEXT NOT NULL DEFAULT '',
    status                          VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    selection_criteria_id           UUID REFERENCES selection_criteria(id),
    template_id                     UUID,
    start_date                      TIMESTAMPTZ NOT NULL,
    end_date                        TIMESTAMPTZ NOT NULL,
    created_by                      UUID NOT NULL REFERENCES users(id),
    max_invitations_per_minute      INT NOT NULL DEFAULT 100,
    monitoring_interval_minutes     INT NOT NULL DEFAULT 30,
    compliance_check_enabled        BOOLEAN NOT NULL DEFAULT TRUE,
    alert_thresholds                JSONB NOT NULL DEFAULT '{}',
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- influencers
-- =============================================================================
CREATE TABLE IF NOT EXISTS influencers (
    id                      VARCHAR(255) PRIMARY KEY,   -- ID from Affiliate Center
    tiktok_user_id          VARCHAR(255) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    phone_number            VARCHAR(20),
    follower_count          INT NOT NULL DEFAULT 0,
    engagement_rate         NUMERIC(6, 5) NOT NULL DEFAULT 0,
    content_categories      TEXT[] NOT NULL DEFAULT '{}',
    location                VARCHAR(255) NOT NULL DEFAULT '',
    relevance_score         NUMERIC(4, 3),
    status                  VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    blacklisted             BOOLEAN NOT NULL DEFAULT FALSE,
    blacklist_reason        TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- blacklist
-- =============================================================================
CREATE TABLE IF NOT EXISTS blacklist (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    influencer_id       VARCHAR(255) NOT NULL REFERENCES influencers(id),
    reason              TEXT NOT NULL,
    added_by            UUID NOT NULL REFERENCES users(id),
    removed_by          UUID REFERENCES users(id),
    removal_reason      TEXT,
    added_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    removed_at          TIMESTAMPTZ
);

-- =============================================================================
-- message_templates
-- =============================================================================
CREATE TABLE IF NOT EXISTS message_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    content         TEXT NOT NULL,
    variables       TEXT[] NOT NULL DEFAULT '{}',
    default_values  JSONB NOT NULL DEFAULT '{}',
    version         INT NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    campaign_ids    UUID[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- template_versions  (version history)
-- =============================================================================
CREATE TABLE IF NOT EXISTS template_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID NOT NULL REFERENCES message_templates(id),
    version         INT NOT NULL,
    content         TEXT NOT NULL,
    variables       TEXT[] NOT NULL DEFAULT '{}',
    default_values  JSONB NOT NULL DEFAULT '{}',
    saved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- invitations
-- =============================================================================
CREATE TABLE IF NOT EXISTS invitations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             UUID NOT NULL REFERENCES campaigns(id),
    influencer_id           VARCHAR(255) NOT NULL REFERENCES influencers(id),
    template_id             UUID NOT NULL REFERENCES message_templates(id),
    message_content         TEXT NOT NULL,
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    sent_at                 TIMESTAMPTZ,
    scheduled_at            TIMESTAMPTZ,
    error_message           TEXT,
    whatsapp_message_id     VARCHAR(255),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- content_metrics
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_metrics (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id                 UUID NOT NULL REFERENCES campaigns(id),
    influencer_id               VARCHAR(255) NOT NULL REFERENCES influencers(id),
    tiktok_video_id             VARCHAR(255) NOT NULL,
    views                       BIGINT NOT NULL DEFAULT 0,
    likes                       BIGINT NOT NULL DEFAULT 0,
    comments                    BIGINT NOT NULL DEFAULT 0,
    shares                      BIGINT NOT NULL DEFAULT 0,
    has_valid_affiliate_link    BOOLEAN NOT NULL DEFAULT FALSE,
    gmv_generated               NUMERIC(18, 2) NOT NULL DEFAULT 0,
    conversion_rate             NUMERIC(6, 5) NOT NULL DEFAULT 0,
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_compliant                BOOLEAN NOT NULL DEFAULT TRUE
);

-- =============================================================================
-- influencer_feedback
-- =============================================================================
CREATE TABLE IF NOT EXISTS influencer_feedback (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id             UUID NOT NULL REFERENCES campaigns(id),
    influencer_id           VARCHAR(255) NOT NULL REFERENCES influencers(id),
    invitation_id           UUID NOT NULL REFERENCES invitations(id),
    raw_message             TEXT NOT NULL,
    classification          VARCHAR(60),
    confidence_score        NUMERIC(4, 3),
    requires_manual_review  BOOLEAN NOT NULL DEFAULT FALSE,
    classified_at           TIMESTAMPTZ,
    received_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- audit_logs
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    action          VARCHAR(100) NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     VARCHAR(255),
    details         JSONB NOT NULL DEFAULT '{}',
    ip_address      VARCHAR(45),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- whatsapp_collection_records
-- =============================================================================
CREATE TABLE IF NOT EXISTS whatsapp_collection_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    affiliate_id        VARCHAR(255) NOT NULL,
    influencer_id       VARCHAR(255) NOT NULL REFERENCES influencers(id),
    phone_number        VARCHAR(20),
    method              VARCHAR(20),
    status              VARCHAR(20) NOT NULL DEFAULT 'pending_chat',
    chat_message_id     VARCHAR(255),
    raw_extracted       TEXT,
    collected_at        TIMESTAMPTZ,
    chat_sent_at        TIMESTAMPTZ,
    timeout_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- campaign_outcomes  (for Learning Engine)
-- =============================================================================
CREATE TABLE IF NOT EXISTS campaign_outcomes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id         UUID NOT NULL REFERENCES campaigns(id),
    influencer_id       VARCHAR(255) NOT NULL REFERENCES influencers(id),
    accepted            BOOLEAN NOT NULL DEFAULT FALSE,
    gmv_generated       NUMERIC(18, 2) NOT NULL DEFAULT 0,
    conversion_rate     NUMERIC(6, 5) NOT NULL DEFAULT 0,
    content_count       INT NOT NULL DEFAULT 0,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================================
-- model_versions  (for Learning Engine)
-- =============================================================================
CREATE TABLE IF NOT EXISTS model_versions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_type              VARCHAR(20) NOT NULL,
    version                 INT NOT NULL,
    accuracy_before         NUMERIC(5, 4),
    accuracy_after          NUMERIC(5, 4) NOT NULL,
    trained_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    training_data_size      INT NOT NULL DEFAULT 0,
    UNIQUE (model_type, version)
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_campaigns_status
    ON campaigns(status);

CREATE INDEX IF NOT EXISTS idx_campaigns_created_by
    ON campaigns(created_by);

CREATE INDEX IF NOT EXISTS idx_influencers_status
    ON influencers(status);

CREATE INDEX IF NOT EXISTS idx_influencers_blacklisted
    ON influencers(blacklisted);

CREATE INDEX IF NOT EXISTS idx_invitations_campaign_id
    ON invitations(campaign_id);

CREATE INDEX IF NOT EXISTS idx_invitations_influencer_id
    ON invitations(influencer_id);

CREATE INDEX IF NOT EXISTS idx_invitations_status
    ON invitations(status);

CREATE INDEX IF NOT EXISTS idx_content_metrics_campaign_influencer
    ON content_metrics(campaign_id, influencer_id);

CREATE INDEX IF NOT EXISTS idx_content_metrics_recorded_at
    ON content_metrics(recorded_at);

CREATE INDEX IF NOT EXISTS idx_feedback_campaign_id
    ON influencer_feedback(campaign_id);

CREATE INDEX IF NOT EXISTS idx_feedback_influencer_id
    ON influencer_feedback(influencer_id);

CREATE INDEX IF NOT EXISTS idx_feedback_requires_review
    ON influencer_feedback(requires_manual_review)
    WHERE requires_manual_review = TRUE;

CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id
    ON audit_logs(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_audit_logs_resource
    ON audit_logs(resource_type, resource_id);

CREATE INDEX IF NOT EXISTS idx_wa_collection_affiliate
    ON whatsapp_collection_records(affiliate_id);

CREATE INDEX IF NOT EXISTS idx_wa_collection_status
    ON whatsapp_collection_records(status);

CREATE INDEX IF NOT EXISTS idx_wa_collection_influencer
    ON whatsapp_collection_records(influencer_id);

CREATE INDEX IF NOT EXISTS idx_campaign_outcomes_influencer
    ON campaign_outcomes(influencer_id);

CREATE INDEX IF NOT EXISTS idx_campaign_outcomes_campaign
    ON campaign_outcomes(campaign_id);

CREATE INDEX IF NOT EXISTS idx_model_versions_type_version
    ON model_versions(model_type, version);

CREATE INDEX IF NOT EXISTS idx_blacklist_influencer
    ON blacklist(influencer_id);

CREATE INDEX IF NOT EXISTS idx_template_versions_template
    ON template_versions(template_id, version);
