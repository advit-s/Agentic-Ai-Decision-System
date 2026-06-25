"""Tests for the v1.0 storage (SQLite workspace) layer."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from decision_system.storage.migrations import run_migrations
from decision_system.storage.models import ArtifactType, StoredArtifact, Workspace
from decision_system.storage.repositories import (
    ArtifactRepository,
    SettingsRepository,
    WorkspaceRepository,
)
from decision_system.storage.inspector import WorkspaceInspector
from decision_system.storage.sqlite_store import DatabaseConnection, create_tables
from decision_system.storage.export_import import (
    WorkspaceExporter,
    WorkspaceImporter,
    get_default_db_path,
    init_workspace_dir,
)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Return an in-memory (or temp-file) DatabaseConnection with tables ready."""
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DECISION_WORKSPACE_DB", str(db_file))
    conn = DatabaseConnection(db_file)
    conn.connect()
    run_migrations(conn.connect())
    yield conn, db_file
    conn.close()


@pytest.fixture()
def repos(db):
    conn, _ = db
    ws = WorkspaceRepository(conn)
    art = ArtifactRepository(conn)
    settings = SettingsRepository(conn)
    return ws, art, settings, conn


# ------------------------------------------------------------------
# Migration tests
# ------------------------------------------------------------------


class TestMigrations:
    def test_run_migrations_creates_tables(self, tmp_path):
        db_file = tmp_path / "mig.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        # SQLite creates the file on connect; size > 0 is expected.
        assert db_file.exists()
        run_migrations(conn.connect())
        # Verify all three tables exist
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {r["name"] for r in cur.fetchall()}
        assert "artifacts" in tables
        assert "settings" in tables
        assert "workspaces" in tables

    def test_repeated_migrations_are_idempotent(self, tmp_path):
        db_file = tmp_path / "idempotent.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        # Second call must not fail
        run_migrations(conn.connect())
        run_migrations(conn.connect())
        conn.close()

    def test_tables_not_dropped_automatically(self, tmp_path):
        db_file = tmp_path / "persist.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        # Insert a workspace
        ws = Workspace(
            workspace_id="test-ws",
            name="Test Workspace",
            description="Test",
            active=True,
        )
        WorkspaceRepository(conn).create(ws)
        # Run migrations again - data must survive
        run_migrations(conn.connect())
        found = WorkspaceRepository(conn).get_by_id("test-ws")
        assert found is not None
        assert found.name == "Test Workspace"
        conn.close()

    def test_create_tables_backward_compat(self, tmp_path):
        db_file = tmp_path / "compat.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        # create_tables delegates to run_migrations
        create_tables(conn.connect())
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {r["name"] for r in cur.fetchall()}
        assert "artifacts" in tables
        conn.close()


# ------------------------------------------------------------------
# WorkspaceRepository tests
# ------------------------------------------------------------------


class TestWorkspaceRepository:
    def test_create_and_retrieve(self, repos):
        ws_repo, _, _, conn = repos
        ws = Workspace(
            workspace_id="ws-1", name="demo", description="Demo workspace"
        )
        ws_repo.create(ws)
        fetched = ws_repo.get_by_id("ws-1")
        assert fetched is not None
        assert fetched.name == "demo"
        assert fetched.description == "Demo workspace"
        assert fetched.active is False

    def test_create_duplicate_name_fails(self, repos):
        ws_repo, _, _, conn = repos
        ws = Workspace(workspace_id="ws-a", name="UniqueName")
        ws_repo.create(ws)
        with pytest.raises(sqlite3.IntegrityError):
            ws_repo.create(Workspace(workspace_id="ws-b", name="UniqueName"))

    def test_list_all(self, repos):
        ws_repo, _, _, conn = repos
        ws_repo.create(Workspace(workspace_id="w1", name="Alpha"))
        ws_repo.create(Workspace(workspace_id="w2", name="Beta", active=True))
        all_ws = ws_repo.list_all()
        assert len(all_ws) == 2

    def test_get_active_single_active(self, repos):
        ws_repo, _, _, conn = repos
        ws_repo.create(Workspace(workspace_id="w1", name="Active1", active=True))
        ws_repo.create(Workspace(workspace_id="w2", name="Active2", active=False))
        active = ws_repo.get_active()
        assert active is not None
        assert active.name == "Active1"

    def test_set_active_only_one_active(self, repos):
        ws_repo, _, _, conn = repos
        ws_repo.create(Workspace(workspace_id="w1", name="First", active=True))
        ws_repo.create(Workspace(workspace_id="w2", name="Second", active=False))
        ws_repo.set_active("w2")
        # First should no longer be active
        first = ws_repo.get_by_id("w1")
        assert first is not None and first.active is False
        second = ws_repo.get_by_id("w2")
        assert second is not None and second.active is True

    def test_delete(self, repos):
        ws_repo, _, _, conn = repos
        ws_repo.create(Workspace(workspace_id="del-me", name="DeleteMe"))
        assert ws_repo.get_by_id("del-me") is not None
        result = ws_repo.delete("del-me")
        assert result is True
        assert ws_repo.get_by_id("del-me") is None

    def test_ensure_exists_idempotent(self, repos):
        ws_repo, _, _, conn = repos
        ws = Workspace(workspace_id="e1", name="Existing")
        first = ws_repo.ensure_exists(ws)
        second = ws_repo.ensure_exists(ws)
        assert first.workspace_id == second.workspace_id
        all_ws = ws_repo.list_all()
        assert len(all_ws) == 1


