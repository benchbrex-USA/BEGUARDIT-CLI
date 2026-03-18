# Auth domain — Pydantic request / response schemas
# Source: ARCH-002-2026-03-17, Section 8.2
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9\-]*$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SwitchTenantRequest(BaseModel):
    tenant_id: uuid.UUID


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MembershipOut(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    tenant_slug: str
    role: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserOut
    current_tenant_id: uuid.UUID
    current_role: str
    memberships: list[MembershipOut]


class AuthResponse(BaseModel):
    user: UserOut
    tenant_id: uuid.UUID
    role: str


class MessageResponse(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Password reset schemas
# ---------------------------------------------------------------------------

class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordResetResponse(BaseModel):
    message: str
    token: str | None = None  # only populated in dev mode
