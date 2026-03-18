# Admin domain — Pydantic schemas
# Source: ARCH-002-2026-03-17, Section 6.6
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── User management ─────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    """User record visible to tenant admins."""
    id: uuid.UUID
    email: str
    display_name: str | None = None
    is_active: bool
    role: str | None = None  # populated from membership
    last_login_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    """Admin-level user updates (role, active status)."""
    role: str | None = Field(None, pattern=r"^(admin|operator|viewer)$")
    is_active: bool | None = None
    display_name: str | None = Field(None, max_length=255)


# ── Audit log ────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    user_id: uuid.UUID | None = None
    action: str
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    detail: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Data export (GDPR) ──────────────────────────────────────────────

class DataExportJobOut(BaseModel):
    """Response for a queued data export job."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    requested_by: uuid.UUID
    status: str
    output_path: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Tenant deletion ─────────────────────────────────────────────────

class DeleteTenantRequest(BaseModel):
    """Confirmation payload for tenant soft-delete."""
    confirm_slug: str = Field(..., description="Must match the tenant slug to confirm deletion.")
