"""Local audit timeline — summarizes recent local audit events.

Aggregates events from the security audit log, workspace import/export
events, index runs, war-room runs, connector jobs, and security scans.

All events are stored in local JSON/JSONL files and never expose secrets.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class TimelineEvent:
    """One event in the audit timeline."""

    timestamp: str
    event_type: str
    source: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditTimeline:
    """Aggregated audit timeline result."""

    events: list[TimelineEvent] = field(default_factory=list)
    total_count: int = 0
    sources: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [asdict(e) for e in self.events],
            "total_count": self.total_count,
            "sources": self.sources,
        }


# Well-known event source paths under .decision_system/
_SOURCES: list[tuple[str, str, str]] = [
    ("security", "audit", "audit/audit_log.jsonl"),
    ("war_room", "runs", "war_room/runs"),
    ("connectors", "jobs", "connectors"),
    ("runs", "ask_runs", "runs"),
    ("orchestration", "orchestration", "orchestration/runs"),
]


def _load_jsonl(path: Path, max_events: int) -> list[dict[str, Any]]:
    """Load up to *max_events* JSONL entries from *path*."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
    except (json.JSONDecodeError, OSError):
        pass
    # Return most recent first
    events.reverse()
    return events[:max_events]


def _load_json_dir(path: Path, max_events: int) -> list[dict[str, Any]]:
    """Load up to *max_events* entries from JSON files in *path*."""
    if not path.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for f in sorted(path.iterdir(), reverse=True):
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                events.append(data)
            except (json.JSONDecodeError, OSError):
                pass
        if len(events) >= max_events:
            break
    return events


def build_timeline(
    decision_root: str | Path = ".decision_system",
    max_events_per_source: int = 10,
) -> AuditTimeline:
    """Aggregate audit events from all known local sources."""
    root = Path(decision_root)
    timeline = AuditTimeline()
    source_counts: dict[str, int] = {}

    for source_name, label, rel_path in _SOURCES:
        full_path = root / rel_path
        loaded: list[dict[str, Any]] = []

        if full_path.suffix == ".jsonl":
            loaded = _load_jsonl(full_path, max_events_per_source)
        elif full_path.suffix == "":
            # Directory of JSON files
            loaded = _load_json_dir(full_path, max_events_per_source)

        source_counts[source_name] = len(loaded)

        for item in loaded:
            ts = item.get("created_at") or item.get("timestamp") or str(datetime.now(timezone.utc))
            event_type = item.get("event_type") or item.get("type") or source_name
            summary = item.get("message") or item.get("summary") or f"{label} event"
            details = dict(item)
            # Never expose raw text that could contain secrets
            for secret_key in ("original_text", "text", "content"):
                details.pop(secret_key, None)

            timeline.events.append(
                TimelineEvent(
                    timestamp=ts,
                    event_type=event_type,
                    source=source_name,
                    summary=str(summary)[:200],
                    details=details,
                )
            )

    # Sort by timestamp descending, newest first
    timeline.events.sort(key=lambda e: e.timestamp, reverse=True)
    timeline.total_count = len(timeline.events)
    timeline.sources = source_counts

    return timeline


def timeline_to_text(timeline: AuditTimeline) -> str:
    """Render an AuditTimeline as human-readable text."""
    lines = ["# Audit Timeline", ""]
    if not timeline.events:
        lines.append("No audit events found.")
        lines.append("")
        lines.append("Events appear after running commands such as:")
        lines.append("- decision-system index")
        lines.append("- decision-system ask")
        lines.append("- decision-system run-war-room")
        lines.append("- decision-system security scan-secrets")
        lines.append("- decision-system connectors import")
        lines.append("- decision-system export-workspace")
        return "\n".join(lines)

    lines.append(f"Total events: {timeline.total_count}")
    lines.append(f"Event sources: {timeline.sources}")
    lines.append("")

    for i, ev in enumerate(timeline.events[:30], start=1):
        ts = ev.timestamp[:19] if len(ev.timestamp) > 19 else ev.timestamp
        lines.append(f"{i}. [{ts}] [{ev.source}] {ev.event_type}")
        lines.append(f"   {ev.summary[:120]}")
        if ev.details:
            safe_keys = [
                k for k in ev.details if k not in ("original_text", "raw", "text", "content")
            ]
            if safe_keys:
                preview = ", ".join(
                    f"{k}={v}" for k, v in list(ev.details.items())[:3] if k in safe_keys
                )
                if preview:
                    lines.append(f"   ({preview})")
        lines.append("")

    return "\n".join(lines)
