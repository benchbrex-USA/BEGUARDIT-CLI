# ARQ worker entry point — WorkerSettings
# Source: ARCH-002-2026-03-17, Section 9
#
# Usage:
#   arq src.main.WorkerSettings
#
# Jobs:
#   generate_html_report  — §9.2, timeout 5min, retries 3
#   generate_pdf_report   — §9.2, timeout 10min, retries 2
#   generate_sarif_export — §9.2, timeout 2min, retries 3
from __future__ import annotations

import structlog
from arq.connections import RedisSettings

from src.config import get_config
from src.jobs.report_html import generate_html_report
from src.jobs.report_pdf import generate_pdf_report
from src.jobs.report_sarif import generate_sarif_export

logger = structlog.get_logger()

_config = get_config()


def _parse_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into arq RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(_config.REDIS_URL)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or "0"),
        password=parsed.password,
    )


async def startup(ctx: dict) -> None:
    """Called once when the worker starts."""
    logger.info("worker_startup", max_jobs=_config.MAX_JOBS)


async def shutdown(ctx: dict) -> None:
    """Called once when the worker shuts down."""
    from src.db import engine

    await engine.dispose()
    logger.info("worker_shutdown")


async def on_job_start(ctx: dict) -> None:
    """Called before each job executes."""
    logger.info("job_start", job_id=ctx.get("job_id"))


async def on_job_end(ctx: dict) -> None:
    """Called after each job completes (success or failure)."""
    logger.info("job_end", job_id=ctx.get("job_id"))


class WorkerSettings:
    """ARQ worker configuration — passed to `arq src.main.WorkerSettings`."""

    redis_settings = _parse_redis_settings()

    functions = [
        generate_html_report,
        generate_pdf_report,
        generate_sarif_export,
    ]

    on_startup = startup
    on_shutdown = shutdown
    on_job_start = on_job_start
    on_job_end = on_job_end

    max_jobs = _config.MAX_JOBS
    job_timeout = _config.JOB_TIMEOUT
    health_check_interval = _config.HEALTH_CHECK_INTERVAL

    # Queue name — matches what the API enqueues to
    queue_name = "beguardit:reports"
