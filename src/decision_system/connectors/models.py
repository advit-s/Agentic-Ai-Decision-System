"""Pydantic models for the v1.28 read-only connector framework.

Supports connector configs, import jobs, runtime items, and full
workspace-scoped operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
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
    last_sync_at: datetime | None = Field(None, description="Last successful sync/import timestamp")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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


class ConnectorCredentialStatus(BaseModel):
    """Safe credential status for a connector (no token values exposed)."""

    configured: bool = Field(default=False, description="Whether credentials are configured")
    token_present: bool = Field(default=False, description="Whether a token/env-var value is set")
    env_var_name: str = Field(default="", description="Recommended environment variable name")
    missing_message: str = Field(
        default="", description="User-friendly message if credentials are missing"
    )
    has_required: bool = Field(
        default=False, description="Whether all required credentials are present"
    )


class ConnectorTestDiagnostics(BaseModel):
    """Structured test result for a connector connection."""

    status: str = Field(default="unknown", description="Overall status: success, warning, error")
    message: str = Field(default="", description="Human-readable result message")
    checked_at: str = Field(default="", description="ISO timestamp of test")
    connector_type: str = Field(default="", description="Connector type tested")
    reachable: bool = Field(default=False, description="Whether the target is reachable")
    auth_configured: bool = Field(default=False, description="Whether auth credentials are present")
    permissions_summary: str = Field(default="", description="What permissions the connector has")
    rate_limit_info: str | None = Field(
        default=None, description="Rate limit information if available"
    )
    sample_item_count: int | None = Field(
        default=None, description="Number of items found if tested"
    )
    warnings: list[str] = Field(default_factory=list, description="Non-fatal warnings")
    errors: list[str] = Field(default_factory=list, description="Error messages")


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


class ConnectorJobStatus(StrEnum):
    """Import/sync job status values."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class JobProgress(BaseModel):
    """Progress tracking for a connector import/sync job."""

    total_items: int = 0
    processed_items: int = 0
    imported_items: int = 0
    skipped_items: int = 0
    changed_items: int = 0
    unchanged_items: int = 0
    failed_items: int = 0
    rate_limited_items: int = 0
    current_item_id: str | None = None
    current_item_title: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    batch_number: int = 0
    total_batches: int = 0

    def percent_complete(self) -> float:
        if self.total_items <= 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100.0

    def is_finished(self) -> bool:
        return self.processed_items >= self.total_items

    def add_progress(
        self,
        processed: int = 0,
        imported: int = 0,
        skipped: int = 0,
        changed: int = 0,
        failed: int = 0,
        rate_limited: int = 0,
    ) -> None:
        self.processed_items += processed
        self.imported_items += imported
        self.skipped_items += skipped
        self.changed_items += changed
        self.failed_items += failed
        self.rate_limited_items += rate_limited


class ConnectorImportJob(BaseModel):
    """An executed import job record with rich tracking fields."""

    job_id: str = Field(description="Unique job identifier")
    workspace_id: str | None = Field(None, description="Workspace scope")
    connector_id: str = Field(description="Connector identifier")
    status: str = Field(
        default="queued",
        description="Job status: queued, running, completed, completed_with_warnings, failed, cancelled, paused",
    )
    job_type: str = Field(default="import", description="Job type: import, sync, preview")
    progress: JobProgress = Field(default_factory=JobProgress, description="Job progress tracking")
    source_path: str = ""
    imported_files: list[str] = Field(default_factory=list)
    skipped_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    batch_size: int = Field(default=50, description="Number of items per batch")
    current_batch: int = Field(default=0, description="Current batch number")
    cancel_requested: bool = Field(default=False, description="True if cancel has been requested")
    resume_from_checkpoint: dict[str, Any] = Field(
        default_factory=dict, description="Checkpoint data for resume"
    )
    checkpoint_id: str | None = Field(default=None, description="Resume checkpoint identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)
    items_found: int = 0
    items_imported: int = 0
    items_skipped: int = 0
    items_failed: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    duration_ms: float | None = Field(
        default=None, description="Total job duration in milliseconds"
    )
    total_items: int = Field(default=0, description="Total items to process")
    processed_items: int = Field(default=0, description="Items processed so far")
    changed_items: int = Field(default=0, description="Items that changed since last import")
    unchanged_items: int = Field(default=0, description="Items unchanged since last import")
    rate_limited_items: int = Field(default=0, description="Items skipped due to rate limiting")
    current_item_id: str | None = Field(default=None, description="Currently processing item ID")

    def to_progress_dict(self) -> dict[str, Any]:
        """Return a compact progress snapshot for API responses."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "total_items": self.total_items or self.items_found,
            "processed_items": self.processed_items,
            "imported_items": self.items_imported,
            "skipped_items": self.items_skipped,
            "changed_items": self.changed_items,
            "unchanged_items": self.unchanged_items,
            "failed_items": self.items_failed,
            "rate_limited_items": self.rate_limited_items,
            "current_item_id": self.current_item_id,
            "percent_complete": self.percent_complete(),
            "duration_ms": self.duration_ms,
            "batch_number": self.current_batch,
            "errors": self.errors[:5] if self.errors else [],
            "warnings": self.warnings[:5] if self.warnings else [],
        }

    def percent_complete(self) -> float:
        total = self.total_items or self.items_found or 1
        return (self.processed_items / total) * 100.0

    def is_cancelled(self) -> bool:
        return self.cancel_requested or self.status == "cancelled"


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
    imported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
