# Core — middleware pipeline
# Source: ARCH-002-2026-03-17, Section 8.3
#
# Middleware order (reversed in add_middleware, so last-added runs first):
#   1. RequestLoggingMiddleware  — log method, path, status, duration with correlation ID
#   2. CORSMiddleware           — restrict origins to portal domain (no wildcard)
#   3. TenantScopingMiddleware  — extract tenant_id from session cookie into request.state
#   4. RateLimitMiddleware      — Redis sliding window, per-IP and per-email on login
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# 1. Request Logging (order 1)
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
        )

        response.headers["X-Correlation-ID"] = correlation_id
        return response


# ---------------------------------------------------------------------------
# 3. Tenant Scoping (order 3)
# ---------------------------------------------------------------------------

class TenantScopingMiddleware(BaseHTTPMiddleware):
    """Extract tenant_id from the session cookie and inject into request.state.

    For authenticated requests the middleware reads the ``bg_session`` cookie,
    hashes it with SHA-256, and looks it up in the ``sessions`` table.  If the
    session is valid and not expired, ``request.state.tenant_id`` and
    ``request.state.user_id`` are populated so that downstream handlers and
    dependencies can rely on them without an extra DB round-trip.

    Unauthenticated paths are skipped — only the placeholder attributes are
    initialised so code never hits ``AttributeError``.
    """

    SKIP_PATHS = frozenset({
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/health",
        "/api/v1/ready",
    })

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Always initialise state so downstream code can reference safely
        request.state.user = None
        request.state.user_id = None
        request.state.tenant_id = None

        path = request.url.path

        if path not in self.SKIP_PATHS:
            token = request.cookies.get("bg_session")
            if token:
                try:
                    import hashlib
                    from datetime import datetime, timezone

                    from sqlalchemy import select, text

                    from src.core.database import async_session_factory

                    token_hash = hashlib.sha256(token.encode()).hexdigest()

                    async with async_session_factory() as session:
                        row = (
                            await session.execute(
                                text(
                                    "SELECT user_id, tenant_id, expires_at "
                                    "FROM sessions WHERE token_hash = :th"
                                ),
                                {"th": token_hash},
                            )
                        ).first()

                        if row and row.expires_at > datetime.now(timezone.utc):
                            request.state.user_id = row.user_id
                            request.state.tenant_id = row.tenant_id
                except Exception:
                    # Middleware must never block requests — if the lookup
                    # fails the auth dependency will raise 401 later.
                    logger.debug("tenant_scoping_lookup_failed", path=path)

        return await call_next(request)


# ---------------------------------------------------------------------------
# 4. Rate Limiting (order 4)
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-based sliding-window rate limiter.

    - Default: RATE_LIMIT_DEFAULT req/min per IP.
    - Login:   RATE_LIMIT_LOGIN req/min per email on POST /auth/login.

    Raises 429 with Retry-After header when limit exceeded.
    """

    def __init__(self, app, redis_pool=None, default_limit: int = 100, login_limit: int = 10):
        super().__init__(app)
        self.redis_pool = redis_pool
        self.default_limit = default_limit
        self.login_limit = login_limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting if Redis is not configured (e.g. in tests)
        if self.redis_pool is None:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # Determine limit and key
        if path == "/api/v1/auth/login" and request.method == "POST":
            limit = self.login_limit
            # Per-email limiting is enforced in the auth service layer
            # after the body is parsed.  At middleware level we rate-limit
            # by IP to prevent brute-force from a single source.
            key = f"rl:login:{client_ip}"
        else:
            limit = self.default_limit
            key = f"rl:default:{client_ip}"

        window = 60  # 1 minute sliding window

        current = await self.redis_pool.incr(key)
        if current == 1:
            await self.redis_pool.expire(key, window)

        if current > limit:
            ttl = await self.redis_pool.ttl(key)
            return Response(
                content='{"error":{"code":"RATE_LIMITED","message":"Too many requests. Try again later.","detail":null}}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(max(ttl, 1))},
            )

        response = await call_next(request)
        return response
