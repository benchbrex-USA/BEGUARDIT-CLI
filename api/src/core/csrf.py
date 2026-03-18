# Core — CSRF protection middleware
# Source: ARCH-002-2026-03-17, Section 8.3 (gap fix)
#
# For state-changing methods (POST, PATCH, DELETE), compares the
# X-CSRF-Token request header against the csrf_token stored in the
# server-side session.  Exempt paths (login, register, health, etc.)
# are skipped so unauthenticated endpoints still work.
from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger()

# Paths exempt from CSRF validation — unauthenticated or read-only endpoints
_CSRF_EXEMPT_PATHS: frozenset[str] = frozenset({
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/forgot-password",
    "/api/v1/auth/reset-password",
    "/api/v1/health",
    "/api/v1/ready",
})

# HTTP methods that require CSRF validation
_CSRF_PROTECTED_METHODS: frozenset[str] = frozenset({"POST", "PATCH", "DELETE"})


class CSRFMiddleware(BaseHTTPMiddleware):
    """Validate CSRF tokens on state-changing requests.

    The middleware reads the ``X-CSRF-Token`` header and compares it
    against the ``csrf_token`` column stored in the ``sessions`` table
    for the authenticated user.  On mismatch (or missing token) a
    ``403 Forbidden`` response is returned.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        method = request.method

        # Skip non-state-changing methods and exempt paths
        if method not in _CSRF_PROTECTED_METHODS or path in _CSRF_EXEMPT_PATHS:
            return await call_next(request)

        # Read the CSRF token from the request header
        csrf_header = request.headers.get("X-CSRF-Token")
        if not csrf_header:
            logger.warning("csrf_missing", path=path, method=method)
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_FAILED",
                        "message": "Missing CSRF token.",
                        "detail": None,
                    }
                },
            )

        # Look up the session's csrf_token from the DB
        try:
            import hashlib

            from sqlalchemy import text

            from src.core.database import async_session_factory

            session_cookie = request.cookies.get("bg_session")
            if not session_cookie:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_FAILED",
                            "message": "No active session.",
                            "detail": None,
                        }
                    },
                )

            token_hash = hashlib.sha256(session_cookie.encode()).hexdigest()

            async with async_session_factory() as db_session:
                row = (
                    await db_session.execute(
                        text("SELECT csrf_token FROM sessions WHERE token_hash = :th"),
                        {"th": token_hash},
                    )
                ).first()

            if not row or not row.csrf_token:
                logger.warning("csrf_no_session_token", path=path)
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_FAILED",
                            "message": "Session has no CSRF token.",
                            "detail": None,
                        }
                    },
                )

            if csrf_header != row.csrf_token:
                logger.warning("csrf_mismatch", path=path, method=method)
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "CSRF_FAILED",
                            "message": "CSRF token mismatch.",
                            "detail": None,
                        }
                    },
                )

        except Exception:
            logger.exception("csrf_check_error", path=path)
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "CSRF_FAILED",
                        "message": "CSRF validation error.",
                        "detail": None,
                    }
                },
            )

        return await call_next(request)
