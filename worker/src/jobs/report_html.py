# Job: generate_html_report (§9.2)
# Input: {session_id, tenant_id, job_id}
# Output: HTML file written to REPORT_STORAGE_PATH; report_jobs row updated
# Timeout: 5min, Retries: 3
# Idempotent: checks for existing completed output before processing (§9.3)
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import select, text

from src.config import get_config
from src.db import async_session_factory

logger = structlog.get_logger()

# Severity color mapping for inline HTML
SEVERITY_COLORS = {
    "critical": ("#dc2626", "#fef2f2"),
    "high": ("#ea580c", "#fff7ed"),
    "medium": ("#d97706", "#fffbeb"),
    "low": ("#2563eb", "#eff6ff"),
    "info": ("#6b7280", "#f9fafb"),
}


async def generate_html_report(ctx: dict, *, job_id: str, session_id: str, tenant_id: str) -> dict:
    """Generate an HTML report for an assessment session.

    Idempotency (§9.3): if the job already has status='completed' and the
    output file exists on disk, we skip regeneration and return early.
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
            # ── Fetch assessment data ─────────────────────────────────
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

            # ── Severity summary ──────────────────────────────────────
            sev_counts = {}
            for f in findings:
                sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

            # ── Render HTML ───────────────────────────────────────────
            html = _render_report_html(
                assessment=assessment,
                findings=findings,
                assets=assets,
                sev_counts=sev_counts,
                session_id=session_id,
            )

            # ── Write to disk ─────────────────────────────────────────
            report_dir = Path(config.REPORT_STORAGE_PATH) / str(tenant_id)
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(report_dir / f"{job_id}.html")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html)

            # ── Mark completed ────────────────────────────────────────
            await db.execute(
                text(
                    "UPDATE report_jobs SET status = 'completed', output_path = :path, "
                    "completed_at = :now WHERE id = :id"
                ),
                {"id": job_id, "path": output_path, "now": datetime.now(timezone.utc)},
            )
            await db.commit()

            log.info("html_report_generated", output_path=output_path, findings=len(findings))
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
            log.error("html_report_failed", error=str(exc))
            raise


def _esc(val: str | None) -> str:
    return str(val or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_report_html(*, assessment, findings, assets, sev_counts, session_id: str) -> str:
    findings_html = ""
    for f in findings:
        fg, bg = SEVERITY_COLORS.get(f.severity, ("#6b7280", "#f9fafb"))
        findings_html += f"""
<div style="background:#fff;border:1px solid #e2e8f0;border-radius:8px;padding:12px;margin:8px 0;border-left:4px solid {fg}">
  <div style="font-weight:600;margin-bottom:4px">
    <span style="display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600;background:{bg};color:{fg};text-transform:uppercase">{_esc(f.severity)}</span>
    {_esc(f.rule_id)} — {_esc(f.title)}
  </div>
  <div style="font-size:14px;color:#475569">{_esc(f.description)}</div>
  {"<div style='font-size:13px;color:#059669;margin-top:6px'>Remediation: " + _esc(f.remediation) + "</div>" if f.remediation else ""}
</div>"""

    assets_rows = "".join(
        f"<tr><td style='padding:6px 12px;border-bottom:1px solid #e2e8f0'>{_esc(a.asset_type)}</td>"
        f"<td style='padding:6px 12px;border-bottom:1px solid #e2e8f0;font-family:monospace;font-size:13px'>{_esc(a.name)}</td></tr>"
        for a in assets[:100]
    )

    def sev_card(label: str, count: int, color: str) -> str:
        return (
            f"<div style='background:#fff;border:1px solid #e2e8f0;border-radius:8px;"
            f"padding:12px;text-align:center;min-width:100px'>"
            f"<div style='font-size:28px;font-weight:700;color:{color}'>{count}</div>"
            f"<div style='font-size:12px;color:#64748b'>{label}</div></div>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BeGuardit Report — {_esc(session_id[:8])}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8fafc;color:#0f172a;line-height:1.6;padding:2rem;max-width:1100px;margin:0 auto}}h1{{font-size:1.5rem}}h2{{font-size:1.2rem;margin:2rem 0 1rem;padding-bottom:.5rem;border-bottom:2px solid #2563eb}}table{{width:100%;border-collapse:collapse}}th{{background:#f1f5f9;text-align:left;padding:8px 12px;font-size:12px;text-transform:uppercase;color:#64748b}}</style>
</head><body>
<h1>BeGuardit Security Assessment</h1>
<p style="color:#64748b;font-size:14px">
Session: <code>{_esc(session_id)}</code><br>
Host: {_esc(assessment.hostname)} · Mode: {_esc(assessment.mode)} · Status: {_esc(assessment.status)}<br>
Started: {_esc(str(assessment.started_at))} · Completed: {_esc(str(assessment.completed_at) if assessment.completed_at else "—")}
</p>

<h2>Summary</h2>
<div style="display:flex;gap:12px;flex-wrap:wrap;margin:12px 0">
{sev_card("Critical", sev_counts.get("critical", 0), "#dc2626")}
{sev_card("High", sev_counts.get("high", 0), "#ea580c")}
{sev_card("Medium", sev_counts.get("medium", 0), "#d97706")}
{sev_card("Low", sev_counts.get("low", 0), "#2563eb")}
{sev_card("Info", sev_counts.get("info", 0), "#6b7280")}
{sev_card("Assets", len(assets), "#0ea5e9")}
</div>

<h2>Findings ({len(findings)})</h2>
{findings_html if findings else "<p>No findings.</p>"}

<h2>Assets ({len(assets)})</h2>
<table><thead><tr><th>Type</th><th>Name</th></tr></thead><tbody>{assets_rows}</tbody></table>
{"<p style='color:#94a3b8;font-size:13px'>… and " + str(len(assets) - 100) + " more</p>" if len(assets) > 100 else ""}

<footer style="margin-top:3rem;padding-top:1rem;border-top:1px solid #e2e8f0;font-size:12px;color:#94a3b8;text-align:center">
Generated by BeGuardit Worker · {datetime.now(timezone.utc).isoformat()}
</footer>
</body></html>"""
