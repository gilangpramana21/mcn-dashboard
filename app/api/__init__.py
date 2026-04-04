"""API package — exposes all FastAPI routers."""

from app.api.affiliates import router as affiliates_router
from app.api.auth import router as auth_router
from app.api.learning import router as learning_router
from app.api.templates import router as templates_router

__all__ = [
    "affiliates_router",
    "auth_router",
    "learning_router",
    "templates_router",
]
