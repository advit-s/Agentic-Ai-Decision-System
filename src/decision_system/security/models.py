"""Pydantic models for the v1.2 security, governance, and audit subsystem.

All models are plain Pydantic v2 ``BaseModel`` classes with sensible defaults
and ``model_config`` settings that keep validation strict without requiring a
database layer.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums / literal unions
# ---------------------------------------------------------------------------

SecretType = Literal[
    "api_key",
    "token",
    "password",
    "private_key",
    "aws_key",
    "env_file",
    "other",
]

RedactionKind = Literal[
    "email",
    "phone",
    "secret_token",
    "customer_id",
    "address",
]

PolicySeverity = Literal["critical", "warning", "info"]

ApprovalStatus = Literal["pending", "approved", "rejected", "cancelled"]


# ---------------------------------------------------------------------------
# Secret scanning
# ---------------------------------------------------------------------------

class SecretFinding(BaseModel):
    """One secret (or suspicious credential-ish pattern) found in a file.

    The full secret value is intentionally **never** stored in
    ``matched_preview``; only a short masked preview is kept so that audit
    logs remain safe to share.
    """

    model_config = {"extra": "forbid"}

    finding_id: str = Field(..., description="Unique identifier for this finding.")
    source_path: str = Field(..., description="Relative path of the scanned file.")
    line_number: int = Field(
        ..., description="1-based line number where the pattern was detected."
    )
    secret_type: SecretType = Field(
        ...,
        description="Categorisation of the detected secret-like pattern.",
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="How dangerous this finding is."
    )
    matched_preview: str = Field(
        ...,
        description="Short masked preview of the matched text (never the full value).",
    )
    recommendation: str = Field(
        default="Remove the secret from version control and rotate the credential.",
        description="Suggested remediation.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 timestamp when the finding was recorded.",
    )


class SecretScanResult(BaseModel):
    """Aggregated results of a secret-scan pass."""

    model_config = {"extra": "forbid"}

    scan_id: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    scanned_path: str = Field(..., description="Root path that was scanned.")
    files_scanned: int = Field(default=0)
    files_skipped: int = Field(default=0)
    findings: list[SecretFinding] = Field(default_factory=list)
    overall_status: Literal["ok", "warn", "fail"] = Field(default="ok")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Redaction preview
# ---------------------------------------------------------------------------

class RedactionFinding(BaseModel):
    """One PII / secret-like span in a piece of text."""

    model_config = {"extra": "forbid"}

    finding_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    text_type: RedactionKind = Field(...)
    start: int = Field(..., description="Character start index (inclusive).")
    end: int = Field(..., description="Character end index (exclusive).")
    matched_preview: str = Field(
        ..., description="The matched text, truncated for display."
    )
    replacement: str = Field(..., description="Replacement placeholder.")
    confidence: Literal["high", "medium", "low"] = Field(default="high")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RedactionPreviewResult(BaseModel):
    """Result of running the redaction previewer over a text string."""

    model_config = {"extra": "forbid"}

    original_text: str = Field(...)
    redacted_text: str = Field(...)
    findings: list[RedactionFinding] = Field(default_factory=list)
    finding_count: int = Field(default=0)


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    """One entry in the local audit log JSONL file."""

    model_config = {"extra": "forbid"}

    event_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    event_type: str = Field(
        ...,
        description="Machine-readable event category (e.g. secret_scan_run).",
    )
    actor: str = Field(
        default="local-user",
        description="Who triggered the event (no real auth system yet).",
    )
    message: str = Field(
        default="",
        description="Free-form human-readable description.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured auxiliary data.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

class PolicyCheck(BaseModel):
    """One individual policy check result."""

    model_config = {"extra": "forbid"}

    check_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex[:8])
    name: str = Field(...)
    passed: bool = Field(...)
    severity: PolicySeverity = Field(...)
    message: str = Field(...)
    recommendation: str = Field(default="")


class PolicyCheckResult(BaseModel):
    """Aggregate policy evaluation result."""

    model_config = {"extra": "forbid"}

    checks: list[PolicyCheck] = Field(default_factory=list)
    passed_count: int = Field(default=0)
    warning_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    overall_status: Literal["ok", "warn", "fail"] = Field(default="ok")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------

class ApprovalRequest(BaseModel):
    """A local approval request record.

    There is no real auth or notification system yet; these are local
    JSON records that a future workflow can query before performing
    high-risk operations.
    """

    model_config = {"extra": "forbid"}

    approval_id: str = Field(
        default_factory=lambda: __import__("uuid").uuid4().hex[:12]
    )
    reason: str = Field(...)
    status: ApprovalStatus = Field(default="pending")
    requested_by: str = Field(
        default="local-user",
        description="Actor identifier (no real auth yet).",
    )
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    resolved_at: str | None = Field(
        default=None,
        description="ISO timestamp when the request was approved/rejected/cancelled.",
    )
