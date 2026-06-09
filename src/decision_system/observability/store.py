"""Persistent storage helpers for observability artifacts."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .models import (
    EvalRunRecord,
    MetricPoint,
    MetricSummary,
    ObservabilityStorePaths,
    QualityReport,
    TraceSummary,
)


def _get_default_root() -> str:
    return os.environ.get(
        "DECISION_OBSERVABILITY_ROOT",
        str(Path(".decision_system/observability").resolve()),
    )


def get_paths(root: Optional[str] = None) -> ObservabilityStorePaths:
    r = root or _get_default_root()
    return ObservabilityStorePaths(
        root=r,
        metrics=os.path.join(r, "metrics"),
        eval_history=os.path.join(r, "eval_history"),
        quality_reports=os.path.join(r, "quality_reports"),
        traces=os.path.join(r, "traces"),
    )


def init_store(root: Optional[str] = None) -> ObservabilityStorePaths:
    paths = get_paths(root)
    for d in [paths.root, paths.metrics, paths.eval_history, paths.quality_reports, paths.traces]:
        Path(d).mkdir(parents=True, exist_ok=True)
    return paths


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def save_metric_point(point: MetricPoint, root: Optional[str] = None) -> str:
    paths = get_paths(root)
    Path(paths.metrics).mkdir(parents=True, exist_ok=True)
    path = os.path.join(paths.metrics, f"{point.name}.jsonl")
    row = {
        "name": point.name,
        "value": point.value,
        "metric_type": point.metric_type.value,
        "timestamp": point.timestamp.isoformat(),
        "labels": point.labels,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return path


def list_metric_names(root: Optional[str] = None) -> list[str]:
    paths = get_paths(root)
    metrics_dir = Path(paths.metrics)
    if not metrics_dir.exists():
        return []
    return sorted([p.stem for p in metrics_dir.glob("*.jsonl")])


def load_metric_points(name: str, root: Optional[str] = None) -> list[MetricPoint]:
    paths = get_paths(root)
    path = Path(paths.metrics) / f"{name}.jsonl"
    if not path.exists():
        return []
    points: list[MetricPoint] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                points.append(
                    MetricPoint(
                        name=row["name"],
                        value=row["value"],
                        metric_type=row["metric_type"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        labels=row.get("labels", {}),
                    )
                )
            except (json.JSONDecodeError, KeyError):
                continue
    return points


def compute_metric_summary(name: str, root: Optional[str] = None) -> Optional[MetricSummary]:
    points = load_metric_points(name, root)
    if not points:
        return None
    values = [p.value for p in points]
    values.sort()
    n = len(values)
    total = sum(values)
    avg = total / n if n else 0.0
    p50 = values[n // 2] if n else 0.0
    p95 = values[int(n * 0.95)] if n else 0.0
    p99 = values[int(n * 0.99)] if n else 0.0
    return MetricSummary(
        name=name,
        count=n,
        sum=total,
        min=values[0] if values else 0.0,
        max=values[-1] if values else 0.0,
        avg=avg,
        p50=p50,
        p95=p95,
        p99=p99,
    )


def save_eval_run(record: EvalRunRecord, root: Optional[str] = None) -> str:
    paths = get_paths(root)
    Path(paths.eval_history).mkdir(parents=True, exist_ok=True)
    path = Path(paths.eval_history) / f"{record.run_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(record.model_dump_json(indent=2))
    return str(path)


def load_eval_runs(root: Optional[str] = None) -> list[EvalRunRecord]:
    paths = get_paths(root)
    dir_path = Path(paths.eval_history)
    if not dir_path.exists():
        return []
    records: list[EvalRunRecord] = []
    for p in dir_path.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                records.append(EvalRunRecord.model_validate_json(f.read()))
        except Exception:
            continue
    return sorted(records, key=lambda r: r.started_at, reverse=True)


def save_quality_report(report: QualityReport, root: Optional[str] = None) -> str:
    paths = get_paths(root)
    Path(paths.quality_reports).mkdir(parents=True, exist_ok=True)
    path = Path(paths.quality_reports) / f"{report.report_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    return str(path)


def load_quality_reports(root: Optional[str] = None) -> list[QualityReport]:
    paths = get_paths(root)
    dir_path = Path(paths.quality_reports)
    if not dir_path.exists():
        return []
    reports: list[QualityReport] = []
    for p in dir_path.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                reports.append(QualityReport.model_validate_json(f.read()))
        except Exception:
            continue
    return sorted(reports, key=lambda r: r.created_at, reverse=True)


def save_trace(trace: TraceSummary, root: Optional[str] = None) -> str:
    paths = get_paths(root)
    Path(paths.traces).mkdir(parents=True, exist_ok=True)
    path = Path(paths.traces) / f"{trace.trace_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        f.write(trace.model_dump_json(indent=2))
    return str(path)


def load_traces(root: Optional[str] = None) -> list[TraceSummary]:
    paths = get_paths(root)
    dir_path = Path(paths.traces)
    if not dir_path.exists():
        return []
    traces: list[TraceSummary] = []
    for p in dir_path.glob("*.json"):
        try:
            with open(p, "r", encoding="utf-8") as f:
                traces.append(TraceSummary.model_validate_json(f.read()))
        except Exception:
            continue
    return sorted(traces, key=lambda t: t.started_at, reverse=True)
