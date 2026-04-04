"""Seed template dengan wa_category."""
import asyncio
import uuid
import json
from sqlalchemy import text
from app.database import AsyncSessionFactory

TEMPLATES = [
    {
        "name": "Undangan Kampanye Skincare",
        "content": "Halo {{nama_influencer}}!\n\nKami dari MCN mengundang kamu untuk kampanye produk skincare premium kami.\n\nProduk: {{produk}}\nKomisi: {{komisi}}% per penjualan\nMulai: {{tanggal_mulai}}\n\nTertarik? Balas pesan ini ya!",
        "wa_category": "Skincare",
        "defaults": {"nama_influencer": "Kak", "produk": "Serum Vitamin C", "komisi": "15", "tanggal_mulai": "Minggu depan"},
    },
    {
        "name": "Undangan Kampanye FnB",
        "content": "Halo {{nama_influencer}}!\n\nAda penawaran kolaborasi seru untuk konten kuliner kamu!\n\nProduk: {{produk}}\nKomisi: {{komisi}}% per penjualan\nTarget: 3-5 video/bulan\n\nMinat? Hubungi kami!",
        "wa_category": "FnB",
        "defaults": {"nama_influencer": "Kak", "produk": "Minuman Herbal", "komisi": "12"},
    },
    {
        "name": "Undangan Kampanye Fashion",
        "content": "Hi {{nama_influencer}}!\n\nKami punya koleksi fashion terbaru yang cocok banget sama style kamu!\n\nBrand: {{brand}}\nKomisi: {{komisi}}% + free produk\nKampanye: {{nama_kampanye}}\n\nDeal?",
        "wa_category": "Fashion",
        "defaults": {"nama_influencer": "Kak", "brand": "Brand Fashion", "komisi": "18", "nama_kampanye": "Summer Collection"},
    },
    {
        "name": "Undangan Kampanye Olahraga",
        "content": "Hi {{nama_influencer}}!\n\nAda brand suplemen olahraga yang cocok banget sama konten fitness kamu!\n\nProduk: {{produk}}\nKomisi: {{komisi}}%\nBonus: Sample pack gratis\n\nTertarik?",
        "wa_category": "Olahraga",
        "defaults": {"nama_influencer": "Kak", "produk": "Protein Shake", "komisi": "20"},
    },
]

async def seed():
    async with AsyncSessionFactory() as db:
        count = 0
        for t in TEMPLATES:
            await db.execute(text("""
                INSERT INTO message_templates
                    (id, name, content, default_values, wa_category, message_type, channel, version, is_active)
                VALUES
                    (:id, :name, :content, cast(:defaults as jsonb), :wa_cat, 'campaign_invitation', 'whatsapp', 1, TRUE)
                ON CONFLICT DO NOTHING
            """), {
                "id": str(uuid.uuid4()),
                "name": t["name"],
                "content": t["content"],
                "defaults": json.dumps(t["defaults"]),
                "wa_cat": t["wa_category"],
            })
            count += 1
        await db.commit()
        print(f"Seeded {count} category-specific templates.")

asyncio.run(seed())
