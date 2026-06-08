"""Workspace management commands for the decision-system.

These commands operate on the local SQLite-backed workspace store under
``.decision_system/workspaces/``. They are provided as a Typer sub-app
wired into the main CLI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from decision_system.config import load_settings
from decision_system.storage.export_import import (
    WorkspaceImporter,
    WorkspaceExporter,
    get_default_db_path,
    init_workspace_dir,
)
from decision_system.storage.inspector import WorkspaceInspector
from decision_system.storage.migrations import run_migrations
from decision_system.storage.models import ArtifactType, StoredArtifact, Workspace
from decision_system.storage.repositories import (
    ArtifactRepository,
    SettingsRepository,
    WorkspaceRepository,
)
from decision_system.storage.sqlite_store import DatabaseConnection

workspace_app = typer.Typer(
    name="workspace",
    help="Local workspace management (init, list, use, status, inspect, export, import).",
)

console = Console()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_db_path(settings) -> Path:
    return Path(settings.workspace_db_path)


def _connect(settings) -> DatabaseConnection:
    db_path = _get_db_path(settings)
    init_workspace_dir()
    db = DatabaseConnection(db_path)
    db.connect()
    run_migrations(db.connect())
    return db


def _workspace_repo(settings):
    db = _connect(settings)
    return WorkspaceRepository(db), db


def _active_workspace(settings) -> Workspace | None:
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
        return ws
    finally:
        db.close()


def _fail(msg: str) -> None:
    console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@workspace_app.command("init-workspace")
def init_workspace(
    name: str = typer.Argument(
        ..., help="Name for the new workspace (alphanumeric + hyphens/underscores)."
    ),
    description: str = typer.Option(
        "", "--description", "-d", help="Description for the workspace."
    ),
) -> None:
    """Create (or accept existing) local workspace, activating if needed."""
    settings = load_settings()
    workspace_name = name.strip()
    workspace_id = (
        workspace_name.lower()
        .replace(" ", "-")
        .replace("_", "-")
    )

    repo, db = _workspace_repo(settings)
    try:
        existing = repo.get_by_name(workspace_name)
        if existing is not None:
            repo.ensure_active(existing.workspace_id)
            _report_active_workspace(existing, settings)
            return

        ws = Workspace(
            workspace_id=workspace_id,
            name=workspace_name,
            description=description,
            active=True,
        )
        # Ensure no other workspace is active
        repo.ensure_exists(ws)
        repo.set_active(ws.workspace_id)
        created = repo.get_by_id(ws.workspace_id)
        _report_active_workspace(created, settings)
    finally:
        db.close()


def _report_active_workspace(ws: Workspace | None, settings) -> None:
    if ws is None:
        _fail("No active workspace.")
    db_path = _get_db_path(settings)
    console.print(f"Workspace: {ws.name}")
    console.print(f"Database: {db_path}")


@workspace_app.command("list-workspaces")
def list_workspaces() -> None:
    """List all known workspaces and indicate which is active."""
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        workspaces = repo.list_all()
    finally:
        db.close()

    if not workspaces:
        console.print("No workspaces found. Run `decision-system init-workspace <name>` first.")
        return

    table = Table(title="Workspaces")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Active", justify="center")
    table.add_column("Created")

    for ws in workspaces:
        active_mark = "[green]yes[/green]" if ws.active else "[dim]no[/dim]"
        table.add_row(
            ws.name,
            ws.description or "(no description)",
            active_mark,
            ws.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        )
    console.print(table)


@workspace_app.command("use-workspace")
def use_workspace(
    name: str = typer.Argument(..., help="Name of the workspace to activate."),
) -> None:
    """Set a named workspace as the active workspace for subsequent commands."""
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_by_name(name)
        if ws is None:
            _fail(f"Workspace '{name}' not found. Run `decision-system init-workspace {name}` first.")
        repo.set_active(ws.workspace_id)
        console.print(f"Active workspace set to: {ws.name}")
        console.print(f"Database: {_get_db_path(settings)}")
    finally:
        db.close()


@workspace_app.command("workspace-status")
def workspace_status(
    include_generated: bool = typer.Option(
        False,
        "--include-generated-summary",
        help="Also include a lightweight summary of generated local JSON files.",
    ),
) -> None:
    """Show the active workspace and its artifact counts."""
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
    finally:
        db.close()

    if ws is None:
        console.print(
            "No active workspace. Run `decision-system init-workspace <name>` first."
        )
        return

    db_path = _get_db_path(settings)
    art_repo = ArtifactRepository(db)
    counts = art_repo.count_by_type(ws.workspace_id)
    db.close()

    console.print(f"Active workspace: {ws.name}")
    console.print(f"ID: {ws.workspace_id}")
    console.print(f"Description: {ws.description or '(none)'}")
    console.print(f"Database: {db_path}")
    console.print(f"Created: {ws.created_at.strftime('%Y-%m-%d %H:%M UTC')}")

    if counts:
        table = Table(title="Artifacts by Type")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        for atype, cnt in sorted(counts.items()):
            table.add_row(atype, str(cnt))
        console.print(table)
    else:
        console.print("Artifacts: none")

    if include_generated:
        _print_generated_summary()


def _print_generated_summary() -> None:
    """Lightweight summary of generated local JSON files (not stored in the DB)."""
    base = Path(".decision_system")
    entries: list[str] = []
    potential = [
        base / "graph" / "knowledge_graph.json",
        base / "data_profiles" / "profiles.json",
        base / "ontology" / "ontology_map.json",
        base / "insights" / "insights.json",
        base / "contexts",
        base / "orchestration" / "runs",
        base / "war_room" / "runs",
        base / "provider_evals" / "provider_eval_results.json",
    ]
    for p in potential:
        if p.exists():
            if p.is_file():
                entries.append(f"- {p} ({_human_bytes(p.stat().st_size)})")
            elif p.is_dir():
                entries.append(f"- {p}/ ({len(list(p.glob('*.json')))} JSON files)")
    if entries:
        console.print("\nGenerated JSON files (not in workspace DB):")
        console.print("\n".join(entries))


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} TB"


@workspace_app.command("inspect-workspace")
def inspect_workspace(
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Inspect the active workspace: metadata, artifact counts, recent artifacts."""
    settings = load_settings()
    db_path = _get_db_path(settings)

    if not db_path.exists():
        console.print(f"No workspace database found at {db_path}.")
        console.print("Run `decision-system init-workspace <name>` first.")
        return

    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
    finally:
        db.close()

    if ws is None:
        console.print(
            "No active workspace. Run `decision-system init-workspace <name>` first."
        )
        return

    inspector = WorkspaceInspector(
        workspaces=repo,
        artifacts=ArtifactRepository(db),
        database_path=str(db_path),
    )
    status = inspector.status()
    if status is None:
        _fail("Could not load workspace status.")

    recent = inspector.recent_artifacts(ws.workspace_id)

    if json_output:
        payload = _inspect_json(status, recent)
        typer.echo(json.dumps(payload, indent=2))
        return

    console.print(f"Active workspace: {ws.name} ({ws.workspace_id})")
    console.print(f"Database: {db_path}")
    console.print(f"Description: {ws.description or '(none)'}")
    console.print(f"Created at: {ws.created_at.strftime('%Y-%m-%d %H:%M UTC')}")

    if status.artifact_counts:
        table = Table(title="Artifact Counts")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        for atype, cnt in sorted(status.artifact_counts.items()):
            table.add_row(atype, str(cnt))
        console.print(table)
    else:
        console.print("No artifacts yet.")

    if recent:
        console.print("\nRecent artifacts:")
        for art in recent:
            console.print(
                f" - {art['title'] or art['artifact_id']} "
                f"({art['artifact_type']}) {art['source_path']}"
            )
    else:
        console.print("No recent artifacts.")


