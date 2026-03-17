# Tenants domain — business logic
# Source: ARCH-002-2026-03-17, Section 8.2
#
# CRUD for tenants, member invite / remove / role update.
# All queries are scoped to the caller's tenant_id.
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Membership, Tenant, User
from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------

async def get_tenant(db: AsyncSession, *, tenant_id: uuid.UUID) -> Tenant:
    """Fetch a tenant by ID or raise NotFoundError."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant not found.")
    return tenant


async def update_tenant(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    name: str | None = None,
    plan: str | None = None,
    settings: dict | None = None,
) -> Tenant:
    """Update mutable tenant fields."""
    tenant = await get_tenant(db, tenant_id=tenant_id)

    if name is not None:
        tenant.name = name
    if plan is not None:
        tenant.plan = plan
    if settings is not None:
        tenant.settings = settings

    tenant.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(tenant)

    logger.info("tenant_updated", tenant_id=str(tenant_id))
    return tenant


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

async def list_members(db: AsyncSession, *, tenant_id: uuid.UUID) -> list[Membership]:
    """List all memberships for a tenant."""
    result = await db.execute(
        select(Membership).where(Membership.tenant_id == tenant_id)
    )
    return list(result.scalars().all())


async def add_member(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    email: str,
    role: str = "viewer",
) -> Membership:
    """Invite a user to the tenant by email.

    The user must already have an account.
    """
    # Look up user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("No user found with that email.")

    # Check for existing membership
    existing = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.tenant_id == tenant_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError("User is already a member of this tenant.")

    membership = Membership(user_id=user.id, tenant_id=tenant_id, role=role)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    logger.info("member_added", tenant_id=str(tenant_id), user_id=str(user.id), role=role)
    return membership


async def update_member_role(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    role: str,
    acting_user_id: uuid.UUID,
) -> Membership:
    """Change a member's role within the tenant."""
    result = await db.execute(
        select(Membership).where(
            Membership.id == member_id,
            Membership.tenant_id == tenant_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found.")

    # Prevent demoting yourself from admin (last-admin guard)
    if membership.user_id == acting_user_id and membership.role == "admin" and role != "admin":
        admin_count_result = await db.execute(
            select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.role == "admin",
            )
        )
        admins = admin_count_result.scalars().all()
        if len(admins) <= 1:
            raise ForbiddenError("Cannot remove the last admin from the tenant.")

    membership.role = role
    await db.commit()
    await db.refresh(membership)

    logger.info("member_role_updated", tenant_id=str(tenant_id), member_id=str(member_id), role=role)
    return membership


async def remove_member(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    member_id: uuid.UUID,
    acting_user_id: uuid.UUID,
) -> None:
    """Remove a member from the tenant."""
    result = await db.execute(
        select(Membership).where(
            Membership.id == member_id,
            Membership.tenant_id == tenant_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise NotFoundError("Membership not found.")

    # Prevent removing the last admin
    if membership.role == "admin":
        admin_count_result = await db.execute(
            select(Membership).where(
                Membership.tenant_id == tenant_id,
                Membership.role == "admin",
            )
        )
        admins = admin_count_result.scalars().all()
        if len(admins) <= 1:
            raise ForbiddenError("Cannot remove the last admin from the tenant.")

    # Prevent self-removal
    if membership.user_id == acting_user_id:
        raise ForbiddenError("Cannot remove yourself. Use the leave endpoint or transfer admin first.")

    await db.execute(
        delete(Membership).where(
            Membership.id == member_id,
            Membership.tenant_id == tenant_id,
        )
    )
    await db.commit()

    logger.info("member_removed", tenant_id=str(tenant_id), member_id=str(member_id))
