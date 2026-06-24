"""Observability API endpoints (v1.3).

Exposes metrics, eval history, quality reports, and trace summaries
from the local observability store.  Returns empty defaults when no
data has been recorded yet (the observability module is standalone
scaffolding not yet wired into the core workflow).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from dataclasses import asdict

from decision_system.observability.store import (
    compute_metric_summary,
    list_metric_names,
    load_eval_runs,
    load_metric_points,
    load_quality_reports,
    load_traces,
)


def __dataclass_to_dict(obj):
    """Convert a dataclass instance to a JSON-compatible dict."""
    d = asdict(obj)
    # Convert datetime objects to ISO strings
    for k, v in d.items():
        if hasattr(v, 'isoformat'):
            d[k] = v.isoformat()
    return d

router = APIRouter(prefix="/observability", tags=["observability"])


@router.get("/metrics")
def get_observability_metrics() -> dict[str, Any]:
    """Return collected metrics and summaries."""
    names = list_metric_names()
    metrics = {}
    for name in names:
        points = load_metric_points(name)
        summary = compute_metric_summary(name)
        metrics[name] = {
            "points": [__dataclass_to_dict(p) for p in points],
            "summary": __dataclass_to_dict(summary) if summary else None,
        }
    return {
        "metrics": metrics,
        "metric_count": len(names),
    }


@router.get("/eval-history")
def get_observability_eval_history() -> dict[str, Any]:
    """Return recent evaluation run history."""
    runs = load_eval_runs()
    return {
        "eval_runs": [r.model_dump(mode="json") for r in runs],
        "count": len(runs),
    }


@router.get("/quality-report")
def get_observability_quality_report() -> dict[str, Any]:
    """Return quality reports."""
    reports = load_quality_reports()
    return {
        "quality_reports": [r.model_dump(mode="json") for r in reports],
        "count": len(reports),
    }


@router.get("/traces")
def get_observability_traces() -> dict[str, Any]:
    """Return recent trace summaries."""
    traces = load_traces()
    return {
        "traces": [t.model_dump(mode="json") for t in traces],
        "count": len(traces),
    }
