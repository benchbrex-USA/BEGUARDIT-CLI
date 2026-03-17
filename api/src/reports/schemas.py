# Reports domain — Pydantic schemas
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateReportRequest(BaseModel):
    session_id: uuid.UUID
    format: str = Field(default="html", pattern=r"^(html|pdf|sarif|json)$")


class ReportJobOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    format: str
    status: str
    output_path: str | None
    error_message: str | None
    attempts: int
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str
