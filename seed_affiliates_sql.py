"""
Seed affiliator langsung via psql — bypass SQLAlchemy type issues.
Jalankan: python3 seed_affiliates_sql.py
"""
import subprocess
import json
import uuid

AFFILIATES = [
    {"name": "Siti Rahayu", "tiktok_user_id": "@sitirahayubeauty", "follower_count": 250000, "engagement_rate": 4.2, "content_categories": ["Kecantikan", "Skincare"], "location": "Jakarta"},
    {"name": "Budi Santoso", "tiktok_user_id": "@budisantosofashion", "follower_count": 180000, "engagement_rate": 3.8, "content_categories": ["Fashion", "Lifestyle"], "location": "Bandung"},
    {"name": "Dewi Kusuma", "tiktok_user_id": "@dewikusumafit", "follower_count": 320000, "engagement_rate": 5.1, "content_categories": ["Fitness", "Kesehatan"], "location": "Surabaya"},
    {"name": "Andi Pratama", "tiktok_user_id": "@andipratamaculinary", "follower_count": 95000, "engagement_rate": 6.3, "content_categories": ["Kuliner", "Masakan"], "location": "Yogyakarta"},
    {"name": "Rina Wulandari", "tiktok_user_id": "@rinawulandaritech", "follower_count": 410000, "engagement_rate": 3.5, "content_categories": ["Teknologi", "Gadget"], "location": "Jakarta"},
    {"name": "Fajar Nugroho", "tiktok_user_id": "@fajarnugrohotravel", "follower_count": 560000, "engagement_rate": 4.7, "content_categories": ["Travel", "Lifestyle"], "location": "Bali"},
    {"name": "Maya Indah", "tiktok_user_id": "@mayaindahskincare", "follower_count": 145000, "engagement_rate": 5.8, "content_categories": ["Kecantikan", "Perawatan Kulit"], "location": "Medan"},
    {"name": "Rizky Firmansyah", "tiktok_user_id": "@rizkyfirmansyahgaming", "follower_count": 890000, "engagement_rate": 4.1, "content_categories": ["Gaming", "Teknologi"], "location": "Jakarta"},
    {"name": "Lestari Putri", "tiktok_user_id": "@lestariputrimom", "follower_count": 230000, "engagement_rate": 6.9, "content_categories": ["Parenting", "Lifestyle"], "location": "Semarang"},
    {"name": "Hendra Wijaya", "tiktok_user_id": "@hendrawijayafinance", "follower_count": 175000, "engagement_rate": 3.2, "content_categories": ["Keuangan", "Investasi"], "location": "Surabaya"},
    {"name": "Nadia Safitri", "tiktok_user_id": "@nadiasafitribeauty", "follower_count": 680000, "engagement_rate": 5.4, "content_categories": ["Kecantikan", "Fashion"], "location": "Jakarta"},
    {"name": "Dimas Ardiansyah", "tiktok_user_id": "@dimasardiansyahsport", "follower_count": 290000, "engagement_rate": 4.6, "content_categories": ["Olahraga", "Fitness"], "location": "Bandung"},
    {"name": "Fitri Handayani", "tiktok_user_id": "@fitrihandayanicook", "follower_count": 120000, "engagement_rate": 7.2, "content_categories": ["Kuliner", "Resep"], "location": "Solo"},
    {"name": "Agus Setiawan", "tiktok_user_id": "@agussetiawanmotivasi", "follower_count": 450000, "engagement_rate": 3.9, "content_categories": ["Motivasi", "Bisnis"], "location": "Jakarta"},
    {"name": "Yuni Astuti", "tiktok_user_id": "@yuniastutifashion", "follower_count": 310000, "engagement_rate": 4.8, "content_categories": ["Fashion", "Kecantikan"], "location": "Malang"},
]

sql_lines = []
for aff in AFFILIATES:
    new_id = str(uuid.uuid4())
    cats = json.dumps(aff["content_categories"]).replace("'", "''")
    name = aff["name"].replace("'", "''")
    tiktok_id = aff["tiktok_user_id"].replace("'", "''")
    location = aff["location"].replace("'", "''")
    
    sql_lines.append(
        f"INSERT INTO influencers (id, name, tiktok_user_id, follower_count, engagement_rate, "
        f"content_categories, location, has_whatsapp, status, created_at, updated_at) "
        f"SELECT '{new_id}'::uuid, '{name}', '{tiktok_id}', {aff['follower_count']}, {aff['engagement_rate']}, "
        f"'{cats}'::jsonb, '{location}', FALSE, 'ACTIVE', NOW(), NOW() "
        f"WHERE NOT EXISTS (SELECT 1 FROM influencers WHERE tiktok_user_id = '{tiktok_id}');"
    )

sql = "\n".join(sql_lines)

result = subprocess.run(
    ["su", "-s", "/bin/bash", "postgres", "-c", f"psql -d mcn_dashboard -c \"{sql}\""],
    capture_output=True, text=True
)

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Verifikasi
count = subprocess.run(
    ["su", "-s", "/bin/bash", "postgres", "-c", "psql -d mcn_dashboard -c 'SELECT COUNT(*) FROM influencers;'"],
    capture_output=True, text=True
)
print(count.stdout)
