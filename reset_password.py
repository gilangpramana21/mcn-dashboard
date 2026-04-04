"""Reset password untuk user manajer."""
import asyncio
from sqlalchemy import text
from passlib.context import CryptContext
from app.database import AsyncSessionFactory
from app.config import get_settings

async def reset_password():
    # Hash password baru
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    new_password = "admin123"
    password_hash = pwd_context.hash(new_password)
    
    async with AsyncSessionFactory() as session:
        await session.execute(
            text("UPDATE users SET password_hash = :password_hash WHERE username = :username"),
            {"password_hash": password_hash, "username": "manajer"}
        )
        await session.commit()
        
    print(f"✅ Password untuk user 'manajer' berhasil direset!")
    print(f"   Username: manajer")
    print(f"   Password: {new_password}")
    print(f"\n🌐 Silakan login di: http://localhost:3000/login")

if __name__ == "__main__":
    asyncio.run(reset_password())
