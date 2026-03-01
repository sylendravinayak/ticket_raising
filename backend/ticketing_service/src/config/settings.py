from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "Ticketing Genie — Ticketing Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Databases ──────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/ticketing_service"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ── Redis / Celery ─────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Auth Service ───────────────────────────────────────────────────────
    AUTH_SERVICE_URL: str = "http://localhost:8001"

    # ── JWT (used only to read claims set by middleware) ────────────────��──
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"

    # ── SLA defaults (minutes) ─────────────────────────────────────────────
    DEFAULT_RESPONSE_TIME_MINUTES: int = 480      # 8 h
    DEFAULT_RESOLUTION_TIME_MINUTES: int = 2880   # 48 h
    DEFAULT_ESCALATION_AFTER_MINUTES: int = 120   # 2 h after breach

    # ── Auto-close ─────────────────────────────────────────────────────────
    AUTO_CLOSE_AFTER_HOURS: int = 72

    # ── CORS ───────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()