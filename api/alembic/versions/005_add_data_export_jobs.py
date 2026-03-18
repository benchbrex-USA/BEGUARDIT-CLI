# Alembic migration — add data_export_jobs table
# Source: ARCH-002-2026-03-17, Fix 9.1 (Tenant Data Export — GDPR)
from __future__ import annotations

"""Add data_export_jobs table

Revision ID: e5f6a7b8c9d0
Revises: a1b2c3d4e5f6
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "data_export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("output_path", sa.String(1000), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_dej_tenant", "data_export_jobs", ["tenant_id"])
    op.create_index(
        "idx_dej_status",
        "data_export_jobs",
        ["status"],
        postgresql_where=sa.text("status IN ('queued', 'processing')"),
    )


def downgrade() -> None:
    op.drop_index("idx_dej_status", table_name="data_export_jobs")
    op.drop_index("idx_dej_tenant", table_name="data_export_jobs")
    op.drop_table("data_export_jobs")
