# Tenants domain — API router
# Source: ARCH-002-2026-03-17, Section 8.2
#
# GET    /                — get current tenant details
# PATCH  /                — update tenant (admin only)
# GET    /members         — list members
# POST   /members         — invite member (admin only)
# PATCH  /members/:id     — update member role (admin only)
# DELETE /members/:id     — remove member (admin only)
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import Session, Tenant, User
from src.core.database import get_db
from src.tenants.dependencies import get_current_tenant, require_tenant_admin
from src.tenants.schemas import (
    AddMemberRequest,
    MemberOut,
    MessageResponse,
    TenantOut,
    TenantUpdate,
    UpdateMemberRoleRequest,
)
from src.tenants.service import (
    add_member,
    list_members,
    remove_member,
    update_member_role,
    update_tenant,
)

router = APIRouter(tags=["tenants"])


# ---------------------------------------------------------------------------
# GET / — current tenant details
# ---------------------------------------------------------------------------

@router.get("/", response_model=TenantOut)
async def get_tenant_detail(
    tenant: Tenant = Depends(get_current_tenant),
):
    return TenantOut.model_validate(tenant)


# ---------------------------------------------------------------------------
# PATCH / — update tenant (admin only)
# ---------------------------------------------------------------------------

@router.patch("/", response_model=TenantOut)
async def patch_tenant(
    body: TenantUpdate,
    admin: User = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    updated = await update_tenant(
        db,
        tenant_id=tenant.id,
        name=body.name,
        plan=body.plan,
        settings=body.settings,
    )
    return TenantOut.model_validate(updated)


# ---------------------------------------------------------------------------
# GET /members — list all members
# ---------------------------------------------------------------------------

@router.get("/members", response_model=list[MemberOut])
async def get_members(
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    memberships = await list_members(db, tenant_id=session.tenant_id)
    return [
        MemberOut(
            id=m.id,
            user_id=m.user_id,
            email=m.user.email,
            display_name=m.user.display_name,
            role=m.role,
            created_at=m.created_at,
        )
        for m in memberships
    ]


# ---------------------------------------------------------------------------
# POST /members — invite member (admin only)
# ---------------------------------------------------------------------------

@router.post("/members", response_model=MemberOut, status_code=201)
async def invite_member(
    body: AddMemberRequest,
    admin: User = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    membership = await add_member(
        db,
        tenant_id=tenant.id,
        email=body.email,
        role=body.role,
    )
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        display_name=membership.user.display_name,
        role=membership.role,
        created_at=membership.created_at,
    )


# ---------------------------------------------------------------------------
# PATCH /members/:id — update member role (admin only)
# ---------------------------------------------------------------------------

@router.patch("/members/{member_id}", response_model=MemberOut)
async def patch_member_role(
    member_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    admin: User = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    membership = await update_member_role(
        db,
        tenant_id=tenant.id,
        member_id=member_id,
        role=body.role,
        acting_user_id=admin.id,
    )
    return MemberOut(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        display_name=membership.user.display_name,
        role=membership.role,
        created_at=membership.created_at,
    )


# ---------------------------------------------------------------------------
# DELETE /members/:id — remove member (admin only)
# ---------------------------------------------------------------------------

@router.delete("/members/{member_id}", response_model=MessageResponse)
async def delete_member(
    member_id: uuid.UUID,
    admin: User = Depends(require_tenant_admin),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    await remove_member(
        db,
        tenant_id=tenant.id,
        member_id=member_id,
        acting_user_id=admin.id,
    )
    return MessageResponse(message="Member removed.")
