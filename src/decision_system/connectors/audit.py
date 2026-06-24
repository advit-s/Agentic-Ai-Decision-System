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
EVENT_CONNECTOR_SCHEDULE_TOGGLED = "connector_schedule_toggled"


# ---------------------------------------------------------------------------
# Setup audit events (v1.30)
# ---------------------------------------------------------------------------

EVENT_CONNECTOR_SETUP_STARTED = "connector_setup_started"
EVENT_CONNECTOR_SETUP_TESTED = "connector_setup_tested"
EVENT_CONNECTOR_SETUP_COMPLETED = "connector_setup_completed"
EVENT_CONNECTOR_SETUP_FAILED = "connector_setup_failed"
EVENT_CONNECTOR_CREDENTIALS_MISSING = "connector_credentials_missing"
EVENT_CONNECTOR_ITEM_PREVIEWED = "connector_item_previewed"
EVENT_GITHUB_ISSUE_IMPORTED = "github_issue_imported"
EVENT_CONNECTOR_PREVIEW_ITEM_COUNT = "connector_preview_item_count"


def record_setup_started(
    connector_type: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SETUP_STARTED,
        f"Connector setup started for type '{connector_type}'",
        connector_type=connector_type,
        workspace_id=workspace_id,
        **extra,
    )


def record_setup_tested(
    connector_type: str,
    success: bool,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SETUP_TESTED,
        f"Connector setup test for '{connector_type}' {'succeeded' if success else 'failed'}",
        connector_type=connector_type,
        success=success,
        workspace_id=workspace_id,
        **extra,
    )


def record_setup_completed(
    connector_type: str,
    connector_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SETUP_COMPLETED,
        f"Connector setup completed for '{connector_type}' (id={connector_id})",
        connector_type=connector_type,
        connector_id=connector_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_setup_failed(
    connector_type: str,
    error: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SETUP_FAILED,
        f"Connector setup failed for '{connector_type}': {error}",
        connector_type=connector_type,
        error=error,
        workspace_id=workspace_id,
        **extra,
    )


def record_credentials_missing(
    connector_type: str,
    env_var_name: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_CREDENTIALS_MISSING,
        f"Credentials missing for '{connector_type}': set {env_var_name}",
        connector_type=connector_type,
        env_var_name=env_var_name,
        workspace_id=workspace_id,
        **extra,
    )


def record_item_previewed(
    connector_id: str,
    item_count: int,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_ITEM_PREVIEWED,
        f"Connector '{connector_id}' previewed {item_count} items",
        connector_id=connector_id,
        item_count=item_count,
        workspace_id=workspace_id,
        **extra,
    )


def record_github_issue_imported(
    connector_id: str,
    issue_number: int,
    issue_title: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_GITHUB_ISSUE_IMPORTED,
        f"GitHub issue #{issue_number} '{issue_title}' imported via connector '{connector_id}'",
        connector_id=connector_id,
        issue_number=issue_number,
        issue_title=issue_title,
        workspace_id=workspace_id,
        **extra,
    )
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

# ---------------------------------------------------------------------------
# Sync audit events (v1.29)
# ---------------------------------------------------------------------------

EVENT_CONNECTOR_SYNC_STARTED = "connector_sync_started"
EVENT_CONNECTOR_SYNC_COMPLETED = "connector_sync_completed"
EVENT_CONNECTOR_SYNC_FAILED = "connector_sync_failed"
EVENT_CONNECTOR_SYNC_ITEM_NEW = "connector_sync_item_new"
EVENT_CONNECTOR_SYNC_ITEM_CHANGED = "connector_sync_item_changed"
EVENT_CONNECTOR_SYNC_ITEM_UNCHANGED = "connector_sync_item_unchanged"
EVENT_CONNECTOR_SYNC_ITEM_FAILED = "connector_sync_item_failed"
EVENT_CONNECTOR_SCHEDULE_CREATED = "connector_schedule_created"
EVENT_CONNECTOR_SCHEDULE_UPDATED = "connector_schedule_updated"
EVENT_CONNECTOR_SCHEDULE_DELETED = "connector_schedule_deleted"
EVENT_CONNECTOR_SCHEDULE_TOGGLED = "connector_schedule_toggled"


def record_sync_started(
    connector_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_STARTED,
        f"Connector '{connector_id}' sync started",
        connector_id=connector_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_completed(
    connector_id: str,
    items_new: int,
    items_changed: int,
    items_unchanged: int,
    items_failed: int,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_COMPLETED,
        f"Connector '{connector_id}' sync completed: "
        f"{items_new} new, {items_changed} changed, {items_unchanged} unchanged, {items_failed} failed",
        connector_id=connector_id,
        items_new=items_new,
        items_changed=items_changed,
        items_unchanged=items_unchanged,
        items_failed=items_failed,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_failed(
    connector_id: str,
    error: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_FAILED,
        f"Connector '{connector_id}' sync failed: {error}",
        connector_id=connector_id,
        error=error,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_item_new(
    connector_id: str,
    external_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_ITEM_NEW,
        f"New item '{external_id}' from connector '{connector_id}'",
        connector_id=connector_id,
        external_id=external_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_item_changed(
    connector_id: str,
    external_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_ITEM_CHANGED,
        f"Changed item '{external_id}' from connector '{connector_id}'",
        connector_id=connector_id,
        external_id=external_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_item_unchanged(
    connector_id: str,
    external_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_ITEM_UNCHANGED,
        f"Unchanged item '{external_id}' from connector '{connector_id}'",
        connector_id=connector_id,
        external_id=external_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_sync_item_failed(
    connector_id: str,
    external_id: str,
    error: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SYNC_ITEM_FAILED,
        f"Item '{external_id}' sync failed: {error}",
        connector_id=connector_id,
        external_id=external_id,
        error=error,
        workspace_id=workspace_id,
        **extra,
    )


def record_schedule_created(
    connector_id: str,
    schedule_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SCHEDULE_CREATED,
        f"Schedule '{schedule_id}' created for connector '{connector_id}'",
        connector_id=connector_id,
        schedule_id=schedule_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_schedule_updated(
    connector_id: str,
    schedule_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SCHEDULE_UPDATED,
        f"Schedule '{schedule_id}' updated for connector '{connector_id}'",
        connector_id=connector_id,
        schedule_id=schedule_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_schedule_deleted(
    connector_id: str,
    schedule_id: str,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SCHEDULE_DELETED,
        f"Schedule '{schedule_id}' deleted for connector '{connector_id}'",
        connector_id=connector_id,
        schedule_id=schedule_id,
        workspace_id=workspace_id,
        **extra,
    )


def record_schedule_toggled(
    connector_id: str,
    schedule_id: str,
    enabled: bool,
    workspace_id: str | None = None,
    **extra: Any,
) -> None:
    _emit(
        EVENT_CONNECTOR_SCHEDULE_TOGGLED,
        f"Schedule '{schedule_id}' {'enabled' if enabled else 'disabled'} for connector '{connector_id}'",
        connector_id=connector_id,
        schedule_id=schedule_id,
        enabled=enabled,
        workspace_id=workspace_id,
        **extra,
    )
