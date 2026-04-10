"""Entry point FastAPI — Sistem Agen Cerdas Pemasaran Influencer TikTok."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import (
    affiliates_router,
    auth_router,
    learning_router,
    templates_router,
)
from app.api.analytics import router as analytics_router
from app.api.messages import router as messages_router
from app.api.tiktok_shop import router as tiktok_shop_router
from app.api.brands import router as brands_router
from app.database import engine

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    # Startup
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Koneksi database berhasil.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Tidak dapat terhubung ke database saat startup: %s", exc)

    logger.info("Aplikasi siap — %s v%s", app.title, APP_VERSION)

    yield

    # Shutdown
    await engine.dispose()
    logger.info("Database engine di-dispose. Aplikasi berhenti.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Sistem Agen Cerdas Pemasaran Influencer TikTok",
    version=APP_VERSION,
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Railway/Vercel: set ALLOWED_ORIGINS env var
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


@app.middleware("http")
async def update_last_activity_middleware(request: Request, call_next: Any) -> Any:
    """Update last_activity_at untuk setiap request yang terautentikasi (non-blocking)."""
    response = await call_next(request)

    # Skip untuk endpoint yang tidak perlu tracking
    path = request.url.path
    if path in ("/health", "/docs", "/openapi.json", "/redoc"):
        return response

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        import asyncio

        async def _update_activity():
            try:
                from datetime import datetime, timezone
                from sqlalchemy import update
                from app.config import get_settings
                from app.database import AsyncSessionFactory
                from app.services.auth_service import AuthService

                token = auth_header.removeprefix("Bearer ").strip()
                settings = get_settings()
                svc = AuthService.__new__(AuthService)
                svc._settings = settings
                payload = svc.verify_token(token)
                user_id: str = payload["sub"]

                async with AsyncSessionFactory() as session:
                    from app.models.domain import User as UserORM
                    await session.execute(
                        update(UserORM)
                        .where(UserORM.id == user_id)
                        .values(last_activity_at=datetime.now(timezone.utc))
                    )
                    await session.commit()
            except Exception:
                pass

        # Fire and forget — tidak blocking response
        asyncio.create_task(_update_activity())

    return response


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=_PREFIX)
app.include_router(templates_router, prefix=_PREFIX)
app.include_router(affiliates_router, prefix=_PREFIX)
app.include_router(learning_router, prefix=_PREFIX)
app.include_router(analytics_router, prefix=_PREFIX)
app.include_router(messages_router, prefix=_PREFIX)
app.include_router(tiktok_shop_router, prefix=_PREFIX)
app.include_router(brands_router, prefix=_PREFIX)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["health"])
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": APP_VERSION}
