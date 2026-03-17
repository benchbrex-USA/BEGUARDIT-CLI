# Core — Redis connection pool
# Source: ARCH-002-2026-03-17, Section 8.4
from __future__ import annotations

from redis.asyncio import Redis, from_url

from src.core.config import get_settings

_settings = get_settings()

redis_pool: Redis = from_url(_settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    """FastAPI dependency — returns the shared Redis connection."""
    return redis_pool
