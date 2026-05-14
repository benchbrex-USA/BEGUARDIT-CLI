# Tests for assessments service — session management, findings, assets, evidence
# Source: ARCH-002-2026-03-17, Section 6.3
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.assessments.service import delete_assessment
from src.core.exceptions import ForbiddenError, NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession with chainable execute()."""
    db = AsyncMock()
    db.commit = AsyncMock()
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


def _make_assessment(*, id: uuid.UUID | None = None, tenant_id: uuid.UUID | None = None, status: str = "completed") -> MagicMock:
    """Create a minimal AssessmentSession stub."""
    assessment = MagicMock()
    assessment.id = id or uuid.uuid4()
    assessment.tenant_id = tenant_id or uuid.uuid4()
    assessment.status = status
    return assessment


# ---------------------------------------------------------------------------
# Tests: delete_assessment
# ---------------------------------------------------------------------------

class TestDeleteAssessment:
    @pytest.mark.asyncio
    async def test_delete_successful(self):
        """Successfully deletes an assessment when status is not 'running'."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment(id=assessment_id, tenant_id=tenant_id, status="completed")

        db = _mock_db_session()
        # First execute: get_assessment -> returns assessment
        # Second execute: delete query -> returns nothing
        db.execute = AsyncMock(side_effect=_mock_execute_returns(assessment, None))

        await delete_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

        # Verify calls
        assert db.execute.call_count == 2

        # Verify the first call was for get_assessment (select)
        # Note: We can't easily inspect the SQLAlchemy query object in a unit test without deeper mocking,
        # but we can verify the session was committed.
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found_raises(self):
        """Raises NotFoundError if the assessment does not exist."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()

        db = _mock_db_session()
        # get_assessment returns None
        db.execute = AsyncMock(side_effect=_mock_execute_returns(None))

        with pytest.raises(NotFoundError, match="Assessment not found"):
            await delete_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

        db.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_running_raises(self):
        """Raises ForbiddenError if the assessment is currently running."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment(id=assessment_id, tenant_id=tenant_id, status="running")

        db = _mock_db_session()
        # get_assessment returns a running assessment
        db.execute = AsyncMock(side_effect=_mock_execute_returns(assessment))

        with pytest.raises(ForbiddenError, match="Cannot delete a running assessment"):
            await delete_assessment(db, tenant_id=tenant_id, assessment_id=assessment_id)

        db.commit.assert_not_awaited()
