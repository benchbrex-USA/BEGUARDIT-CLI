# Core — exception hierarchy and global handlers
# Source: ARCH-002-2026-03-17, Section 17
from __future__ import annotations

import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Exception hierarchy (§17.2)
# ---------------------------------------------------------------------------

class BeGuarditError(Exception):
    """Base exception for all BeGuardit domain errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "An unexpected error occurred.", detail: dict | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ValidationError(BeGuarditError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class NotAuthenticatedError(BeGuarditError):
    status_code = 401
    error_code = "NOT_AUTHENTICATED"

    def __init__(self, message: str = "Not authenticated."):
        super().__init__(message)


class ForbiddenError(BeGuarditError):
    status_code = 403
    error_code = "FORBIDDEN"

    def __init__(self, message: str = "Insufficient permissions."):
        super().__init__(message)


class NotFoundError(BeGuarditError):
    status_code = 404
    error_code = "NOT_FOUND"

    def __init__(self, message: str = "Resource not found."):
        super().__init__(message)


class ConflictError(BeGuarditError):
    status_code = 409
    error_code = "CONFLICT"

    def __init__(self, message: str = "Resource already exists."):
        super().__init__(message)


class RateLimitError(BeGuarditError):
    status_code = 429
    error_code = "RATE_LIMITED"

    def __init__(self, message: str = "Too many requests. Try again later."):
        super().__init__(message)


# ---------------------------------------------------------------------------
# Error response schema (§17.1)
# ---------------------------------------------------------------------------

def _error_response(status_code: int, code: str, message: str, detail: dict | None = None, correlation_id: str | None = None) -> JSONResponse:
    body: dict = {
        "error": {
            "code": code,
            "message": message,
            "detail": detail,
        }
    }
    if correlation_id:
        body["error"]["correlation_id"] = correlation_id
    return JSONResponse(status_code=status_code, content=body)


# ---------------------------------------------------------------------------
# Register handlers on app
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(BeGuarditError)
    async def beguardit_error_handler(request: Request, exc: BeGuarditError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", None)
        if exc.status_code >= 500:
            logger.error("unhandled_domain_error", error=exc.message, correlation_id=correlation_id)
        return _error_response(exc.status_code, exc.error_code, exc.message, exc.detail, correlation_id)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        logger.exception("unhandled_exception", correlation_id=correlation_id)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.", correlation_id=correlation_id)
