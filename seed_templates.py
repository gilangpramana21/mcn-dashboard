"""Tambah template pesan default dengan berbagai jenis."""
import asyncio
import uuid
from datetime import datetime, timezone
from app.database import AsyncSessionFactory
from sqlalchemy import text

async def main():
    async with AsyncSessionFactory() as session:
        now = datetime.now(timezone.utc)
        templates = [
            {
                "id": str(uuid.uuid4()),
                "name": "Minta Nomor WA",
                "content": "Halo {{nama_affiliator}}, saya dari tim {{brand}}. Kami tertarik bekerja sama dengan kamu. Boleh minta nomor WhatsApp kamu untuk diskusi lebih lanjut?",
                "variables": ["nama_affiliator", "brand"],
                "default_values": '{"nama_affiliator": "Kreator", "brand": "Brand Kami"}',
                "message_type": "request_whatsapp",
                "channel": "tiktok_chat",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Follow-up Undangan",
                "content": "Halo {{nama_influencer}}, sebelumnya kami sudah mengirimkan undangan kampanye {{nama_kampanye}}. Apakah kamu sudah sempat melihatnya? Kami sangat berharap bisa bekerja sama!",
                "variables": ["nama_influencer", "nama_kampanye"],
                "default_values": '{"nama_influencer": "Kreator", "nama_kampanye": "Kampanye Kami"}',
                "message_type": "followup",
                "channel": "whatsapp",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Brief Produk",
                "content": "Halo {{nama_influencer}}! Terima kasih sudah bergabung. Berikut brief untuk kampanye {{nama_kampanye}}:\n\nProduk: {{nama_produk}}\nTarget konten: {{target_konten}}\nDeadline: {{deadline}}\n\nAda pertanyaan?",
                "variables": ["nama_influencer", "nama_kampanye", "nama_produk", "target_konten", "deadline"],
                "default_values": '{"nama_influencer": "Kreator", "nama_kampanye": "Kampanye", "nama_produk": "Produk", "target_konten": "1 video", "deadline": "7 hari"}',
                "message_type": "product_brief",
                "channel": "whatsapp",
            },
            {
                "id": str(uuid.uuid4()),
                "name": "Pengumuman Kampanye Baru",
                "content": "Halo semua! Kami dengan senang hati mengumumkan kampanye baru: {{nama_kampanye}}. Komisi: {{komisi}}. Daftar sekarang sebelum {{deadline}}!",
                "variables": ["nama_kampanye", "komisi", "deadline"],
                "default_values": '{"nama_kampanye": "Kampanye Baru", "komisi": "10%", "deadline": "7 hari lagi"}',
                "message_type": "broadcast",
                "channel": "whatsapp",
            },
        ]

        for t in templates:
            await session.execute(text("""
                INSERT INTO message_templates (id, name, content, variables, default_values,
                    version, is_active, campaign_ids, message_type, channel, created_at, updated_at)
                VALUES (:id, :name, :content, :variables, CAST(:default_values AS jsonb),
                    1, TRUE, '{}', :message_type, :channel, :now, :now)
                ON CONFLICT DO NOTHING
            """), {**t, "now": now})

        await session.commit()
        print(f"✓ {len(templates)} template berhasil ditambahkan!")

asyncio.run(main())
