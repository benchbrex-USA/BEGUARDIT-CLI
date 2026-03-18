# BeGuardit API — Application Factory
# Source: ARCH-002-2026-03-17, Section 8.1
#
# Factory pattern: create_app() builds the FastAPI instance with all
# middleware, routers, and exception handlers.  Enables separate
# configurations for production, testing, and development.
#
# Middleware execution order (§8.3):
#   1. RequestLoggingMiddleware  — correlation ID, method, path, status, duration
#   2. CORSMiddleware           — restrict to portal domain, no wildcard
#   3. TenantScopingMiddleware  — initialise tenant/user state on request
#   4. RateLimitMiddleware      — Redis sliding window (100/min default, 10/min login)
#
# Routers (§6 — full endpoint catalogue):
#   /api/v1/auth         — register, login, logout, me, switch-tenant
#   /api/v1/tenants      — CRUD, member management
#   /api/v1/assessments  — list, detail, findings, assets, evidence, delete
#   /api/v1/reports      — create job, list, status, download
#   /api/v1/upload       — CLI online-mode assessment upload
#   /api/v1/admin        — user management, audit log
#   /api/v1              — health, readiness
from __future__ import annotations

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.tenants.router import router as tenants_router
from src.assessments.router import router as assessments_router
from src.reports.router import router as reports_router
from src.upload.router import router as upload_router
from src.admin.router import router as admin_router
from src.core.config import get_settings
from src.core.exceptions import register_exception_handlers
from src.core.middleware import (
    RateLimitMiddleware,
    RequestLoggingMiddleware,
    TenantScopingMiddleware,
)
from src.core.database import engine
from src.core.redis import redis_pool

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Health / readiness router (§6.7)
# ---------------------------------------------------------------------------

health_router = APIRouter(tags=["health"])


@health_router.get("/health")
async def health():
    """Liveness probe — always returns ok if the process is running."""
    return {"status": "ok"}


@health_router.get("/ready")
async def readiness():
    """Readiness probe — checks DB, Redis, and worker connectivity."""
    checks = {"db": False, "redis": False, "worker": False}

    # Database
    try:
        async with engine.connect() as conn:
            await conn.execute(
                __import__("sqlalchemy").text("SELECT 1")
            )
        checks["db"] = True
    except Exception:
        logger.warning("readiness_check_failed", component="db")

    # Redis
    try:
        await redis_pool.ping()
        checks["redis"] = True
    except Exception:
        logger.warning("readiness_check_failed", component="redis")

    # Worker — check if ARQ queue has active workers
    try:
        info = await redis_pool.info("clients")
        checks["worker"] = info.get("connected_clients", 0) > 1
    except Exception:
        logger.warning("readiness_check_failed", component="worker")

    status_code = 200 if all(checks.values()) else 503
    from starlette.responses import JSONResponse
    return JSONResponse(content=checks, status_code=status_code)


# ---------------------------------------------------------------------------
# Application factory (§8.1)
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="BeGuardit API",
        version="1.0",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        openapi_url="/api/v1/openapi.json",
    )

    # ------------------------------------------------------------------
    # Middleware — added in reverse order because Starlette wraps them
    # as an onion: last-added middleware is the outermost layer and
    # executes first.
    # ------------------------------------------------------------------

    # 4. Rate limiting (innermost — runs last)
    app.add_middleware(
        RateLimitMiddleware,
        redis_pool=redis_pool,
        default_limit=settings.RATE_LIMIT_DEFAULT,
        login_limit=settings.RATE_LIMIT_LOGIN,
    )

    # 3. Tenant scoping
    app.add_middleware(TenantScopingMiddleware)

    # 2. CORS — restricted to portal origin, no wildcard
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )

    # 1. Request logging (outermost — runs first)
    app.add_middleware(RequestLoggingMiddleware)

    # ------------------------------------------------------------------
    # Routers (§6)
    # ------------------------------------------------------------------
    app.include_router(auth_router,        prefix="/api/v1/auth",        tags=["auth"])
    app.include_router(tenants_router,     prefix="/api/v1/tenants",     tags=["tenants"])
    app.include_router(assessments_router, prefix="/api/v1/assessments", tags=["assessments"])
    app.include_router(reports_router,     prefix="/api/v1/reports",     tags=["reports"])
    app.include_router(upload_router,      prefix="/api/v1/upload",     tags=["upload"])
    app.include_router(admin_router,       prefix="/api/v1/admin",      tags=["admin"])
    app.include_router(health_router,      prefix="/api/v1")

    # ------------------------------------------------------------------
    # Exception handlers (§17)
    # ------------------------------------------------------------------
    register_exception_handlers(app)

    # ------------------------------------------------------------------
    # Startup / shutdown events
    # ------------------------------------------------------------------
    @app.on_event("startup")
    async def on_startup():
        logger.info("api_started", cors_origins=settings.cors_origins_list)

    @app.on_event("shutdown")
    async def on_shutdown():
        await redis_pool.aclose()
        await engine.dispose()
        logger.info("api_stopped")

    return app
