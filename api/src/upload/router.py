# Upload domain — router
# Endpoint: POST /assessment (multipart JSON canonical report)
# Source: ARCH-002-2026-03-17, Section 6.4 + Fix 10
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.dependencies import get_current_user, require_role
from src.auth.models import Session, User
from src.core.database import get_db
from src.core.exceptions import ConflictError, ValidationError
from src.core.redis import get_redis
from src.upload.schemas import CanonicalReport, UploadResponse
from src.upload.service import import_assessment

router = APIRouter(tags=["upload"])

# Max upload size: 50 MB
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024


# Distributed lock TTL for concurrent scan prevention (Fix 10)
_SCAN_LOCK_TTL_SECONDS = 60


@router.post(
    "/assessment",
    response_model=UploadResponse,
    status_code=201,
    dependencies=[Depends(require_role("operator"))],
)
async def upload_assessment(
    file: UploadFile = File(..., description="JSON canonical report file"),
    user_session: tuple[User, Session] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Upload a JSON canonical assessment report from the CLI.

    Accepts a multipart file upload containing the JSON canonical report
    produced by `beguardit start --mode online`. Validates the SHA-256
    integrity hash and imports all findings, assets, and evidence.

    Concurrent scan prevention (Fix 10): uses a Redis SET NX EX lock
    keyed on tenant_id + hostname to reject duplicate in-flight scans.

    Requires operator role or higher.
    """
    user, session = user_session

    # Validate content type
    if file.content_type and file.content_type not in (
        "application/json",
        "application/octet-stream",
    ):
        raise ValidationError(f"Expected JSON file, got {file.content_type}")

    # Read and size-check
    contents = await file.read()
    if len(contents) > _MAX_UPLOAD_BYTES:
        raise ValidationError(
            f"File exceeds maximum size of {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    if not contents:
        raise ValidationError("Empty file uploaded.")

    # Parse JSON
    try:
        raw_body = json.loads(contents)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc.msg}")

    # Validate against canonical schema
    try:
        report = CanonicalReport.model_validate(raw_body)
    except Exception as exc:
        raise ValidationError(f"Report validation failed: {exc}")

    # ── Concurrent scan prevention (Fix 10) ───────────────────────
    hostname = report.hostname or "unknown"
    lock_key = f"beguardit:scan_lock:{session.tenant_id}:{hostname}"

    acquired = await redis.set(lock_key, "1", nx=True, ex=_SCAN_LOCK_TTL_SECONDS)
    if not acquired:
        raise ConflictError(
            f"A scan is already running for hostname '{hostname}' in this tenant. "
            "Please wait for it to complete or try again later."
        )

    try:
        result = await import_assessment(
            db,
            tenant_id=session.tenant_id,
            user_id=user.id,
            report=report,
            raw_body=raw_body,
        )
    finally:
        # Release the lock after import completes (success or failure)
        await redis.delete(lock_key)

    return UploadResponse(**result)
