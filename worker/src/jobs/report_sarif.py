# Job: generate_sarif_export (§9.2)
# Input: {session_id, tenant_id, job_id}
# Output: SARIF v2.1.0 JSON file
# Timeout: 2min, Retries: 3
# Idempotent: checks for existing completed output before processing (§9.3)
#
# SARIF (Static Analysis Results Interchange Format) is the standard
# format for integrating with GitHub Code Scanning, Azure DevOps, etc.
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import text

from src.config import get_config
from src.db import async_session_factory

logger = structlog.get_logger()

# SARIF severity mapping (BeGuardit → SARIF)
SARIF_LEVELS = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "none",
}


async def generate_sarif_export(ctx: dict, *, job_id: str, session_id: str, tenant_id: str) -> dict:
    """Generate a SARIF v2.1.0 JSON export.

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
            # ── Fetch findings ────────────────────────────────────────
            findings = (await db.execute(
                text(
                    "SELECT id, rule_id, title, description, severity, category, "
                    "remediation FROM findings "
                    "WHERE session_id = :sid AND tenant_id = :tid"
                ),
                {"sid": session_id, "tid": tenant_id},
            )).fetchall()

            # ── Build SARIF document ──────────────────────────────────
            rules = []
            results = []
            seen_rules = set()

            for f in findings:
                # Rule definition (deduplicated)
                if f.rule_id not in seen_rules:
                    seen_rules.add(f.rule_id)
                    rule_def = {
                        "id": f.rule_id,
                        "name": f.rule_id,
                        "shortDescription": {"text": f.title},
                    }
                    if f.remediation:
                        rule_def["help"] = {"text": f.remediation}
                    rules.append(rule_def)

                # Result
                results.append({
                    "ruleId": f.rule_id,
                    "level": SARIF_LEVELS.get(f.severity, "warning"),
                    "message": {"text": f.description or f.title},
                    "properties": {
                        "severity": f.severity,
                        "category": f.category,
                        "beguardit_finding_id": str(f.id),
                    },
                })

            sarif = {
                "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
                "version": "2.1.0",
                "runs": [
                    {
                        "tool": {
                            "driver": {
                                "name": "BeGuardit",
                                "version": "1.0.0",
                                "informationUri": "https://beguardit.com",
                                "rules": rules,
                            }
                        },
                        "results": results,
                        "invocations": [
                            {
                                "executionSuccessful": True,
                                "startTimeUtc": datetime.now(timezone.utc).isoformat(),
                            }
                        ],
                    }
                ],
            }

            # ── Write to disk ─────────────────────────────────────────
            report_dir = Path(config.REPORT_STORAGE_PATH) / str(tenant_id)
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(report_dir / f"{job_id}.sarif.json")

            with open(output_path, "w", encoding="utf-8") as fp:
                json.dump(sarif, fp, indent=2)

            # ── Mark completed ────────────────────────────────────────
            await db.execute(
                text(
                    "UPDATE report_jobs SET status = 'completed', output_path = :path, "
                    "completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "path": output_path, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            log.info("sarif_export_generated", output_path=output_path, findings=len(findings))
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
            log.error("sarif_export_failed", error=str(exc))
            raise
