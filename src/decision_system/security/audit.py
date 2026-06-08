"""Local JSONL audit-log writer.

Writes timestamped audit events to ``.decision_system/security/audit/audit_log.jsonl``
using a nine-line JSON-per-line format that is easy to tail, grep, and replay.

The writer is deliberately simple – it does not require a workspace, does,
and never calls external services.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_system.security.models import AuditEvent

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

DEFAULT_SECURITY_DIR = Path(".decision_system") / "security"
DEFAULT_AUDIT_DIR = DEFAULT_SECURITY_DIR / "audit"
DEFAULT_AUDIT_LOG = DEFAULT_AUDIT_DIR / "audit_log.jsonl"


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    """Create the security output directory tree if it does not already exist."""
    DEFAULT_AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def append_event(
    event_type: str,
    message: str,
    *,
    actor: str = "local-user",
    metadata: dict[str, Any] | None = None,
    audit_path: str | Path = DEFAULT_AUDIT_LOG,
) -> AuditEvent:
    """Append a single audit event to the JSONL log file.

    Returns the created ``AuditEvent`` so callers can chain or inspect it.
    """
    path = Path(audit_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = AuditEvent(
        event_type=event_type,
        actor=actor,
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
    audit_path: str | Path = DEFAULT_AUDIT_LOG,
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
