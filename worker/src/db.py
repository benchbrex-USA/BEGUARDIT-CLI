# Worker — async database session factory
# Separate from the API's database module so the worker process has its own pool.
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_config

_config = get_config()

engine = create_async_engine(
    _config.DATABASE_URL,
    echo=(_config.LOG_LEVEL == "DEBUG"),
    pool_size=5,
    max_overflow=5,
)

async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
