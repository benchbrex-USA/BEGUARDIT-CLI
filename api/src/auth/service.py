# Auth domain — business logic
# Source: ARCH-002-2026-03-17, Section 8.2 / ADR-003 / ADR-010
#
# register  — create user + tenant + membership (admin), create session
# login     — verify argon2id, create session
# logout    — delete session
# switch_tenant — verify membership, create new session for target tenant
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Membership, Session, Tenant, User
from src.core.config import get_settings
from src.core.exceptions import ConflictError, ForbiddenError, NotAuthenticatedError
from src.core.security import generate_session_token, hash_password, hash_token, needs_rehash, verify_password

logger = structlog.get_logger()


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    display_name: str | None,
    tenant_name: str,
    tenant_slug: str,
) -> tuple[User, Tenant, Membership, str]:
    """Register a new user, creating their personal tenant.

    Returns (user, tenant, membership, raw_session_token).
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
    token = await _create_session(db, user_id=user.id, tenant_id=tenant.id)

    await db.commit()
    await db.refresh(user)
    await db.refresh(tenant)
    await db.refresh(membership)

    logger.info("user_registered", user_id=str(user.id), tenant_id=str(tenant.id))
    return user, tenant, membership, token


async def login_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> tuple[User, Membership, str]:
    """Authenticate a user by email + password.

    Returns (user, active_membership, raw_session_token).
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
    token = await _create_session(db, user_id=user.id, tenant_id=membership.tenant_id)

    await db.commit()
    await db.refresh(user)
    await db.refresh(membership)

    logger.info("user_logged_in", user_id=str(user.id), tenant_id=str(membership.tenant_id))
    return user, membership, token


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
) -> tuple[Membership, str]:
    """Switch the user's active tenant.

    Deletes the current session and creates a new one scoped to the target tenant.
    Returns (membership, new_raw_session_token).
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
    token = await _create_session(db, user_id=user_id, tenant_id=target_tenant_id)

    await db.commit()
    await db.refresh(membership)

    logger.info("tenant_switched", user_id=str(user_id), tenant_id=str(target_tenant_id))
    return membership, token


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _create_session(db: AsyncSession, *, user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Create a new session row and return the raw (unhashed) token."""
    settings = get_settings()
    token = generate_session_token()
    session = Session(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_TTL_SECONDS),
    )
    db.add(session)
    await db.flush()
    return token
