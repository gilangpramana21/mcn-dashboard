"""
Test TikTok Shop API dengan App Key yang ada.

Langkah:
1. Jalankan script ini: python3 test_tiktok_api.py
2. Buka URL yang muncul di browser
3. Login TikTok Shop seller account
4. Copy auth_code dari URL redirect
5. Paste ke terminal

App Key: 6jc8vkl0fvakm
"""
import asyncio
import os
import sys

# Set env vars untuk test
os.environ.setdefault("TIKTOK_APP_KEY", "6jc8vkl0fvakm")
os.environ.setdefault("TIKTOK_APP_SECRET", "9e2e044bede647731778502418dbcdf85ab01f91")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:mcn_secure_2024@localhost/mcn_dashboard")

from app.integrations.tiktok_shop_api import TikTokShopOAuth, TikTokShopClient


async def main():
    oauth = TikTokShopOAuth()

    # Step 1: Generate auth URL
    redirect_uri = "https://dashboardmcn.my.id/api/v1/tiktok/callback"
    auth_url = oauth.get_auth_url(redirect_uri=redirect_uri, state="test123")

    print("\n" + "="*60)
    print("STEP 1: Buka URL ini di browser dan login dengan akun TikTok Shop seller:")
    print("="*60)
    print(auth_url)
    print("="*60)
    print("\nSetelah login, kamu akan di-redirect ke URL seperti:")
    print(f"{redirect_uri}?code=XXXX&state=test123")
    print("\nCopy nilai 'code' dari URL tersebut.")

    auth_code = input("\nMasukkan auth_code: ").strip()
    if not auth_code:
        print("Auth code kosong, keluar.")
        return

    # Step 2: Exchange code untuk access token
    print("\nMengambil access token...")
    try:
        token_data = await oauth.exchange_code(auth_code=auth_code)
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        print(f"✅ Access token berhasil didapat!")
        print(f"   access_token: {access_token[:20]}..." if access_token else "   TIDAK ADA access_token")
        print(f"   refresh_token: {refresh_token[:20]}..." if refresh_token else "   TIDAK ADA refresh_token")
        print(f"   Full response: {token_data}")
    except Exception as e:
        print(f"❌ Gagal exchange code: {e}")
        return

    if not access_token:
        print("Tidak ada access token, keluar.")
        return

    # Step 3: Test search creators
    print("\n" + "="*60)
    print("STEP 3: Test search creators...")
    print("="*60)
    client = TikTokShopClient(access_token=access_token)
    try:
        result = await client.search_creators(keyword="", page_size=5)
        print(f"✅ Search creators berhasil!")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"❌ Search creators gagal: {e}")

    # Step 4: Test list collaborations
    print("\nTest list collaborations...")
    try:
        collabs = await client.list_collaborations(page_size=5)
        print(f"✅ List collaborations berhasil!")
        print(f"   Result: {collabs}")
    except Exception as e:
        print(f"❌ List collaborations gagal: {e}")

    print("\n" + "="*60)
    print("Simpan token ini ke .env VPS:")
    print(f"TIKTOK_ACCESS_TOKEN={access_token}")
    if refresh_token:
        print(f"TIKTOK_REFRESH_TOKEN={refresh_token}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
