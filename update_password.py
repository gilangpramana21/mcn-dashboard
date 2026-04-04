"""Script untuk mengubah password user yang sudah ada."""
import asyncio
import sys

from app.database import AsyncSessionFactory
from sqlalchemy import text
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def main(username: str, new_password: str):
    async with AsyncSessionFactory() as session:
        # Cek apakah user ada
        result = await session.execute(
            text("SELECT id, username FROM users WHERE username = :username"),
            {"username": username}
        )
        user = result.fetchone()
        
        if not user:
            print(f"✗ User '{username}' tidak ditemukan.")
            sys.exit(1)
        
        # Hash password baru
        password_hash = pwd_context.hash(new_password)
        
        # Update password
        await session.execute(
            text("""
                UPDATE users 
                SET password_hash = :password_hash,
                    failed_login_attempts = 0,
                    locked_until = NULL,
                    updated_at = NOW()
                WHERE username = :username
            """),
            {"password_hash": password_hash, "username": username}
        )
        await session.commit()
        
        print(f"✓ Password untuk user '{username}' berhasil diubah!")
        print(f"  User ID: {user[0]}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python update_password.py <username> <new_password>")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    asyncio.run(main(username, new_password))
