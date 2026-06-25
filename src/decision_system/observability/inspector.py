"""Inspector/CLI display for observability summaries."""

from __future__ import annotations

from typing import Any

from .models import EvalStatus, MetricSummary
from .store import (
    compute_metric_summary,
    list_metric_names,
    load_eval_runs,
    load_quality_reports,
    load_traces,
)


def format_metric_summary(summary: MetricSummary) -> list[str]:
    return [
        f"  {summary.name}",
        f"    count={summary.count} sum={summary.sum:.2f} avg={summary.avg:.2f}",
        f"    min={summary.min:.2f} max={summary.max:.2f}",
    ]


def format_eval_run(record: Any) -> list[str]:
    status_icon = "PASS" if record.status == EvalStatus.PASSED else "FAIL"
    return [
        f"  [{status_icon}] {record.run_id}",
        f"    Type: {record.eval_type}  Status: {record.status.value}",
        f"    Cases: {record.total_cases}  Passed: {record.passed_cases}  Failed: {record.failed_cases}",
        f"    Duration: {record.duration_seconds:.2f}s",
    ]


def format_trace(trace: Any) -> list[str]:
    return [
        f"  [{trace.trace_id}] {trace.workflow_type}",
        f"    Duration: {trace.duration_seconds:.2f}s  Nodes: {trace.node_count}",
        f"    Errors: {trace.error_count}",
    ]


def format_quality_report(report: Any) -> list[str]:
    return [
        f"  Report ID: {report.report_id}",
        f"    Target: {report.target_type}  ID: {report.target_id}",
        f"    Score: {report.overall_score:.2%}  Status: {report.overall_status.upper()}",
    ]


def print_observability_summary(as_json: bool = False) -> dict[str, Any]:
    metrics = [compute_metric_summary(name) for name in list_metric_names()]
    metrics = [m for m in metrics if m is not None]
    runs = load_eval_runs()
    traces = load_traces()
    reports = load_quality_reports()

    if as_json:
        return {
            "metrics": [
                {
                    "name": m.name,
                    "count": m.count,
                    "sum": m.sum,
                    "avg": m.avg,
                    "min": m.min,
                    "max": m.max,
                }
                for m in metrics
            ]
            if metrics
            else [],
            "eval_runs": [
                {
                    "run_id": r.run_id,
                    "eval_type": r.eval_type,
                    "status": r.status.value,
                    "total_cases": r.total_cases,
                    "passed_cases": r.passed_cases,
                    "failed_cases": r.failed_cases,
                }
                for r in runs[:10]
            ]
            if runs
            else [],
            "traces": [
                {
                    "trace_id": t.trace_id,
                    "workflow_type": t.workflow_type,
                    "question": t.question,
                    "duration_seconds": t.duration_seconds,
                    "node_count": t.node_count,
                }
                for t in traces[:10]
            ]
            if traces
            else [],
            "quality_reports": [
                {
                    "report_id": r.report_id,
                    "target_type": r.target_type,
                    "overall_score": r.overall_score,
                    "overall_status": r.overall_status,
                }
                for r in reports[:10]
            ]
            if reports
            else [],
        }

    print("# Observability Summary\n")
    print(f"## Metrics ({len(metrics)})")
    if not metrics:
        print("  (no metrics collected)\n")
    for m in metrics:
        for line in format_metric_summary(m):
            print(line)
    print()

    print(f"## Evaluation Runs ({len(runs)} total, showing 10)")
    if not runs:
        print("  (no eval runs)\n")
    for r in runs[:10]:
        for line in format_eval_run(r):
            print(line)
    print()

    print(f"## Traces ({len(traces)} total, showing 10)")
    if not traces:
        print("  (no traces)\n")
    for t in traces[:10]:
        for line in format_trace(t):
            print(line)
    print()

    print(f"## Quality Reports ({len(reports)} total, showing 10)")
    if not reports:
        print("  (no quality reports)\n")
    for r in reports[:10]:
        for line in format_quality_report(r):
            print(line)

    return {}
