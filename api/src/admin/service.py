# Admin domain — business logic
# Source: ARCH-002-2026-03-17, Section 6.6
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.models import AuditLog
from src.auth.models import Membership, User
from src.core.exceptions import ForbiddenError, NotFoundError

logger = structlog.get_logger()


# ── User management ─────────────────────────────────────────────────

async def list_users(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> tuple[list[dict], int]:
    """List all users who are members of the given tenant.

    Returns dicts with user fields + their role in this tenant.
    """
    base = (
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.tenant_id == tenant_id)
    )

    if is_active is not None:
        base = base.where(User.is_active.is_(is_active))

    # Count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Fetch page
    rows_q = base.order_by(User.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(rows_q)).all()

    results = []
    for user, role in rows:
        results.append({
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "role": role,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
        })

    return results, total


async def update_user(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    target_user_id: uuid.UUID,
    acting_user_id: uuid.UUID,
    role: str | None = None,
    is_active: bool | None = None,
    display_name: str | None = None,
) -> dict:
    """Update a user's role, active status, or display name within a tenant."""
    # Fetch membership
    membership = (await db.execute(
        select(Membership).where(
            Membership.user_id == target_user_id,
            Membership.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()

    if not membership:
        raise NotFoundError("User not found in this tenant.")

    user = (await db.execute(
        select(User).where(User.id == target_user_id)
    )).scalar_one_or_none()

    if not user:
        raise NotFoundError("User not found.")

    # Prevent self-demotion from admin
    if target_user_id == acting_user_id and role and role != "admin" and membership.role == "admin":
        raise ForbiddenError("Cannot demote yourself from admin.")

    # Last-admin guard
    if role and role != "admin" and membership.role == "admin":
        admin_count = (await db.execute(
            select(func.count()).where(
                Membership.tenant_id == tenant_id,
                Membership.role == "admin",
            )
        )).scalar_one()
        if admin_count <= 1:
            raise ForbiddenError("Cannot change role: this is the last admin.")

    # Prevent deactivating the last admin
    if is_active is False and membership.role == "admin":
        admin_count = (await db.execute(
            select(func.count())
            .select_from(Membership)
            .join(User, Membership.user_id == User.id)
            .where(
                Membership.tenant_id == tenant_id,
                Membership.role == "admin",
                User.is_active.is_(True),
            )
        )).scalar_one()
        if admin_count <= 1:
            raise ForbiddenError("Cannot deactivate the last active admin.")

    # Apply changes
    if role is not None:
        membership.role = role
    if is_active is not None:
        user.is_active = is_active
    if display_name is not None:
        user.display_name = display_name

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info(
        "admin_user_updated",
        target_user_id=str(target_user_id),
        acting_user_id=str(acting_user_id),
        role=role,
        is_active=is_active,
    )

    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "role": membership.role,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


# ── Audit log ────────────────────────────────────────────────────────

async def list_audit_logs(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    action: str | None = None,
    user_id: uuid.UUID | None = None,
) -> tuple[list[AuditLog], int]:
    """List audit log entries for a tenant, newest first."""
    base = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if action:
        base = base.where(AuditLog.action == action)
    if user_id:
        base = base.where(AuditLog.user_id == user_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)

    return list(result.scalars().all()), total


async def create_audit_entry(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | str | None = None,
    detail: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    """Append an audit log entry. Called by other services."""
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry
