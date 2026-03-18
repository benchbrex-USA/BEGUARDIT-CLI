# Auth domain — API router
# Source: ARCH-002-2026-03-17, Section 8.2
#
# POST /register        — create account + tenant, set session cookie
# POST /login           — authenticate, set session cookie
# POST /logout          — clear session
# GET  /me              — current user + tenant + memberships
# POST /switch-tenant   — switch active tenant context
# POST /forgot-password — request password reset (no auth)
# POST /reset-password  — confirm password reset (no auth)
from __future__ import annotations

import structlog
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
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetResponse,
    RegisterRequest,
    SwitchTenantRequest,
    UserOut,
)
from src.auth.service import (
    confirm_password_reset,
    login_user,
    logout_user,
    register_user,
    request_password_reset,
    switch_tenant,
)
from src.core.config import get_settings
from src.core.database import get_db

logger = structlog.get_logger()

router = APIRouter(tags=["auth"])


def _set_session_cookie(response: Response, token: str, csrf_token: str) -> None:
    """Set the HttpOnly session cookie and non-HttpOnly CSRF cookie."""
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
    # CSRF cookie — readable by JavaScript so the portal can send
    # the value back in the X-CSRF-Token header.
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="lax",
        max_age=settings.SESSION_TTL_SECONDS,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    response.delete_cookie(key="csrf_token", path="/")


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user, tenant, membership, token, csrf = await register_user(
        db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
        tenant_name=body.tenant_name,
        tenant_slug=body.tenant_slug,
    )
    _set_session_cookie(response, token, csrf)
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
    user, membership, token, csrf = await login_user(
        db,
        email=body.email,
        password=body.password,
    )
    _set_session_cookie(response, token, csrf)
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
    membership, token, csrf = await switch_tenant(
        db,
        user_id=user.id,
        target_tenant_id=body.tenant_id,
        current_token_hash=session.token_hash,
    )
    _set_session_cookie(response, token, csrf)
    return AuthResponse(
        user=UserOut.model_validate(user),
        tenant_id=membership.tenant_id,
        role=membership.role,
    )


# ---------------------------------------------------------------------------
# POST /forgot-password
# ---------------------------------------------------------------------------

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(
    body: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset link.

    Always returns 200 to prevent email enumeration.
    In dev mode, the raw token is included in the response for testing.
    """
    token = await request_password_reset(db, body.email)

    settings = get_settings()
    dev_mode = settings.LOG_LEVEL == "DEBUG"

    return PasswordResetResponse(
        message="If an account with that email exists, a reset link has been sent.",
        token=token if dev_mode else None,
    )


# ---------------------------------------------------------------------------
# POST /reset-password
# ---------------------------------------------------------------------------

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using a valid reset token."""
    success = await confirm_password_reset(db, body.token, body.new_password)
    if not success:
        from src.core.exceptions import ValidationError
        raise ValidationError("Invalid or expired reset token.")
    return MessageResponse(message="Password has been reset successfully.")
