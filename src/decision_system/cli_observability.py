"""CLI sub-commands for v1.3 Observability, Metrics, and Evaluation History.

All commands operate on local JSONL/JSON stores and require no cloud
telemetry or external services. Heavy imports are deferred inside command
functions so CLI import stays fast.
"""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console

# ---------------------------------------------------------------------------
# Sub-app for observability sub-commands
# ---------------------------------------------------------------------------

observability_app = typer.Typer(
    name="observability",
    help="Observability, metrics, and evaluation history.",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _to_jsonable(value: Any) -> Any:
    """Convert Pydantic models and nested structures to JSON-safe dicts."""
    from pydantic import BaseModel  # noqa: PLC0415

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


# ---------------------------------------------------------------------------
# Core observability commands (shared between sub-app and top-level aliases)
# ---------------------------------------------------------------------------


def _cmd_metrics(json_output: bool = False) -> None:
    """Show collected metrics summary."""
    from decision_system.observability import (  # noqa: PLC0415
        compute_metric_summary,
        list_metric_names,
    )

    names = list_metric_names()
    if not names:
        if json_output:
            typer.echo(json.dumps({"metrics": [], "count": 0}, indent=2))
        else:
            console.print("No metrics collected yet.")
        return

    summaries = [compute_metric_summary(n) for n in names]
    summaries = [s for s in summaries if s is not None]

    if json_output:
        payload = {
            "count": len(summaries),
            "metrics": [
                {
                    "name": s.name,
                    "count": s.count,
                    "sum": s.sum,
                    "avg": s.avg,
                    "min": s.min,
                    "max": s.max,
                }
                for s in summaries
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(f"# Metrics Summary ({len(summaries)})")
        for s in summaries:
            console.print(
                f"  {s.name}: count={s.count} avg={s.avg:.2f} "
                f"min={s.min:.2f} max={s.max:.2f}"
            )


def _cmd_eval_history(json_output: bool = False) -> None:
    """Show evaluation run history."""
    from decision_system.observability import load_eval_runs  # noqa: PLC0415

    runs = load_eval_runs()
    if json_output:
        payload = {
            "total": len(runs),
            "runs": [
                {
                    "run_id": r.run_id,
                    "eval_type": r.eval_type,
                    "status": r.status.value,
                    "total_cases": r.total_cases,
                    "passed_cases": r.passed_cases,
                    "failed_cases": r.failed_cases,
                    "duration_seconds": r.duration_seconds,
                }
                for r in runs[:20]
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(f"# Evaluation History ({len(runs)} runs)")
        if not runs:
            console.print("  (no eval runs recorded)")
        for r in runs[:20]:
            status = "✓" if r.status.value == "passed" else "✗"
            console.print(
                f"  [{status}] {r.run_id} ({r.eval_type}) — "
                f"{r.total_cases} cases, {r.passed_cases} passed, "
                f"{r.duration_seconds:.2f}s"
            )


def _cmd_quality_report(json_output: bool = False) -> None:
    """Generate and view a quality report from evaluation history."""
    from decision_system.observability import (  # noqa: PLC0415
        generate_quality_report,
    )

    report = generate_quality_report()
    if json_output:
        from decision_system.observability.quality_report import (  # noqa: PLC0415
            quality_report_summary_json,
        )

        typer.echo(json.dumps(quality_report_summary_json(report), indent=2))
    else:
        console.print(f"# Quality Report ({report.report_id})")
        console.print(f"  Target: {report.target_type}")
        console.print(f"  Score: {report.overall_score:.2%}")
        console.print(f"  Status: {report.overall_status.upper()}")
        if report.recommendations:
            console.print("  Recommendations:")
            for rec in report.recommendations:
                console.print(f"    - {rec}")


def _cmd_trace_summary(json_output: bool = False) -> None:
    """Show recent trace summaries."""
    from decision_system.observability import load_traces  # noqa: PLC0415

    traces = load_traces()[:10]
    if json_output:
        payload = {
            "total": len(traces),
            "traces": [
                {
                    "trace_id": t.trace_id,
                    "workflow_type": t.workflow_type,
                    "question": t.question,
                    "duration_seconds": t.duration_seconds,
                    "node_count": t.node_count,
                    "error_count": t.error_count,
                }
                for t in traces
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(f"# Recent Traces ({len(traces)})")
        if not traces:
            console.print("  (no traces recorded)")
        for t in traces:
            console.print(
                f"  [{t.trace_id}] {t.workflow_type} - "
                f"{t.duration_seconds:.2f}s, {t.node_count} nodes"
            )


# ---------------------------------------------------------------------------
# Observability sub-app commands (decision-system observability <command>)
# ---------------------------------------------------------------------------


@observability_app.command("metrics")
def _obs_metrics(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show collected metrics summary."""
    _cmd_metrics(json_output=json_output)


@observability_app.command("eval-history")
def _obs_eval_history(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show evaluation run history."""
    _cmd_eval_history(json_output=json_output)


@observability_app.command("quality-report")
def _obs_quality_report(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Generate and view a quality report from evaluation history."""
    _cmd_quality_report(json_output=json_output)


@observability_app.command("trace-summary")
def _obs_trace_summary(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show recent trace summaries."""
    _cmd_trace_summary(json_output=json_output)


# ---------------------------------------------------------------------------
# Registration helper (called from cli.py)
# ---------------------------------------------------------------------------


def register_observability_commands(main_app: typer.Typer) -> None:
    """Attach top-level observability aliases and the sub-app to the main CLI.

    Registers:
    - Top-level commands: ``metrics``, ``eval-history``, ``quality-report``, ``trace-summary``
    - Sub-group: ``decision-system observability <command>``
    """

    @main_app.command("metrics")
    def _top_metrics(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        """Show collected metrics summary."""
        _cmd_metrics(json_output=json_output)

    @main_app.command("eval-history")
    def _top_eval_history(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        """Show evaluation run history."""
        _cmd_eval_history(json_output=json_output)

    @main_app.command("quality-report")
    def _top_quality_report(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        """Generate and view a quality report from evaluation history."""
        _cmd_quality_report(json_output=json_output)

    @main_app.command("trace-summary")
    def _top_trace_summary(
        json_output: bool = typer.Option(False, "--json"),
    ) -> None:
        """Show recent trace summaries."""
        _cmd_trace_summary(json_output=json_output)

    main_app.add_typer(observability_app)
