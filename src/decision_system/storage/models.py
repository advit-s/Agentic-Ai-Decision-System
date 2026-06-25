"""Pydantic models for local workspace persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    """Allowed artifact categories for workspace storage."""

    DOCUMENT = "document"
    DATASET = "dataset"
    DATA_PROFILE = "data_profile"
    ONTOLOGY_MAP = "ontology_map"
    INSIGHT_STORE = "insight_store"
    DECISION_CONTEXT = "decision_context"
    DECISION_REPORT = "decision_report"
    ORCHESTRATION_RUN = "orchestration_run"
    WAR_ROOM_RUN = "war_room_run"
    WAR_ROOM_EVAL_RESULT = "war_room_eval_result"
    PROVIDER_EVAL_RUN = "provider_eval_run"
    GRAPH = "graph"
    IMPORT_MANIFEST = "import_manifest"
    AUDIT_EVENT = "audit_event"
    CONNECTOR_IMPORT_JOB = "connector_import_job"
    UNKNOWN = "unknown"


class Workspace(BaseModel):
    """A named local workspace for organizing decision-system artifacts."""

    workspace_id: str
    name: str = Field(min_length=1)
    description: str = Field(default="")
    active: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StoredArtifact(BaseModel):
    """A typed artifact stored within a workspace."""

    artifact_id: str
    workspace_id: str
    artifact_type: ArtifactType = ArtifactType.UNKNOWN
    source_path: str = Field(default="")
    title: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceStatus(BaseModel):
    """Summary of an active workspace and its contents."""

    workspace: Workspace
    artifact_counts: dict[str, int] = Field(default_factory=dict)
    database_path: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkspaceExport(BaseModel):
    """Exported workspace bundle for JSON serialization."""

    version: str = "1.0"
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    workspace: Workspace
    artifacts: list[StoredArtifact] = Field(default_factory=list)
