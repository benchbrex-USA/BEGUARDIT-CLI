# Assessments domain — API router
# Source: ARCH-002-2026-03-17, Section 6.3
#
# GET    /                        — list assessments (paginated, filterable)
# GET    /{id}                    — assessment detail with counts
# GET    /{id}/findings           — paginated findings (filter by severity/category)
# GET    /{id}/assets             — paginated assets (filter by type)
# GET    /{id}/evidence           — paginated evidence (filter by collector)
# DELETE /{id}                    — delete assessment + cascade children
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.dependencies import get_assessment_or_404, pagination_params
from src.assessments.models import AssessmentSession
from src.assessments.schemas import (
    AssetOut,
    AssessmentDetail,
    AssessmentSummary,
    EvidenceOut,
    FindingOut,
    MessageResponse,
    PaginatedResponse,
)
from src.assessments.service import (
    delete_assessment,
    get_child_counts,
    get_severity_summary,
    list_assessments,
    list_assets,
    list_evidence,
    list_findings,
)
from src.auth.dependencies import get_current_user, require_role
from src.auth.models import Session, User
from src.core.database import get_db

router = APIRouter(tags=["assessments"])


# ---------------------------------------------------------------------------
# GET / — list assessments
# ---------------------------------------------------------------------------

@router.get("/", response_model=PaginatedResponse)
async def get_assessments(
    status: str | None = Query(None, description="Filter by status (running, completed, failed, cancelled)"),
    pagination: tuple[int, int] = Depends(pagination_params),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    offset, limit = pagination

    items, total = await list_assessments(
        db,
        tenant_id=session.tenant_id,
        offset=offset,
        limit=limit,
        status=status,
    )
    return PaginatedResponse(
        items=[AssessmentSummary.model_validate(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /{id} — assessment detail
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}", response_model=AssessmentDetail)
async def get_assessment_detail(
    assessment: AssessmentSession = Depends(get_assessment_or_404),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session

    finding_count, asset_count, evidence_count = await get_child_counts(
        db, assessment_id=assessment.id, tenant_id=session.tenant_id,
    )
    severity_summary = await get_severity_summary(
        db, assessment_id=assessment.id, tenant_id=session.tenant_id,
    )

    return AssessmentDetail(
        id=assessment.id,
        mode=assessment.mode,
        status=assessment.status,
        hostname=assessment.hostname,
        scan_config=assessment.scan_config,
        started_at=assessment.started_at,
        completed_at=assessment.completed_at,
        created_at=assessment.created_at,
        started_by=assessment.started_by,
        os_info=assessment.os_info,
        finding_count=finding_count,
        asset_count=asset_count,
        evidence_count=evidence_count,
        severity_summary=severity_summary,
    )


# ---------------------------------------------------------------------------
# GET /{id}/findings
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}/findings", response_model=PaginatedResponse)
async def get_findings(
    assessment_id: uuid.UUID,
    severity: str | None = Query(None, description="Filter: critical, high, medium, low, info"),
    category: str | None = Query(None, description="Filter by category"),
    pagination: tuple[int, int] = Depends(pagination_params),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    offset, limit = pagination

    items, total = await list_findings(
        db,
        tenant_id=session.tenant_id,
        assessment_id=assessment_id,
        offset=offset,
        limit=limit,
        severity=severity,
        category=category,
    )
    return PaginatedResponse(
        items=[
            FindingOut(
                id=f.id,
                session_id=f.session_id,
                rule_id=f.rule_id,
                title=f.title,
                description=f.description,
                severity=f.severity,
                category=f.category,
                evidence_ids=f.evidence_ids,
                remediation=f.remediation,
                metadata=f.metadata_,
                created_at=f.created_at,
            )
            for f in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /{id}/assets
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}/assets", response_model=PaginatedResponse)
async def get_assets(
    assessment_id: uuid.UUID,
    asset_type: str | None = Query(None, description="Filter by asset type"),
    pagination: tuple[int, int] = Depends(pagination_params),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    offset, limit = pagination

    items, total = await list_assets(
        db,
        tenant_id=session.tenant_id,
        assessment_id=assessment_id,
        offset=offset,
        limit=limit,
        asset_type=asset_type,
    )
    return PaginatedResponse(
        items=[
            AssetOut(
                id=a.id,
                session_id=a.session_id,
                asset_type=a.asset_type,
                name=a.name,
                metadata=a.metadata_,
                created_at=a.created_at,
            )
            for a in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# GET /{id}/evidence
# ---------------------------------------------------------------------------

@router.get("/{assessment_id}/evidence", response_model=PaginatedResponse)
async def get_evidence(
    assessment_id: uuid.UUID,
    collector_name: str | None = Query(None, description="Filter by collector name"),
    pagination: tuple[int, int] = Depends(pagination_params),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    offset, limit = pagination

    items, total = await list_evidence(
        db,
        tenant_id=session.tenant_id,
        assessment_id=assessment_id,
        offset=offset,
        limit=limit,
        collector_name=collector_name,
    )
    return PaginatedResponse(
        items=[EvidenceOut.model_validate(e) for e in items],
        total=total,
        offset=offset,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# DELETE /{id}
# ---------------------------------------------------------------------------

@router.delete("/{assessment_id}", response_model=MessageResponse)
async def remove_assessment(
    assessment_id: uuid.UUID,
    user_session: tuple[User, Session] = Depends(get_current_user),
    admin: User = Depends(require_role("operator")),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    await delete_assessment(db, tenant_id=session.tenant_id, assessment_id=assessment_id)
    return MessageResponse(message="Assessment deleted.")
