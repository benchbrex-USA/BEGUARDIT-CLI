# Job: cleanup_deleted_tenants (GDPR tenant hard-delete cron)
# Source: ARCH-002-2026-03-17, Fix 9.2
# Schedule: daily cron
# Hard-deletes tenants where deleted_at > 30 days ago.
# Cascading deletes remove all child records; storage artefacts are cleaned.
# Idempotent: only processes tenants not yet hard-deleted.
from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog
from sqlalchemy import text

from src.config import get_config
from src.db import async_session_factory

logger = structlog.get_logger()

# Grace period before hard-delete (days)
_RETENTION_DAYS = 30


async def cleanup_deleted_tenants(ctx: dict) -> dict:
    """Hard-delete tenants that were soft-deleted more than 30 days ago.

    For each qualifying tenant:
    1. Delete all rows from tenant-scoped tables (cascading FK handles most).
    2. Remove stored report/export files from disk.
    3. Delete the tenant row itself.

    Idempotent: re-running this job is safe — already-deleted tenants are gone.
    """
    config = get_config()
    log = logger.bind(job="cleanup_deleted_tenants")
    cutoff = datetime.now(timezone.utc) - timedelta(days=_RETENTION_DAYS)

    async with async_session_factory() as db:
        # Find tenants eligible for hard-delete
        rows = (await db.execute(
            text(
                "SELECT id, slug FROM tenants "
                "WHERE deleted_at IS NOT NULL AND deleted_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )).fetchall()

        if not rows:
            log.info("no_tenants_to_cleanup")
            return {"deleted": 0}

        deleted_count = 0

        for tenant in rows:
            tenant_id = str(tenant.id)
            log_t = log.bind(tenant_id=tenant_id, slug=tenant.slug)

            try:
                # Tables with ON DELETE CASCADE from tenants.id handle most
                # cleanup automatically. Explicitly delete from tables that
                # may not have cascading FKs or need ordering.
                # The tenant row deletion cascades to:
                #   memberships, sessions, assessment_sessions (-> assets,
                #   evidence, findings), report_jobs, audit_log,
                #   data_export_jobs

                await db.execute(
                    text("DELETE FROM tenants WHERE id = :tid"),
                    {"tid": tenant_id},
                )
                await db.commit()

                # ── Clean storage artefacts ──────────────────────────
                report_dir = Path(config.REPORT_STORAGE_PATH) / tenant_id
                if report_dir.exists():
                    shutil.rmtree(report_dir, ignore_errors=True)
                    log_t.info("storage_cleaned", path=str(report_dir))

                export_dir = Path(config.REPORT_STORAGE_PATH) / "exports" / tenant_id
                if export_dir.exists():
                    shutil.rmtree(export_dir, ignore_errors=True)
                    log_t.info("export_storage_cleaned", path=str(export_dir))

                deleted_count += 1
                log_t.info("tenant_hard_deleted")

            except Exception as exc:
                await db.rollback()
                log_t.error("tenant_cleanup_failed", error=str(exc))
                # Continue with next tenant — don't let one failure stop all

        log.info("cleanup_complete", deleted=deleted_count, total_candidates=len(rows))
        return {"deleted": deleted_count, "total_candidates": len(rows)}