def _inspect_json(status, recent) -> dict[str, Any]:
    ws = status.workspace
    return {
        "active_workspace": {
            "workspace_id": ws.workspace_id,
            "name": ws.name,
            "description": ws.description,
            "created_at": ws.created_at.isoformat(),
        },
        "artifact_counts": status.artifact_counts,
        "database_path": status.database_path,
        "recent_artifacts": recent,
    }


@workspace_app.command("export-workspace")
def export_workspace(
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output JSON file path (defaults to .decision_system/workspaces/exports/<name>.json).",
    ),
) -> None:
    """Export the active workspace to a JSON bundle."""
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
    finally:
        db.close()

    if ws is None:
        _fail(
            "No active workspace. Run `decision-system init-workspace <name>` first."
        )

    exporter = WorkspaceExporter(db)
    try:
        out_path = exporter.export_workspace(ws.workspace_id, output_path=output)
        console.print(f"Exported workspace '{ws.name}' to: {out_path}")
    except ValueError as exc:
        _fail(str(exc))


@workspace_app.command("import-workspace")
def import_workspace(
    input_path: str = typer.Option(
        ...,
        "--input",
        "-i",
        help="Path to a workspace JSON export file.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite workspace if it already exists by name.",
    ),
) -> None:
    """Import a workspace from a JSON export file."""
    settings = load_settings()
    db = _connect(settings)
    try:
        importer = WorkspaceImporter(db)
        try:
            bundle = importer.import_workspace(input_path, force=force)
        except (ValueError, FileNotFoundError) as exc:
            _fail(str(exc))
        else:
            console.print(
                f"Imported workspace '{bundle.workspace.name}' "
                f"with {len(bundle.artifacts)} artifacts."
            )
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Wire into main CLI
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Artifact import from existing JSON outputs (v1.0)
# ---------------------------------------------------------------------------

