# Job: export_tenant_data (GDPR data export)
# Source: ARCH-002-2026-03-17, Fix 9.1
# Input: {tenant_id, job_id}
# Output: ZIP archive of all tenant data as JSON; uploaded to storage
# Timeout: 10min, Retries: 2
# Idempotent: checks for existing completed output before processing
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import text

from src.db import async_session_factory
from src.storage import get_storage

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


def _write_json_file(filepath: Path, data: Any) -> None:
    """Synchronous helper for writing JSON files, offloaded to thread."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _create_zip_archive(zip_path: Path, source_dir: Path) -> None:
    """Synchronous helper for creating a ZIP archive, offloaded to thread."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name in os.listdir(source_dir):
            file_path = source_dir / file_name
            if file_path.is_file():
                zf.write(file_path, arcname=file_name)


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
    log = logger.bind(job_id=job_id, tenant_id=tenant_id)
    storage = get_storage()
    storage_key = f"exports/{tenant_id}/{job_id}.zip"

    async with async_session_factory() as db:
        # ── Idempotency check ─────────────────────────────────────────
        job_row = (await db.execute(
            text("SELECT status, output_path FROM data_export_jobs WHERE id = :id AND tenant_id = :tid"),
            {"id": job_id, "tid": tenant_id},
        )).first()

        if job_row and job_row.status == "completed" and job_row.output_path:
            if await storage.exists(job_row.output_path):
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
            # Also export the tenant record itself
            tenant_row = (await db.execute(
                text("SELECT * FROM tenants WHERE id = :tid"),
                {"tid": tenant_id},
            )).first()

            # Users connected to this tenant
            user_rows = (await db.execute(
                text(
                    "SELECT u.* FROM users u "
                    "INNER JOIN memberships m ON m.user_id = u.id "
                    "WHERE m.tenant_id = :tid"
                ),
                {"tid": tenant_id},
            )).fetchall()

            # Prepare data tasks for parallel execution
            data_tasks = []

            # Each tenant-scoped table
            for table_name, col in _TENANT_TABLES:
                rows = (await db.execute(
                    text(f"SELECT * FROM {table_name} WHERE {col} = :tid"),  # noqa: S608
                    {"tid": tenant_id},
                )).fetchall()
                data_tasks.append((f"{table_name}.json", [_serialize_row(r) for r in rows]))

            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                write_tasks = []

                # Add tenant task
                if tenant_row:
                    write_tasks.append(
                        asyncio.to_thread(_write_json_file, tmpdir_path / "tenant.json", _serialize_row(tenant_row))
                    )

                # Add users task
                write_tasks.append(
                    asyncio.to_thread(_write_json_file, tmpdir_path / "users.json", [_serialize_row(r) for r in user_rows])
                )

                # Add table tasks
                for filename, data in data_tasks:
                    write_tasks.append(
                        asyncio.to_thread(_write_json_file, tmpdir_path / filename, data)
                    )

                # Run JSON writes in parallel
                await asyncio.gather(*write_tasks)

                # ── Create ZIP ─────────────────────────────────────────
                # We create the zip in the same temp directory but outside it or just use a named temp file
                with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
                    tmp_zip_path = Path(tmp_zip.name)

                try:
                    await asyncio.to_thread(_create_zip_archive, tmp_zip_path, tmpdir_path)

                    # ── Upload to storage ──────────────────────────────────
                    zip_bytes = await asyncio.to_thread(tmp_zip_path.read_bytes)
                    await storage.upload(storage_key, zip_bytes, content_type="application/zip")
                finally:
                    if tmp_zip_path.exists():
                        await asyncio.to_thread(tmp_zip_path.unlink)

            # ── Mark completed ────────────────────────────────────────
            await db.execute(
                text(
                    "UPDATE data_export_jobs SET status = 'completed', output_path = :path, "
                    "completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "path": storage_key, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            log.info("tenant_data_exported", output_path=storage_key)
            return {"status": "completed", "output_path": storage_key}

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
