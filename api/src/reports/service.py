# Reports domain — business logic
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

import uuid

import structlog
from arq.connections import ArqRedis, create_pool, RedisSettings
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.models import AssessmentSession
from src.core.exceptions import ForbiddenError, NotFoundError
from src.reports.models import ReportJob

logger = structlog.get_logger()

# Job function name mapping per report format
_FORMAT_TO_JOB = {
    "html": "generate_html_report",
    "pdf": "generate_pdf_report",
    "sarif": "generate_sarif_export",
    "json": "generate_sarif_export",  # JSON canonical uses SARIF path
}

_arq_pool: ArqRedis | None = None


async def _get_arq_pool() -> ArqRedis:
    """Lazy-init a shared ARQ Redis connection pool."""
    global _arq_pool
    if _arq_pool is None:
        from urllib.parse import urlparse
        from src.core.config import get_settings

        settings = get_settings()
        redis_url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        parsed = urlparse(redis_url)
        _arq_pool = await create_pool(
            RedisSettings(
                host=parsed.hostname or "localhost",
                port=parsed.port or 6379,
                database=int(parsed.path.lstrip("/") or "0"),
                password=parsed.password,
            )
        )
    return _arq_pool


async def create_report_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    format: str = "html",
) -> ReportJob:
    """Queue a new report generation job."""
    # Verify assessment exists and belongs to tenant
    result = await db.execute(
        select(AssessmentSession).where(
            AssessmentSession.id == session_id,
            AssessmentSession.tenant_id == tenant_id,
        )
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise NotFoundError("Assessment not found.")

    if assessment.status == "running":
        raise ForbiddenError("Cannot generate report for a running assessment.")

    job = ReportJob(
        session_id=session_id,
        tenant_id=tenant_id,
        format=format,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Enqueue the worker job via ARQ
    job_func = _FORMAT_TO_JOB.get(format, "generate_html_report")
    try:
        pool = await _get_arq_pool()
        await pool.enqueue_job(
            job_func,
            job_id=str(job.id),
            session_id=str(session_id),
            tenant_id=str(tenant_id),
            _queue_name="beguardit:reports",
        )
        logger.info("report_job_enqueued", job_id=str(job.id), function=job_func)
    except Exception as exc:
        logger.error("report_job_enqueue_failed", job_id=str(job.id), error=str(exc))

    return job


async def list_report_jobs(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    offset: int = 0,
    limit: int = 50,
    session_id: uuid.UUID | None = None,
) -> tuple[list[ReportJob], int]:
    """List report jobs for a tenant, optionally filtered by session."""
    base = select(ReportJob).where(ReportJob.tenant_id == tenant_id)
    if session_id:
        base = base.where(ReportJob.session_id == session_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows_q = base.order_by(ReportJob.queued_at.desc()).offset(offset).limit(limit)
    result = await db.execute(rows_q)

    return list(result.scalars().all()), total


async def get_report_job(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ReportJob:
    """Fetch a single report job by ID, scoped to tenant."""
    result = await db.execute(
        select(ReportJob).where(
            ReportJob.id == job_id,
            ReportJob.tenant_id == tenant_id,
        )
    )
    job = result.scalar_one_or_none()
    if not job:
        raise NotFoundError("Report job not found.")
    return job
