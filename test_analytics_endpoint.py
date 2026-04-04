"""Test analytics endpoints with authentication."""
import asyncio
import httpx
from app.services.auth_service import AuthService
from app.config import get_settings
from app.models.domain import UserRole

async def test_analytics():
    settings = get_settings()
    auth_service = AuthService(settings)
    
    # Generate token for test user
    user_id = "5baf998e-fd42-40a2-b377-7439b34ff0f4"
    token = auth_service.create_access_token(user_id, UserRole.CAMPAIGN_MANAGER)
    
    print(f"🔑 Token: {token[:50]}...")
    
    # Test overview endpoint
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        print("\n📊 Testing /api/v1/analytics/overview...")
        response = await client.get("http://localhost:8000/api/v1/analytics/overview", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total GMV: Rp {data['data']['total_gmv']:,.0f}")
            print(f"Total Views: {data['data']['total_views']:,}")
            print(f"Total Creators: {data['data']['total_creators']}")
            print(f"Global Conversion Rate: {data['data']['global_conversion_rate']:.2f}%")
        else:
            print(f"Error: {response.text}")
        
        print("\n👥 Testing /api/v1/analytics/creators...")
        response = await client.get("http://localhost:8000/api/v1/analytics/creators?limit=5", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data['data'])} creators")
            for creator in data['data'][:3]:
                print(f"  - {creator['name']}: {creator['creator_role']} (score: {creator['creator_score']:.2f})")
        else:
            print(f"Error: {response.text}")
        
        print("\n🎬 Testing /api/v1/analytics/content...")
        response = await client.get("http://localhost:8000/api/v1/analytics/content?limit=5", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data['data'])} content videos")
            for content in data['data'][:3]:
                print(f"  - {content['title'][:50]}... (views: {content['views']:,})")
        else:
            print(f"Error: {response.text}")
        
        print("\n📦 Testing /api/v1/analytics/products...")
        response = await client.get("http://localhost:8000/api/v1/analytics/products?limit=5", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data['data'])} products")
            for product in data['data'][:3]:
                print(f"  - {product['name']}: Rp {product['price']:,} (GMV: Rp {product['total_gmv']:,.0f})")
        else:
            print(f"Error: {response.text}")
        
        print("\n💰 Testing /api/v1/analytics/revenue...")
        response = await client.get("http://localhost:8000/api/v1/analytics/revenue?limit=5", headers=headers)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {len(data['data'])} revenue insights")
            for revenue in data['data'][:3]:
                print(f"  - {revenue['creator_name']} x {revenue['product_name']}: Rp {revenue['revenue']:,.0f}")
        else:
            print(f"Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_analytics())
