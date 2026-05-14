# Tests for assessments service
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.assessments.models import Asset, AssessmentSession
from src.assessments.service import list_assets, list_assessments
from src.core.exceptions import NotFoundError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession with chainable execute()."""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


def _mock_execute_returns(*values):
    """Create a sequence of mock execute results."""
    results = []
    for val in values:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        result.scalar_one = MagicMock(return_value=val)
        # For result.scalars().all()
        result.scalars.return_value.all.return_value = val if isinstance(val, list) else [val]
        results.append(result)
    return results


def _make_assessment_session(*, tenant_id: uuid.UUID | None = None, status: str = "completed") -> MagicMock:
    """Create a minimal AssessmentSession stub."""
    session = MagicMock(spec=AssessmentSession)
    session.id = uuid.uuid4()
    session.tenant_id = tenant_id or uuid.uuid4()
    session.status = status
    return session


def _make_asset(*, tenant_id: uuid.UUID | None = None, session_id: uuid.UUID | None = None, asset_type: str = "host") -> MagicMock:
    """Create a minimal Asset stub."""
    asset = MagicMock(spec=Asset)
    asset.id = uuid.uuid4()
    asset.tenant_id = tenant_id or uuid.uuid4()
    asset.session_id = session_id or uuid.uuid4()
    asset.asset_type = asset_type
    return asset


# ---------------------------------------------------------------------------
# Tests: list_assets
# ---------------------------------------------------------------------------

class TestListAssets:
    @pytest.mark.asyncio
    async def test_list_assets_success(self):
        """Successfully returns paginated assets and total count."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment_session(tenant_id=tenant_id)
        assets = [_make_asset(tenant_id=tenant_id, session_id=assessment_id) for _ in range(3)]

        db = _mock_db_session()
        # 1. get_assessment
        # 2. count query
        # 3. list query
        db.execute.side_effect = _mock_execute_returns(assessment, 3, assets)

        items, total = await list_assets(
            db, tenant_id=tenant_id, assessment_id=assessment_id, offset=0, limit=50
        )

        assert total == 3
        assert len(items) == 3
        assert items == assets
        assert db.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_list_assets_with_type_filter(self):
        """Successfully filters assets by asset_type."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()
        assessment = _make_assessment_session(tenant_id=tenant_id)
        assets = [_make_asset(tenant_id=tenant_id, session_id=assessment_id, asset_type="container")]

        db = _mock_db_session()
        db.execute.side_effect = _mock_execute_returns(assessment, 1, assets)

        items, total = await list_assets(
            db,
            tenant_id=tenant_id,
            assessment_id=assessment_id,
            asset_type="container"
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].asset_type == "container"

    @pytest.mark.asyncio
    async def test_list_assets_assessment_not_found(self):
        """Raises NotFoundError if the assessment does not exist."""
        tenant_id = uuid.uuid4()
        assessment_id = uuid.uuid4()

        db = _mock_db_session()
        # get_assessment returns None
        db.execute.side_effect = _mock_execute_returns(None)

        with pytest.raises(NotFoundError, match="Assessment not found"):
            await list_assets(db, tenant_id=tenant_id, assessment_id=assessment_id)

# ---------------------------------------------------------------------------
# Tests: list_assessments
# ---------------------------------------------------------------------------

class TestListAssessments:
    @pytest.mark.asyncio
    async def test_list_assessments_success(self):
        """Successfully returns paginated assessment sessions."""
        tenant_id = uuid.uuid4()
        sessions = [_make_assessment_session(tenant_id=tenant_id) for _ in range(2)]

        db = _mock_db_session()
        # 1. count query
        # 2. list query
        db.execute.side_effect = _mock_execute_returns(2, sessions)

        items, total = await list_assessments(
            db, tenant_id=tenant_id, offset=0, limit=50
        )

        assert total == 2
        assert len(items) == 2
        assert items == sessions
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_list_assessments_with_status_filter(self):
        """Successfully filters assessments by status."""
        tenant_id = uuid.uuid4()
        sessions = [_make_assessment_session(tenant_id=tenant_id, status="running")]

        db = _mock_db_session()
        db.execute.side_effect = _mock_execute_returns(1, sessions)

        items, total = await list_assessments(
            db, tenant_id=tenant_id, status="running"
        )

        assert total == 1
        assert len(items) == 1
        assert items[0].status == "running"
