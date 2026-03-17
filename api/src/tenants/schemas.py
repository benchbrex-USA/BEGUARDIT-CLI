# Tenants domain — Pydantic request / response schemas
# Source: ARCH-002-2026-03-17, Section 8.2
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------

class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9][a-z0-9\-]*$")


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    plan: str | None = Field(default=None, max_length=50)
    settings: dict | None = None


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    plan: str
    settings: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

class AddMemberRequest(BaseModel):
    email: str = Field(max_length=320)
    role: str = Field(default="viewer", pattern=r"^(admin|operator|viewer)$")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(pattern=r"^(admin|operator|viewer)$")


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    display_name: str | None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
