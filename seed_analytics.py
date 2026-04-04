"""
Seed script untuk data analytics dummy
"""
import asyncio
import uuid
from datetime import datetime, timedelta
import random
from sqlalchemy import text
from app.database import AsyncSessionFactory

# Data dummy products
PRODUCTS = [
    {"name": "Serum Wajah Glowing", "price": 125000, "category": "Skincare", "shop_name": "Beauty Store ID"},
    {"name": "Lipstik Matte Long Lasting", "price": 89000, "category": "Makeup", "shop_name": "Kosmetik Cantik"},
    {"name": "Tas Selempang Mini", "price": 175000, "category": "Fashion", "shop_name": "Fashion Hub"},
    {"name": "Sepatu Sneakers Putih", "price": 299000, "category": "Fashion", "shop_name": "Sneaker Store"},
    {"name": "Masker Wajah Korea", "price": 45000, "category": "Skincare", "shop_name": "K-Beauty Shop"},
    {"name": "Eyeshadow Palette", "price": 159000, "category": "Makeup", "shop_name": "Makeup Pro"},
    {"name": "Kaos Oversize Premium", "price": 99000, "category": "Fashion", "shop_name": "Streetwear ID"},
    {"name": "Sunscreen SPF 50", "price": 135000, "category": "Skincare", "shop_name": "Beauty Store ID"},
    {"name": "Jam Tangan Smartwatch", "price": 450000, "category": "Electronics", "shop_name": "Tech Gadget"},
    {"name": "Earphone Wireless", "price": 199000, "category": "Electronics", "shop_name": "Audio Shop"},
]

# Video titles template
VIDEO_TITLES = [
    "Review jujur produk ini! Worth it ga sih?",
    "Unboxing + First Impression",
    "Tutorial makeup natural sehari-hari",
    "OOTD kasual tapi tetap stylish",
    "Skincare routine pagi hari",
    "Haul belanja online bulan ini",
    "Produk viral TikTok yang wajib dicoba",
    "Makeup look untuk acara formal",
    "Tips mix and match outfit",
    "Rekomendasi produk affordable",
]

