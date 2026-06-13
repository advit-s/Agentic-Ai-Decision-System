"""CLI commands for workflow management and execution."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.dag import DAGValidator, TopologicalSort
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.nodes import create_default_registry

console = Console()
app = typer.Typer(help="Create, validate, and run workflow definitions.")
_registry = create_default_registry()


def _load_workflow(path: Path) -> WorkflowDefinition:
    """Load a WorkflowDefinition from a JSON file."""
    data = json.loads(path.read_text())
    if "name" in data:
        nodes = [NodeConfig(**n) for n in data.get("nodes", [])]
        connections = [Connection(**c) for c in data.get("connections", [])]
        return WorkflowDefinition(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            nodes=nodes,
            connections=connections,
            version=data.get("version", 1),
        )
    raise ValueError("Invalid workflow definition: missing 'name' field")


@app.command()
def validate(
    workflow_path: Path = typer.Argument(
        ..., help="Path to workflow JSON file", exists=True,
    ),
) -> None:
    """Validate a workflow DAG definition."""
    try:
        wf = _load_workflow(workflow_path)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    errors = DAGValidator.validate(wf)
    if errors:
        console.print(f"[red]Workflow has {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(1)

    layers = TopologicalSort.sort(wf)
    console.print(f"[green]✓[/green] Workflow is valid: {len(wf.nodes)} nodes in {len(layers)} layers")


@app.command()
def list_nodes() -> None:
    """List all available node types."""
    types = _registry.list_types()
    table = Table(title=f"Available Nodes ({len(types)})")
    table.add_column("Type", style="cyan")
    table.add_column("Label", style="green")
    table.add_column("Description")

    for nt in types:
        desc = nt.description[:60] + "..." if len(nt.description) > 60 else nt.description
        table.add_row(nt.type, nt.label, desc)

    console.print(table)


@app.command()
def create(
    output_path: Path = typer.Argument(
        ..., help="Path to write the workflow template JSON",
    ),
    name: str = typer.Option("untitled", "--name", "-n", help="Workflow name"),
) -> None:
    """Generate a workflow template JSON file."""
    template = {
        "name": name,
        "description": "",
        "version": 1,
        "nodes": [
            {
                "id": "trigger_1",
                "type": "decision_system.trigger_manual",
                "label": "Manual Trigger",
                "config": {},
                "error_policy": "fail_workflow",
                "position_x": 100,
                "position_y": 100,
            },
            {
                "id": "node_1",
                "type": "decision_system.input_text",
                "label": "Input Text",
                "config": {"text": ""},
                "error_policy": "fail_workflow",
                "position_x": 300,
                "position_y": 100,
            },
        ],
        "connections": [
            {"source_node": "trigger_1", "source_output": "default",
             "target_node": "node_1", "target_input": "default"},
        ],
        "tags": [],
    }
    output_path.write_text(json.dumps(template, indent=2))
    console.print(f"[green]✓[/green] Created workflow template at {output_path}")


@app.command(name="list")
def list_workflows(
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """List saved workflow definitions."""
    from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore
    import tempfile

    if store_dir:
        ws = JSONWorkflowStore(store_dir)
    else:
        ws = JSONWorkflowStore(Path(tempfile.mkdtemp()))

    workflows = ws.list()
    if not workflows:
        console.print("No saved workflows found.")
        return

    table = Table(title=f"Saved Workflows ({len(workflows)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Nodes")
    table.add_column("Connections")

    for wf in workflows:
        table.add_row(
            wf.id[:8] + "...",
            wf.name,
            str(len(wf.nodes)),
            str(len(wf.connections)),
        )
    console.print(table)


@app.command()
def run(
    workflow_path: Path = typer.Argument(
        ..., help="Path to workflow JSON file", exists=True,
    ),
    global_input: list[str] = typer.Option(
        [], "--input", "-i",
        help="Global inputs as key=value pairs (can repeat)",
    ),
) -> None:
    """Execute a workflow definition."""
    try:
        wf = _load_workflow(workflow_path)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    errors = DAGValidator.validate(wf)
    if errors:
        console.print(f"[red]Workflow has {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(1)

    # Parse global inputs
    global_inputs: dict[str, str] = {}
    for pair in global_input:
        if "=" in pair:
            key, value = pair.split("=", 1)
            global_inputs[key] = value

    # Build engine (temporary stores for CLI runs)
    from decision_system.workflow_engine.stores.json_store import (
        JSONWorkflowStore, JSONExecutionStore,
    )
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp())
    ws = JSONWorkflowStore(tmp_dir)
    es = JSONExecutionStore(tmp_dir)
    engine = DAGEngine(registry=_registry, workflow_store=ws, execution_store=es)

    # Print progress
    def on_event(event: ExecutionEvent) -> None:
        if event.event_type == "node_started":
            console.print(f"  [yellow]▶[/yellow] {event.node_id}...")
        elif event.event_type == "node_completed":
            console.print(f"  [green]✓[/green] {event.node_id}")
        elif event.event_type == "node_failed":
            console.print(f"  [red]✗[/red] {event.node_id}: {event.data.get('error', '')}")
        elif event.event_type == "workflow_completed":
            console.print(f"\n[green]Workflow completed: {event.data.get('status', '')}[/green]")
        elif event.event_type == "workflow_failed":
            console.print(f"\n[red]Workflow failed: {event.data.get('error', '')}[/red]")

    engine.on_event(on_event)

    import asyncio
    state = asyncio.run(engine.execute(wf, global_inputs=global_inputs))

    # Print summary
    if state.status == "completed":
        console.print(f"\n[bold green]✓ Execution {state.execution_id} completed[/bold green]")
    else:
        console.print(f"\n[bold red]✗ Execution {state.execution_id} failed: {state.error}[/bold red]")
        raise typer.Exit(1)


# --- Execution sub-app ---

exec_app = typer.Typer(help="Inspect workflow executions.")


@exec_app.command(name="list")
def list_executions(
    workflow_id: str | None = typer.Option(
        None, "--workflow-id", "-w", help="Filter by workflow ID",
    ),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """List workflow executions."""
    from decision_system.workflow_engine.stores.json_store import JSONExecutionStore
    import tempfile

    if store_dir:
        es = JSONExecutionStore(store_dir)
    else:
        es = JSONExecutionStore(Path(tempfile.mkdtemp()))

    states = es.list(workflow_id=workflow_id)
    if not states:
        console.print("No executions found.")
        return

    table = Table(title=f"Executions ({len(states)})")
    table.add_column("Execution ID", style="cyan")
    table.add_column("Workflow ID")
    table.add_column("Status", style="green")
    table.add_column("Error")

    for s in states:
        eid = s.execution_id[:8] + "..."
        wid = s.workflow_id[:8] + "..."
        table.add_row(eid, wid, s.status, s.error or "")
    console.print(table)


@exec_app.command(name="inspect")
def inspect_execution(
    execution_id: str = typer.Argument(..., help="Execution ID to inspect"),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """Show detailed execution information."""
    from decision_system.workflow_engine.stores.json_store import JSONExecutionStore
    import tempfile

    if store_dir:
        es = JSONExecutionStore(store_dir)
    else:
        es = JSONExecutionStore(Path(tempfile.mkdtemp()))

    state = es.load(execution_id)
    if state is None:
        console.print(f"[red]Execution '{execution_id}' not found[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Execution:[/bold] {state.execution_id}")
    console.print(f"[bold]Workflow:[/bold] {state.workflow_id}")
    console.print(f"[bold]Status:[/bold] {state.status}")
    console.print(f"[bold]Error:[/bold] {state.error or 'None'}")

    if state.node_states:
        table = Table(title="Node States")
        table.add_column("Node ID")
        table.add_column("Status")
        table.add_column("Error")
        for ns in state.node_states.values():
            table.add_row(ns.node_id, ns.status, ns.error or "")
        console.print(table)


# Register the execution sub-app
app.add_typer(exec_app, name="execution", help="Inspect workflow executions.")


# --- Schedules sub-app ---

schedule_app = typer.Typer(help="Manage workflow schedules and triggers.")


def _get_schedule_store(store_dir: Path | None) -> "ScheduleStore":
    """Get a ScheduleStore, defaulting to a temporary directory."""
    from decision_system.workflow_engine.scheduler.store import ScheduleStore
    import tempfile

    if store_dir:
        return ScheduleStore(store_dir)
    return ScheduleStore(Path(tempfile.mkdtemp()))


@schedule_app.command(name="list")
def list_schedules(
    workflow_id: str | None = typer.Option(
        None, "--workflow-id", "-w", help="Filter by workflow ID",
    ),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """List saved schedule definitions."""
    store = _get_schedule_store(store_dir)
    schedules = store.list(workflow_id=workflow_id)

    if not schedules:
        console.print("No schedules found.")
        return

    table = Table(title=f"Schedules ({len(schedules)})")
    table.add_column("ID", style="cyan")
    table.add_column("Workflow ID")
    table.add_column("Trigger", style="green")
    table.add_column("Enabled", style="yellow")
    table.add_column("Last Fired")

    for s in schedules:
        sid = s.id[:12] + "..." if len(s.id) > 12 else s.id
        wid = s.workflow_id[:12] + "..." if len(s.workflow_id) > 12 else s.workflow_id
        last_fired = s.last_fired.isoformat() if s.last_fired else "-"
        enabled_str = "[green]Yes[/green]" if s.enabled else "[red]No[/red]"
        table.add_row(sid, wid, s.trigger_type.value, enabled_str, last_fired)
    console.print(table)


@schedule_app.command(name="create")
def create_schedule(
    workflow_id: str = typer.Argument(..., help="Workflow ID to schedule"),
    trigger_type: str = typer.Option(
        "cron", "--trigger-type", "-t", help="Trigger type (cron, webhook, file_watch)",
    ),
    trigger_config: str = typer.Option(
        "{}", "--config", "-c", help="Trigger config as JSON string",
    ),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """Create a new schedule for a workflow."""
    from decision_system.workflow_engine.scheduler import ScheduleDefinition, TriggerType
    from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore
    from uuid import uuid4
    import tempfile

    store = _get_schedule_store(store_dir)
    effective_dir = store_dir or Path(tempfile.mkdtemp())
    ws = JSONWorkflowStore(effective_dir)

    try:
        trigger_type_enum = TriggerType(trigger_type)
    except ValueError:
        console.print(f"[red]Invalid trigger type '{trigger_type}'. Must be one of: {[t.value for t in TriggerType]}[/red]")
        raise typer.Exit(1)

    try:
        config = json.loads(trigger_config)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON config: {exc}[/red]")
        raise typer.Exit(1)

    # Verify the workflow exists
    wf = ws.load(workflow_id)
    if wf is None:
        console.print(f"[red]Workflow '{workflow_id}' not found[/red]")
        raise typer.Exit(1)

    schedule = ScheduleDefinition(
        id=f"sch-{uuid4().hex[:12]}",
        workflow_id=workflow_id,
        trigger_type=trigger_type_enum,
        trigger_config=config,
    )
    store.save(schedule)
    console.print(f"[green]✓[/green] Created schedule {schedule.id} ({trigger_type})")


@schedule_app.command(name="delete")
def delete_schedule(
    schedule_id: str = typer.Argument(..., help="Schedule ID to delete"),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """Delete a schedule definition."""
    store = _get_schedule_store(store_dir)

    if not store.delete(schedule_id):
        console.print(f"[red]Schedule '{schedule_id}' not found[/red]")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Deleted schedule {schedule_id}")


@schedule_app.command(name="toggle")
def toggle_schedule(
    schedule_id: str = typer.Argument(..., help="Schedule ID to toggle"),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """Enable or disable a schedule."""
    store = _get_schedule_store(store_dir)

    schedule = store.load(schedule_id)
    if schedule is None:
        console.print(f"[red]Schedule '{schedule_id}' not found[/red]")
        raise typer.Exit(1)

    schedule.enabled = not schedule.enabled
    store.save(schedule)
    state = "enabled" if schedule.enabled else "disabled"
    console.print(f"[green]✓[/green] Schedule {schedule.id} {state}")


# Register the schedule sub-app
app.add_typer(schedule_app, name="schedule", help="Manage workflow schedules and triggers.")
