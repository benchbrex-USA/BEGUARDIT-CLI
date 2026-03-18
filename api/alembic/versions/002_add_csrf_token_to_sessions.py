"""Add csrf_token column to sessions table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-18

Source: ARCH-002-2026-03-17, Section 8.3 (CSRF gap fix)
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("csrf_token", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "csrf_token")
