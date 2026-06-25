"""Local JSONL audit-log writer.

Writes timestamped audit events to ``.decision_system/security/audit/audit_log.jsonl``
using a nine-line JSON-per-line format that is easy to tail, grep, and replay.

The writer is deliberately simple – it does not require a workspace, does,
and never calls external services.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_system._data_root import get_data_root
from decision_system.security.models import AuditEvent

# Optional identity integration — the audit module tries to import the
# identity system but does not require it. If the identity module is
# not available, audit events fall back to "local-user".
try:
    from decision_system.identity.permissions import get_current_user as _get_audit_user

    _IDENTITY_AVAILABLE = True
except (ImportError, Exception):
    _IDENTITY_AVAILABLE = False

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _get_security_dir() -> Path:
    """Return the security data directory (lazy)."""
    return get_data_root() / "security"


def _get_audit_dir() -> Path:
    """Return the audit directory (lazy)."""
    return _get_security_dir() / "audit"


def _get_audit_log() -> Path:
    """Return the audit log file path (lazy)."""
    return _get_audit_dir() / "audit_log.jsonl"


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    """Create the security output directory tree if it does not already exist."""
    _get_audit_dir().mkdir(parents=True, exist_ok=True)


def _resolve_actor(actor: str | None = None) -> str:
    """Resolve the actor for an audit event.

    Priority:
    1. Explicitly provided actor
    2. Current user from identity system
    3. Fallback to "local-user"
    """
    if actor is not None:
        return actor
    if _IDENTITY_AVAILABLE:
        try:
            user = _get_audit_user()
            return user.user_id
        except Exception:
            pass
    return "local-user"


def append_event(
    event_type: str,
    message: str,
    *,
    actor: str | None = None,
    metadata: dict[str, Any] | None = None,
    audit_path: str | Path = _get_audit_log(),
) -> AuditEvent:
    """Append a single audit event to the JSONL log file.

    Returns the created ``AuditEvent`` so callers can chain or inspect it.
    """
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_actor = _resolve_actor(actor)
    event = AuditEvent(
        event_type=event_type,
        actor=resolved_actor,
        message=message,
        metadata=metadata or {},
    )
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event.model_dump(mode="json"), default=str) + "\n")
    return event


# ---------------------------------------------------------------------------
# Reader
# ---------------------------------------------------------------------------


def load_events(
    audit_path: str | Path = _get_audit_log(),
    *,
    limit: int | None = None,
) -> list[AuditEvent]:
    """Load audit events from the JSONL log.

    Returns an empty list when the log file does not yet exist or is empty.
    """
    path = Path(audit_path)
    if not path.exists():
        return []
    events: list[AuditEvent] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                    events.append(AuditEvent.model_validate(raw))
                except (json.JSONDecodeError, ValueError, TypeError):
                    continue  # skip corrupt lines
    except (OSError, PermissionError):
        pass
    if limit is not None and limit > 0:
        events = events[-limit:]
    return events


# ---------------------------------------------------------------------------
# Inspector helpers
# ---------------------------------------------------------------------------


def event_counts(events: list[AuditEvent]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for ev in events:
        counts[ev.event_type] = counts.get(ev.event_type, 0) + 1
    return counts


def render_audit_log(
    events: list[AuditEvent],
    *,
    limit: int | None = None,
) -> str:
    """Render audit events as ASCII-safe Markdown."""
    lines: list[str] = ["# Audit Log", ""]
    display = events
    if limit is not None and limit > 0:
        display = display[-limit:]
    if not display:
        lines.append("(no events)")
        return "\n".join(lines)
    lines.append(f"Total events: {len(events)}")
    lines.append("")
    counts = event_counts(display)
    if counts:
        lines.append("By type:")
        for etype, count in sorted(counts.items()):
            lines.append(f"- {etype}: {count}")
        lines.append("")
    for ev in display:
        lines.append(f"- [{ev.created_at}] `{ev.event_type}` by *{ev.actor}*")
        if ev.message:
            lines.append(f"  {ev.message}")
        if ev.metadata:
            meta_str = ", ".join(f"{k}={v}" for k, v in sorted(ev.metadata.items()))
            lines.append(f"  _({meta_str})_")
    lines.append("")
    return "\n".join(lines)


def log_audit_event(
    event: dict[str, Any],
    actor: str | None = None,
) -> AuditEvent:
    """Log an audit event from a dict.

    This is a convenience wrapper around ``append_event`` that accepts
    a single dict. The dict must contain at minimum an ``event_type`` key.
    Additional dict keys are included as metadata.

    Example::

        log_audit_event({
            "event_type": "workflow_executed",
            "workflow_id": "abc-123",
            "execution_id": "xyz-456",
        })
    """
    event_type = event.pop("event_type", "unknown")
    message = event.pop("message", f"Event: {event_type}")
    metadata = event  # Remaining keys become metadata
    resolved_actor = _resolve_actor(actor)
    return append_event(
        event_type=str(event_type),
        message=str(message),
        actor=resolved_actor,
        metadata=metadata,
    )
