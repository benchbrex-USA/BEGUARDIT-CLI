# Auth domain — FastAPI dependencies
# Source: ARCH-002-2026-03-17, ADR-003
#
# get_current_user: reads session cookie → validates → returns (User, Session)
# require_role: factory that enforces minimum RBAC role
from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import Membership, Session, User
from src.auth.service import get_session_by_token
from src.core.database import get_db
from src.core.exceptions import ForbiddenError, NotAuthenticatedError

# Cookie name for session token (HttpOnly, Secure, SameSite=Lax)
SESSION_COOKIE = "bg_session"

# Role hierarchy — higher index = more privileges
_ROLE_HIERARCHY = {"viewer": 0, "operator": 1, "admin": 2}


async def get_current_user(
    request: Request,
    bg_session: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Session]:
    """Extract and validate the session cookie.

    Returns (user, session) or raises NotAuthenticatedError.
    Sets request.state.user and request.state.tenant_id for downstream use.
    """
    if not bg_session:
        raise NotAuthenticatedError()

    session = await get_session_by_token(db, token=bg_session)
    if not session:
        raise NotAuthenticatedError("Session expired or invalid.")

    user = session.user
    if not user.is_active:
        raise ForbiddenError("Account is deactivated.")

    # Populate request state for middleware / downstream handlers
    request.state.user = user
    request.state.tenant_id = session.tenant_id

    return user, session


def require_role(minimum_role: str):
    """Dependency factory that enforces a minimum RBAC role.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    min_level = _ROLE_HIERARCHY.get(minimum_role, 0)

    async def _check(
        request: Request,
        user_session: tuple[User, Session] = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user, session = user_session

        # Look up the user's role in the current tenant
        result = await db.execute(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.tenant_id == session.tenant_id,
            )
        )
        membership = result.scalar_one_or_none()
        if not membership:
            raise ForbiddenError("No membership in current tenant.")

        user_level = _ROLE_HIERARCHY.get(membership.role, 0)
        if user_level < min_level:
            raise ForbiddenError(f"Requires {minimum_role} role or higher.")

        return user

    return _check
