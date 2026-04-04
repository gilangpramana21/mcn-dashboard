"""Script untuk dapat TikTok Shop access token dari auth_code.

Usage: python get_token.py TTP_xxxxxxxx
"""
import asyncio
import sys
import httpx

APP_KEY = "6jc8vkl0fvakm"
APP_SECRET = "9e2e044bede647731778502418dbcdf85ab01f91"

async def main():
    if len(sys.argv) < 2:
        print("Usage: python get_token.py <auth_code>")
        print()
        print("Cara dapat auth_code:")
        print("1. Buka URL ini di browser:")
        print(f"   https://auth.tiktok-shops.com/oauth/authorize?app_key={APP_KEY}&redirect_uri=http://localhost:3000/oauth/tiktok/callback")
        print("2. Login & authorize")
        print("3. Copy nilai ?code= dari URL bar")
        return

    auth_code = sys.argv[1]
    print(f"Menukar auth_code: {auth_code[:20]}...")

    async with httpx.AsyncClient() as client:
        r = await client.get(
            "https://auth.tiktok-shops.com/api/v2/token/get",
            params={
                "app_key": APP_KEY,
                "app_secret": APP_SECRET,
                "auth_code": auth_code,
                "grant_type": "authorized_code",
            }
        )

    data = r.json()
    print("Response:", data)

    if data.get("code") == 0:
        token_data = data.get("data", {})
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")
        expires = token_data.get("access_token_expire_in", 3600)

        print()
        print("=" * 60)
        print("ACCESS TOKEN BERHASIL DIDAPAT!")
        print("=" * 60)
        print(f"access_token: {access_token}")
        print(f"refresh_token: {refresh_token}")
        print(f"expires_in: {expires} detik")
        print()

        # Simpan langsung ke database
        try:
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from sqlalchemy import text
            from app.database import AsyncSessionFactory
            import uuid

            async with AsyncSessionFactory() as db:
                await db.execute(text("""
                    INSERT INTO tiktok_shop_tokens
                        (id, access_token, refresh_token, expires_at)
                    VALUES
                        (:id, :access_token, :refresh_token,
                         NOW() + (:expires * INTERVAL '1 second'))
                """), {
                    "id": str(uuid.uuid4()),
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires": expires,
                })
                await db.commit()
            print("Token berhasil disimpan ke database!")
            print("Sekarang buka dashboard Agent dan cek status token.")
        except Exception as e:
            print(f"Gagal simpan ke DB: {e}")
            print()
            print("Simpan manual via dashboard:")
            print("Dashboard → TikTok Shop Agent → Pengaturan Token → Input Token Manual")
            print(f"Paste access_token: {access_token[:50]}...")
    else:
        print(f"Error: {data.get('message')}")
        print("auth_code mungkin sudah expired (berlaku hanya beberapa menit)")

asyncio.run(main())