async def seed_analytics_data():
    """Seed products, content_videos, dan update influencers dengan analytics data"""
    async with AsyncSessionFactory() as session:
        try:
            print("🌱 Starting analytics data seeding...")
            
            # 1. Insert products
            print("\n📦 Seeding products...")
            product_ids = []
            for product in PRODUCTS:
                product_id = str(uuid.uuid4())
                tiktok_product_id = f"PROD_{random.randint(100000, 999999)}"
                
                await session.execute(text("""
                    INSERT INTO products (id, tiktok_product_id, name, price, category, shop_name, is_active, created_at, updated_at)
                    VALUES (:id, :tiktok_product_id, :name, :price, :category, :shop_name, :is_active, :created_at, :updated_at)
                    ON CONFLICT (tiktok_product_id) DO NOTHING
                """), {
                    "id": product_id,
                    "tiktok_product_id": tiktok_product_id,
                    "name": product["name"],
                    "price": product["price"],
                    "category": product["category"],
                    "shop_name": product["shop_name"],
                    "is_active": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                
                product_ids.append(product_id)
                print(f"  ✓ {product['name']}")
            
            await session.commit()
            
            # 2. Get active influencers
            print("\n👥 Fetching active influencers...")
            result = await session.execute(text("SELECT id, name FROM influencers WHERE status = 'ACTIVE' LIMIT 20"))
            influencers = result.fetchall()
            
            if not influencers:
                print("  ⚠️  No active influencers found. Please run seed_data.py first.")
                return
            
            print(f"  ✓ Found {len(influencers)} active influencers")
            
            # 3. Generate content_videos
            print("\n🎬 Seeding content videos...")
            video_count = 0
            
            for influencer in influencers:
                # Each influencer creates 3-8 videos
                num_videos = random.randint(3, 8)
                
                for _ in range(num_videos):
                    video_id = str(uuid.uuid4())
                    tiktok_video_id = f"VID_{random.randint(1000000000, 9999999999)}"
                    product_id = random.choice(product_ids)
                    title = random.choice(VIDEO_TITLES)
                    
                    # Random metrics
                    views = random.randint(10000, 5000000)
                    likes = int(views * random.uniform(0.03, 0.15))
                    comments = int(views * random.uniform(0.005, 0.03))
                    shares = int(views * random.uniform(0.01, 0.05))
                    buyers = int(views * random.uniform(0.001, 0.05))
                    gmv_generated = buyers * random.randint(50000, 500000)
                    
                    # Posted date in last 90 days
                    days_ago = random.randint(1, 90)
                    posted_at = datetime.utcnow() - timedelta(days=days_ago)
                    
                    await session.execute(text("""
                        INSERT INTO content_videos 
                        (id, tiktok_video_id, creator_id, product_id, title, views, likes, comments, shares, 
                         gmv_generated, buyers, posted_at, created_at)
                        VALUES (:id, :tiktok_video_id, :creator_id, :product_id, :title, :views, :likes, :comments, :shares, 
                                :gmv_generated, :buyers, :posted_at, :created_at)
                        ON CONFLICT (tiktok_video_id) DO NOTHING
                    """), {
                        "id": video_id,
                        "tiktok_video_id": tiktok_video_id,
                        "creator_id": influencer.id,
                        "product_id": product_id,
                        "title": title,
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "shares": shares,
                        "gmv_generated": gmv_generated,
                        "buyers": buyers,
                        "posted_at": posted_at,
                        "created_at": datetime.utcnow()
                    })
                    
                    video_count += 1
            
            await session.commit()
            print(f"  ✓ Created {video_count} content videos")
            
            # 4. Update influencers with calculated analytics
            print("\n📊 Updating influencer analytics...")
            
            for influencer in influencers:
                # Calculate aggregated metrics
                result = await session.execute(text("""
                    SELECT 
                        COUNT(*) as video_count,
                        COALESCE(SUM(gmv_generated), 0) as total_gmv,
                        COALESCE(AVG(views), 0) as avg_views
                    FROM content_videos
                    WHERE creator_id = :creator_id
                """), {"creator_id": influencer.id})
                
                stats = result.fetchone()
                
                # Calculate creator score (simplified)
                video_count_val = stats.video_count
                total_gmv = float(stats.total_gmv)
                avg_views = float(stats.avg_views)
                
                # Normalize and calculate score
                gmv_score = min(1.0, total_gmv / 10_000_000)  # Max 10M
                views_score = min(1.0, avg_views / 1_000_000)  # Max 1M avg
                video_score = min(1.0, video_count_val / 20)  # Max 20 videos
                
                creator_score = (0.5 * gmv_score) + (0.3 * views_score) + (0.2 * video_score)
                
                # Classify role based on score
                if creator_score >= 0.8:
                    creator_role = 'Superstar'
                elif creator_score >= 0.6:
                    creator_role = 'Rising Star'
                elif creator_score >= 0.4:
                    creator_role = 'Consistent Performer'
                else:
                    creator_role = 'Underperformer'
                
                # Assign creator_type based on index for variety
                creator_types = ['influencer', 'influencer', 'affiliator', 'hybrid']
                creator_type = creator_types[influencers.index(influencer) % len(creator_types)]
                
                await session.execute(text("""
                    UPDATE influencers
                    SET creator_score = :creator_score,
                        creator_role = :creator_role,
                        creator_type = :creator_type,
                        estimated_revenue = :estimated_revenue,
                        avg_views = :avg_views
                    WHERE id = :id
                """), {
                    "creator_score": creator_score,
                    "creator_role": creator_role,
                    "creator_type": creator_type,
                    "estimated_revenue": total_gmv,
                    "avg_views": int(avg_views),
                    "id": influencer.id
                })
                
                print(f"  ✓ {influencer.name}: score={creator_score:.2f}, role={creator_role}")
            
            await session.commit()
            
            print("\n✅ Analytics data seeding completed successfully!")
            print(f"\nSummary:")
            print(f"  - Products: {len(PRODUCTS)}")
            print(f"  - Content Videos: {video_count}")
            print(f"  - Updated Influencers: {len(influencers)}")
            
        except Exception as e:
            print(f"\n❌ Error seeding analytics data: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(seed_analytics_data())
