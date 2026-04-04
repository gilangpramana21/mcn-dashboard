"""Script untuk membuat user admin pertama di database."""
import asyncio
import sys

from app.database import AsyncSessionFactory
from app.models.domain import UserRole
from app.services.auth_service import AuthService


async def main(username: str, password: str, role: str = "Administrator"):
    role_map = {
        "Administrator": UserRole.ADMINISTRATOR,
        "Manajer_Kampanye": UserRole.CAMPAIGN_MANAGER,
        "Peninjau": UserRole.REVIEWER,
    }
    user_role = role_map.get(role, UserRole.ADMINISTRATOR)

    async with AsyncSessionFactory() as session:
        svc = AuthService(session)
        try:
            user = await svc.register_user(username, password, user_role)
            await session.commit()
            print(f"✓ User berhasil dibuat!")
            print(f"  Username : {user.username}")
            print(f"  Role     : {user.role.value}")
            print(f"  ID       : {user.id}")
        except Exception as e:
            print(f"✗ Gagal: {e}")
            sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password> [role]")
        print("Roles: Administrator, Manajer_Kampanye, Peninjau")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    role = sys.argv[3] if len(sys.argv) > 3 else "Administrator"

    asyncio.run(main(username, password, role))
