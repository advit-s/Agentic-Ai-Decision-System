"""Pydantic models for the v1.1 safe connector framework."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ConnectorType(StrEnum):
    """Known connector types in the registry."""

    LOCAL_FILES = "local-files"
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    EMAIL = "email"


class ConnectorStatus(StrEnum):
    """Operational readiness of a connector."""

    REAL = "real"
    STUB = "stub"
    UNAVAILABLE = "unavailable"


class ConnectorCapability(StrEnum):
    """Capabilities a connector may advertise."""

    DRY_RUN = "dry_run"
    IMPORT = "import"
    LIST = "list"
    INSPECT = "inspect"


class ConnectorDefinition(BaseModel):
    """Descriptor for a registered connector."""

    connector_id: str
    name: str
    connector_type: ConnectorType
    status: ConnectorStatus
    description: str = ""
    capabilities: list[ConnectorCapability] = Field(default_factory=list)
    requires_secrets: bool = False
    supports_dry_run: bool = False
    supports_import: bool = False
    is_stub: bool = False


class ConnectorDryRunFile(BaseModel):
    """A single file discovered during a dry-run scan."""

    source_path: str
    relative_path: str = ""
    filename: str = ""
    extension: str = ""
    size_bytes: int = 0
    target_category: str = ""
    action: str = "import"
    reason: str = ""


class ConnectorDryRunResult(BaseModel):
    """Summary produced by a dry-run scan."""

    connector_id: str
    source_path: str
    files: list[ConnectorDryRunFile] = Field(default_factory=list)
    skipped_files: list[ConnectorDryRunFile] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    would_import_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectorImportJob(BaseModel):
    """An executed import job record."""

    job_id: str
    connector_id: str
    status: str
    source_path: str
    imported_files: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None


class ConnectorImportResult(BaseModel):
    """Lightweight summary returned after an import."""

    job: ConnectorImportJob
    dry_run: bool = False
    imported_count: int = 0
    skipped_count: int = 0
