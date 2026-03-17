# Reports domain — FastAPI dependencies
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

import uuid

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user
from src.auth.models import Session, User
from src.core.database import get_db
from src.reports.models import ReportJob
from src.reports.service import get_report_job


async def get_report_job_or_404(
    job_id: uuid.UUID = Path(..., description="Report job ID"),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReportJob:
    """Resolve a report job by path param, scoped to the caller's tenant."""
    _, session = user_session
    return await get_report_job(db, tenant_id=session.tenant_id, job_id=job_id)
