# Tests for password reset flow — service layer
# Source: ARCH-002-2026-03-17, Fix 2 (Password Reset Flow)
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest import mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.auth.models import PasswordResetToken, User
from src.core.exceptions import RateLimitError, ValidationError
from src.core.security import hash_password, hash_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(
    user_id: uuid.UUID | None = None,
    email: str = "alice@example.com",
) -> User:
    """Create a minimal User stub for testing."""
    user = MagicMock(spec=User)
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.password_hash = hash_password("OldPassword1!")
    user.is_active = True
    user.updated_at = datetime.now(timezone.utc)
    return user


def _make_reset_token(
    user_id: uuid.UUID,
    raw_token: str = "test-token-value",
    *,
    expired: bool = False,
    used: bool = False,
) -> PasswordResetToken:
    """Create a PasswordResetToken stub."""
    tok = MagicMock(spec=PasswordResetToken)
    tok.id = uuid.uuid4()
    tok.user_id = user_id
    tok.token_hash = hash_token(raw_token)
    if expired:
        tok.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
    else:
        tok.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    tok.used_at = datetime.now(timezone.utc) if used else None
    tok.created_at = datetime.now(timezone.utc)
    return tok


def _mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession with chainable execute()."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


def _mock_execute_returns(*values):
    """Create a sequence of mock execute results, each with scalar_one_or_none/scalar_one."""
    results = []
    for val in values:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        result.scalar_one = MagicMock(return_value=val)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Tests: request_password_reset
# ---------------------------------------------------------------------------

class TestRequestPasswordReset:
    @pytest.mark.asyncio
    async def test_existing_user_returns_token(self):
        """Requesting a reset for an existing email returns a raw token string."""
        from src.auth.service import request_password_reset

        user = _make_user()
        db = _mock_db_session()

        # First execute: user lookup -> found
        # Second execute: rate limit count -> 0
        results = _mock_execute_returns(user, 0)
        db.execute = AsyncMock(side_effect=results)

        token = await request_password_reset(db, "alice@example.com")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_nonexistent_email_returns_none(self):
        """Requesting a reset for an unknown email returns None (no enumeration)."""
        from src.auth.service import request_password_reset

        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        token = await request_password_reset(db, "nobody@example.com")
        assert token is None
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_rate_limit_raises_error(self):
        """4th reset request within an hour raises RateLimitError."""
        from src.auth.service import request_password_reset

        user = _make_user()
        db = _mock_db_session()

        # First execute: user lookup -> found
        # Second execute: rate limit count -> 3 (already at limit)
        results = _mock_execute_returns(user, 3)
        db.execute = AsyncMock(side_effect=results)

        with pytest.raises(RateLimitError):
            await request_password_reset(db, "alice@example.com")


# ---------------------------------------------------------------------------
# Tests: confirm_password_reset
# ---------------------------------------------------------------------------

