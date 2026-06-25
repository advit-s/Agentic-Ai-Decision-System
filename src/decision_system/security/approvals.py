"""Local approval request store and inspector.

Approval requests are persisted as JSON under
``.decision_system/security/approvals/``. There is no real auth or
notification system yet; this exists so that future workflows can gate
high-risk operations on human approval.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from decision_system.security.models import ApprovalRequest, ApprovalStatus
from decision_system._data_root import get_data_root

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _get_security_dir() -> Path:
    """Return the security data directory (lazy)."""
    return get_data_root() / "security"


def _get_approvals_dir() -> Path:
    """Return the approvals directory (lazy)."""
    return _get_security_dir() / "approvals"


def _get_approvals_index() -> Path:
    """Return the approvals index path (lazy)."""
    return _get_approvals_dir() / "index.json"


# ---------------------------------------------------------------------------
# Store API
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    _get_approvals_dir().mkdir(parents=True, exist_ok=True)


def _load_index() -> dict[str, dict]:
    if not _get_approvals_index().exists():
        return {}
    try:
        raw = json.loads(_get_approvals_index().read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def _save_index(index: dict[str, dict]) -> None:
    _ensure_dirs()
    _get_approvals_index().write_text(
        json.dumps(index, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _persist(request: ApprovalRequest) -> None:
    _ensure_dirs()
    index = _load_index()
    index[request.approval_id] = request.model_dump(mode="json")
    _save_index(index)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def create_approval(
    reason: str,
    *,
    requested_by: str = "local-user",
    metadata: dict[str, str] | None = None,
) -> ApprovalRequest:
    """Create and persist a new pending approval request."""
    request = ApprovalRequest(
        reason=reason,
        requested_by=requested_by,
        metadata=metadata or {},
    )
    _persist(request)
    return request


def list_approvals(
    status_filter: ApprovalStatus | None = None,
) -> list[ApprovalRequest]:
    """List approval requests, optionally filtered by status."""
    index = _load_index()
    results: list[ApprovalRequest] = []
    for data in index.values():
        try:
            req = ApprovalRequest.model_validate(data)
            if status_filter is None or req.status == status_filter:
                results.append(req)
        except (ValueError, TypeError):
            continue
    results.sort(key=lambda r: r.created_at, reverse=True)
    return results


def inspect_approval(approval_id: str) -> ApprovalRequest | None:
    """Return a single approval request by ID, or None when not found."""
    index = _load_index()
    data = index.get(approval_id)
    if data is None:
        return None
    try:
        return ApprovalRequest.model_validate(data)
    except (ValueError, TypeError):
        return None


def update_approval_status(
    approval_id: str,
    new_status: str,
    *,
    actor: str = "local-user",
) -> ApprovalRequest | None:
    """Update the status of an existing approval request."""
    index = _load_index()
    data = index.get(approval_id)
    if data is None:
        return None
    data["status"] = new_status
    data["resolved_at"] = datetime.now(timezone.utc).isoformat()
    data.setdefault("metadata", {})
    data["metadata"]["resolved_by"] = actor
    _save_index(index)
    try:
        return ApprovalRequest.model_validate(data)
    except (ValueError, TypeError):
        return None


def render_approvals(requests: list[ApprovalRequest]) -> str:
    """Render approval requests as ASCII-safe Markdown."""
    lines: list[str] = ["# Approval Requests", ""]
    if not requests:
        lines.append("(no approval requests)")
        return "\n".join(lines)
    lines.append(f"Total requests: {len(requests)}")
    lines.append("")
    for req in requests:
        tag = f"`[{req.status}]`"
        lines.append(f"- {tag} **{req.approval_id}** — {req.reason}")
        lines.append(f"  Requested by: *{req.requested_by}* | {req.created_at}")
        if req.metadata:
            meta_str = ", ".join(
                f"{k}={v}" for k, v in sorted(req.metadata.items()) if v
            )
            if meta_str:
                lines.append(f"  Metadata: {meta_str}")
    lines.append("")
    return "\n".join(lines)
