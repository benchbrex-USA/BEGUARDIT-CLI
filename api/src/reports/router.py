# Reports domain — API router
# Source: ARCH-002-2026-03-17, Section 6.4
#
# POST   /              — create report job (queues for worker)
# GET    /              — list report jobs
# GET    /{id}          — report job status
# GET    /{id}/download — download completed report file
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.dependencies import pagination_params
from src.auth.dependencies import get_current_user
from src.auth.models import Session, User
from src.core.database import get_db
from src.core.exceptions import ForbiddenError
from src.reports.dependencies import get_report_job_or_404
from src.reports.models import ReportJob
from src.reports.schemas import CreateReportRequest, ReportJobOut, MessageResponse
from src.reports.service import create_report_job, list_report_jobs

router = APIRouter(tags=["reports"])


# ---------------------------------------------------------------------------
# POST / — create report job
# ---------------------------------------------------------------------------

@router.post("/", response_model=ReportJobOut, status_code=201)
async def create_report(
    body: CreateReportRequest,
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    job = await create_report_job(
        db,
        tenant_id=session.tenant_id,
        session_id=body.session_id,
        format=body.format,
    )
    return ReportJobOut.model_validate(job)


# ---------------------------------------------------------------------------
# GET / — list report jobs
# ---------------------------------------------------------------------------

@router.get("/", response_model=dict)
async def list_reports(
    session_id: uuid.UUID | None = Query(None, description="Filter by assessment session"),
    pagination: tuple[int, int] = Depends(pagination_params),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _, session = user_session
    offset, limit = pagination

    items, total = await list_report_jobs(
        db,
        tenant_id=session.tenant_id,
        offset=offset,
        limit=limit,
        session_id=session_id,
    )
    return {
        "items": [ReportJobOut.model_validate(j) for j in items],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# GET /{id} — report job status
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=ReportJobOut)
async def get_report_status(
    job: ReportJob = Depends(get_report_job_or_404),
):
    return ReportJobOut.model_validate(job)


# ---------------------------------------------------------------------------
# GET /{id}/download — download completed report
# ---------------------------------------------------------------------------

@router.get("/{job_id}/download")
async def download_report(
    job: ReportJob = Depends(get_report_job_or_404),
):
    if job.status != "completed":
        raise ForbiddenError(f"Report is not ready (status: {job.status}).")

    if not job.output_path:
        raise ForbiddenError("Report file path is missing.")

    media_types = {
        "html": "text/html",
        "pdf": "application/pdf",
        "json": "application/json",
        "sarif": "application/json",
    }

    return FileResponse(
        path=job.output_path,
        media_type=media_types.get(job.format, "application/octet-stream"),
        filename=f"beguardit-report-{job.id}.{job.format}",
    )
