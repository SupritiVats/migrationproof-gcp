"""Pydantic schemas shared across the API, agents, and verification engine."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    SERVICE = "service"
    DATABASE = "database"
    VM = "vm"
    DNS = "dns"
    EXTERNAL_API = "external_api"


class DependencyStatus(str, Enum):
    CANDIDATE = "candidate"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"


class Entity(BaseModel):
    entity_id: str
    name: str
    type: EntityType
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_artifact: Optional[str] = None
    created_at: Optional[datetime] = None


class Dependency(BaseModel):
    dependency_id: str
    source_entity_id: str
    target_entity_id: str
    dependency_type: str
    confidence: float = 0.0
    status: DependencyStatus = DependencyStatus.CANDIDATE
    created_at: Optional[datetime] = None


class Evidence(BaseModel):
    evidence_id: str
    dependency_id: str
    artifact_uri: str
    artifact_type: str
    quoted_snippet: str
    extracted_by: str
    created_at: Optional[datetime] = None


class MigrationWaveAssignment(BaseModel):
    wave_id: str
    wave_number: int
    entity_id: str
    scenario_id: str


class VerificationReason(BaseModel):
    rule: str
    message: str
    related_entity_ids: list[str] = Field(default_factory=list)
    related_dependency_ids: list[str] = Field(default_factory=list)


class BlastRadius(BaseModel):
    root_entity_id: str
    affected_entity_ids: list[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    result_id: str
    scenario_id: str
    wave_number: int
    decision: Decision
    reasons: list[VerificationReason] = Field(default_factory=list)
    confidence: float
    blast_radius: Optional[BlastRadius] = None
    created_at: Optional[datetime] = None
    narrative: Optional[str] = None
