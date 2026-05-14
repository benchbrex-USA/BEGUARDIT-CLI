# Tests for main application — health and readiness endpoints
# Source: ARCH-002-2026-03-17, Section 6.7
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Verify liveness probe returns 200 OK and status: ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@patch("src.main.engine")
@patch("src.main.redis_pool")
async def test_readiness_endpoint_success(mock_redis, mock_engine, client):
    """Verify readiness probe returns 200 OK when all systems are healthy."""
    # Mock Database
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

    # Mock Redis
    mock_redis.ping = AsyncMock(return_value=True)

    # Mock Worker (heartbeat < 90s)
    now = datetime.now(timezone.utc)
    mock_redis.hgetall = AsyncMock(return_value={"last_seen": now.isoformat()})

    response = await client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json() == {"db": True, "redis": True, "worker": True}


@pytest.mark.asyncio
@patch("src.main.engine")
@patch("src.main.redis_pool")
async def test_readiness_endpoint_db_failure(mock_redis, mock_engine, client):
    """Verify readiness probe returns 503 when Database is down."""
    # Database fails
    mock_engine.connect.side_effect = Exception("DB connection error")

    # Redis and Worker are OK
    mock_redis.ping = AsyncMock(return_value=True)
    now = datetime.now(timezone.utc)
    mock_redis.hgetall = AsyncMock(return_value={"last_seen": now.isoformat()})

    response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"db": False, "redis": True, "worker": True}


@pytest.mark.asyncio
@patch("src.main.engine")
@patch("src.main.redis_pool")
async def test_readiness_endpoint_redis_failure(mock_redis, mock_engine, client):
    """Verify readiness probe returns 503 when Redis is down."""
    # Database is OK
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)

    # Redis fails
    mock_redis.ping.side_effect = Exception("Redis connection error")
    # Worker check also uses redis_pool.hgetall, so it will also fail
    mock_redis.hgetall.side_effect = Exception("Redis connection error")

    response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"db": True, "redis": False, "worker": False}


@pytest.mark.asyncio
@patch("src.main.engine")
@patch("src.main.redis_pool")
async def test_readiness_endpoint_worker_failure_stale(mock_redis, mock_engine, client):
    """Verify readiness probe returns 503 when worker heartbeat is stale."""
    # Database and Redis are OK
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_redis.ping = AsyncMock(return_value=True)

    # Worker heartbeat is old (> 90s)
    stale_time = datetime.now(timezone.utc) - timedelta(seconds=100)
    mock_redis.hgetall = AsyncMock(return_value={"last_seen": stale_time.isoformat()})

    response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"db": True, "redis": True, "worker": False}


@pytest.mark.asyncio
@patch("src.main.engine")
@patch("src.main.redis_pool")
async def test_readiness_endpoint_worker_failure_missing(mock_redis, mock_engine, client):
    """Verify readiness probe returns 503 when worker heartbeat is missing."""
    # Database and Redis are OK
    mock_conn = AsyncMock()
    mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_redis.ping = AsyncMock(return_value=True)

    # Worker heartbeat is missing from Redis
    mock_redis.hgetall = AsyncMock(return_value={})

    response = await client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json() == {"db": True, "redis": True, "worker": False}
