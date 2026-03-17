# Auth domain — API router
# Source: ARCH-002-2026-03-17, Section 8.2
#
# POST /register       — create account + tenant, set session cookie
# POST /login          — authenticate, set session cookie
# POST /logout         — clear session
# GET  /me             — current user + tenant + memberships
# POST /switch-tenant  — switch active tenant context
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import SESSION_COOKIE, get_current_user
from src.auth.models import Session, User
from src.auth.schemas import (
    AuthResponse,
    LoginRequest,
    MeResponse,
    MembershipOut,
    MessageResponse,
    RegisterRequest,
    SwitchTenantRequest,
    UserOut,
)
from src.auth.service import login_user, logout_user, register_user, switch_tenant
from src.core.config import get_settings
from src.core.database import get_db
from src.core.security import hash_token

router = APIRouter(tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    """Set the HttpOnly session cookie (Secure, SameSite=Lax)."""
    settings = get_settings()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user, tenant, membership, token = await register_user(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        tenant_name=body.tenant_name,
        tenant_slug=body.tenant_slug,
    )
    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserOut.model_validate(user),
        tenant_id=tenant.id,
        role=membership.role,
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user, membership, token = await login_user(
        db,
        email=body.email,
        password=body.password,
    )
    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserOut.model_validate(user),
        tenant_id=membership.tenant_id,
        role=membership.role,
    )


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    await logout_user(db, token_hash=session.token_hash)
    _clear_session_cookie(response)
    return MessageResponse(message="Logged out.")


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=MeResponse)
async def me(
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, session = user_session

    # Build membership list with tenant info
    memberships = [
        MembershipOut(
            tenant_id=m.tenant_id,
            tenant_name=m.tenant.name,
            tenant_slug=m.tenant.slug,
            role=m.role,
        )
        for m in user.memberships
    ]

    # Find current role
    current_role = "viewer"
    for m in user.memberships:
        if m.tenant_id == session.tenant_id:
            current_role = m.role
            break

    return MeResponse(
        user=UserOut.model_validate(user),
        current_tenant_id=session.tenant_id,
        current_role=current_role,
        memberships=memberships,
    )


# ---------------------------------------------------------------------------
# POST /switch-tenant
# ---------------------------------------------------------------------------

@router.post("/switch-tenant", response_model=AuthResponse)
async def switch_tenant_endpoint(
    body: SwitchTenantRequest,
    response: Response,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user, session = user_session
    membership, token = await switch_tenant(
        db,
        user_id=user.id,
        target_tenant_id=body.tenant_id,
        current_token_hash=session.token_hash,
    )
    _set_session_cookie(response, token)
    return AuthResponse(
        user=UserOut.model_validate(user),
        tenant_id=membership.tenant_id,
        role=membership.role,
    )
