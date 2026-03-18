# Job: partition_maintenance — monthly cron to create audit_log partitions
# Source: ARCH-002-2026-03-17, Fix 6 (Audit Log Partitioning)
#
# Creates the audit_log partition for 2 months ahead so that inserts never
# fail due to a missing partition.  Safe to run multiple times (idempotent).
from __future__ import annotations

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

import structlog
from sqlalchemy import text

from src.db import async_session_factory

logger = structlog.get_logger()


async def partition_maintenance(ctx: dict) -> dict:
    """Create audit_log partition for current_month + 2.

    Runs on a monthly cron schedule.  The partition is created with
    IF NOT EXISTS so repeated execution is safe.
    """
    now = datetime.now(timezone.utc)
    target = now + relativedelta(months=2)
    partition_start = target.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    partition_end = partition_start + relativedelta(months=1)

    partition_name = f"audit_log_{partition_start.strftime('%Y_%m')}"
    start_str = partition_start.strftime("%Y-%m-%d")
    end_str = partition_end.strftime("%Y-%m-%d")

    log = logger.bind(partition=partition_name, range_start=start_str, range_end=end_str)

    async with async_session_factory() as session:
        # Use IF NOT EXISTS to make this idempotent
        await session.execute(text(
            f"CREATE TABLE IF NOT EXISTS {partition_name} "
            f"PARTITION OF audit_log "
            f"FOR VALUES FROM ('{start_str}') TO ('{end_str}')"
        ))
        await session.commit()

    log.info("partition_maintenance_completed")
    return {"partition": partition_name, "range": f"{start_str} .. {end_str}"}
