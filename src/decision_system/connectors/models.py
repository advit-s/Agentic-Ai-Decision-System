"""Pydantic models for the v1.28 read-only connector framework.

Supports connector configs, import jobs, runtime items, and full
workspace-scoped operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConnectorType(StrEnum):
    """Known connector types in the registry."""

    LOCAL_FILES = "local-files"
    GITHUB = "github"
    JIRA = "jira"
    SLACK = "slack"
    EMAIL = "email"
    URL_IMPORT = "url-import"
    NOTION = "notion"
    GOOGLE_DRIVE = "google-drive"
    UNKNOWN = "unknown"


class ConnectorStatus(StrEnum):
    """Operational readiness of a connector definition."""

    REAL = "real"
    STUB = "stub"
    UNAVAILABLE = "unavailable"


class ConnectorConfigStatus(StrEnum):
    """Health status for a persisted connector config."""

    CONFIGURED = "configured"
    MISSING_CONFIG = "missing_config"
    HEALTHY = "healthy"
    OFFLINE = "offline"
    ERROR = "error"


class ConnectorMode(StrEnum):
    """Enforced operation mode. All connectors must be read-only."""

    READ_ONLY = "read_only"


class ConnectorCapability(StrEnum):
    """Capabilities a connector may advertise."""

    DRY_RUN = "dry_run"
    IMPORT = "import"
    LIST = "list"
    INSPECT = "inspect"
    TEST = "test"
    SYNC = "sync"


class ConnectorSecretRef(BaseModel):
    """Reference to a secret stored outside the connector config."""

    key: str = Field(description="Environment variable or placeholder name")
    description: str = ""
    optional: bool = False


class ConnectorConfig(BaseModel):
    """Persisted connector configuration (workspace-scoped or global).

    Every connector is read-only by design. Secrets are never stored
    as plaintext in the config — they are referenced via secret_refs.
    """

    connector_id: str = Field(description="Unique identifier for this config")
    workspace_id: str | None = Field(None, description="Workspace scope; None = global")
    name: str = Field(description="Human-readable display name")
    connector_type: ConnectorType = Field(description="Which connector type")
    mode: ConnectorMode = Field(
        default=ConnectorMode.READ_ONLY,
        description="Always read_only per v1.28 safety rule",
    )
    status: ConnectorConfigStatus = Field(
        default=ConnectorConfigStatus.CONFIGURED,
        description="Current health status",
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Type-specific configuration (path, URL, repo, etc.)",
    )
    secret_refs: list[ConnectorSecretRef] = Field(
        default_factory=list,
        description="References to secrets that must be set externally",
    )
    last_sync_at: datetime | None = Field(
        None, description="Last successful sync/import timestamp"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("mode")
    @classmethod
    def _enforce_read_only(cls, v: ConnectorMode) -> ConnectorMode:
        if v != ConnectorMode.READ_ONLY:
            raise ValueError("All connectors must be read_only per v1.28 safety rule")
        return v

    def to_api_response(self, include_secrets: bool = False) -> dict[str, Any]:
        """Serialize for API responses, redacting secrets by default."""
        data = self.model_dump(mode="json")
        if not include_secrets:
            for key in list(data.get("config", {}).keys()):
                if any(s in key.lower() for s in ("secret", "token", "password", "key", "auth")):
                    data["config"][key] = "***REDACTED***"
        return data


class ConnectorRuntimeItem(BaseModel):
    """A single item listed by a connector runtime."""

    external_id: str
    title: str
    item_type: str = "file"
    source_url: str | None = None
    modified_at: datetime | None = None
    content_type: str = ""
    size_bytes: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    supports_list: bool = False
    supports_test: bool = False
    supports_sync: bool = False
    is_stub: bool = False


class ConnectorFetchedContent(BaseModel):
    """Fetched content from a connector runtime."""

    external_id: str
    title: str
    filename: str
    content_bytes: bytes | None = None
    content_text: str | None = None
    content_type: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


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
    items_found: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectorImportJob(BaseModel):
    """An executed import job record with rich tracking fields."""

    job_id: str
    workspace_id: str | None = None
    connector_id: str
    status: str
    source_path: str = ""
    imported_files: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    items_found: int = 0
    items_imported: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectorImportResult(BaseModel):
    """Lightweight summary returned after an import."""

    job: ConnectorImportJob
    dry_run: bool = False
    imported_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0


# ---------------------------------------------------------------------------
# Connector citation metadata for evidence/reports
# ---------------------------------------------------------------------------


class ConnectorCitation(BaseModel):
    """Citation metadata attached to imported data sources."""

    connector_id: str
    connector_type: ConnectorType
    external_id: str
    source_url: str | None = None
    imported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    content_hash: str = ""
    label: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_display_string(self) -> str:
        """Return a human-readable citation string for reports."""
        if self.connector_type == ConnectorType.GITHUB:
            return f"GitHub: {self.label or self.external_id}"
        elif self.connector_type == ConnectorType.URL_IMPORT:
            title = self.label or "Web page"
            url = self.source_url or ""
            return f"{title} ({url})" if url else title
        elif self.connector_type == ConnectorType.LOCAL_FILES:
            return self.label or f"Local file: {self.external_id}"
        elif self.connector_type == ConnectorType.NOTION:
            return f"Notion: {self.label or self.external_id}"
        elif self.connector_type == ConnectorType.GOOGLE_DRIVE:
            return f"Google Drive: {self.label or self.external_id}"
        return self.label or self.external_id

    def to_evidence_metadata(self) -> dict[str, Any]:
        """Return metadata dict for attaching to evidence results."""
        return {
            "connector_id": self.connector_id,
            "connector_type": self.connector_type.value,
            "external_id": self.external_id,
            "source_url": self.source_url,
            "imported_at": self.imported_at.isoformat() if self.imported_at else None,
            "citation_label": self.to_display_string(),
        }
