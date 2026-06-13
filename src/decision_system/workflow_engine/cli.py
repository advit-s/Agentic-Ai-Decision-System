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
