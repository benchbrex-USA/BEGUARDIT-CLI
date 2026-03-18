# Worker configuration — pydantic-settings
# Source: ARCH-002-2026-03-17, Section 9 / 14.2
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://bg_dev:dev_password@localhost:5432/beguardit"
    REDIS_URL: str = "redis://localhost:6379/0"
    REPORT_STORAGE_PATH: str = "/data/reports"
    LOG_LEVEL: str = "INFO"

    # Job defaults
    MAX_JOBS: int = 10
    JOB_TIMEOUT: int = 300       # 5 minutes default
    HEALTH_CHECK_INTERVAL: int = 30


@lru_cache
def get_config() -> WorkerConfig:
    return WorkerConfig()
