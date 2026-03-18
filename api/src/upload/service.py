# Upload domain — business logic
# Source: ARCH-002-2026-03-17, Section 6.4
#
# Accepts a JSON canonical report from the CLI (online mode),
# validates the integrity hash, and persists all entities.
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.assessments.models import Asset, AssessmentSession, Evidence, Finding
from src.core.exceptions import ConflictError, ValidationError
from src.upload.schemas import CanonicalReport

logger = structlog.get_logger()


def _verify_integrity(report: CanonicalReport, raw_body: dict) -> None:
    """Verify the SHA-256 integrity hash embedded in the canonical report.

    The hash covers the entire report *except* the integrity field itself,
    matching how the CLI computes it in json-canonical.js.
    """
    if not report.integrity:
        return  # No integrity block — skip verification (offline uploads)

    body_without_integrity = {k: v for k, v in raw_body.items() if k != "integrity"}
    body_string = json.dumps(body_without_integrity, indent=2)
    computed = hashlib.sha256(body_string.encode("utf-8")).hexdigest()

    if computed != report.integrity.hash:
        raise ValidationError(
            "Integrity check failed: SHA-256 hash mismatch.",
            detail={"expected": report.integrity.hash, "computed": computed},
        )


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


async def import_assessment(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    report: CanonicalReport,
    raw_body: dict,
) -> dict:
    """Import a canonical JSON report into the database.

    Creates an AssessmentSession plus all child Assets, Evidence, and Findings.
    Returns counts of imported entities.
    """
    _verify_integrity(report, raw_body)

    # Check for duplicate session_id within tenant
    from sqlalchemy import select

    existing = (await db.execute(
        select(AssessmentSession.id).where(
            AssessmentSession.tenant_id == tenant_id,
            AssessmentSession.id == uuid.UUID(report.session_id) if _is_uuid(report.session_id) else False,
        )
    )).first()

    session_uuid = uuid.UUID(report.session_id) if _is_uuid(report.session_id) else uuid.uuid4()

    if existing:
        raise ConflictError(f"Assessment {report.session_id} already exists in this tenant.")

    # ── Create AssessmentSession ─────────────────────────────────────
    session = AssessmentSession(
        id=session_uuid,
        tenant_id=tenant_id,
        started_by=user_id,
        mode="online",
        status="completed",
        hostname=report.hostname,
        os_info=report.os_info,
        scan_config=report.scan_config,
        started_at=_parse_ts(report.started_at) or datetime.now(timezone.utc),
        completed_at=_parse_ts(report.completed_at) or datetime.now(timezone.utc),
    )
    db.add(session)

    # ── Import assets ────────────────────────────────────────────────
    for a in report.assets:
        db.add(Asset(
            session_id=session_uuid,
            tenant_id=tenant_id,
            asset_type=a.asset_type,
            name=a.name,
            metadata_=a.metadata,
        ))

    # ── Import evidence ──────────────────────────────────────────────
    evidence_map: dict[int, uuid.UUID] = {}
    for idx, e in enumerate(report.evidence):
        eid = uuid.uuid4()
        evidence_map[idx] = eid
        db.add(Evidence(
            id=eid,
            session_id=session_uuid,
            tenant_id=tenant_id,
            collector_name=e.collector,
            evidence_type=e.type,
            data=e.data,
            collected_at=_parse_ts(e.collected_at) or datetime.now(timezone.utc),
        ))

    # ── Import findings ──────────────────────────────────────────────
    for f in report.findings:
        # Map string evidence IDs to UUIDs where possible
        evidence_ids = []
        for eid_str in f.evidence_ids:
            if _is_uuid(eid_str):
                evidence_ids.append(uuid.UUID(eid_str))

        db.add(Finding(
            session_id=session_uuid,
            tenant_id=tenant_id,
            rule_id=f.rule_id,
            title=f.title,
            description=f.description,
            severity=f.severity if f.severity in ("critical", "high", "medium", "low", "info") else "info",
            category=f.category,
            evidence_ids=evidence_ids,
            remediation=f.remediation,
            metadata_=f.metadata,
        ))

    await db.commit()

    logger.info(
        "assessment_imported",
        session_id=str(session_uuid),
        tenant_id=str(tenant_id),
        findings=len(report.findings),
        assets=len(report.assets),
        evidence=len(report.evidence),
    )

    return {
        "session_id": str(session_uuid),
        "findings_imported": len(report.findings),
        "assets_imported": len(report.assets),
        "evidence_imported": len(report.evidence),
    }


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
