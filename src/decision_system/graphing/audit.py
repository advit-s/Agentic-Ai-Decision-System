"""Graph operation audit events and metrics.

Integrates with the existing observability metrics system to record
graph extraction events and performance metrics.

Events:
  - graph_extraction_started
  - graph_extraction_completed
  - graph_extraction_failed
  - risk_extraction_completed
  - metric_extraction_completed
  - graph_fact_created

Metrics:
  - graph_extraction_duration_ms
  - entities_extracted_count
  - edges_extracted_count
  - risks_extracted_count
  - metrics_extracted_count
  - graph_extraction_failure_count
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator

from decision_system.observability.metrics import default_metrics_collector
from decision_system.observability.models import MetricType


def _record_metric(name: str, value: float, metric_type: str = "counter", **labels: str) -> None:
    """Record a single metric point via the observability system."""
    collector = default_metrics_collector()
    mt = MetricType(metric_type) if isinstance(metric_type, str) else metric_type
    collector.record(name=name, value=value, metric_type=mt, labels=labels or None)


# ---------------------------------------------------------------------------
# Event helpers
# ---------------------------------------------------------------------------


def graph_extraction_started(workspace_id: str, **extra: str) -> None:
    """Emit graph_extraction_started event."""
    _record_metric(
        "graph_extraction_started", 1.0,
        event_type="graph_extraction_started",
        workspace_id=workspace_id,
        **extra,
    )


def graph_extraction_completed(
    workspace_id: str,
    duration_ms: float,
    entities_count: int = 0,
    edges_count: int = 0,
    risks_count: int = 0,
    metrics_count: int = 0,
    **extra: str,
) -> None:
    """Emit graph_extraction_completed event with metrics."""
    _record_metric(
        "graph_extraction_completed", 1.0,
        event_type="graph_extraction_completed",
        workspace_id=workspace_id,
        **extra,
    )
    # Performance metric
    _record_metric(
        "graph_extraction_duration_ms", duration_ms,
        metric_type="timer",
        workspace_id=workspace_id,
    )
    # Count metrics
    if entities_count > 0:
        _record_metric("entities_extracted_count", float(entities_count), workspace_id=workspace_id)
    if edges_count > 0:
        _record_metric("edges_extracted_count", float(edges_count), workspace_id=workspace_id)
    if risks_count > 0:
        _record_metric("risks_extracted_count", float(risks_count), workspace_id=workspace_id)
    if metrics_count > 0:
        _record_metric("metrics_extracted_count", float(metrics_count), workspace_id=workspace_id)


def graph_extraction_failed(workspace_id: str, error: str, **extra: str) -> None:
    """Emit graph_extraction_failed event."""
    _record_metric(
        "graph_extraction_failed", 1.0,
        event_type="graph_extraction_failed",
        workspace_id=workspace_id,
        error=error[:80] if error else "unknown",
        **extra,
    )
    _record_metric(
        "graph_extraction_failure_count", 1.0,
        metric_type="counter",
        workspace_id=workspace_id,
    )


def risk_extraction_completed(workspace_id: str, risks_count: int = 0, **extra: str) -> None:
    """Emit risk_extraction_completed event."""
    _record_metric(
        "risk_extraction_completed", 1.0,
        event_type="risk_extraction_completed",
        workspace_id=workspace_id,
        **extra,
    )
    if risks_count > 0:
        _record_metric("risks_extracted_count", float(risks_count), workspace_id=workspace_id)


def metric_extraction_completed(workspace_id: str, metrics_count: int = 0, **extra: str) -> None:
    """Emit metric_extraction_completed event."""
    _record_metric(
        "metric_extraction_completed", 1.0,
        event_type="metric_extraction_completed",
        workspace_id=workspace_id,
        **extra,
    )
    if metrics_count > 0:
        _record_metric("metrics_extracted_count", float(metrics_count), workspace_id=workspace_id)


def graph_fact_created(
    workspace_id: str,
    fact_type: str,
    fact_id: str,
    **extra: str,
) -> None:
    """Emit graph_fact_created event for a single graph fact."""
    _record_metric(
        "graph_fact_created", 1.0,
        event_type="graph_fact_created",
        workspace_id=workspace_id,
        fact_type=fact_type,
        fact_id=fact_id[:40],
        **extra,
    )


# ---------------------------------------------------------------------------
# Timing context manager
# ---------------------------------------------------------------------------


@contextmanager
def track_graph_extraction(workspace_id: str) -> Generator[dict[str, Any], None, None]:
    """Context manager that tracks extraction duration and emits events.

    Usage:
        with track_graph_extraction(ws_id) as state:
            ... do extraction ...
            state["entities"] = 5
            state["edges"] = 3
    """
    state: dict[str, Any] = {
        "workspace_id": workspace_id,
        "started": time.monotonic(),
    }
    graph_extraction_started(workspace_id)
    try:
        yield state
        duration_ms = (time.monotonic() - state["started"]) * 1000.0
        graph_extraction_completed(
            workspace_id=workspace_id,
            duration_ms=duration_ms,
            entities_count=state.get("entities", 0),
            edges_count=state.get("edges", 0),
            risks_count=state.get("risks", 0),
            metrics_count=state.get("metrics", 0),
        )
    except Exception as exc:
        duration_ms = (time.monotonic() - state["started"]) * 1000.0
        graph_extraction_failed(workspace_id, str(exc))
        raise
