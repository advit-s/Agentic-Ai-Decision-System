"""Tests for workspace CLI commands."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.cli_workspaces import (
    _connect,
    _get_db_path,
    _workspace_repo,
)
from decision_system.config import load_settings
from decision_system.storage.models import ArtifactType, StoredArtifact, Workspace
from decision_system.storage.repositories import (
    ArtifactRepository,
    WorkspaceRepository,
)
from decision_system.storage.migrations import run_migrations
from decision_system.storage.sqlite_store import DatabaseConnection


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def workspace_env(tmp_path, monkeypatch):
    """Set up an isolated workspace environment with a temp SQLite DB."""
    db_file = tmp_path / "workspaces.sqlite"
    monkeypatch.setenv("DECISION_WORKSPACE_DB", str(db_file))
    # Unset any leaked DECISION_SYSTEM_DATA_DIR so get_data_root() uses cwd
    monkeypatch.delenv("DECISION_SYSTEM_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path, db_file


def test_init_workspace_creates_db(workspace_env, runner, monkeypatch):
    _, db_file = workspace_env
    result = runner.invoke(app, ["workspace-commands", "init-workspace", "demo"])
    assert result.exit_code == 0
    assert db_file.exists()
    assert "demo" in result.output


def test_init_workspace_is_idempotent(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "idem"])
    result = runner.invoke(app, ["workspace-commands", "init-workspace", "idem"])
    assert result.exit_code == 0
    # Should not create duplicate workspaces
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        all_ws = repo.list_all()
    finally:
        db.close()
    names = [w.name for w in all_ws]
    assert names.count("idem") == 1


def test_init_workspace_sets_active_when_none_exist(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "first"])
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        ws = repo.get_active()
    finally:
        db.close()
    assert ws is not None and ws.name == "first"


def test_list_workspaces_shows_active(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "alpha"])
    runner.invoke(app, ["workspace-commands", "init-workspace", "beta"])
    result = runner.invoke(app, ["workspace-commands", "list-workspaces"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" in result.output


def test_use_workspace_switches_active(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "alpha"])
    runner.invoke(app, ["workspace-commands", "init-workspace", "beta"])
    result = runner.invoke(app, ["workspace-commands", "use-workspace", "alpha"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        active = repo.get_active()
    finally:
        db.close()
    assert active is not None and active.name == "alpha"


def test_use_workspace_missing_fails(workspace_env, runner):
    result = runner.invoke(
        app, ["workspace-commands", "use-workspace", "nonexistent"]
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_workspace_status_counts_artifacts(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "stats"])

    # Manually add artifacts
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    art_repo = None
    try:
        ws = repo.get_active()
        assert ws is not None
        art_repo = ArtifactRepository(db)
        art_repo.add(
            StoredArtifact(
                artifact_id="art-stats-1",
                workspace_id=ws.workspace_id,
                artifact_type=ArtifactType.DECISION_REPORT,
                title="Rep 1",
            )
        )
    finally:
        db.close()

    result = runner.invoke(app, ["workspace-commands", "workspace-status"])
    assert result.exit_code == 0
    assert "stats" in result.output or "decision_report" in result.output


def test_inspect_workspace(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "inspect-me"])
    result = runner.invoke(app, ["workspace-commands", "inspect-workspace"])
    assert result.exit_code == 0
    assert "inspect-me" in result.output
    assert "active workspace" in result.output.lower()


def test_inspect_workspace_json(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "json-inspect"])
    result = runner.invoke(app, ["workspace-commands", "inspect-workspace", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "active_workspace" in payload
    assert payload["active_workspace"]["name"] == "json-inspect"
    assert "artifact_counts" in payload
    assert "recent_artifacts" in payload
    assert "database_path" in payload


def test_export_workspace(workspace_env, runner):
    runner.invoke(app, ["workspace-commands", "init-workspace", "export-demo"])
    result = runner.invoke(app, ["workspace-commands", "export-workspace"])
    assert result.exit_code == 0
    assert "Exported" in result.output


def test_import_workspace(workspace_env, runner, tmp_path):
    runner.invoke(app, ["workspace-commands", "init-workspace", "export-demo"])
    runner.invoke(app, ["workspace-commands", "export-workspace"])
    export_path = (
        Path(".decision_system") / "workspaces" / "exports" / "export-demo.json"
    )
    assert export_path.exists()

    # Import under a different name by modifying the export
    import shutil
    import_path = tmp_path / "import-test.json"
    shutil.copy(export_path, import_path)
    data = json.loads(import_path.read_text(encoding="utf-8"))
    data["workspace"]["name"] = "imported-demo"
    data["workspace"]["workspace_id"] = "imported-demo"
    import_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "workspace-commands",
            "import-workspace",
            "--input",
            str(import_path),
        ],
    )
    assert result.exit_code == 0
    assert "imported" in result.output


def test_import_workspace_force_flag(workspace_env, runner, tmp_path):
    runner.invoke(app, ["workspace-commands", "init-workspace", "existing-ws"])
    # Export, then import with force
    runner.invoke(app, ["workspace-commands", "export-workspace"])
    export_path = (
        Path(".decision_system") / "workspaces" / "exports" / "existing-ws.json"
    )
    assert export_path.exists()

    result = runner.invoke(
        app,
        [
            "workspace-commands",
            "import-workspace",
            "--input",
            str(export_path),
            "--force",
        ],
    )
    assert result.exit_code == 0


def test_import_workspace_force_required_to_overwrite(workspace_env, runner, tmp_path):
    runner.invoke(app, ["workspace-commands", "init-workspace", "overwrite-me"])
    # Export but modified description
    runner.invoke(app, ["workspace-commands", "export-workspace"])
    export_path = (
        Path(".decision_system") / "workspaces" / "exports" / "overwrite-me.json"
    )
    assert export_path.exists()

    result = runner.invoke(
        app,
        [
            "workspace-commands",
            "import-workspace",
            "--input",
            str(export_path),
        ],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_missing_db_handled_gracefully_on_list(tmp_path, runner, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["workspace-commands", "list-workspaces"])
    assert result.exit_code == 0
    assert "No workspaces found" in result.output or "workspace" in result.output.lower()


def test_inspect_workspace_no_db(tmp_path, runner, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["workspace-commands", "inspect-workspace"])
    assert result.exit_code == 0
    assert "No workspace database found" in result.output or "No active workspace" in result.output


def test_export_no_active_workspace(tmp_path, runner, monkeypatch):
    db_file = tmp_path / "noactive.sqlite"
    monkeypatch.setenv("DECISION_WORKSPACE_DB", str(db_file))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["workspace-commands", "export-workspace"])
    assert result.exit_code != 0
    assert "No active workspace" in result.output


def test_no_raw_datasets_in_export(tmp_path, runner):
    db_file = tmp_path / "rawtest.sqlite"
    conn = DatabaseConnection(db_file)
    conn.connect()
    run_migrations(conn.connect())
    ws_repo = WorkspaceRepository(conn)
    ws_repo.ensure_exists(Workspace(workspace_id="raw1", name="RawTest"))

    art_repo = ArtifactRepository(conn)
    # Add a dataset artifact (should NOT be included in export)
    art_repo.add(
        StoredArtifact(
            artifact_id="dataset-1",
            workspace_id="raw1",
            artifact_type=ArtifactType.DATASET,
            title="Raw Customer Data",
            content={"rows": 50000, "path": "company_data/customers.csv"},
        )
    )
    # Add a decision report (should be included)
    art_repo.add(
        StoredArtifact(
            artifact_id="report-1",
            workspace_id="raw1",
            artifact_type=ArtifactType.DECISION_REPORT,
            title="Q1 Report",
            content={"markdown": "# Q1"},
        )
    )

    exporter_cls = __import__(
        "decision_system.storage.export_import", fromlist=["WorkspaceExporter"]
    ).WorkspaceExporter
    exporter = exporter_cls(conn)
    out = exporter.export_workspace("raw1")
    payload = json.loads(out.read_text(encoding="utf-8"))
    exported_types = {a["artifact_type"] for a in payload["artifacts"]}
    assert "dataset" not in exported_types
    assert "decision_report" in exported_types
    conn.close()


def test_import_artifacts_with_existing_files(tmp_path, runner, monkeypatch):
    # Create fake .decision_system artifacts
    ds = tmp_path / ".decision_system"
    (ds / "insights").mkdir(parents=True)
    (ds / "insights" / "insights.json").write_text(
        json.dumps({"insights": [{"category": "test", "severity": "low"}]}),
        encoding="utf-8",
    )
    (ds / "graph").mkdir(parents=True)
    (ds / "graph" / "knowledge_graph.json").write_text(
        json.dumps({"entities": [], "relationships": []}),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["workspace-commands", "init-workspace", "import-test"])
    assert result.exit_code == 0
    result = runner.invoke(
        app,
        ["workspace-commands", "import-artifacts"],
    )
    assert result.exit_code == 0
    assert "Imported" in result.output


def test_import_artifacts_dry_run(tmp_path, runner, monkeypatch):
    ds = tmp_path / ".decision_system"
    (ds / "insights").mkdir(parents=True)
    (ds / "insights" / "insights.json").write_text(
        json.dumps({"insights": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["workspace-commands", "init-workspace", "dry-run-test"])
    result = runner.invoke(
        app,
        ["workspace-commands", "import-artifacts", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "dry-run" in result.output


def test_import_artifacts_no_existing_artifacts(tmp_path, runner, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["workspace-commands", "init-workspace", "empty-test"])
    result = runner.invoke(
        app, ["workspace-commands", "import-artifacts"]
    )
    assert result.exit_code == 0
    assert "No existing artifacts" in result.output


def test_import_artifacts_no_active_workspace(tmp_path, runner, monkeypatch):
    ds = tmp_path / ".decision_system"
    (ds / "insights").mkdir(parents=True)
    (ds / "insights" / "insights.json").write_text(
        json.dumps({"insights": []}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["workspace-commands", "import-artifacts"]
    )
    assert result.exit_code != 0


def test_import_artifacts_idempotent(tmp_path, runner, monkeypatch):
    ds = tmp_path / ".decision_system"
    (ds / "insights").mkdir(parents=True)
    (ds / "insights" / "insights.json").write_text(
        json.dumps({"insights": [{"id": "i1"}]}), encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["workspace-commands", "init-workspace", "idem-import"])
    # First import
    r1 = runner.invoke(app, ["workspace-commands", "import-artifacts"])
    assert r1.exit_code == 0
    assert "Imported" in r1.output
    # Second import -- should skip
    r2 = runner.invoke(app, ["workspace-commands", "import-artifacts"])
    assert r2.exit_code == 0
    assert "skipped" in r2.output


# ---------------------------------------------------------------------------
# Top-level alias tests (v1.0.1: commands available without workspace-commands)
# ---------------------------------------------------------------------------


def test_top_level_init_workspace(workspace_env, runner):
    result = runner.invoke(app, ["init-workspace", "top-demo"])
    assert result.exit_code == 0
    assert "top-demo" in result.output


def test_top_level_list_workspaces(workspace_env, runner):
    runner.invoke(app, ["init-workspace", "list-alias-a"])
    runner.invoke(app, ["init-workspace", "list-alias-b"])
    result = runner.invoke(app, ["list-workspaces"])
    assert result.exit_code == 0
    assert "list-alias-a" in result.output
    assert "list-alias-b" in result.output


def test_top_level_use_workspace(workspace_env, runner):
    runner.invoke(app, ["init-workspace", "use-a"])
    runner.invoke(app, ["init-workspace", "use-b"])
    result = runner.invoke(app, ["use-workspace", "use-a"])
    assert result.exit_code == 0
    assert "use-a" in result.output
    settings = load_settings()
    repo, db = _workspace_repo(settings)
    try:
        active = repo.get_active()
    finally:
        db.close()
    assert active is not None and active.name == "use-a"


def test_top_level_workspace_status(workspace_env, runner):
    runner.invoke(app, ["init-workspace", "status-alias"])
    result = runner.invoke(app, ["workspace-status"])
    assert result.exit_code == 0
    assert "status-alias" in result.output


def test_top_level_inspect_workspace(workspace_env, runner):
    runner.invoke(app, ["init-workspace", "inspect-alias"])
    result = runner.invoke(app, ["inspect-workspace"])
    assert result.exit_code == 0
    assert "inspect-alias" in result.output


def test_top_level_import_workspace_positional(workspace_env, runner, tmp_path):
    runner.invoke(app, ["init-workspace", "export-alias"])
    runner.invoke(app, ["export-workspace"])
    export_path = (
        Path(".decision_system") / "workspaces" / "exports" / "export-alias.json"
    )
    assert export_path.exists()

    # Copy with a different workspace name to avoid conflict
    import shutil

    import_path = tmp_path / "imported-alias.json"
    shutil.copy(export_path, import_path)
    data = json.loads(import_path.read_text(encoding="utf-8"))
    data["workspace"]["name"] = "imported-pos"
    data["workspace"]["workspace_id"] = "imported-pos"
    import_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    result = runner.invoke(app, ["import-workspace", str(import_path)])
    assert result.exit_code == 0
    assert "imported" in result.output


def test_top_level_import_workspace_no_path_fails(workspace_env, runner):
    result = runner.invoke(app, ["import-workspace"])
    assert result.exit_code != 0


def test_top_level_import_artifacts(workspace_env, runner, monkeypatch):
    ds = Path(".decision_system") / "insights"
    ds.mkdir(parents=True, exist_ok=True)
    (ds / "insights.json").write_text(
        json.dumps({"insights": [{"category": "t", "severity": "low"}]}),
        encoding="utf-8",
    )
    monkeypatch.chdir(workspace_env[0])
    runner.invoke(app, ["init-workspace", "import-alias"])
    result = runner.invoke(app, ["import-artifacts"])
    assert result.exit_code == 0
    assert "Imported" in result.output


def test_workspace_commands_sub_app_still_works(workspace_env, runner):
    """Backward-compat: workspace-commands prefix still functions."""
    result = runner.invoke(app, ["workspace-commands", "list-workspaces"])
    assert result.exit_code == 0
    assert "workspace" in result.output.lower()


def test_version_consistency(tmp_path):
    import tomllib
    from decision_system import __version__

    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        pyproject_version = data["project"]["version"]
        assert __version__ == pyproject_version, (
            f"Version mismatch: __init__.py={__version__}, pyproject.toml={pyproject_version}"
        )
