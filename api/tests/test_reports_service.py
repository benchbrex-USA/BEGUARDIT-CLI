# Tests for reports service — job creation, listing, retrieval
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.reports.models import ReportJob


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession with chainable execute()."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


def _mock_execute_returns(*values):
    """Create a sequence of mock execute results."""
    results = []
    for val in values:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        result.scalar_one = MagicMock(return_value=val)
        results.append(result)
    return results


def _make_assessment(*, status: str = "completed") -> MagicMock:
    """Create a minimal AssessmentSession stub."""
    assessment = MagicMock()
    assessment.id = uuid.uuid4()
    assessment.tenant_id = uuid.uuid4()
    assessment.status = status
    return assessment


def _make_report_job(
    *,
    tenant_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    format: str = "html",
    status: str = "queued",
) -> MagicMock:
    """Create a minimal ReportJob stub."""
    job = MagicMock(spec=ReportJob)
    job.id = uuid.uuid4()
    job.tenant_id = tenant_id or uuid.uuid4()
    job.session_id = session_id or uuid.uuid4()
    job.format = format
    job.status = status
    job.queued_at = datetime.now(timezone.utc)
    return job


# ---------------------------------------------------------------------------
# Tests: create_report_job
# ---------------------------------------------------------------------------

class TestCreateReportJob:
    @pytest.mark.asyncio
    @patch("src.reports.service._get_arq_pool")
    async def test_creates_job_and_enqueues(self, mock_pool):
        """Successfully creates a report job and enqueues it to ARQ."""
        from src.reports.service import create_report_job

        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()
        assessment = _make_assessment()

        db = _mock_db_session()
        results = _mock_execute_returns(assessment)
        db.execute = AsyncMock(side_effect=results)

        # Mock the job object that gets created
        mock_job = _make_report_job(tenant_id=tenant_id, session_id=session_id)
        db.refresh = AsyncMock(return_value=None)

        # Mock ARQ pool
        arq_pool = AsyncMock()
        mock_pool.return_value = arq_pool

        job = await create_report_job(
            db, tenant_id=tenant_id, session_id=session_id, format="html"
        )

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        arq_pool.enqueue_job.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_assessment_not_found_raises(self):
        """Raises NotFoundError when assessment doesn't exist."""
        from src.reports.service import create_report_job

        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        with pytest.raises(NotFoundError, match="Assessment not found"):
            await create_report_job(
                db,
                tenant_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                format="html",
            )

    @pytest.mark.asyncio
    async def test_running_assessment_raises(self):
        """Raises ForbiddenError when assessment is still running."""
        from src.reports.service import create_report_job

        assessment = _make_assessment(status="running")
        db = _mock_db_session()
        results = _mock_execute_returns(assessment)
        db.execute = AsyncMock(side_effect=results)

        with pytest.raises(ForbiddenError, match="running"):
            await create_report_job(
                db,
                tenant_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                format="html",
            )


# ---------------------------------------------------------------------------
# Tests: list_report_jobs
# ---------------------------------------------------------------------------

class TestListReportJobs:
    @pytest.mark.asyncio
    async def test_returns_paginated_results(self):
        """Returns list of jobs and total count."""
        from src.reports.service import list_report_jobs

        tenant_id = uuid.uuid4()
        jobs = [_make_report_job(tenant_id=tenant_id) for _ in range(3)]

        db = _mock_db_session()
        # First execute: count query -> 3
        # Second execute: list query -> jobs
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=3)

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = jobs

        db.execute = AsyncMock(side_effect=[count_result, list_result])

        result_jobs, total = await list_report_jobs(
            db, tenant_id=tenant_id, offset=0, limit=50
        )

        assert total == 3
        assert len(result_jobs) == 3

    @pytest.mark.asyncio
    async def test_filters_by_session_id(self):
        """Can filter results by session_id."""
        from src.reports.service import list_report_jobs

        tenant_id = uuid.uuid4()
        session_id = uuid.uuid4()

        db = _mock_db_session()
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=1)

        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = [
            _make_report_job(tenant_id=tenant_id, session_id=session_id)
        ]

        db.execute = AsyncMock(side_effect=[count_result, list_result])

        result_jobs, total = await list_report_jobs(
            db, tenant_id=tenant_id, session_id=session_id
        )

        assert total == 1
        assert len(result_jobs) == 1


# ---------------------------------------------------------------------------
# Tests: get_report_job
# ---------------------------------------------------------------------------

class TestGetReportJob:
    @pytest.mark.asyncio
    async def test_returns_job_by_id(self):
        """Returns a report job when it exists."""
        from src.reports.service import get_report_job

        tenant_id = uuid.uuid4()
        job = _make_report_job(tenant_id=tenant_id)

        db = _mock_db_session()
        results = _mock_execute_returns(job)
        db.execute = AsyncMock(side_effect=results)

        result = await get_report_job(db, tenant_id=tenant_id, job_id=job.id)
        assert result == job

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        """Raises NotFoundError when job doesn't exist."""
        from src.reports.service import get_report_job

        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        with pytest.raises(NotFoundError, match="Report job not found"):
            await get_report_job(
                db, tenant_id=uuid.uuid4(), job_id=uuid.uuid4()
            )
