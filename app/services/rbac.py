"""RBAC helpers — FastAPI dependencies for role-based access control."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.exceptions import AuthenticationError, TokenExpiredError
from app.models.domain import UserRole
from app.services.auth_service import AuthService

_bearer = HTTPBearer(auto_error=False)


def _get_auth_service() -> AuthService:
    """Lightweight factory — returns an AuthService without a DB session.

    Token verification is stateless (JWT), so no DB session is needed here.
    For operations that require DB access, inject a full AuthService via DI.
    """
    from app.services.auth_service import AuthService as _AS
    from app.config import get_settings

    class _StatelessAuthService(_AS):
        """AuthService variant that skips DB for token-only operations."""

        def __init__(self) -> None:  # type: ignore[override]
            self._db = None  # type: ignore[assignment]
            self._settings = get_settings()

    return _StatelessAuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Dict[str, Any]:
    """FastAPI dependency — decode JWT and return user info dict.

    Returns a dict with keys: ``sub`` (user_id) and ``role``.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi diperlukan.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    svc = _get_auth_service()
    try:
        payload = svc.verify_token(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token telah kedaluwarsa.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"sub": payload["sub"], "role": payload["role"]}


def require_role(*roles: UserRole):
    """FastAPI dependency factory — enforce that the caller has one of the given roles."""

    async def _dependency(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        allowed = {r.value for r in roles}
        if current_user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Anda tidak memiliki izin untuk mengakses resource ini.",
            )
        return current_user

    return _dependency
