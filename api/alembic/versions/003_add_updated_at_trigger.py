"""Add updated_at auto-update triggers on tenants and users.

Revision ID: 003
Revises: 002
Create Date: 2026-03-18

Source: ARCH-002-2026-03-17, Section 5 (updated_at gap fix)

Creates a PostgreSQL function ``update_updated_at_column()`` and attaches
BEFORE UPDATE triggers on the ``tenants`` and ``users`` tables so that
``updated_at`` is automatically set to ``now()`` on every update.
"""
from __future__ import annotations

from alembic import op

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

_FUNCTION_SQL = """\
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""

_TRIGGER_SQL_TEMPLATE = """\
CREATE TRIGGER trg_{table}_updated_at
    BEFORE UPDATE ON {table}
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""

_TABLES = ("tenants", "users")


def upgrade() -> None:
    op.execute(_FUNCTION_SQL)
    for table in _TABLES:
        op.execute(_TRIGGER_SQL_TEMPLATE.format(table=table))


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_updated_at ON {table};")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
