# Admin domain — SQLAlchemy ORM models
# Source: ARCH-002-2026-03-17, Section 5.3 / 6.6
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.auth.models import Base


class AuditLog(Base):
    """Immutable audit trail for security-relevant actions.

    Records who did what, when, and from where.  Entries are append-only;
    the table has no UPDATE/DELETE in application code.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"))
    user_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True))
    detail: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(INET)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")


class DataExportJob(Base):
    """GDPR data export job record.

    Tracks tenant data export requests from creation through completion.
    """
    __tablename__ = "data_export_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    requested_by: Mapped[str] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="queued")
    output_path: Mapped[str | None] = mapped_column(String(1000))
    error_message: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
