# Tests for upload router — concurrent scan prevention (Fix 10)
# Source: ARCH-002-2026-03-17, Section 6.4 + Fix 10
from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from src.auth.models import Session, User
from src.core.exceptions import ConflictError


@pytest.mark.asyncio
async def test_upload_assessment_acquires_and_releases_lock():
    """Verify that a lock is acquired before import and released after."""
    # We must patch the router's dependencies or mock the router call directly.
    # Since we want to test the logic inside the router function, we mock its arguments.
    from src.upload.router import upload_assessment

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True
    mock_redis.delete.return_value = 1

    mock_db = AsyncMock()

    # Mock UploadFile
    content = b'{"hostname": "test-host", "session_id": "some-uuid"}'
    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "application/json"
    mock_file.read = AsyncMock(return_value=content)

    # Mock User and Session
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    session = MagicMock(spec=Session)
    session.tenant_id = uuid.uuid4()
    user_session = (user, session)

    # Mock CanonicalReport and import_assessment
    mock_report = MagicMock()
    mock_report.hostname = "test-host"

    with patch("src.upload.router.CanonicalReport.model_validate", return_value=mock_report), \
         patch("src.upload.router.import_assessment", AsyncMock(return_value={
             "session_id": "sid", "findings_imported": 1, "assets_imported": 1, "evidence_imported": 1
         })) as mock_import, \
         patch("secrets.token_hex", return_value="mock-token"):

        await upload_assessment(
            file=mock_file,
            user_session=user_session,
            db=mock_db,
            redis=mock_redis
        )

        # Verify lock key
        expected_lock_key = f"beguardit:scan_lock:{session.tenant_id}:test-host"
        mock_redis.set.assert_called_once_with(expected_lock_key, "mock-token", nx=True, ex=60)

        # Verify import was called
        mock_import.assert_called_once()

        # Verify lock release via eval
        mock_redis.eval.assert_called_once()
        call_args = mock_redis.eval.call_args
        assert expected_lock_key in call_args.args
        assert "mock-token" in call_args.args


@pytest.mark.asyncio
async def test_upload_assessment_raises_conflict_if_locked():
    """Verify ConflictError is raised if Redis lock cannot be acquired."""
    from src.upload.router import upload_assessment

    mock_redis = AsyncMock()
    mock_redis.set.return_value = None  # Acquisition failed

    mock_db = AsyncMock()

    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "application/json"
    mock_file.read = AsyncMock(return_value=b'{"hostname": "locked-host"}')

    user = MagicMock(spec=User)
    session = MagicMock(spec=Session)
    session.tenant_id = uuid.uuid4()
    user_session = (user, session)

    mock_report = MagicMock()
    mock_report.hostname = "locked-host"

    with patch("src.upload.router.CanonicalReport.model_validate", return_value=mock_report), \
         patch("src.upload.router.import_assessment", AsyncMock()) as mock_import:

        with pytest.raises(ConflictError, match="scan is already running"):
            await upload_assessment(
                file=mock_file,
                user_session=user_session,
                db=mock_db,
                redis=mock_redis
            )

        # Import should NOT be called
        mock_import.assert_not_called()
        # Delete should NOT be called because we didn't acquire it
        mock_redis.delete.assert_not_called()


@pytest.mark.asyncio
async def test_upload_assessment_releases_lock_on_error():
    """Verify lock is released even if import_assessment fails."""
    from src.upload.router import upload_assessment

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    mock_db = AsyncMock()
    mock_file = MagicMock(spec=UploadFile)
    mock_file.content_type = "application/json"
    mock_file.read = AsyncMock(return_value=b'{"hostname": "error-host"}')

    user = MagicMock(spec=User)
    session = MagicMock(spec=Session)
    session.tenant_id = uuid.uuid4()
    user_session = (user, session)

    mock_report = MagicMock()
    mock_report.hostname = "error-host"

    with patch("src.upload.router.CanonicalReport.model_validate", return_value=mock_report), \
         patch("src.upload.router.import_assessment", AsyncMock(side_effect=Exception("DB Error"))), \
         patch("secrets.token_hex", return_value="error-token"):

        with pytest.raises(Exception, match="DB Error"):
            await upload_assessment(
                file=mock_file,
                user_session=user_session,
                db=mock_db,
                redis=mock_redis
            )

        # Verify lock release despite the error
        expected_lock_key = f"beguardit:scan_lock:{session.tenant_id}:error-host"
        mock_redis.eval.assert_called_once()
        assert expected_lock_key in mock_redis.eval.call_args.args
        assert "error-token" in mock_redis.eval.call_args.args