# ------------------------------------------------------------------
# ArtifactRepository tests
# ------------------------------------------------------------------


class TestArtifactRepository:
    def test_add_and_get(self, repos):
        ws_repo, art_repo, _, conn = repos
        ws_repo.ensure_exists(Workspace(workspace_id="a1", name="Arty"))
        art = StoredArtifact(
            artifact_id="art-1",
            workspace_id="a1",
            artifact_type=ArtifactType.DECISION_REPORT,
            title="Q2 Report",
            source_path=".decision_system/runs/run-1.json",
            content={"markdown": "# Q2 Report"},
        )
        stored = art_repo.add(art)
        fetched = art_repo.get_by_id("art-1")
        assert fetched is not None
        assert fetched.title == "Q2 Report"
        assert fetched.artifact_type == ArtifactType.DECISION_REPORT
        assert fetched.content == {"markdown": "# Q2 Report"}

    def test_add_many(self, repos):
        ws_repo, art_repo, _, conn = repos
        ws_repo.ensure_exists(Workspace(workspace_id="a2", name="Multi"))
        arts = [
            StoredArtifact(
                artifact_id=f"m{i}",
                workspace_id="a2",
                artifact_type=ArtifactType.ONTOLOGY_MAP,
                title=f"Map {i}",
            )
            for i in range(5)
        ]
        art_repo.add_many(arts)
        all_arts = art_repo.get_by_workspace("a2")
        assert len(all_arts) == 5

    def test_count_by_type(self, repos):
        ws_repo, art_repo, _, conn = repos
        ws_repo.ensure_exists(Workspace(workspace_id="t1", name="Counts"))
        art_repo.add(
            StoredArtifact(
                artifact_id="t1-a",
                workspace_id="t1",
                artifact_type=ArtifactType.DECISION_REPORT,
            )
        )
        art_repo.add(
            StoredArtifact(
                artifact_id="t1-b",
                workspace_id="t1",
                artifact_type=ArtifactType.DECISION_REPORT,
            )
        )
        art_repo.add(
            StoredArtifact(
                artifact_id="t1-c",
                workspace_id="t1",
                artifact_type=ArtifactType.ONTOLOGY_MAP,
            )
        )
        counts = art_repo.count_by_type("t1")
        assert counts.get("decision_report") == 2
        assert counts.get("ontology_map") == 1

    def test_delete_artifact(self, repos):
        ws_repo, art_repo, _, conn = repos
        ws_repo.ensure_exists(Workspace(workspace_id="del", name="Del"))
        art_repo.add(
            StoredArtifact(
                artifact_id="del-art",
                workspace_id="del",
                artifact_type=ArtifactType.UNKNOWN,
            )
        )
        assert art_repo.get_by_id("del-art") is not None
        result = art_repo.delete("del-art")
        assert result is True
        assert art_repo.get_by_id("del-art") is None

    def test_get_by_type_filter(self, repos):
        ws_repo, art_repo, _, conn = repos
        ws_repo.ensure_exists(Workspace(workspace_id="ft", name="FilterType"))
        art_repo.add(
            StoredArtifact(
                artifact_id="ft-1",
                workspace_id="ft",
                artifact_type=ArtifactType.WAR_ROOM_RUN,
            )
        )
        art_repo.add(
            StoredArtifact(
                artifact_id="ft-2",
                workspace_id="ft",
                artifact_type=ArtifactType.ONTOLOGY_MAP,
            )
        )
        war_arts = art_repo.get_by_type("ft", ArtifactType.WAR_ROOM_RUN)
        assert len(war_arts) == 1
        assert war_arts[0].artifact_type == ArtifactType.WAR_ROOM_RUN


