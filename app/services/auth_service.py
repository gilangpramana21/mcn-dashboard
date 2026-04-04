"""Authentication service — registration, login, JWT, session, audit log."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.exceptions import AuthenticationError, TokenExpiredError, ValidationError
from app.models.domain import User, UserRole

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class AuthService:
    """Handles user auth, JWT lifecycle, session management, and audit logging."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    async def register_user(
        self,
        username: str,
        password: str,
        role: UserRole,
    ) -> User:
        """Hash password and persist a new user. Raises ValidationError if password < 8 chars."""
        if len(password) < 8:
            raise ValidationError("Password harus minimal 8 karakter.")

        password_hash = _pwd_context.hash(password)
        user_id = str(uuid.uuid4())
        now = _now_utc()

        await self._db.execute(
            text(
                """
                INSERT INTO users (id, username, password_hash, role, is_active,
                                   failed_login_attempts, created_at, updated_at)
                VALUES (:id, :username, :password_hash, :role, TRUE, 0, :now, :now)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": password_hash,
                "role": role.value,
                "now": now,
            },
        )
        await self._db.flush()

        return User(
            id=user_id,
            username=username,
            password_hash=password_hash,
            role=role,
            is_active=True,
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def login(self, username: str, password: str) -> User:
        """Verify credentials, handle lockout, update activity timestamp."""
        row = await self._db.execute(
            text("SELECT * FROM users WHERE username = :username"),
            {"username": username},
        )
        record = row.mappings().first()

        if record is None:
            raise AuthenticationError("Username atau password salah.")

        now = _now_utc()

        # Check account lock
        locked_until = record["locked_until"]
        if locked_until is not None:
            if isinstance(locked_until, datetime):
                lu = locked_until if locked_until.tzinfo else locked_until.replace(tzinfo=timezone.utc)
            else:
                lu = locked_until
            if now < lu:
                raise AuthenticationError(
                    f"Akun terkunci hingga {lu.isoformat()}. Coba lagi nanti."
                )

        # Verify password
        if not _pwd_context.verify(password, record["password_hash"]):
            new_attempts = record["failed_login_attempts"] + 1
            if new_attempts >= 5:
                lock_until = now + timedelta(minutes=15)
                await self._db.execute(
                    text(
                        """
                        UPDATE users
                        SET failed_login_attempts = :attempts,
                            locked_until = :lock_until,
                            updated_at = :now
                        WHERE id = :id
                        """
                    ),
                    {"attempts": new_attempts, "lock_until": lock_until, "now": now, "id": str(record["id"])},
                )
            else:
                await self._db.execute(
                    text(
                        """
                        UPDATE users
                        SET failed_login_attempts = :attempts, updated_at = :now
                        WHERE id = :id
                        """
                    ),
                    {"attempts": new_attempts, "now": now, "id": str(record["id"])},
                )
            await self._db.flush()
            raise AuthenticationError("Username atau password salah.")

        # Successful login — reset counter and update last_activity_at
        await self._db.execute(
            text(
                """
                UPDATE users
                SET failed_login_attempts = 0,
                    locked_until = NULL,
                    last_activity_at = :now,
                    updated_at = :now
                WHERE id = :id
                """
            ),
            {"now": now, "id": str(record["id"])},
        )
        await self._db.flush()

        role = UserRole(record["role"])
        return User(
            id=str(record["id"]),
            username=record["username"],
            password_hash=record["password_hash"],
            role=role,
            is_active=record["is_active"],
            failed_login_attempts=0,
            locked_until=None,
            last_activity_at=now,
        )

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------

    def create_access_token(self, user_id: str, role: UserRole) -> str:
        """Create a signed JWT with expiry from config."""
        settings = self._settings
        expire = _now_utc() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
        payload: Dict[str, Any] = {
            "sub": user_id,
            "role": role.value,
            "exp": expire,
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT. Raises TokenExpiredError or AuthenticationError."""
        settings = self._settings
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except ExpiredSignatureError:
            raise TokenExpiredError("Token telah kedaluwarsa.")
        except JWTError:
            raise AuthenticationError("Token tidak valid.")

    # ------------------------------------------------------------------
    # Session timeout
    # ------------------------------------------------------------------

    def check_session_timeout(self, user: User) -> None:
        """Raise AuthenticationError if last_activity_at is older than JWT_EXPIRE_MINUTES."""
        if user.last_activity_at is None:
            return
        now = _now_utc()
        last = (
            user.last_activity_at
            if user.last_activity_at.tzinfo
            else user.last_activity_at.replace(tzinfo=timezone.utc)
        )
        timeout_minutes = self._settings.JWT_EXPIRE_MINUTES
        if (now - last) > timedelta(minutes=timeout_minutes):
            raise AuthenticationError("Sesi telah berakhir. Silakan login kembali.")

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------

    async def write_audit_log(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist an audit log entry."""
        import json

        await self._db.execute(
            text(
                """
                INSERT INTO audit_logs (id, user_id, action, resource_type, resource_id, details, created_at)
                VALUES (:id, :user_id, :action, :resource_type, :resource_id, CAST(:details AS jsonb), :now)
                """
            ),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": json.dumps(details or {}),
                "now": _now_utc(),
            },
        )
        await self._db.flush()
