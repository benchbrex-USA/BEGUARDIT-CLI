# Core — application settings via pydantic-settings
# Source: ARCH-002-2026-03-17, Section 14.2
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://bg_dev:dev_password@localhost:5432/beguardit"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Security
    SECRET_KEY: str = "change-me-generate-a-real-secret-key"
    SESSION_TTL_SECONDS: int = 86400  # 24 hours

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Worker
    REPORT_STORAGE_PATH: str = "/data/reports"

    # Logging
    LOG_LEVEL: str = "INFO"

    # Rate limiting
    RATE_LIMIT_DEFAULT: int = 100   # requests/min per IP
    RATE_LIMIT_LOGIN: int = 10      # attempts/min per email

    # Password hashing fallback
    BCRYPT_ROUNDS: int = 12

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
