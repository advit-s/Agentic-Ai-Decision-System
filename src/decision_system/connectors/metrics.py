"""Connector observability metrics helpers.

Records connector operation metrics to the observability store.
"""

from __future__ import annotations

from typing import Any


def _record(name: str, value: float, **tags: Any) -> None:
    """Record a metric point, best-effort."""
    try:
        from decision_system.observability.store import record_metric_point
        record_metric_point(name=name, value=value, tags=tags)
    except Exception:
        pass


def record_import_duration(
    connector_id: str,
    duration_ms: float,
    items_imported: int = 0,
    items_failed: int = 0,
) -> None:
    _record(
        "connector_import_duration_ms",
        duration_ms,
        connector_id=connector_id,
        items_imported=items_imported,
        items_failed=items_failed,
    )


def record_items_found(
    connector_id: str,
    count: int,
) -> None:
    _record(
        "connector_items_found_count",
        float(count),
        connector_id=connector_id,
    )


def record_items_imported(
    connector_id: str,
    count: int,
) -> None:
    _record(
        "connector_items_imported_count",
        float(count),
        connector_id=connector_id,
    )


def record_items_failed(
    connector_id: str,
    count: int,
) -> None:
    _record(
        "connector_items_failed_count",
        float(count),
        connector_id=connector_id,
    )


def record_error(
    connector_id: str,
    error_type: str = "general",
) -> None:
    _record(
        "connector_error_count",
        1.0,
        connector_id=connector_id,
        error_type=error_type,
    )

# ---------------------------------------------------------------------------
# Sync metrics (v1.29)
# ---------------------------------------------------------------------------


def record_sync_duration(
    connector_id: str,
    duration_ms: float,
    items_new: int = 0,
    items_changed: int = 0,
    items_unchanged: int = 0,
    items_failed: int = 0,
) -> None:
    _record(
        "connector_sync_duration_ms",
        duration_ms,
        connector_id=connector_id,
        items_new=items_new,
        items_changed=items_changed,
        items_unchanged=items_unchanged,
        items_failed=items_failed,
    )


def record_sync_items_count(
    connector_id: str,
    status: str,
    count: int,
) -> None:
    _record(
        f"connector_sync_items_{status}_count",
        float(count),
        connector_id=connector_id,
    )


def record_schedules_due(
    count: int,
) -> None:
    _record(
        "connector_schedules_due_count",
        float(count),
    )
