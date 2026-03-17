# Reports domain — SQLAlchemy ORM models
# Source: ARCH-002-2026-03-17, Section 5.3
# Re-exports ReportJob; canonical table lives in the shared Base.
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.auth.models import Base


class ReportJob(Base):
    __tablename__ = "report_jobs"
    __table_args__ = (
        CheckConstraint("format IN ('html', 'pdf', 'sarif', 'json')", name="ck_rjob_format"),
        CheckConstraint("status IN ('queued', 'processing', 'completed', 'failed')", name="ck_rjob_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("assessment_sessions.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False, default="html")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    output_path: Mapped[str | None] = mapped_column(String(1000))
    error_message: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
