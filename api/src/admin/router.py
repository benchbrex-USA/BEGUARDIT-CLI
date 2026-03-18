# Admin domain — router
# Endpoints: GET /users, PATCH /users/:id, GET /audit-log,
#            POST /data-export, DELETE /tenant
# Source: ARCH-002-2026-03-17, Section 6.6 + Fix 9
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.dependencies import require_admin
from src.admin.schemas import (
    AdminUserOut,
    AuditLogOut,
    DataExportJobOut,
    DeleteTenantRequest,
    UpdateUserRequest,
)
from src.admin.service import (
    create_audit_entry,
    create_data_export_job,
    list_audit_logs,
    list_users,
    soft_delete_tenant,
    update_user,
)
from src.assessments.schemas import PaginatedResponse
from src.auth.dependencies import get_current_user
from src.auth.models import Session, User
from src.core.database import get_db

router = APIRouter(tags=["admin"])


@router.get(
    "/users",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_admin)],
)
async def get_users(
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_active: bool | None = Query(None),
):
    """List all users in the current tenant. Requires admin role."""
    _, session = user_session
    users, total = await list_users(
        db,
        tenant_id=session.tenant_id,
        offset=offset,
        limit=limit,
        is_active=is_active,
    )
    return PaginatedResponse(
        items=[AdminUserOut(**u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserOut,
    dependencies=[Depends(require_admin)],
)
async def patch_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role, active status, or display name. Requires admin role."""
    acting_user, session = user_session

    result = await update_user(
        db,
        tenant_id=session.tenant_id,
        target_user_id=user_id,
        acting_user_id=acting_user.id,
        role=body.role,
        is_active=body.is_active,
        display_name=body.display_name,
    )

    # Audit the change
    await create_audit_entry(
        db,
        tenant_id=session.tenant_id,
        user_id=acting_user.id,
        action="user.updated",
        resource_type="user",
        resource_id=str(user_id),
        detail={
            k: v for k, v in body.model_dump(exclude_none=True).items()
        },
    )

    return AdminUserOut(**result)


@router.get(
    "/audit-log",
    response_model=PaginatedResponse,
    dependencies=[Depends(require_admin)],
)
async def get_audit_log(
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    action: str | None = Query(None, description="Filter by action type"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user"),
):
    """List audit log entries for the current tenant. Requires admin role."""
    _, session = user_session
    logs, total = await list_audit_logs(
        db,
        tenant_id=session.tenant_id,
        offset=offset,
        limit=limit,
        action=action,
        user_id=user_id,
    )
    return PaginatedResponse(
        items=[AuditLogOut.model_validate(log) for log in logs],
        total=total,
        offset=offset,
        limit=limit,
    )


# ── Data export (GDPR, Fix 9.1) ─────────────────────────────────────

@router.post(
    "/data-export",
    response_model=DataExportJobOut,
    status_code=202,
    dependencies=[Depends(require_admin)],
)
async def request_data_export(
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue a GDPR data export for the current tenant. Requires admin role.

    Creates a data_export_jobs record with status='queued'. The worker
    picks up the job asynchronously and produces a ZIP archive containing
    all tenant data as JSON files.
    """
    user, session = user_session

    job = await create_data_export_job(
        db,
        tenant_id=session.tenant_id,
        requested_by=user.id,
    )

    # Audit the export request
    await create_audit_entry(
        db,
        tenant_id=session.tenant_id,
        user_id=user.id,
        action="data_export.requested",
        resource_type="data_export_job",
        resource_id=str(job.id),
    )

    return DataExportJobOut.model_validate(job)


# ── Tenant soft-delete (GDPR, Fix 9.2) ──────────────────────────────

@router.delete(
    "/tenant",
    status_code=204,
    dependencies=[Depends(require_admin)],
)
async def delete_tenant(
    body: DeleteTenantRequest,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the current tenant. Requires admin role.

    The request body must include confirm_slug matching the tenant's slug
    as a safety measure.  Sets deleted_at on the tenant and deactivates
    all memberships.  After 30 days, a worker cron job hard-deletes the
    tenant and all associated data.
    """
    user, session = user_session

    await soft_delete_tenant(
        db,
        tenant_id=session.tenant_id,
        confirm_slug=body.confirm_slug,
        acting_user_id=user.id,
    )

    # Audit the deletion
    await create_audit_entry(
        db,
        tenant_id=session.tenant_id,
        user_id=user.id,
        action="tenant.deleted",
        resource_type="tenant",
        resource_id=str(session.tenant_id),
        detail={"confirm_slug": body.confirm_slug},
    )
