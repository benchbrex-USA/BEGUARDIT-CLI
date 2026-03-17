# Assessments domain — business logic
# Source: ARCH-002-2026-03-17, Section 6.3
#
# All queries are tenant-scoped via tenant_id parameter.
from __future__ import annotations

import uuid

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.models import Asset, AssessmentSession, Evidence, Finding
from src.core.exceptions import ForbiddenError, NotFoundError

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Assessment sessions
# ---------------------------------------------------------------------------

async def list_assessments(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    status: str | None = None,
) -> tuple[list[AssessmentSession], int]:
    """Return paginated assessment sessions for a tenant.

    Returns (items, total_count).
    """
    base = select(AssessmentSession).where(AssessmentSession.tenant_id == tenant_id)
    if status:
        base = base.where(AssessmentSession.status == status)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated rows ordered by newest first
    rows_q = base.order_by(AssessmentSession.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)
    items = list(result.scalars().all())

    return items, total


async def get_assessment(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> AssessmentSession:
    """Fetch a single assessment session scoped to tenant."""
    result = await db.execute(
        select(AssessmentSession).where(
            AssessmentSession.id == assessment_id,
            AssessmentSession.tenant_id == tenant_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Assessment not found.")
    return session


async def delete_assessment(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
) -> None:
    """Delete an assessment and all its child rows (CASCADE)."""
    assessment = await get_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

    # Only allow deletion of completed/failed/cancelled assessments
    if assessment.status == "running":
        raise ForbiddenError("Cannot delete a running assessment. Cancel it first.")

    await db.execute(
        delete(AssessmentSession).where(
            AssessmentSession.id == assessment_id,
            AssessmentSession.tenant_id == tenant_id,
        )
    )
    await db.commit()

    logger.info("assessment_deleted", tenant_id=str(tenant_id), assessment_id=str(assessment_id))


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

async def list_findings(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    severity: str | None = None,
    category: str | None = None,
) -> tuple[list[Finding], int]:
    """Return paginated findings for an assessment."""
    # Ensure assessment belongs to tenant
    await get_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

    base = select(Finding).where(
        Finding.session_id == assessment_id,
        Finding.tenant_id == tenant_id,
    )
    if severity:
        base = base.where(Finding.severity == severity)
    if category:
        base = base.where(Finding.category == category)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(Finding.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)

    return list(result.scalars().all()), total


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

async def list_assets(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    asset_type: str | None = None,
) -> tuple[list[Asset], int]:
    """Return paginated assets for an assessment."""
    await get_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

    base = select(Asset).where(
        Asset.session_id == assessment_id,
        Asset.tenant_id == tenant_id,
    )
    if asset_type:
        base = base.where(Asset.asset_type == asset_type)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(Asset.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)

    return list(result.scalars().all()), total


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

async def list_evidence(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    collector_name: str | None = None,
) -> tuple[list[Evidence], int]:
    """Return paginated evidence for an assessment."""
    await get_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

    base = select(Evidence).where(
        Evidence.session_id == assessment_id,
        Evidence.tenant_id == tenant_id,
    )
    if collector_name:
        base = base.where(Evidence.collector_name == collector_name)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(Evidence.collected_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)

    return list(result.scalars().all()), total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def get_severity_summary(
    db: AsyncSession,
    *,
    assessment_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> dict[str, int]:
    """Return finding counts grouped by severity."""
    result = await db.execute(
        select(Finding.severity, func.count())
        .where(
            Finding.session_id == assessment_id,
            Finding.tenant_id == tenant_id,
        )
        .group_by(Finding.severity)
    )
    return dict(result.all())


async def get_child_counts(
    db: AsyncSession,
    *,
    assessment_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> tuple[int, int, int]:
    """Return (finding_count, asset_count, evidence_count)."""
    finding_count = (await db.execute(
        select(func.count()).where(Finding.session_id == assessment_id, Finding.tenant_id == tenant_id)
    )).scalar_one()

    asset_count = (await db.execute(
        select(func.count()).where(Asset.session_id == assessment_id, Asset.tenant_id == tenant_id)
    )).scalar_one()

    evidence_count = (await db.execute(
        select(func.count()).where(Evidence.session_id == assessment_id, Evidence.tenant_id == tenant_id)
    )).scalar_one()

    return finding_count, asset_count, evidence_count
