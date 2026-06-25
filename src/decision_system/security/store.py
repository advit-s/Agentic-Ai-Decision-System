"""Persistence helpers for the v1.2 security subsystem.

All generated artifacts live under ``.decision_system/security/`` which is
listed in ``.gitignore`` so nothing is committed accidentally.

No external services are contacted.
"""

from __future__ import annotations

import json
from pathlib import Path
from decision_system._data_root import get_data_root
from datetime import datetime, timezone

from decision_system.security.models import (
    ApprovalRequest,
    AuditEvent,
    PolicyCheckResult,
    RedactionPreviewResult,
    SecretScanResult,
)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------

def _get_security_dir() -> Path:
    """Return the security data directory (lazy)."""
    return get_data_root() / "security"


def _get_scan_dir() -> Path:
    """Return the scan output directory (lazy)."""
    return _get_security_dir() / "scans"


def _get_scan_json() -> Path:
    """Return the latest scan JSON path (lazy)."""
    return _get_scan_dir() / "latest_scan.json"
DEFAULT_AUDIT_DIR = _get_security_dir() / "audit"
DEFAULT_AUDIT_LOG = DEFAULT_AUDIT_DIR / "audit_log.jsonl"
DEFAULT_POLICY_RESULT = _get_security_dir() / "policy" / "latest.json"
DEFAULT_APPROVALS_DIR = _get_security_dir() / "approvals"
DEFAULT_APPROVALS_INDEX = DEFAULT_APPROVALS_DIR / "index.json"

SECURITY_IGNORE_DIRS: set[str] = {
    ".git",
    ".venv",
    "venv",
    ".decision_system",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "egg-info",
    "datasets",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _save_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return path.resolve()


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Secret scan
# ---------------------------------------------------------------------------


def save_secret_scan(result: SecretScanResult) -> Path:
    """Persist a SecretScanResult and return the written path."""
    return _save_json(_get_scan_json(), result.model_dump(mode="json"))


def load_secret_scan(path: Path | str = _get_scan_json()) -> SecretScanResult | None:
    p = Path(path)
    raw = _load_json(p)
    if raw is None:
        return None
    try:
        return SecretScanResult.model_validate(raw)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Policy result
# ---------------------------------------------------------------------------


def save_policy_result(result: PolicyCheckResult) -> Path:
    """Persist a PolicyCheckResult and return the written path."""
    return _save_json(DEFAULT_POLICY_RESULT, result.model_dump(mode="json"))


def load_policy_result(path: Path | str = DEFAULT_POLICY_RESULT) -> PolicyCheckResult | None:
    p = Path(path)
    raw = _load_json(p)
    if raw is None:
        return None
    try:
        return PolicyCheckResult.model_validate(raw)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Redaction result
# ---------------------------------------------------------------------------


def save_redaction_result(result: RedactionPreviewResult) -> Path:
    """Persist a RedactionPreviewResult and return the written path."""
    ts = datetime.now(timezone.utc).isoformat().replace(":", "-")
    path = _get_security_dir() / "redactions" / f"{ts}.json"
    return _save_json(path, result.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


def save_audit_event(event: AuditEvent) -> Path:
    """Append a single audit event as a JSON line and return the log path."""
    DEFAULT_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.model_dump(mode="json"), default=str) + "\n")
    return DEFAULT_AUDIT_LOG.resolve()


def load_audit_events(
    path: Path | str = DEFAULT_AUDIT_LOG,
    limit: int | None = None,
) -> list[AuditEvent]:
    """Load audit events from the JSONL log file."""
    p = Path(path)
    if not p.exists():
        return []
    events: list[AuditEvent] = []
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(AuditEvent.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValueError, TypeError):
            continue
    if limit is not None and limit > 0:
        events = events[-limit:]
    return events


# ---------------------------------------------------------------------------
# Approval requests
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    DEFAULT_APPROVALS_DIR.mkdir(parents=True, exist_ok=True)


def save_approval_request(request: ApprovalRequest) -> Path:
    """Persist a single approval request and return the index path."""
    _ensure_dirs()
    index = _load_approval_index()
    index[request.approval_id] = request.model_dump(mode="json")
    DEFAULT_APPROVALS_INDEX.write_text(
        json.dumps(index, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return DEFAULT_APPROVALS_INDEX.resolve()


def _load_approval_index() -> dict:
    if not DEFAULT_APPROVALS_INDEX.exists():
        return {}
    try:
        raw = json.loads(DEFAULT_APPROVALS_INDEX.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def load_approval_requests(path: Path | str = DEFAULT_APPROVALS_INDEX) -> list[ApprovalRequest]:
    """Load all approval requests from the index."""
    p = Path(path)
    if not p.exists():
        return []
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return []
        results: list[ApprovalRequest] = []
        for data in raw.values():
            try:
                results.append(ApprovalRequest.model_validate(data))
            except (ValueError, TypeError):
                continue
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results
    except (json.JSONDecodeError, OSError):
        return []


def load_approval(approval_id: str) -> ApprovalRequest | None:
    """Load a single approval request by ID."""
    index = _load_approval_index()
    data = index.get(approval_id)
    if data is None:
        return None
    try:
        return ApprovalRequest.model_validate(data)
    except (ValueError, TypeError):
        return None
