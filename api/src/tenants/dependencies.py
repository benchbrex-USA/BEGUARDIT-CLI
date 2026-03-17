# Tenants domain — FastAPI dependencies
# Source: ARCH-002-2026-03-17, Section 8.2
#
# get_current_tenant: resolves the Tenant object from request.state.tenant_id
# require_tenant_admin: ensures the caller is an admin in the current tenant
from __future__ import annotations

import uuid

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import Membership, Session, Tenant, User
from src.core.database import get_db
from src.core.exceptions import ForbiddenError, NotFoundError


async def get_current_tenant(
    request: Request,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """Resolve the Tenant object for the current session.

    Relies on get_current_user having populated request.state.tenant_id.
    """
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if not tenant_id:
        raise NotFoundError("No tenant context.")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise NotFoundError("Tenant not found.")
    return tenant


async def require_tenant_admin(
    request: Request,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Ensure the caller holds the 'admin' role in the current tenant."""
    user, session = user_session

    result = await db.execute(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.tenant_id == session.tenant_id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership or membership.role != "admin":
        raise ForbiddenError("Tenant admin role required.")

    return user
