# Auth domain — business logic
# Source: ARCH-002-2026-03-17, Section 8.2 / ADR-003 / ADR-010
#
# register  — create user + tenant + membership (admin), create session
# login     — verify argon2id, create session
# logout    — delete session
# switch_tenant — verify membership, create new session for target tenant
from __future__ import annotations

import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models import AuditLog
from src.auth.models import Membership, PasswordResetToken, Session, Tenant, User
from src.core.config import get_settings
from src.core.exceptions import ConflictError, ForbiddenError, NotAuthenticatedError, RateLimitError, ValidationError
from src.core.security import generate_csrf_token, generate_session_token, hash_password, hash_token, needs_rehash, verify_password

logger = structlog.get_logger()


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
    tenant_name: str,
    tenant_slug: str,
) -> tuple[User, Tenant, Membership, str, str]:
    """Register a new user, creating their personal tenant.

    Returns (user, tenant, membership, raw_session_token, csrf_token).
    """
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise ConflictError("A user with this email already exists.")

    # Check for existing tenant slug
    existing_tenant = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
    if existing_tenant.scalar_one_or_none():
        raise ConflictError("A tenant with this slug already exists.")

    # Create tenant
    tenant = Tenant(name=tenant_name, slug=tenant_slug)
    db.add(tenant)
    await db.flush()

    # Create user
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    # Create membership (admin for own tenant)
    membership = Membership(user_id=user.id, tenant_id=tenant.id, role="admin")
    db.add(membership)
    await db.flush()

    # Create session
    token, csrf = await _create_session(db, user_id=user.id, tenant_id=tenant.id)

    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)
    await db.refresh(membership)

    logger.info("user_registered", user_id=str(user.id), tenant_id=str(tenant.id))
    return user, tenant, membership, token, csrf


async def login_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> tuple[User, Membership, str, str]:
    """Authenticate a user by email + password.

    Returns (user, active_membership, raw_session_token, csrf_token).
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise NotAuthenticatedError("Invalid email or password.")

    if not user.is_active:
        raise ForbiddenError("Account is deactivated.")

    # Rehash if argon2id parameters changed
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)

    # Pick the first membership as default tenant
    memberships_result = await db.execute(
        select(Membership).where(Membership.user_id == user.id)
    )
    membership = memberships_result.scalars().first()
    if not membership:
        raise ForbiddenError("User has no tenant memberships.")

    # Create session
    token, csrf = await _create_session(db, user_id=user.id, tenant_id=membership.tenant_id)

    await db.commit()
    await db.refresh(user)
    await db.refresh(membership)

    logger.info("user_logged_in", user_id=str(user.id), tenant_id=str(membership.tenant_id))
    return user, membership, token, csrf


async def logout_user(db: AsyncSession, *, token_hash: str) -> None:
    """Delete the session matching the given token hash."""
    await db.execute(delete(Session).where(Session.token_hash == token_hash))
    await db.commit()
    logger.info("user_logged_out")


async def get_session_by_token(db: AsyncSession, *, token: str) -> Session | None:
    """Look up a valid (non-expired) session by raw token."""
    hashed = hash_token(token)
    result = await db.execute(
        select(Session).where(
            Session.token_hash == hashed,
            Session.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def switch_tenant(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    target_tenant_id: uuid.UUID,
    current_token_hash: str,
) -> tuple[Membership, str, str]:
    """Switch the user's active tenant.

    Deletes the current session and creates a new one scoped to the target tenant.
    Returns (membership, new_raw_session_token, csrf_token).
    """
    # Verify user has membership in target tenant
    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.tenant_id == target_tenant_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise ForbiddenError("You are not a member of this tenant.")

    # Delete current session
    await db.execute(delete(Session).where(Session.token_hash == current_token_hash))

    # Create new session for target tenant
    token, csrf = await _create_session(db, user_id=user_id, tenant_id=target_tenant_id)

    await db.commit()
    await db.refresh(membership)

    logger.info("tenant_switched", user_id=str(user_id), tenant_id=str(target_tenant_id))
    return membership, token, csrf


# ---------------------------------------------------------------------------
# Password reset (Fix 2 — ARCH-002)
# ---------------------------------------------------------------------------

_PASSWORD_RE = re.compile(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:'\",.<>?/\\`~])"
)
_RESET_TOKEN_BYTES = 32
_RESET_TTL_SECONDS = 3600  # 1 hour
_RESET_RATE_LIMIT = 3      # max requests per email per hour


def _validate_password_strength(password: str) -> None:
    """Enforce minimum password complexity rules."""
    if len(password) < 12:
        raise ValidationError("Password must be at least 12 characters.")
    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter.")
    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*()\-_=+\[\]{}|;:'\",.<>?/\\`~]", password):
        raise ValidationError("Password must contain at least one special character.")


async def request_password_reset(db: AsyncSession, email: str) -> str | None:
    """Request a password reset for the given email.

    Returns the raw reset token if a user was found, None otherwise.
    The caller should always return HTTP 200 to avoid email enumeration.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    # Rate limit: max 3 requests per email per hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(seconds=3600)
    count_result = await db.execute(
        select(func.count()).select_from(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= one_hour_ago,
        )
    )
    count = count_result.scalar_one()
    if count >= _RESET_RATE_LIMIT:
        raise RateLimitError("Too many password reset requests. Try again later.")

    # Generate token and store hash
    raw_token = secrets.token_urlsafe(_RESET_TOKEN_BYTES)
    token_hashed = hash_token(raw_token)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hashed,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=_RESET_TTL_SECONDS),
    )
    db.add(reset)
    await db.commit()

    logger.info("password_reset_requested", user_id=str(user.id))
    return raw_token


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> bool:
    """Confirm a password reset using the raw token.

    Validates the token, enforces password strength, updates the user's
    password, invalidates all sessions, and creates an audit log entry.
    Returns True on success, False if the token is invalid/expired/used.
    """
    token_hashed = hash_token(token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hashed)
    )
    reset = result.scalar_one_or_none()

    if not reset:
        return False

    now = datetime.now(timezone.utc)

    # Check expiry
    if reset.expires_at < now:
        return False

    # Check already used
    if reset.used_at is not None:
        return False

    # Validate password strength
    _validate_password_strength(new_password)

    # Update user password
    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one()
    user.password_hash = hash_password(new_password)
    user.updated_at = now

    # Mark token as used
    reset.used_at = now

    # Delete all sessions for this user (force re-login)
    await db.execute(delete(Session).where(Session.user_id == user.id))

    # Audit log entry
    audit = AuditLog(
        user_id=user.id,
        action="password_reset",
        resource_type="user",
        resource_id=user.id,
        detail={"method": "token"},
    )
    db.add(audit)
    await db.commit()

    logger.info("password_reset_confirmed", user_id=str(user.id))
    return True


async def _create_session(db: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> tuple[str, str]:
    """Create a new session row and return (raw_session_token, csrf_token)."""
    settings = get_settings()
    token = generate_session_token()
    csrf = generate_csrf_token()
    session = Session(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=hash_token(token),
        csrf_token=csrf,
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_TTL_SECONDS),
    )
    db.add(session)
    await db.flush()
    return token, csrf
