-- Migration 018: Performance indexes untuk query-query berat

-- incoming_messages: query by affiliate_name (conversations, history)
CREATE INDEX IF NOT EXISTS idx_incoming_messages_affiliate_name
    ON incoming_messages(affiliate_name);

-- incoming_messages: query unread count
CREATE INDEX IF NOT EXISTS idx_incoming_messages_unread
    ON incoming_messages(is_read) WHERE is_read = FALSE;

-- message_history: query by affiliate_name
CREATE INDEX IF NOT EXISTS idx_message_history_affiliate_name
    ON message_history(affiliate_name);

-- message_history: query by sent_at (conversations sort)
CREATE INDEX IF NOT EXISTS idx_message_history_sent_at_desc
    ON message_history(sent_at DESC);

-- influencers: query by name (conversations N+1 fix)
CREATE INDEX IF NOT EXISTS idx_influencers_name
    ON influencers(name);

-- influencers: query by status (active count)
CREATE INDEX IF NOT EXISTS idx_influencers_status
    ON influencers(status) WHERE status = 'ACTIVE';

-- content_videos: query by creator_id (analytics)
CREATE INDEX IF NOT EXISTS idx_content_videos_creator_id
    ON content_videos(creator_id);

-- content_videos: query by product_id (analytics)
CREATE INDEX IF NOT EXISTS idx_content_videos_product_id
    ON content_videos(product_id);

-- content_videos: query by posted_at (trend)
CREATE INDEX IF NOT EXISTS idx_content_videos_posted_at
    ON content_videos(posted_at DESC);
