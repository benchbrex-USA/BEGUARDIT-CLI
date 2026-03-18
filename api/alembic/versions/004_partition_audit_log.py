# Alembic migration — partition audit_log by created_at (monthly)
# Source: ARCH-002-2026-03-17, Fix 6 (Audit Log Partitioning)
from __future__ import annotations

"""Partition audit_log table by created_at (monthly ranges)

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # 1. Rename existing table so we can recreate it as partitioned
    op.execute("ALTER TABLE audit_log RENAME TO audit_log_old")

    # 2. Create partitioned table with composite primary key
    #    (id, created_at) is required because the partition key must be part
    #    of the primary key in PostgreSQL declarative partitioning.
    op.execute("""
        CREATE TABLE audit_log (
            id          UUID        NOT NULL DEFAULT gen_random_uuid(),
            tenant_id   UUID        NOT NULL,
            user_id     UUID,
            action      VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100),
            entity_id   UUID,
            detail      JSONB,
            ip_address  INET,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
    """)

    # 3. Create initial monthly partitions (2026-03 through 2026-06)
    partitions = [
        ("audit_log_2026_03", "2026-03-01", "2026-04-01"),
        ("audit_log_2026_04", "2026-04-01", "2026-05-01"),
        ("audit_log_2026_05", "2026-05-01", "2026-06-01"),
        ("audit_log_2026_06", "2026-06-01", "2026-07-01"),
    ]
    for name, start, end in partitions:
        op.execute(
            f"CREATE TABLE {name} PARTITION OF audit_log "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )

    # 4. Migrate data from the old table into the new partitioned table
    op.execute("INSERT INTO audit_log SELECT * FROM audit_log_old")

    # 5. Drop the old unpartitioned table
    op.execute("DROP TABLE audit_log_old")

    # 6. Recreate indexes on the partitioned table
    op.execute(
        "CREATE INDEX idx_audit_log_tenant_created "
        "ON audit_log (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_log_action "
        "ON audit_log (action)"
    )


def downgrade() -> None:
    # Reverse: collapse back into a regular (non-partitioned) table
    op.execute("ALTER TABLE audit_log RENAME TO audit_log_partitioned")

    op.execute("""
        CREATE TABLE audit_log (
            id          UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
            tenant_id   UUID        NOT NULL,
            user_id     UUID,
            action      VARCHAR(100) NOT NULL,
            entity_type VARCHAR(100),
            entity_id   UUID,
            detail      JSONB,
            ip_address  INET,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("INSERT INTO audit_log SELECT * FROM audit_log_partitioned")
    op.execute("DROP TABLE audit_log_partitioned CASCADE")

    op.execute(
        "CREATE INDEX idx_audit_log_tenant_created "
        "ON audit_log (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_audit_log_action "
        "ON audit_log (action)"
    )
