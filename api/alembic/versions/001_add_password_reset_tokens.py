# Alembic migration — add password_reset_tokens table
# Source: ARCH-002-2026-03-17, Fix 2 (Password Reset Flow)
from __future__ import annotations

"""Add password_reset_tokens table

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-03-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_prt_user", "password_reset_tokens", ["user_id"])
    op.create_index(
        "idx_prt_expiry",
        "password_reset_tokens",
        ["expires_at"],
        postgresql_where=sa.text("used_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_prt_expiry", table_name="password_reset_tokens")
    op.drop_index("idx_prt_user", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
