"""Workspace-scoped audit log API endpoints.

Provides filtered audit event queries per workspace, plus aggregate
summaries. Requires audit.read permission.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from decision_system.api.models import to_jsonable
from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import require_workspace_permission
from decision_system.security.audit import load_events as load_audit_events
from decision_system.security.store import load_audit_events as load_store_events

router = APIRouter(tags=["audit"])


@router.get("/workspaces/{id}/audit/events")
def list_audit_events(
    id: str,
    event_type: str | None = None,
    actor: str | None = None,
    artifact_type: str | None = None,
    artifact_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
    _user: LocalUser = Depends(require_workspace_permission(Permission.AUDIT_READ)),
) -> dict[str, Any]:
    """List audit events for a workspace with optional filters.

    Filters are applied client-side against the loaded event list since
    the local JSONL store does not support server-side filtering natively.
    """
    # Load all events (from the global audit log and workspace-scoped store)
    events = load_audit_events()
    store_events = load_store_events()
    all_events = events + store_events

    # Deduplicate by event_id
    seen: set[str] = set()
    unique_events = []
    for ev in all_events:
        if ev.event_id not in seen:
            seen.add(ev.event_id)
            unique_events.append(ev)

    # Filter by workspace_id
    filtered = [
        e
        for e in unique_events
        if e.metadata.get("workspace_id") == id or e.event_type.startswith("workspace_")
    ]

    # Apply additional filters
    if event_type:
        filtered = [e for e in filtered if e.event_type == event_type]
    if actor:
        filtered = [e for e in filtered if e.actor == actor]
    if artifact_type:
        filtered = [e for e in filtered if e.metadata.get("artifact_type") == artifact_type]
    if artifact_id:
        filtered = [e for e in filtered if e.metadata.get("artifact_id") == artifact_id]

    # Sort by created_at descending
    filtered.sort(key=lambda e: e.created_at, reverse=True)

    # Paginate
    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "events": [to_jsonable(e) for e in page],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@router.get("/workspaces/{id}/audit/summary")
def audit_summary(
    id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.AUDIT_READ)),
) -> dict[str, Any]:
    """Return a summary of audit events for a workspace."""
    events = load_audit_events()
    store_events = load_store_events()
    all_events = events + store_events

    # Filter by workspace_id
    ws_events = [
        e
        for e in all_events
        if e.metadata.get("workspace_id") == id or e.event_type.startswith("workspace_")
    ]

    # Event type counts
    type_counts: dict[str, int] = {}
    actor_counts: dict[str, int] = {}
    for ev in ws_events:
        type_counts[ev.event_type] = type_counts.get(ev.event_type, 0) + 1
        actor_counts[ev.actor] = actor_counts.get(ev.actor, 0) + 1

    return {
        "total_events": len(ws_events),
        "by_type": type_counts,
        "by_actor": actor_counts,
    }
