# Tests for src.core.exceptions — exception hierarchy
import pytest
from src.core.exceptions import (
    BeGuarditError,
    ConflictError,
    ForbiddenError,
    NotAuthenticatedError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_all_inherit_from_base(self):
        for exc_cls in [ValidationError, NotAuthenticatedError, ForbiddenError,
                        NotFoundError, ConflictError, RateLimitError]:
            assert issubclass(exc_cls, BeGuarditError)

    def test_status_codes(self):
        assert ValidationError().status_code == 400
        assert NotAuthenticatedError().status_code == 401
        assert ForbiddenError().status_code == 403
        assert NotFoundError().status_code == 404
        assert ConflictError().status_code == 409
        assert RateLimitError().status_code == 429
        assert BeGuarditError().status_code == 500

    def test_error_codes(self):
        assert ValidationError.error_code == "VALIDATION_ERROR"
        assert NotFoundError.error_code == "NOT_FOUND"
        assert ForbiddenError.error_code == "FORBIDDEN"

    def test_custom_message(self):
        exc = NotFoundError("User not found.")
        assert exc.message == "User not found."
        assert str(exc) == "User not found."

    def test_default_message(self):
        exc = NotFoundError()
        assert exc.message == "Resource not found."

    def test_detail_dict(self):
        exc = ValidationError("Bad input", detail={"field": "email"})
        assert exc.detail == {"field": "email"}
