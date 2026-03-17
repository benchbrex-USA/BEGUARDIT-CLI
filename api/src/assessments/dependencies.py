# Assessments domain — FastAPI dependencies
# Source: ARCH-002-2026-03-17, Section 6.3
from __future__ import annotations

import uuid

from fastapi import Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.models import AssessmentSession
from src.assessments.service import get_assessment
from src.auth.dependencies import get_current_user
from src.auth.models import Session, User
from src.core.database import get_db


async def get_assessment_or_404(
    assessment_id: uuid.UUID = Path(..., description="Assessment session ID"),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AssessmentSession:
    """Resolve an assessment by path param, scoped to the caller's tenant."""
    _, session = user_session
    return await get_assessment(db, tenant_id=session.tenant_id, assessment_id=assessment_id)


def pagination_params(
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
) -> tuple[int, int]:
    """Common pagination query params."""
    return offset, limit
