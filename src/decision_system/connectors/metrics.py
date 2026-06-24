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


# ---------------------------------------------------------------------------
# Setup metrics (v1.30)
# ---------------------------------------------------------------------------


def record_setup_duration(
    connector_type: str,
    duration_ms: float,
    success: bool = True,
) -> None:
    """Record connector setup duration."""
    _record(
        "connector_setup_duration_ms",
        duration_ms,
        connector_type=connector_type,
        success=str(success),
    )


def record_test_success(
    connector_type: str,
) -> None:
    """Record a successful connector test."""
    _record(
        "connector_test_success_count",
        1.0,
        connector_type=connector_type,
    )


def record_test_failure(
    connector_type: str,
    error_type: str = "general",
) -> None:
    """Record a failed connector test."""
    _record(
        "connector_test_failure_count",
        1.0,
        connector_type=connector_type,
        error_type=error_type,
    )


def record_preview_item_count(
    connector_id: str,
    count: int,
) -> None:
    """Record the number of items previewed before import."""
    _record(
        "connector_preview_item_count",
        float(count),
        connector_id=connector_id,
    )


def record_import_by_type(
    connector_type: str,
    item_type: str,
    count: int = 1,
) -> None:
    """Record import by connector and item type."""
    _record(
        "connector_import_by_type_count",
        float(count),
        connector_type=connector_type,
        item_type=item_type,
    )
# ---------------------------------------------------------------------------
# Reliability metrics (v1.31)
# ---------------------------------------------------------------------------


def record_batch_duration(
    connector_id: str,
    duration_ms: float,
    batch_number: int = 0,
) -> None:
    _record(
        "connector_batch_duration_ms",
        duration_ms,
        connector_id=connector_id,
        batch_number=batch_number,
    )


def record_retry_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_retry_count",
        float(count),
        connector_id=connector_id,
    )


def record_rate_limit_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_rate_limit_count",
        float(count),
        connector_id=connector_id,
    )


def record_cancel_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_cancel_count",
        float(count),
        connector_id=connector_id,
    )


def record_resume_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_resume_count",
        float(count),
        connector_id=connector_id,
    )


def record_duplicate_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_duplicate_count",
        float(count),
        connector_id=connector_id,
    )


def record_large_import_count(
    connector_id: str,
    count: int = 1,
) -> None:
    _record(
        "connector_large_import_count",
        float(count),
        connector_id=connector_id,
    )
