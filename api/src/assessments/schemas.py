# Assessments domain — Pydantic request / response schemas
# Source: ARCH-002-2026-03-17, Section 6.3
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Assessment session
# ---------------------------------------------------------------------------

class ScanConfigOut(BaseModel):
    model_config = {"from_attributes": True}


class AssessmentSummary(BaseModel):
    """Lightweight representation for list endpoints."""
    id: uuid.UUID
    mode: str
    status: str
    hostname: str | None
    scan_config: dict
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AssessmentDetail(AssessmentSummary):
    """Full representation including counts."""
    started_by: uuid.UUID | None
    os_info: dict | None
    finding_count: int = 0
    asset_count: int = 0
    evidence_count: int = 0
    severity_summary: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------

class AssetOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    asset_type: str
    name: str
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

class EvidenceOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    collector_name: str
    evidence_type: str
    data: dict
    collected_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class FindingOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    rule_id: str
    title: str
    description: str | None
    severity: str
    category: str
    evidence_ids: list[uuid.UUID]
    remediation: str | None
    metadata: dict
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationParams(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class PaginatedResponse(BaseModel):
    """Generic wrapper for paginated lists."""
    items: list
    total: int
    offset: int
    limit: int


class MessageResponse(BaseModel):
    message: str
