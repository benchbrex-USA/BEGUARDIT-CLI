# Tests for upload service — assessment import and validation
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.exceptions import ConflictError, ValidationError
from src.upload.schemas import (
    CanonicalReport,
    UploadAsset,
    UploadEvidence,
    UploadFinding,
    UploadIntegrity,
)


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
    db.refresh = AsyncMock()
    return db


def _mock_execute_returns(*values):
    """Create a sequence of mock execute results."""
    results = []
    for val in values:
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=val)
        result.scalar_one = MagicMock(return_value=val)
        result.first = MagicMock(return_value=val)
        results.append(result)
    return results


def _make_report(
    *,
    session_id: str | None = None,
    hostname: str = "test-host",
    with_integrity: bool = False,
    assets: list | None = None,
    findings: list | None = None,
    evidence: list | None = None,
) -> tuple[CanonicalReport, dict]:
    """Create a CanonicalReport and its raw dict form."""
    sid = session_id or str(uuid.uuid4())
    raw = {
        "schema_version": "1.0",
        "session_id": sid,
        "hostname": hostname,
        "os_info": {"platform": "linux"},
        "scan_config": {"mode": "offline", "profile": "standard"},
        "started_at": "2026-01-01T00:00:00Z",
        "completed_at": "2026-01-01T00:05:00Z",
        "summary": {"total_findings": 1},
        "assets": assets or [{"asset_type": "host", "name": "server-1"}],
        "findings": findings or [
            {
                "id": str(uuid.uuid4()),
                "rule_id": "SEC-001",
                "title": "Test finding",
                "description": "A test finding",
                "severity": "medium",
                "category": "security",
                "evidence_ids": [],
            }
        ],
        "evidence": evidence or [
            {
                "collector": "os-info",
                "type": "system",
                "data": {"kernel": "6.1"},
                "collected_at": "2026-01-01T00:00:00Z",
            }
        ],
        "attack_paths": [],
    }

    if with_integrity:
        body_string = json.dumps(raw, indent=2)
        sha = hashlib.sha256(body_string.encode("utf-8")).hexdigest()
        raw["integrity"] = {"algorithm": "sha256", "hash": sha}

    report = CanonicalReport(**raw)
    return report, raw


# ---------------------------------------------------------------------------
# Tests: import_assessment
# ---------------------------------------------------------------------------

class TestImportAssessment:
    @pytest.mark.asyncio
    async def test_successful_import(self):
        """A valid report is imported with correct entity counts."""
        from src.upload.service import import_assessment

        report, raw = _make_report()
        db = _mock_db_session()
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        # No existing assessment
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        result = await import_assessment(
            db, tenant_id=tenant_id, user_id=user_id, report=report, raw_body=raw
        )

        assert result["findings_imported"] == 1
        assert result["assets_imported"] == 1
        assert result["evidence_imported"] == 1
        assert result["session_id"] is not None
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_integrity_hash_mismatch_raises(self):
        """A tampered report with wrong integrity hash raises ValidationError."""
        from src.upload.service import import_assessment

        report, raw = _make_report(with_integrity=True)
        # Tamper with the raw body after computing the hash
        raw["hostname"] = "tampered-host"

        db = _mock_db_session()

        with pytest.raises(ValidationError, match="hash mismatch"):
            await import_assessment(
                db,
                tenant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                report=report,
                raw_body=raw,
            )

    @pytest.mark.asyncio
    async def test_duplicate_session_raises_conflict(self):
        """Uploading the same session_id twice raises ConflictError."""
        from src.upload.service import import_assessment

        sid = str(uuid.uuid4())
        report, raw = _make_report(session_id=sid)
        db = _mock_db_session()
        tenant_id = uuid.uuid4()

        # Existing assessment found
        existing = MagicMock()
        existing.id = uuid.UUID(sid)
        results = _mock_execute_returns(existing)
        db.execute = AsyncMock(side_effect=results)

        with pytest.raises(ConflictError, match="already exists"):
            await import_assessment(
                db,
                tenant_id=tenant_id,
                user_id=uuid.uuid4(),
                report=report,
                raw_body=raw,
            )

    @pytest.mark.asyncio
    async def test_unknown_severity_defaults_to_info(self):
        """Findings with invalid severity get normalized to 'info'."""
        from src.upload.service import import_assessment

        findings = [
            {
                "id": str(uuid.uuid4()),
                "rule_id": "SEC-999",
                "title": "Unknown severity finding",
                "severity": "unknown_level",
                "category": "test",
                "evidence_ids": [],
            }
        ]
        report, raw = _make_report(findings=findings)
        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        result = await import_assessment(
            db,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            report=report,
            raw_body=raw,
        )

        assert result["findings_imported"] == 1
        # Verify the add call used "info" severity
        added_objs = [call.args[0] for call in db.add.call_args_list]
        finding_objs = [o for o in added_objs if hasattr(o, "severity")]
        assert any(f.severity == "info" for f in finding_objs)

    @pytest.mark.asyncio
    async def test_missing_optional_fields(self):
        """Reports without integrity or completed_at import successfully."""
        from src.upload.service import import_assessment

        report, raw = _make_report()
        raw.pop("completed_at", None)
        report.completed_at = None
        report.integrity = None

        db = _mock_db_session()
        results = _mock_execute_returns(None)
        db.execute = AsyncMock(side_effect=results)

        result = await import_assessment(
            db,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            report=report,
            raw_body=raw,
        )

        assert result["session_id"] is not None
        db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: integrity verification
# ---------------------------------------------------------------------------

class TestIntegrityVerification:
    def test_valid_integrity_passes(self):
        """A report with correct integrity hash passes verification."""
        from src.upload.service import _verify_integrity

        report, raw = _make_report(with_integrity=True)
        # Should not raise
        _verify_integrity(report, raw)

    def test_no_integrity_skips(self):
        """A report without integrity block is silently accepted."""
        from src.upload.service import _verify_integrity

        report, raw = _make_report()
        report.integrity = None
        # Should not raise
        _verify_integrity(report, raw)

    def test_tampered_body_raises(self):
        """Modifying the body after hash computation raises ValidationError."""
        from src.upload.service import _verify_integrity

        report, raw = _make_report(with_integrity=True)
        raw["hostname"] = "evil-host"

        with pytest.raises(ValidationError, match="hash mismatch"):
            _verify_integrity(report, raw)
