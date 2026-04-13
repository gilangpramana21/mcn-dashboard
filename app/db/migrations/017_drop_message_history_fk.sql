-- Migration 017: Drop FK constraint on message_history.affiliate_id
-- Agar bisa menyimpan pesan untuk affiliate yang tidak ada di tabel influencers
-- (misal dari simulasi atau pesan masuk tanpa affiliate terdaftar)

ALTER TABLE message_history DROP CONSTRAINT IF EXISTS message_history_affiliate_id_fkey;
