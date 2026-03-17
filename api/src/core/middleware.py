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
    """Extract tenant_id from the authenticated session and inject into request.state.

    Skips unauthenticated paths (auth/register, auth/login, health, ready).
    Actual session lookup happens in auth dependencies; this middleware just
    initialises request.state placeholders so downstream code can rely on them.
    """

    SKIP_PATHS = frozenset({
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/health",
        "/api/v1/ready",
    })

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.user = None
        request.state.tenant_id = None

        if request.url.path not in self.SKIP_PATHS:
            # Actual tenant resolution is performed by the get_current_tenant
            # dependency (§8.4) which reads the session cookie, validates it,
            # and populates request.state.  This middleware only ensures the
            # attributes exist so downstream code never hits AttributeError.
            pass

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
