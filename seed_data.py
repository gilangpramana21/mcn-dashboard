"""Script untuk mengisi data dummy ke database untuk testing tampilan dashboard."""
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import random

from app.database import AsyncSessionFactory
from sqlalchemy import text


async def main():
    async with AsyncSessionFactory() as session:
        now = datetime.now(timezone.utc)

        # Ambil user admin
        result = await session.execute(text("SELECT id FROM users WHERE username = 'admin' LIMIT 1"))
        admin = result.fetchone()
        if not admin:
            print("✗ User admin tidak ditemukan. Jalankan create_admin.py terlebih dahulu.")
            return
        admin_id = str(admin[0])

        # ── 1. Influencer ──────────────────────────────────────────────────────
        print("Membuat data influencer...")
        influencers = [
            ("inf-001", "tiktok-001", "Sari Cantika", "+6281234567890", 850000, 0.067, ["Kecantikan & Perawatan", "Skincare"], "Jakarta"),
            ("inf-002", "tiktok-002", "Budi Santoso", "+6281234567891", 320000, 0.045, ["Makanan & Minuman", "Kuliner & Resep"], "Surabaya"),
            ("inf-003", "tiktok-003", "Dewi Rahayu", "+6281234567892", 1200000, 0.038, ["Fashion Wanita", "Aksesoris Fashion"], "Bandung"),
            ("inf-004", "tiktok-004", "Andi Pratama", None, 95000, 0.082, ["Gaming", "Teknologi"], "Jakarta"),
            ("inf-005", "tiktok-005", "Rina Kusuma", "+6281234567894", 450000, 0.055, ["Kesehatan & Suplemen", "Olahraga & Outdoor"], "Medan"),
            ("inf-006", "tiktok-006", "Fajar Nugroho", "+6281234567895", 2100000, 0.029, ["Motivasi & Bisnis", "Edukasi"], "Jakarta"),
            ("inf-007", "tiktok-007", "Maya Indah", None, 67000, 0.091, ["Anak & Bayi", "Rumah Tangga"], "Yogyakarta"),
            ("inf-008", "tiktok-008", "Rizky Aditya", "+6281234567897", 180000, 0.063, ["Otomotif", "Elektronik & Gadget"], "Bandung"),
            ("inf-009", "tiktok-009", "Lestari Wulan", "+6281234567898", 560000, 0.048, ["Kecantikan & Perawatan", "Perawatan Rambut"], "Surabaya"),
            ("inf-010", "tiktok-010", "Hendra Wijaya", None, 430000, 0.041, ["Makanan & Minuman", "Travel & Lifestyle"], "Bali"),
        ]

        for inf in influencers:
            inf_id, tiktok_id, name, phone, followers, engagement, categories, location = inf
            has_wa = phone is not None
            await session.execute(text("""
                INSERT INTO influencers (id, tiktok_user_id, name, phone_number, follower_count,
                    engagement_rate, content_categories, location, status, has_whatsapp, created_at, updated_at)
                VALUES (:id, :tiktok_id, :name, :phone, :followers, :engagement,
                    :categories, :location, 'ACTIVE', :has_wa, :now, :now)
                ON CONFLICT (id) DO NOTHING
            """), {
                "id": inf_id, "tiktok_id": tiktok_id, "name": name, "phone": phone,
                "followers": followers, "engagement": engagement,
                "categories": categories, "location": location,
                "has_wa": has_wa, "now": now,
            })

        # ── 2. Selection Criteria ──────────────────────────────────────────────
        print("Membuat kriteria seleksi...")
        criteria_id = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO selection_criteria (id, name, min_followers, min_engagement_rate, created_at, updated_at)
            VALUES (:id, 'Kriteria Standar', 50000, 0.03, :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": criteria_id, "now": now})

        # ── 3. Templates ───────────────────────────────────────────────────────
        print("Membuat template pesan...")
        template_id = str(uuid.uuid4())
        await session.execute(text("""
            INSERT INTO message_templates (id, name, content, variables, default_values, version, is_active, campaign_ids, created_at, updated_at)
            VALUES (:id, 'Template Undangan Standar',
                'Halo {{nama_influencer}}, kami dari {{brand}} ingin mengundang kamu bergabung dalam kampanye {{nama_kampanye}}. Komisi: {{komisi}}. Tertarik?',
                ARRAY['nama_influencer', 'brand', 'nama_kampanye', 'komisi'],
                '{"nama_influencer": "Kreator", "brand": "Brand Kami", "nama_kampanye": "Kampanye Baru", "komisi": "10%"}'::jsonb,
                1, TRUE, ARRAY[]::uuid[], :now, :now)
            ON CONFLICT DO NOTHING
        """), {"id": template_id, "now": now})

        # ── 4. Campaigns ───────────────────────────────────────────────────────
        print("Membuat kampanye...")
        campaigns = [
            (str(uuid.uuid4()), "Kampanye Skincare Q1 2026", "Kampanye produk skincare untuk Q1 2026", "ACTIVE",
             now - timedelta(days=15), now + timedelta(days=45)),
            (str(uuid.uuid4()), "Kampanye Fashion Lebaran", "Koleksi fashion untuk Lebaran 2026", "ACTIVE",
             now - timedelta(days=5), now + timedelta(days=25)),
            (str(uuid.uuid4()), "Kampanye Makanan Sehat", "Promosi produk makanan sehat", "COMPLETED",
             now - timedelta(days=60), now - timedelta(days=10)),
            (str(uuid.uuid4()), "Kampanye Gaming Accessories", "Aksesoris gaming terbaru", "DRAFT",
             now + timedelta(days=10), now + timedelta(days=40)),
            (str(uuid.uuid4()), "Kampanye Suplemen Fitness", "Suplemen olahraga premium", "PAUSED",
             now - timedelta(days=20), now + timedelta(days=10)),
        ]

        campaign_ids = []
        for camp in campaigns:
            camp_id, name, desc, status, start, end = camp
            campaign_ids.append(camp_id)
            await session.execute(text("""
                INSERT INTO campaigns (id, name, description, status, selection_criteria_id, template_id,
                    start_date, end_date, created_by, created_at, updated_at)
                VALUES (:id, :name, :desc, :status, :criteria_id, :template_id,
                    :start, :end, :created_by, :now, :now)
                ON CONFLICT DO NOTHING
            """), {
                "id": camp_id, "name": name, "desc": desc, "status": status,
                "criteria_id": criteria_id, "template_id": template_id,
                "start": start, "end": end, "created_by": admin_id, "now": now,
            })

        # ── 5. Invitations ─────────────────────────────────────────────────────
        print("Membuat undangan...")
        statuses = ["SENT", "DELIVERED", "FAILED", "PENDING"]
        for camp_id in campaign_ids[:3]:  # hanya 3 kampanye pertama
            for inf_id, *_ in influencers[:6]:
                inv_status = random.choice(statuses)
                await session.execute(text("""
                    INSERT INTO invitations (id, campaign_id, influencer_id, template_id,
                        message_content, status, sent_at, created_at, updated_at)
                    VALUES (:id, :camp_id, :inf_id, :template_id,
                        'Halo, kami mengundang kamu bergabung kampanye kami!',
                        :status, :now, :now, :now)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": str(uuid.uuid4()), "camp_id": camp_id, "inf_id": inf_id,
                    "template_id": template_id, "status": inv_status, "now": now,
                })

        # ── 6. Content Metrics ─────────────────────────────────────────────────
        print("Membuat metrik konten...")
        for camp_id in campaign_ids[:2]:
            for inf_id, *_ in influencers[:4]:
                views = random.randint(50000, 2000000)
                gmv = random.uniform(500000, 15000000)
                await session.execute(text("""
                    INSERT INTO content_metrics (id, campaign_id, influencer_id, tiktok_video_id,
                        views, likes, comments, shares, has_valid_affiliate_link,
                        gmv_generated, conversion_rate, recorded_at, is_compliant)
                    VALUES (:id, :camp_id, :inf_id, :video_id,
                        :views, :likes, :comments, :shares, TRUE,
                        :gmv, :cr, :now, TRUE)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": str(uuid.uuid4()), "camp_id": camp_id, "inf_id": inf_id,
                    "video_id": f"video-{uuid.uuid4().hex[:8]}",
                    "views": views, "likes": int(views * 0.08), "comments": int(views * 0.02),
                    "shares": int(views * 0.01), "gmv": gmv, "cr": random.uniform(0.02, 0.12),
                    "now": now,
                })

        await session.commit()
        print("\n✓ Data dummy berhasil dibuat!")
        print("  - 10 influencer")
        print("  - 5 kampanye (aktif, selesai, draft, dijeda)")
        print("  - 1 template pesan")
        print("  - Undangan & metrik konten")
        print("\nRefresh browser untuk melihat data di dashboard.")


asyncio.run(main())
