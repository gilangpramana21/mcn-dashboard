"""Application configuration loaded from environment variables via pydantic-settings."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/tiktok_agent",
        description="Async PostgreSQL connection URL",
    )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL (used for cache and Streams queue)",
    )

    # ------------------------------------------------------------------
    # Affiliate Center
    # ------------------------------------------------------------------
    AFFILIATE_CENTER_API_URL: str = Field(
        default="https://affiliate-center.example.com/api",
        description="Base URL for the Affiliate Center Indonesia API",
    )
    AFFILIATE_CENTER_CLIENT_ID: str = Field(
        default="",
        description="OAuth 2.0 client ID for Affiliate Center",
    )
    AFFILIATE_CENTER_CLIENT_SECRET: str = Field(
        default="",
        description="OAuth 2.0 client secret for Affiliate Center",
    )

    # ------------------------------------------------------------------
    # TikTok API
    # ------------------------------------------------------------------
    TIKTOK_API_KEY: str = Field(
        default="",
        description="API key for TikTok API access (legacy)",
    )
    TIKTOK_APP_KEY: str = Field(
        default="6jc8vkl0fvakm",
        description="TikTok Shop Open Platform App Key",
    )
    TIKTOK_APP_SECRET: str = Field(
        default="9e2e044bede647731778502418dbcdf85ab01f91",
        description="TikTok Shop Open Platform App Secret",
    )

    # ------------------------------------------------------------------
    # WhatsApp API
    # ------------------------------------------------------------------
    WHATSAPP_API_URL: str = Field(
        default="https://whatsapp-api.example.com",
        description="Base URL for the WhatsApp API",
    )
    WHATSAPP_API_TOKEN: str = Field(
        default="",
        description="Bearer token for WhatsApp API authentication (Meta Cloud API access token)",
    )
    WHATSAPP_PHONE_NUMBER_ID: str = Field(
        default="",
        description="Default Meta phone_number_id (untuk backward compatibility)",
    )
    WHATSAPP_WABA_ID: str = Field(
        default="",
        description="WhatsApp Business Account ID (untuk list phone numbers)",
    )

    # ------------------------------------------------------------------
    # OpenAI (untuk NLP Classifier Agent)
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key untuk klasifikasi feedback NLP",
    )
    OPENAI_MODEL: str = Field(
        default="gpt-4o-mini",
        description="Model OpenAI yang digunakan (gpt-4o-mini lebih hemat)",
    )

    # ------------------------------------------------------------------
    # Anthropic Claude (untuk AI generate pesan outreach)
    # ------------------------------------------------------------------
    ANTHROPIC_API_KEY: str = Field(
        default="",
        description="Anthropic API key untuk generate pesan outreach dengan Claude",
    )
    ANTHROPIC_MODEL: str = Field(
        default="claude-3-5-haiku-20241022",
        description="Model Claude yang digunakan",
    )

    # ------------------------------------------------------------------
    # Hugging Face (IndoBERT NLP)
    # ------------------------------------------------------------------
    HF_API_TOKEN: str = Field(
        default="",
        description="Hugging Face API token untuk IndoBERT zero-shot classification",
    )

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key used to sign JWT tokens",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm used for JWT signing",
    )
    JWT_EXPIRE_MINUTES: int = Field(
        default=30,
        description="JWT token expiry in minutes (also used as session timeout)",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
