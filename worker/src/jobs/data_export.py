# Job: export_tenant_data (GDPR data export)
# Source: ARCH-002-2026-03-17, Fix 9.1
# Input: {tenant_id, job_id}
# Output: ZIP archive of all tenant data as JSON; uploaded to storage
# Timeout: 10min, Retries: 2
# Idempotent: checks for existing completed output before processing
from __future__ import annotations

import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import structlog
from sqlalchemy import text

from src.config import get_config
from src.db import async_session_factory

logger = structlog.get_logger()

# Tables scoped to a tenant, with their tenant_id column name
_TENANT_TABLES: list[tuple[str, str]] = [
    ("assessment_sessions", "tenant_id"),
    ("assets", "tenant_id"),
    ("evidence", "tenant_id"),
    ("findings", "tenant_id"),
    ("report_jobs", "tenant_id"),
    ("memberships", "tenant_id"),
    ("audit_log", "tenant_id"),
    ("sessions", "tenant_id"),
    ("data_export_jobs", "tenant_id"),
]


def _serialize_row(row) -> dict:
    """Convert a SQLAlchemy row mapping to a JSON-safe dict."""
    result = {}
    for key, value in row._mapping.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, UUID):
            result[key] = str(value)
        else:
            result[key] = value
    return result


async def export_tenant_data(ctx: dict, *, job_id: str, tenant_id: str) -> dict:
    """Export all tenant data to a ZIP archive containing JSON files.

    Idempotent: if the job is already completed and the output file exists,
    returns immediately without reprocessing.
    """
    config = get_config()
    log = logger.bind(job_id=job_id, tenant_id=tenant_id)

    async with async_session_factory() as db:
        # ── Idempotency check ─────────────────────────────────────────
        job_row = (await db.execute(
            text("SELECT status, output_path FROM data_export_jobs WHERE id = :id AND tenant_id = :tid"),
            {"id": job_id, "tid": tenant_id},
        )).first()

        if job_row and job_row.status == "completed" and job_row.output_path:
            if os.path.exists(job_row.output_path):
                log.info("idempotent_skip", output_path=job_row.output_path)
                return {"status": "already_completed", "output_path": job_row.output_path}

        # ── Mark processing ───────────────────────────────────────────
        await db.execute(
            text(
                "UPDATE data_export_jobs SET status = 'processing' WHERE id = :id"
            ),
            {"id": job_id},
        )
        await db.commit()

        try:
            # ── Export each table to JSON ─────────────────────────────
            export_dir = Path(config.REPORT_STORAGE_PATH) / "exports" / str(tenant_id)
            export_dir.mkdir(parents=True, exist_ok=True)
            zip_path = str(export_dir / f"{job_id}.zip")

            # Also export the tenant record itself
            tenant_row = (await db.execute(
                text("SELECT * FROM tenants WHERE id = :tid"),
                {"tid": tenant_id},
            )).first()

            with tempfile.TemporaryDirectory() as tmpdir:
                # Tenant record
                if tenant_row:
                    with open(os.path.join(tmpdir, "tenant.json"), "w", encoding="utf-8") as f:
                        json.dump(_serialize_row(tenant_row), f, indent=2, default=str)

                # Users connected to this tenant
                user_rows = (await db.execute(
                    text(
                        "SELECT u.* FROM users u "
                        "INNER JOIN memberships m ON m.user_id = u.id "
                        "WHERE m.tenant_id = :tid"
                    ),
                    {"tid": tenant_id},
                )).fetchall()
                with open(os.path.join(tmpdir, "users.json"), "w", encoding="utf-8") as f:
                    json.dump([_serialize_row(r) for r in user_rows], f, indent=2, default=str)

                # Each tenant-scoped table
                for table_name, col in _TENANT_TABLES:
                    rows = (await db.execute(
                        text(f"SELECT * FROM {table_name} WHERE {col} = :tid"),  # noqa: S608
                        {"tid": tenant_id},
                    )).fetchall()

                    with open(os.path.join(tmpdir, f"{table_name}.json"), "w", encoding="utf-8") as f:
                        json.dump([_serialize_row(r) for r in rows], f, indent=2, default=str)

                # ── Create ZIP ─────────────────────────────────────────
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_name in os.listdir(tmpdir):
                        file_path = os.path.join(tmpdir, file_name)
                        zf.write(file_path, arcname=file_name)

            # ── Mark completed ────────────────────────────────────────
            await db.execute(
                text(
                    "UPDATE data_export_jobs SET status = 'completed', output_path = :path, "
                    "completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "path": zip_path, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            log.info("tenant_data_exported", output_path=zip_path)
            return {"status": "completed", "output_path": zip_path}

        except Exception as exc:
            await db.execute(
                text(
                    "UPDATE data_export_jobs SET status = 'failed', "
                    "error_message = :msg, completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "msg": str(exc)[:1000], "now": datetime.now(timezone.utc)},
            )
            await db.commit()
            log.error("tenant_data_export_failed", error=str(exc))
            raise