# ------------------------------------------------------------------
# SettingsRepository tests
# ------------------------------------------------------------------


class TestSettingsRepository:
    def test_set_and_get(self, repos):
        _, _, settings_repo, conn = repos
        settings_repo.set("key1", "value1")
        assert settings_repo.get("key1") == "value1"

    def test_default_for_missing_key(self, repos):
        _, _, settings_repo, conn = repos
        assert settings_repo.get("nonexistent") == ""
        assert settings_repo.get("nonexistent", "fallback") == "fallback"

    def test_update_overwrites(self, repos):
        _, _, settings_repo, conn = repos
        settings_repo.set("k", "v1")
        settings_repo.set("k", "v2")
        assert settings_repo.get("k") == "v2"

    def test_delete(self, repos):
        _, _, settings_repo, conn = repos
        settings_repo.set("del-me", "val")
        assert settings_repo.get("del-me") == "val"
        result = settings_repo.delete("del-me")
        assert result is True
        assert settings_repo.get("del-me") == ""


# ------------------------------------------------------------------
# WorkspaceInspector tests
# ------------------------------------------------------------------


class TestWorkspaceInspector:
    def test_status_with_active_workspace(self, tmp_path):
        db_file = tmp_path / "inspector.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        art_repo = ArtifactRepository(conn)

        ws = Workspace(workspace_id="insp-1", name="InspWorkspace", active=True)
        ws_repo.create(ws)

        inspector = WorkspaceInspector(
            workspaces=ws_repo,
            artifacts=art_repo,
            database_path=str(db_file),
        )
        status = inspector.status()
        assert status is not None
        assert status.workspace.name == "InspWorkspace"
        assert status.database_path == str(db_file)
        conn.close()

    def test_status_no_active_workspace(self, tmp_path):
        db_file = tmp_path / "noactive.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        art_repo = ArtifactRepository(conn)
        inspector = WorkspaceInspector(ws_repo, art_repo, str(db_file))
        assert inspector.status() is None
        conn.close()

    def test_recent_artifacts(self, tmp_path):
        db_file = tmp_path / "recent.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        art_repo = ArtifactRepository(conn)
        ws_repo.ensure_exists(Workspace(workspace_id="r1", name="Recent"))
        title2 = StoredArtifact(
            artifact_id="ra-2",
            workspace_id="r1",
            artifact_type=ArtifactType.DECISION_REPORT,
            title="Report 2",
        )
        art_repo.add(title2)
        title1 = StoredArtifact(
            artifact_id="ra-1",
            workspace_id="r1",
            artifact_type=ArtifactType.DECISION_REPORT,
            title="Report 1",
        )
        art_repo.add(title1)
        inspector = WorkspaceInspector(ws_repo, art_repo, str(db_file))
        recent = inspector.recent_artifacts("r1", limit=1)
        assert len(recent) == 1
        assert recent[0]["title"] == "Report 1"
        conn.close()


# ------------------------------------------------------------------
# Export / Import tests (requires JSON round-trip)
# ------------------------------------------------------------------


