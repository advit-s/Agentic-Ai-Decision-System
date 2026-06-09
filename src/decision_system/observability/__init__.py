"""Observability package.

Provides local quality measurement and trace/evaluation history.
No cloud telemetry or external services are used.
"""

from __future__ import annotations

from .eval_history import EvalHistory
from .inspector import print_observability_summary
from .metrics import MetricsCollector, MetricsReporter
from .models import (
    EvalRunRecord,
    EvalStatus,
    MetricPoint,
    MetricSummary,
    MetricType,
    QualityDimension,
    QualityReport,
    TraceSummary,
)
from .quality_report import generate_quality_report, quality_report_summary_json
from .store import (
    compute_metric_summary,
    get_paths,
    init_store,
    list_metric_names,
    load_eval_runs,
    load_metric_points,
    load_quality_reports,
    load_traces,
    save_eval_run,
    save_quality_report,
    save_trace,
)
from .trace_summary import create_trace, get_recent_traces

__all__ = [
    "EvalHistory",
    "print_observability_summary",
    "MetricsCollector",
    "MetricsReporter",
    "EvalRunRecord",
    "EvalStatus",
    "MetricPoint",
    "MetricSummary",
    "MetricType",
    "QualityDimension",
    "QualityReport",
    "TraceSummary",
    "generate_quality_report",
    "quality_report_summary_json",
    "create_trace",
    "get_recent_traces",
    "compute_metric_summary",
    "get_paths",
    "init_store",
    "list_metric_names",
    "load_eval_runs",
    "load_metric_points",
    "load_quality_reports",
    "load_traces",
    "save_eval_run",
    "save_quality_report",
    "save_trace",
]
