# Tests for assessments domain — service and router layers
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.assessments.models import AssessmentSession, Evidence
from src.core.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession with chainable execute()."""
    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.execute = AsyncMock()
    return db


def _mock_execute_returns(*values):
    """Create a sequence of mock execute results."""
    results = []
    for val in values:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        result.scalar_one = MagicMock(return_value=val)
        result.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=val if isinstance(val, list) else [val])))
        results.append(result)
    return results


def _make_assessment(*, id: uuid.UUID | None = None, tenant_id: uuid.UUID | None = None, status: str = "completed") -> MagicMock:
    """Create a minimal AssessmentSession stub."""
    assessment = MagicMock()
    assessment.id = id or uuid.uuid4()
    assessment.tenant_id = tenant_id or uuid.uuid4()
    assessment.status = status
    assessment.created_at = datetime.now(timezone.utc)
    return assessment


def _make_evidence(
    *,
    id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    collector_name: str = "test-collector",
) -> MagicMock:
    """Create a minimal Evidence stub."""
    ev = MagicMock()
    ev.id = id or uuid.uuid4()
    ev.session_id = session_id or uuid.uuid4()
    ev.tenant_id = tenant_id or uuid.uuid4()
    ev.collector_name = collector_name
    ev.evidence_type = "json"
    ev.data = {"key": "value"}
    ev.collected_at = datetime.now(timezone.utc)
    return ev


# ---------------------------------------------------------------------------
# Tests: list_evidence (Service)
# ---------------------------------------------------------------------------

class TestListEvidence:
    @pytest.mark.asyncio
    async def test_list_evidence_success(self):
        """Successfully list evidence for an assessment."""
        from src.assessments.service import list_evidence

        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment(id=assessment_id, tenant_id=tenant_id)
        evidence_list = [_make_evidence(session_id=assessment_id, tenant_id=tenant_id) for _ in range(2)]

        db = _mock_db_session()

        # 1. get_assessment check
        # 2. count query
        # 3. rows query
        count_res = MagicMock()
        count_res.scalar_one.return_value = 2

        rows_res = MagicMock()
        rows_res.scalars.return_value.all.return_value = evidence_list

        db.execute.side_effect = [
            _mock_execute_returns(assessment)[0],
            count_res,
            rows_res
        ]

        items, total = await list_evidence(
            db, tenant_id=tenant_id, assessment_id=assessment_id, offset=0, limit=50
        )

        assert total == 2
        assert len(items) == 2
        assert items == evidence_list

    @pytest.mark.asyncio
    async def test_list_evidence_with_filter(self):
        """Successfully list evidence filtered by collector name."""
        from src.assessments.service import list_evidence

        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment(id=assessment_id, tenant_id=tenant_id)

        db = _mock_db_session()

        count_res = MagicMock()
        count_res.scalar_one.return_value = 1

        rows_res = MagicMock()
        rows_res.scalars.return_value.all.return_value = [_make_evidence(collector_name="specific-collector")]

        db.execute.side_effect = [
            _mock_execute_returns(assessment)[0],
            count_res,
            rows_res
        ]

        items, total = await list_evidence(
            db,
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            collector_name="specific-collector"
        )

        assert total == 1
        assert items[0].collector_name == "specific-collector"

    @pytest.mark.asyncio
    async def test_list_evidence_assessment_not_found(self):
        """Raises NotFoundError if the assessment does not exist for the tenant."""
        from src.assessments.service import list_evidence

        db = _mock_db_session()
        db.execute.return_value = _mock_execute_returns(None)[0]

        with pytest.raises(NotFoundError, match="Assessment not found"):
            await list_evidence(
                db, tenant_id=uuid.uuid4(), assessment_id=uuid.uuid4()
            )


# ---------------------------------------------------------------------------
# Tests: get_evidence (Router)
# ---------------------------------------------------------------------------

class TestGetEvidenceRouter:
    @pytest.mark.asyncio
    async def test_get_evidence_router_success(self):
        """Router correctly calls service and returns paginated response."""
        from src.assessments.router import get_evidence
        from src.auth.models import User, Session

        assessment_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        # Mock dependencies
        mock_user = MagicMock()
        mock_session = MagicMock()
        mock_session.tenant_id = tenant_id
        user_session = (mock_user, mock_session)

        db = _mock_db_session()
        pagination = (0, 50)

        evidence_items = [_make_evidence(session_id=assessment_id, tenant_id=tenant_id)]

        # Patch list_evidence
        with patch("src.assessments.router.list_evidence", new_callable=AsyncMock) as mock_list_evidence:
            mock_list_evidence.return_value = (evidence_items, 1)

            response = await get_evidence(
                assessment_id=assessment_id,
                collector_name=None,
                pagination=pagination,
                user_session=user_session,
                db=db
            )

            assert response.total == 1
            assert len(response.items) == 1
            assert response.offset == 0
            assert response.limit == 50

            mock_list_evidence.assert_awaited_once_with(
                db,
                tenant_id=tenant_id,
                assessment_id=assessment_id,
                offset=0,
                limit=50,
                collector_name=None
            )