class TestExportImport:
    def test_export_creates_json_file(self, tmp_path):
        db_file = tmp_path / "export.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        art_repo = ArtifactRepository(conn)
        ws = Workspace(workspace_id="ex-1", name="ExportMe")
        ws_repo.create(ws)
        art_repo.add(
            StoredArtifact(
                artifact_id="ex-a1",
                workspace_id="ex-1",
                artifact_type=ArtifactType.DECISION_REPORT,
                title="Exported Report",
                source_path="runs/run.json",
                metadata={"run_id": "run-1"},
                content={"markdown": "# DB"},
            )
        )
        exporter = WorkspaceExporter(conn)
        out = exporter.export_workspace("ex-1")
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["version"] == "1.0"
        assert payload["workspace"]["name"] == "ExportMe"
        assert len(payload["artifacts"]) == 1
        conn.close()

    def test_export_fails_missing_workspace(self, tmp_path):
        db_file = tmp_path / "badexp.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        exporter = WorkspaceExporter(conn)
        with pytest.raises(ValueError, match="not found"):
            exporter.export_workspace("nonexistent")
        conn.close()

    def test_import_creates_workspace_and_artifacts(self, tmp_path):
        db_file = tmp_path / "import.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())

        # Build a minimal export file
        export_data = {
            "version": "1.0",
            "workspace": {
                "workspace_id": "imp-1",
                "name": "ImportTest",
                "description": "Imported from test",
                "active": False,
                "created_at": "2026-06-07T00:00:00+00:00",
                "updated_at": "2026-06-07T00:00:00+00:00",
            },
            "artifacts": [
                {
                    "artifact_id": "imp-a1",
                    "workspace_id": "imp-1",
                    "artifact_type": "decision_report",
                    "title": "Imported Report",
                    "source_path": ".decision_system/runs/run.json",
                }
            ],
        }
        export_file = tmp_path / "import.json"
        export_file.write_text(
            json.dumps(export_data, indent=2) + "\n", encoding="utf-8"
        )
        importer = WorkspaceImporter(conn)
        bundle = importer.import_workspace(str(export_file))
        assert bundle.workspace.name == "ImportTest"

        ws_repo = WorkspaceRepository(conn)
        art_repo = ArtifactRepository(conn)
        ws = ws_repo.get_by_name("ImportTest")
        assert ws is not None
        arts = art_repo.get_by_workspace(ws.workspace_id)
        assert len(arts) == 1
        assert arts[0].title == "Imported Report"
        conn.close()

    def test_import_refuses_overwrite_without_force(self, tmp_path):
        db_file = tmp_path / "noforce.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        ws_repo.create(Workspace(workspace_id="existing", name="ExistingWS"))
        export_data = {"version": "1.0", "workspace": {"workspace_id": "whatever", "name": "ExistingWS"}, "artifacts": []}
        export_file = tmp_path / "dup.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")
        importer = WorkspaceImporter(conn)
        with pytest.raises(ValueError, match="already exists"):
            importer.import_workspace(str(export_file), force=False)
        conn.close()

    def test_import_with_force_overwrites(self, tmp_path):
        db_file = tmp_path / "force.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        ws_repo = WorkspaceRepository(conn)
        ws_repo.create(Workspace(workspace_id="old", name="OverwriteMe"))
        export_data = {"version": "1.0", "workspace": {"workspace_id": "new", "name": "OverwriteMe"}, "artifacts": []}
        export_file = tmp_path / "force.json"
        export_file.write_text(json.dumps(export_data), encoding="utf-8")
        importer = WorkspaceImporter(conn)
        bundle = importer.import_workspace(str(export_file), force=True)
        assert bundle.workspace.name == "OverwriteMe"
        conn.close()

    def test_import_invalid_json_raises(self, tmp_path):
        db_file = tmp_path / "badjson.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        bad = tmp_path / "bad.json"
        bad.write_text("not json{{{", encoding="utf-8")
        importer = WorkspaceImporter(conn)
        with pytest.raises(ValueError, match="Invalid JSON"):
            importer.import_workspace(str(bad))
        conn.close()

    def test_import_missing_keys_raises(self, tmp_path):
        db_file = tmp_path / "missing.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        bad = tmp_path / "missing.json"
        bad.write_text(json.dumps({"unexpected": 1}), encoding="utf-8")
        importer = WorkspaceImporter(conn)
        with pytest.raises(ValueError, match="missing"):
            importer.import_workspace(str(bad))
        conn.close()

    def test_import_missing_file_raises(self, tmp_path):
        db_file = tmp_path / "nofile.sqlite"
        conn = DatabaseConnection(db_file)
        conn.connect()
        run_migrations(conn.connect())
        importer = WorkspaceImporter(conn)
        with pytest.raises(FileNotFoundError):
            importer.import_workspace(str(tmp_path / "nonexistent.json"))
        conn.close()
