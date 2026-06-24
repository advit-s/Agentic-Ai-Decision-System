"""Connector-specific audit event helpers.

Provides typed audit event recording for all connector operations.
Events are recorded in the shared JSONL audit log under .decision_system/security/audit/.
"""

from __future__ import annotations

from typing import Any

from decision_system.security.audit import append_event

# ---------------------------------------------------------------------------
# Connector audit event types
# ---------------------------------------------------------------------------

EVENT_CONNECTOR_CREATED = "connector_created"
EVENT_CONNECTOR_UPDATED = "connector_updated"
EVENT_CONNECTOR_DELETED = "connector_deleted"
EVENT_CONNECTOR_TESTED = "connector_tested"
EVENT_CONNECTOR_ITEMS_LISTED = "connector_items_listed"
EVENT_CONNECTOR_IMPORT_STARTED = "connector_import_started"
EVENT_CONNECTOR_IMPORT_COMPLETED = "connector_import_completed"
EVENT_CONNECTOR_IMPORT_FAILED = "connector_import_failed"
EVENT_CONNECTOR_ITEM_IMPORTED = "connector_item_imported"


def _emit(event_type: str, message: str, **metadata: Any) -> None:
    """Emit a connector audit event."""
    try:
        append_event(
            event_type=event_type,
            message=message,
            metadata=metadata,
        )
    except Exception:
        pass  # Audit failures must never block connector operations


def record_connector_created(
    connector_id: str,
    name: str,
    connector_type: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_CREATED,
        f"Connector '{name}' ({connector_type}) created",
        connector_id=connector_id,
        name=name,
        connector_type=connector_type,
        workspace_id=workspace_id,
        **extra,
    )


def record_connector_updated(
    connector_id: str,
    name: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_UPDATED,
        f"Connector '{name}' updated",
        connector_id=connector_id,
        name=name,
        workspace_id=workspace_id,
        **extra,
    )


def record_connector_deleted(
    connector_id: str,
    name: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_DELETED,
        f"Connector '{name}' deleted",
        connector_id=connector_id,
        name=name,
        workspace_id=workspace_id,
        **extra,
    )


def record_connector_tested(
    connector_id: str,
    success: bool,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_TESTED,
        f"Connector '{connector_id}' test {'succeeded' if success else 'failed'}",
        connector_id=connector_id,
        success=success,
        workspace_id=workspace_id,
        **extra,
    )


def record_connector_items_listed(
    connector_id: str,
    item_count: int,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_ITEMS_LISTED,
        f"Connector '{connector_id}' listed {item_count} items",
        connector_id=connector_id,
        item_count=item_count,
        workspace_id=workspace_id,
        **extra,
    )


def record_import_started(
    connector_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_IMPORT_STARTED,
        f"Connector '{connector_id}' import started",
        connector_id=connector_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_import_completed(
    connector_id: str,
    items_imported: int,
    items_skipped: int,
    items_failed: int,
    job_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_IMPORT_COMPLETED,
        f"Connector '{connector_id}' import completed: "
        f"{items_imported} imported, {items_skipped} skipped, {items_failed} failed",
        connector_id=connector_id,
        items_imported=items_imported,
        items_skipped=items_skipped,
        items_failed=items_failed,
        job_id=job_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_import_failed(
    connector_id: str,
    error: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_IMPORT_FAILED,
        f"Connector '{connector_id}' import failed: {error}",
        connector_id=connector_id,
        error=error,
        workspace_id=workspace_id,
        **extra,
    )


def record_item_imported(
    connector_id: str,
    external_id: str,
    title: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_ITEM_IMPORTED,
        f"Item '{title}' imported via connector '{connector_id}'",
        connector_id=connector_id,
        external_id=external_id,
        title=title,
        workspace_id=workspace_id,
        **extra,
    )