# Mapping of source file paths to ArtifactType and title
_IMPORT_RULES: list[tuple[Path, ArtifactType, str]] = [
    (Path(".decision_system") / "data_profiles" / "profiles.json", ArtifactType.DATA_PROFILE, "Data Profiles"),
    (Path(".decision_system") / "ontology" / "ontology_map.json", ArtifactType.ONTOLOGY_MAP, "Ontology Map"),
    (Path(".decision_system") / "insights" / "insights.json", ArtifactType.INSIGHT_STORE, "Insights"),
    (Path(".decision_system") / "graph" / "knowledge_graph.json", ArtifactType.GRAPH, "Knowledge Graph"),
    (Path(".decision_system") / "imports" / "import_manifest.json", ArtifactType.IMPORT_MANIFEST, "Import Manifest"),
    (Path(".decision_system") / "provider_evals" / "provider_eval_results.json", ArtifactType.PROVIDER_EVAL_RUN, "Provider Eval Results"),
]


def _collect_importable_artifacts(
    base: Path,
) -> list[tuple[Path, ArtifactType, str]]:
    """Return ``(filepath, artifact_type, title)`` for discoverable JSON artifacts."""
    results: list[tuple[Path, ArtifactType, str]] = []
    for filepath, atype, title in _IMPORT_RULES:
        if filepath.exists() and filepath.is_file():
            results.append((filepath, atype, title))
    # Glob for orchestration runs
    orch_dir = base / "orchestration" / "runs"
    if orch_dir.is_dir():
        for fp in sorted(orch_dir.glob("*.json")):
            results.append((fp, ArtifactType.ORCHESTRATION_RUN, fp.name))
    # Glob for contexts
    ctx_dir = base / "contexts"
    if ctx_dir.is_dir():
        for fp in sorted(ctx_dir.glob("*.json")):
            results.append((fp, ArtifactType.DECISION_CONTEXT, fp.name))
    # Glob for war-room runs
    wr_dir = base / "war_room" / "runs"
    if wr_dir.is_dir():
        for fp in sorted(wr_dir.glob("*.json")):
            results.append((fp, ArtifactType.WAR_ROOM_RUN, fp.name))
    # War-room eval results
    wr_eval = base / "evals" / "war_room_results.json"
    if wr_eval.is_file():
        results.append((wr_eval, ArtifactType.WAR_ROOM_EVAL_RESULT, "War Room Eval Results"))
    return results


@workspace_app.command("import-artifacts")
def import_artifacts(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be imported without writing to the database.",
    ),
) -> None:
    """Import existing generated JSON outputs into the active workspace.

    Scans known ``.decision_system/`` paths for artifact files and stores
    them as typed workspace artifacts. Existing artifacts are skipped when
    the source path already exists (idempotent).
    """
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
        if ws is None:
            _fail(
                "No active workspace. Run "
                "'decision-system init-workspace <name>' first."
            )
            return
        base = Path(".decision_system")
        discoverable = _collect_importable_artifacts(base)
        if not discoverable:
            console.print("No existing artifacts found under .decision_system/.")
            return
        art_repo = ArtifactRepository(db)
        imported: list[tuple[str, str]] = []
        skipped: list[str] = []
        for filepath, atype, title in discoverable:
            rel = str(filepath)
            existing = art_repo.get_by_workspace(ws.workspace_id)
            already = any(a.source_path == rel for a in existing)
            if already:
                skipped.append(rel)
                continue
            if dry_run:
                imported.append((rel, atype.value))
                continue
            try:
                content = json.loads(filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                content = {}
            artifact = StoredArtifact(
                artifact_id=f"imported-{atype.value}-{filepath.name}",
                workspace_id=ws.workspace_id,
                artifact_type=atype,
                source_path=rel,
                title=title,
                content=content if isinstance(content, dict) else {"raw": content},
            )
            art_repo.add(artifact)
            imported.append((rel, atype.value))
        db.connect().commit()
    finally:
        db.close()
    if dry_run:
        lines = ["dry-run: would import %d artifacts" % len(imported)]
        for rel, atype_val in imported:
            lines.append("  %s: %s" % (atype_val, rel))
        if skipped:
            lines.append("Already present (skipped): %d" % len(skipped))
        console.print("\n".join(lines))
        return
        for rel, atype in imported:
            console.print(f"  [{atype}] {rel}")
        if skipped:
            console.print(f"\nAlready present (skipped): {len(skipped)}")
        return
    console.print(f"Imported {len(imported)} artifacts into workspace '{ws.name}'.")
    for rel, atype in imported:
        console.print(f"  [{atype}] {rel}")
    if skipped:
        console.print(f"Already present (skipped): {len(skipped)}")


def register_workspace_commands(main_app: Any) -> None:
    """Attach workspace commands to the main Typer app."""
    main_app.add_typer(workspace_app, name="workspace-commands")
