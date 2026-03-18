# Alembic migration — add deleted_at column to tenants
# Source: ARCH-002-2026-03-17, Fix 9.2 (Tenant Soft Delete — GDPR)
from __future__ import annotations

"""Add deleted_at column to tenants

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_tenants_deleted_at",
        "tenants",
        ["deleted_at"],
        postgresql_where=sa.text("deleted_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_tenants_deleted_at", table_name="tenants")
    op.drop_column("tenants", "deleted_at")
