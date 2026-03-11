"""
ReturnShield AI — Application Configuration

Uses Pydantic BaseSettings to load configuration from environment
variables and .env files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    # App
    APP_NAME: str = "ReturnShield AI"
    APP_URL: str = "http://localhost:8000"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # Shopify
    SHOPIFY_API_KEY: str = ""
    SHOPIFY_API_SECRET: str = ""
    SHOPIFY_SCOPES: str = (
        "read_products,write_products,read_orders,write_orders,"
        "read_customers,read_returns,write_returns"
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://returnshield:returnshield@localhost:5432/returnshield"
    DATABASE_URL_SYNC: str = (
        "postgresql://returnshield:returnshield@localhost:5432/returnshield"
    )

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Sentry
    SENTRY_DSN: str = ""

    # ML
    ML_MODEL_DIR: str = "./ml_models"
    ML_RETRAIN_INTERVAL_HOURS: int = 168  # Weekly

    @property
    def shopify_scopes_list(self) -> list[str]:
        """Return scopes as a list."""
        return [s.strip() for s in self.SHOPIFY_SCOPES.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()
