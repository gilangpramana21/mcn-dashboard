"""Auth API router — login, logout, refresh token."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.exceptions import AuthenticationError, TokenExpiredError
from app.services.auth_service import AuthService
from app.services.rbac import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    confirm_password: str
    full_name: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str


class RefreshRequest(BaseModel):
    token: str


class LogoutResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Login dan kembalikan JWT access token."""
    svc = AuthService(db)
    try:
        user = await svc.login(body.username, body.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = svc.create_access_token(user.id, user.role)
    await svc.write_audit_log(
        user_id=user.id,
        action="login",
        resource_type="user",
        resource_id=user.id,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Daftar akun baru — role default Peninjau, langsung login setelah berhasil."""
    if body.password != body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password dan konfirmasi password tidak cocok.",
        )

    from app.models.domain import UserRole
    from sqlalchemy import text

    # Cek username sudah ada
    result = await db.execute(
        text("SELECT id FROM users WHERE username = :username"),
        {"username": body.username},
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username sudah digunakan.",
        )

    svc = AuthService(db)
    try:
        user = await svc.register_user(body.username, body.password, UserRole.REVIEWER)
        await db.commit()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    token = svc.create_access_token(user.id, user.role)
    await svc.write_audit_log(
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.id,
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        role=user.role.value,
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LogoutResponse:
    """Logout — invalidate session (audit log + optional Redis token blacklist)."""
    from app.config import get_settings

    user_id = current_user["sub"]

    # Write audit log
    svc = AuthService(db)
    await svc.write_audit_log(
        user_id=user_id,
        action="logout",
        resource_type="user",
        resource_id=user_id,
    )

    # Best-effort: add token to Redis blacklist
    try:
        import redis.asyncio as aioredis  # type: ignore

        settings = get_settings()
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        blacklist_key = f"token:blacklist:{user_id}"
        await redis_client.setex(blacklist_key, settings.JWT_EXPIRE_MINUTES * 60, "1")
        await redis_client.aclose()
    except Exception:
        pass

    return LogoutResponse(message="Logout berhasil.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Refresh JWT token — verifikasi token lama dan terbitkan token baru."""
    from app.config import get_settings
    from app.models.domain import UserRole

    settings = get_settings()
    svc = AuthService(db)

    try:
        payload = svc.verify_token(body.token)
    except TokenExpiredError:
        # Allow refresh even if expired — decode without verification for payload
        from jose import jwt as _jwt

        try:
            payload = _jwt.decode(
                body.token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"verify_exp": False},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token tidak valid untuk di-refresh.",
            )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        )

    user_id = payload["sub"]
    role = UserRole(payload["role"])
    new_token = svc.create_access_token(user_id, role)

    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user_id=user_id,
        role=role.value,
    )


# ---------------------------------------------------------------------------
# User Management (Admin only)
# ---------------------------------------------------------------------------

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str  # Administrator | Manajer_Kampanye | Peninjau


class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool
    created_at: Optional[str] = None


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """Daftar semua user — hanya Administrator."""
    from sqlalchemy import text
    if current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Hanya Administrator yang bisa melihat daftar user.")
    result = await db.execute(text("""
        SELECT id, username, role, is_active, created_at FROM users ORDER BY created_at DESC
    """))
    rows = result.mappings().all()
    return [UserResponse(
        id=str(row["id"]),
        username=row["username"],
        role=row["role"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"].isoformat() if row["created_at"] else None,
    ) for row in rows]


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: CreateUserRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Buat user baru — hanya Administrator."""
    if current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Hanya Administrator yang bisa membuat user.")

    from app.models.domain import UserRole
    try:
        role = UserRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Role tidak valid: {body.role}")

    svc = AuthService(db)
    try:
        user = await svc.register_user(body.username, body.password, role)
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return UserResponse(id=user.id, username=user.username, role=user.role.value, is_active=True)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Update user — hanya Administrator."""
    if current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Hanya Administrator yang bisa mengubah user.")

    from sqlalchemy import text
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    updates = []
    params: Dict[str, Any] = {"id": user_id}

    if body.password:
        updates.append("password_hash = :pw")
        params["pw"] = pwd_context.hash(body.password)
    if body.role:
        updates.append("role = :role")
        params["role"] = body.role
    if body.is_active is not None:
        updates.append("is_active = :is_active")
        params["is_active"] = body.is_active

    if updates:
        await db.execute(text(f"UPDATE users SET {', '.join(updates)}, updated_at = NOW() WHERE id = :id"), params)
        await db.commit()

    result = await db.execute(text("SELECT id, username, role, is_active FROM users WHERE id = :id"), {"id": user_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="User tidak ditemukan.")
    return UserResponse(id=str(row["id"]), username=row["username"], role=row["role"], is_active=bool(row["is_active"]))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> Dict[str, str]:
    """Hapus user — hanya Administrator. Tidak bisa hapus diri sendiri."""
    if current_user.get("role") != "Administrator":
        raise HTTPException(status_code=403, detail="Hanya Administrator yang bisa menghapus user.")
    if current_user.get("sub") == user_id:
        raise HTTPException(status_code=400, detail="Tidak bisa menghapus akun sendiri.")

    from sqlalchemy import text
    await db.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
    await db.commit()
    return {"status": "deleted"}
