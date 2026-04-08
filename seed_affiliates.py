"""
Seed data affiliator ke tabel influencers.
Jalankan di VPS: python seed_affiliates.py
"""
import asyncio
import json
import uuid
from app.database import get_db_session
from sqlalchemy import text

AFFILIATES = [
    {
        "name": "Siti Rahayu",
        "tiktok_user_id": "@sitirahayubeauty",
        "follower_count": 250000,
        "engagement_rate": 4.2,
        "content_categories": ["Kecantikan", "Skincare"],
        "location": "Jakarta",
    },
    {
        "name": "Budi Santoso",
        "tiktok_user_id": "@budisantosofashion",
        "follower_count": 180000,
        "engagement_rate": 3.8,
        "content_categories": ["Fashion", "Lifestyle"],
        "location": "Bandung",
    },
    {
        "name": "Dewi Kusuma",
        "tiktok_user_id": "@dewikusumafit",
        "follower_count": 320000,
        "engagement_rate": 5.1,
        "content_categories": ["Fitness", "Kesehatan"],
        "location": "Surabaya",
    },
    {
        "name": "Andi Pratama",
        "tiktok_user_id": "@andipratamaculinary",
        "follower_count": 95000,
        "engagement_rate": 6.3,
        "content_categories": ["Kuliner", "Masakan"],
        "location": "Yogyakarta",
    },
    {
        "name": "Rina Wulandari",
        "tiktok_user_id": "@rinawulandaritech",
        "follower_count": 410000,
        "engagement_rate": 3.5,
        "content_categories": ["Teknologi", "Gadget"],
        "location": "Jakarta",
    },
    {
        "name": "Fajar Nugroho",
        "tiktok_user_id": "@fajarnugrohotravel",
        "follower_count": 560000,
        "engagement_rate": 4.7,
        "content_categories": ["Travel", "Lifestyle"],
        "location": "Bali",
    },
    {
        "name": "Maya Indah",
        "tiktok_user_id": "@mayaindahskincare",
        "follower_count": 145000,
        "engagement_rate": 5.8,
        "content_categories": ["Kecantikan", "Perawatan Kulit"],
        "location": "Medan",
    },
    {
        "name": "Rizky Firmansyah",
        "tiktok_user_id": "@rizkyfirmansyahgaming",
        "follower_count": 890000,
        "engagement_rate": 4.1,
        "content_categories": ["Gaming", "Teknologi"],
        "location": "Jakarta",
    },
    {
        "name": "Lestari Putri",
        "tiktok_user_id": "@lestariputrimom",
        "follower_count": 230000,
        "engagement_rate": 6.9,
        "content_categories": ["Parenting", "Lifestyle"],
        "location": "Semarang",
    },
    {
        "name": "Hendra Wijaya",
        "tiktok_user_id": "@hendrawijayafinance",
        "follower_count": 175000,
        "engagement_rate": 3.2,
        "content_categories": ["Keuangan", "Investasi"],
        "location": "Surabaya",
    },
    {
        "name": "Nadia Safitri",
        "tiktok_user_id": "@nadiasafitribeauty",
        "follower_count": 680000,
        "engagement_rate": 5.4,
        "content_categories": ["Kecantikan", "Fashion"],
        "location": "Jakarta",
    },
    {
        "name": "Dimas Ardiansyah",
        "tiktok_user_id": "@dimasardiansyahsport",
        "follower_count": 290000,
        "engagement_rate": 4.6,
        "content_categories": ["Olahraga", "Fitness"],
        "location": "Bandung",
    },
    {
        "name": "Fitri Handayani",
        "tiktok_user_id": "@fitrihandayanicook",
        "follower_count": 120000,
        "engagement_rate": 7.2,
        "content_categories": ["Kuliner", "Resep"],
        "location": "Solo",
    },
    {
        "name": "Agus Setiawan",
        "tiktok_user_id": "@agussetiawanmotivasi",
        "follower_count": 450000,
        "engagement_rate": 3.9,
        "content_categories": ["Motivasi", "Bisnis"],
        "location": "Jakarta",
    },
    {
        "name": "Yuni Astuti",
        "tiktok_user_id": "@yuniastutifashion",
        "follower_count": 310000,
        "engagement_rate": 4.8,
        "content_categories": ["Fashion", "Kecantikan"],
        "location": "Malang",
    },
]


async def seed():
    async for db in get_db_session():
        inserted = 0
        skipped = 0

        for aff in AFFILIATES:
            # Cek apakah sudah ada
            existing = await db.execute(
                text("SELECT id FROM influencers WHERE tiktok_user_id = :tid"),
                {"tid": aff["tiktok_user_id"]},
            )
            if existing.fetchone():
                skipped += 1
                continue

            new_id = str(uuid.uuid4())
            await db.execute(
                text("""
                    INSERT INTO influencers
                        (id, name, tiktok_user_id, follower_count, engagement_rate,
                         content_categories, location, has_whatsapp, status,
                         created_at, updated_at)
                    VALUES
                        (:id, :name, :tiktok_id, :followers, :engagement,
                         cast(:categories as jsonb), :location, FALSE, 'ACTIVE',
                         NOW(), NOW())
                """),
                {
                    "id": new_id,
                    "name": aff["name"],
                    "tiktok_id": aff["tiktok_user_id"],
                    "followers": aff["follower_count"],
                    "engagement": aff["engagement_rate"],
                    "categories": json.dumps(aff["content_categories"]),
                    "location": aff["location"],
                },
            )
            inserted += 1

        await db.commit()
        print(f"Selesai: {inserted} affiliator ditambahkan, {skipped} sudah ada.")
        break


if __name__ == "__main__":
    asyncio.run(seed())