class TestConfirmPasswordReset:
    @pytest.mark.asyncio
    async def test_valid_token_resets_password(self):
        """A valid, unexpired, unused token successfully resets the password."""
        from src.auth.service import confirm_password_reset

        user_id = uuid.uuid4()
        raw_token = "valid-reset-token-value"
        user = _make_user(user_id=user_id)
        reset_tok = _make_reset_token(user_id, raw_token)

        db = _mock_db_session()
        # First execute: token lookup -> found
        # Second execute: user lookup -> found
        # Third execute: delete sessions
        results = _mock_execute_returns(reset_tok, user)
        db.execute = AsyncMock(side_effect=[*results, AsyncMock()])

        result = await confirm_password_reset(db, raw_token, "NewSecurePass1!")
        assert result is True
        db.commit.assert_awaited_once()
        # Verify token marked as used
        assert reset_tok.used_at is not None

    @pytest.mark.asyncio
    async def test_expired_token_returns_false(self):
        """An expired token should return False without modifying anything."""
        from src.auth.service import confirm_password_reset

        user_id = uuid.uuid4()
        raw_token = "expired-token-value"
        reset_tok = _make_reset_token(user_id, raw_token, expired=True)

        db = _mock_db_session()
        results = _mock_execute_returns(reset_tok)
        db.execute = AsyncMock(side_effect=results)

        result = await confirm_password_reset(db, raw_token, "NewSecurePass1!")
        assert result is False
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_used_token_returns_false(self):
        """A previously used token should return False."""
        from src.auth.service import confirm_password_reset

        user_id = uuid.uuid4()
        raw_token = "used-token-value"
        reset_tok = _make_reset_token(user_id, raw_token, used=True)

        db = _mock_db_session()
        results = _mock_execute_returns(reset_tok)
        db.execute = AsyncMock(side_effect=results)

        result = await confirm_password_reset(db, raw_token, "NewSecurePass1!")
        assert result is False
        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_weak_password_raises_validation_error(self):
        """A password that doesn't meet strength requirements raises ValidationError."""
        from src.auth.service import confirm_password_reset

        user_id = uuid.uuid4()
        raw_token = "token-for-weak-pass"
        reset_tok = _make_reset_token(user_id, raw_token)

        db = _mock_db_session()
        results = _mock_execute_returns(reset_tok)
        db.execute = AsyncMock(side_effect=results)

        # Too short
        with pytest.raises(ValidationError):
            await confirm_password_reset(db, raw_token, "Short1!")

    @pytest.mark.asyncio
    async def test_nonexistent_token_returns_false(self):
        """A token that doesn't exist in the database returns False."""
        from src.auth.service import confirm_password_reset

        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        result = await confirm_password_reset(db, "nonexistent-token", "NewSecurePass1!")
        assert result is False


# ---------------------------------------------------------------------------
# Tests: password strength validation
# ---------------------------------------------------------------------------

class TestPasswordValidation:
    def test_missing_uppercase(self):
        from src.auth.service import _validate_password_strength
        with pytest.raises(ValidationError, match="uppercase"):
            _validate_password_strength("alllowercase1!")

    def test_missing_digit(self):
        from src.auth.service import _validate_password_strength
        with pytest.raises(ValidationError, match="digit"):
            _validate_password_strength("AllLettersOnly!")

    def test_missing_special_char(self):
        from src.auth.service import _validate_password_strength
        with pytest.raises(ValidationError, match="special"):
            _validate_password_strength("NoSpecialChar1A")

    def test_too_short(self):
        from src.auth.service import _validate_password_strength
        with pytest.raises(ValidationError, match="12 characters"):
            _validate_password_strength("Short1!A")

    def test_valid_password(self):
        from src.auth.service import _validate_password_strength
        # Should not raise
        _validate_password_strength("ValidPassword1!")

    def test_length_boundary_12(self):
        from src.auth.service import _validate_password_strength
        """Exactly 12 characters should pass."""
        _validate_password_strength("Ab1!56789012")

    def test_length_boundary_11(self):
        from src.auth.service import _validate_password_strength
        """11 characters should fail."""
        with pytest.raises(ValidationError, match="at least 12 characters"):
            _validate_password_strength("Ab1!5678901")

    def test_all_standard_special_characters(self):
        from src.auth.service import _validate_password_strength
        """Test each character in the allowed special character set."""
        specials = "!@#$%^&*()-_=+[]{}|;:'\",.<>?/\\`~"
        for char in specials:
            password = f"Upper1{char}LongEnough"
            # Should not raise
            _validate_password_strength(password)

    def test_long_password(self):
        from src.auth.service import _validate_password_strength
        """A very long valid password should pass."""
        _validate_password_strength("A1!" + "a" * 100)

    def test_password_with_space_as_only_potential_special(self):
        from src.auth.service import _validate_password_strength
        """Space is not in the allowed special character set, so it should fail if it's the only one."""
        with pytest.raises(ValidationError, match="special"):
            _validate_password_strength("Upper 12345678")

    def test_unicode_special_not_accepted(self):
        from src.auth.service import _validate_password_strength
        """Unicode symbols like '©' are not in the allowed set, so it should fail if it's the only one."""
        with pytest.raises(ValidationError, match="special"):
            _validate_password_strength("Upper12345678©")

    def test_multiple_special_chars(self):
        from src.auth.service import _validate_password_strength
        """Multiple special characters are fine."""
        _validate_password_strength("Strong!!!!1234A")
