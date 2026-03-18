# Job: generate_pdf_report (§9.2)
# Input: {session_id, tenant_id, job_id}
# Output: PDF file written to REPORT_STORAGE_PATH
# Timeout: 10min, Retries: 2
# Idempotent: checks for existing completed output before processing (§9.3)
#
# Strategy: generate HTML first, then convert to PDF via weasyprint.
# Falls back to raw HTML if weasyprint is not installed.
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import text

from src.config import get_config
from src.db import async_session_factory
from src.jobs.report_html import generate_html_report

logger = structlog.get_logger()


async def generate_pdf_report(ctx: dict, *, job_id: str, session_id: str, tenant_id: str) -> dict:
    """Generate a PDF report by rendering HTML then converting with weasyprint.

    Idempotency (§9.3): if the job is already completed and the file exists,
    skip regeneration.
    """
    config = get_config()
    log = logger.bind(job_id=job_id, session_id=session_id)

    async with async_session_factory() as db:
        # ── Idempotency check ─────────────────────────────────────────
        job_row = (await db.execute(
            text("SELECT status, output_path FROM report_jobs WHERE id = :id AND tenant_id = :tid"),
            {"id": job_id, "tid": tenant_id},
        )).first()

        if job_row and job_row.status == "completed" and job_row.output_path:
            if os.path.exists(job_row.output_path):
                log.info("idempotent_skip", output_path=job_row.output_path)
                return {"status": "already_completed", "output_path": job_row.output_path}

        # ── Mark processing ───────────────────────────────────────────
        await db.execute(
            text(
                "UPDATE report_jobs SET status = 'processing', started_at = :now, "
                "attempts = attempts + 1 WHERE id = :id"
            ),
            {"id": job_id, "now": datetime.now(timezone.utc)},
        )
        await db.commit()

        try:
            # Step 1: generate the HTML content using the HTML job's internals
            # We fetch all the data the same way
            assessment = (await db.execute(
                text(
                    "SELECT id, mode, status, hostname, scan_config, os_info, "
                    "started_at, completed_at FROM assessment_sessions "
                    "WHERE id = :sid AND tenant_id = :tid"
                ),
                {"sid": session_id, "tid": tenant_id},
            )).first()

            if not assessment:
                raise ValueError(f"Assessment {session_id} not found")

            findings = (await db.execute(
                text(
                    "SELECT id, rule_id, title, description, severity, category, "
                    "remediation, metadata FROM findings "
                    "WHERE session_id = :sid AND tenant_id = :tid "
                    "ORDER BY CASE severity "
                    "  WHEN 'critical' THEN 1 WHEN 'high' THEN 2 "
                    "  WHEN 'medium' THEN 3 WHEN 'low' THEN 4 ELSE 5 END"
                ),
                {"sid": session_id, "tid": tenant_id},
            )).fetchall()

            assets = (await db.execute(
                text(
                    "SELECT id, asset_type, name FROM assets "
                    "WHERE session_id = :sid AND tenant_id = :tid"
                ),
                {"sid": session_id, "tid": tenant_id},
            )).fetchall()

            sev_counts = {}
            for f in findings:
                sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

            from src.jobs.report_html import _render_report_html
            html_content = _render_report_html(
                assessment=assessment,
                findings=findings,
                assets=assets,
                sev_counts=sev_counts,
                session_id=session_id,
            )

            # Step 2: convert HTML → PDF
            report_dir = Path(config.REPORT_STORAGE_PATH) / str(tenant_id)
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(report_dir / f"{job_id}.pdf")

            try:
                from weasyprint import HTML as WeasyprintHTML
                WeasyprintHTML(string=html_content).write_pdf(output_path)
                log.info("pdf_generated_weasyprint", output_path=output_path)
            except ImportError:
                # Fallback: save as HTML with .pdf extension (degraded mode)
                output_path = str(report_dir / f"{job_id}.html")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                log.warning("pdf_fallback_html", reason="weasyprint not installed")

            # ── Mark completed ────────────────────────────────────────
            await db.execute(
                text(
                    "UPDATE report_jobs SET status = 'completed', output_path = :path, "
                    "completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "path": output_path, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            log.info("pdf_report_generated", output_path=output_path, findings=len(findings))
            return {"status": "completed", "output_path": output_path}

        except Exception as exc:
            await db.execute(
                text(
                    "UPDATE report_jobs SET status = 'failed', "
                    "error_message = :msg, completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "msg": str(exc)[:1000], "now": datetime.now(timezone.utc)},
            )
            await db.commit()
            log.error("pdf_report_failed", error=str(exc))
            raise
