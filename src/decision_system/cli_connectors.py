"""CLI sub-commands for the v1.1 safe connector framework."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from decision_system.connectors.import_jobs import (
    run_dry_run as _run_dry_run,
)
from decision_system.connectors.import_jobs import (
    run_import as _run_import,
)
from decision_system.connectors.inspector import (
    inspect_dry_run_result,
    inspect_import_job,
    render_connector_detail,
    render_connector_list,
)
from decision_system.connectors.registry import (
    get_connector_definition,
    get_registry,
    list_connectors,
)
from decision_system.connectors.store import (
    delete_job,
    get_job,
    load_jobs,
)

connectors_app = typer.Typer(
    name="connectors",
    help="Safe connector framework for controlled data intake (v1.1).",
)

console = Console()


def _fail(msg: str) -> None:
    console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# connectors list
# ---------------------------------------------------------------------------


@connectors_app.command("list")
def connectors_list() -> None:
    """List all registered connectors and their real/stub status."""
    registry = get_registry()
    output = render_connector_list(registry)
    console.print(output)


# ---------------------------------------------------------------------------
# connectors inspect
# ---------------------------------------------------------------------------


@connectors_app.command("inspect")
def connectors_inspect(
    connector_id: str = typer.Argument(
        ..., help="Connector id, e.g. local-files."
    ),
) -> None:
    """Show capability details for a single connector."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        _fail(
            f"Unknown connector '{connector_id}'. "
            f"Run `decision-system connectors list` to see available connectors."
        )
    output = render_connector_detail(definition)
    console.print(output)


# ---------------------------------------------------------------------------
# connectors dry-run
# ---------------------------------------------------------------------------


@connectors_app.command("dry-run")
def connectors_dry_run(
    connector_id: str = typer.Argument(
        ..., help="Connector id, e.g. local-files."
    ),
    path: str = typer.Option(
        ..., "--path", help="Local source path to scan."
    ),
) -> None:
    """Preview what a connector would import without writing files."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        _fail(f"Unknown connector '{connector_id}'.")
    if definition.is_stub:
        _fail(
            f"Connector '{connector_id}' ({definition.name}) is a stub. "
            f"Dry-run is not supported for stub connectors in v1.1."
        )

    result = _run_dry_run(connector_id, path)
    summary = inspect_dry_run_result(result)

    console.print(
        f"Dry run for [{connector_id}] -> {summary['source_path']}",
        markup=False,
    )
    console.print(f"Would import: {summary['would_import_count']} file(s)")

    if summary["files"]:
        console.print("\nFiles that would be imported:")
        for file_info in summary["files"]:
            console.print(
                f"  [{file_info['target_category']}] {file_info['filename']} "
                f"({file_info['size_bytes']} B) -> {file_info['action']}"
            )

    if summary["skipped_files"]:
        console.print("\nFiles that would be skipped:")
        for file_info in summary["skipped_files"]:
            console.print(
                f"  [skip] {file_info['filename']} "
                f"({file_info.get('extension', '')}): {file_info['reason']}"
            )

    if summary["warnings"]:
        console.print("\nWarnings:")
        for warning in summary["warnings"]:
            console.print(f"  [yellow]{warning}[/yellow]")


# ---------------------------------------------------------------------------
# connectors import
# ---------------------------------------------------------------------------


@connectors_app.command("import")
def connectors_import(
    connector_id: str = typer.Argument(
        ..., help="Connector id, e.g. local-files."
    ),
    path: str = typer.Option(
        ..., "--path", help="Local source path to import from."
    ),
) -> None:
    """Execute a real import for a connector.

    Dry-run first with connectors dry-run before using import.
    """
    definition = get_connector_definition(connector_id)
    if definition is None:
        _fail(f"Unknown connector '{connector_id}'.")
    if definition.is_stub:
        _fail(
            f"Connector '{connector_id}' ({definition.name}) is a stub. "
            f"Import is not supported for stub connectors in v1.1. "
            f"Only local-files can import data."
        )

    result = _run_import(connector_id, path)
    summary = inspect_import_job(result.job)

    console.print(
        f"Import job [{summary['job_id']}] for [{connector_id}]"
    )
    console.print(f"Status: {summary['status']}")
    console.print(f"Source: {summary['source_path']}")
    console.print(
        f"Imported: {summary['imported_count']}, "
        f"Skipped: {summary['skipped_count']}"
    )

    if result.job.output_paths:
        console.print("\nOutput files:")
        for out_path in result.job.output_paths:
            console.print(f"  {out_path}")

    if summary["warnings"]:
        console.print("\nWarnings:")
        for warning in summary["warnings"]:
            console.print(f"  [yellow]{warning}[/yellow]")


# ---------------------------------------------------------------------------
# connectors inspect-jobs
# ---------------------------------------------------------------------------


@connectors_app.command("inspect-jobs")
def connectors_inspect_jobs(
    json_output: bool = typer.Option(
        False, "--json", help="Print structured JSON."
    ),
) -> None:
    """Inspect persisted connector import jobs."""
    jobs = load_jobs()
    if not jobs:
        console.print("No connector import jobs found.")
        raise typer.Exit(code=0)

    if json_output:
        payload = [
            inspect_import_job(job) for job in jobs
        ]
        typer.echo(json.dumps(payload, indent=2))
        return

    table = Table(title="Connector Import Jobs")
    table.add_column("Job ID", style="cyan")
    table.add_column("Connector")
    table.add_column("Status")
    table.add_column("Imported")
    table.add_column("Skipped")
    table.add_column("Created")

    for job in jobs:
        table.add_row(
            job.job_id,
            job.connector_id,
            job.status,
            str(len(job.imported_files)),
            str(len(job.skipped_files)),
            job.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if job.created_at
            else "(unknown)",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Wire into main CLI
# ---------------------------------------------------------------------------


def register_connector_commands(main_app: typer.Typer) -> None:
    """Attach connector commands to the main Typer app."""
    main_app.add_typer(
        connectors_app,
        name="connectors",
        help="Safe connector framework for controlled data intake (v1.1).",
    )
