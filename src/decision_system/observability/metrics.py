"""Metrics collection and aggregation for observability."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from .models import MetricPoint, MetricSummary, MetricType
from .store import compute_metric_summary, list_metric_names, load_metric_points, save_metric_point


class MetricsCollector:
    """Simple in-memory collector that persists to JSONL on demand."""

    def __init__(self) -> None:
        self._points: list[MetricPoint] = []

    def record(self, name: str, value: float, metric_type: MetricType, labels: Optional[dict[str, str]] = None) -> None:
        point = MetricPoint(name=name, value=value, metric_type=metric_type, labels=labels or {})
        self._points.append(point)
        save_metric_point(point)

    def flush(self) -> None:
        for point in self._points:
            save_metric_point(point)
        self._points.clear()


class MetricsReporter:
    """Summarize metric history."""

    def report(self) -> list[MetricSummary]:
        summaries: list[MetricSummary] = []
        for name in list_metric_names():
            summary = compute_metric_summary(name)
            if summary is not None:
                summaries.append(summary)
        return summaries


def default_metrics_collector() -> MetricsCollector:
    return MetricsCollector()


def default_metrics_reporter() -> MetricsReporter:
    return MetricsReporter()
