# Upload domain — Pydantic schemas
# Source: ARCH-002-2026-03-17, Section 6.4
from __future__ import annotations

from pydantic import BaseModel, Field


class UploadIntegrity(BaseModel):
    algorithm: str
    hash: str


class UploadSummary(BaseModel):
    total_findings: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)
    total_assets: int = 0
    total_evidence: int = 0
    total_attack_paths: int = 0


class UploadAsset(BaseModel):
    asset_type: str
    name: str
    metadata: dict = Field(default_factory=dict)


class UploadFinding(BaseModel):
    id: str
    rule_id: str
    title: str
    description: str | None = None
    severity: str
    score: float | None = None
    category: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    remediation: str | None = None
    metadata: dict = Field(default_factory=dict)


class UploadEvidence(BaseModel):
    collector: str
    type: str
    data: dict = Field(default_factory=dict)
    collected_at: str | None = None


class UploadAttackPath(BaseModel):
    id: str
    composite_severity: str
    depth: int
    steps: list[dict] = Field(default_factory=list)
    edge_relations: list[str] = Field(default_factory=list)


class CanonicalReport(BaseModel):
    """Matches the JSON canonical schema produced by the CLI (§7.5)."""
    schema_version: str = "1.0"
    session_id: str
    generated_at: str | None = None
    hostname: str | None = None
    os_info: dict = Field(default_factory=dict)
    scan_config: dict = Field(default_factory=dict)
    started_at: str | None = None
    completed_at: str | None = None
    summary: UploadSummary = Field(default_factory=UploadSummary)
    assets: list[UploadAsset] = Field(default_factory=list)
    findings: list[UploadFinding] = Field(default_factory=list)
    evidence: list[UploadEvidence] = Field(default_factory=list)
    attack_paths: list[UploadAttackPath] = Field(default_factory=list)
    integrity: UploadIntegrity | None = None


class UploadResponse(BaseModel):
    session_id: str
    findings_imported: int
    assets_imported: int
    evidence_imported: int
