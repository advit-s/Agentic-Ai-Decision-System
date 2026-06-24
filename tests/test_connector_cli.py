"""Tests for the v1.1 connector CLI commands."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from decision_system.cli_connectors import connectors_app

runner = CliRunner()


# -------------------------------------------------------------------
# connectors list
# -------------------------------------------------------------------


class TestConnectorsList:
    def test_list_exits_zero(self):
        result = runner.invoke(connectors_app, ["list"])
        assert result.exit_code == 0

    def test_list_shows_local_files(self):
        result = runner.invoke(connectors_app, ["list"])
        assert "local-files" in result.output

    def test_list_shows_available_connectors(self):
        result = runner.invoke(connectors_app, ["list"])
        for name in ("github", "url-import", "notion", "google-drive"):
            assert name in result.output

    def test_list_has_table_format(self):
        result = runner.invoke(connectors_app, ["list"])
        assert "|" in result.output


# -------------------------------------------------------------------
# connectors inspect
# -------------------------------------------------------------------


class TestConnectorsInspect:
    def test_inspect_local_files_exits_zero(self):
        result = runner.invoke(connectors_app, ["inspect", "local-files"])
        assert result.exit_code == 0

    def test_inspect_local_files_shows_details(self):
        result = runner.invoke(connectors_app, ["inspect", "local-files"])
        assert "local-files" in result.output
        assert "real" in result.output.lower()

    def test_inspect_github_shows_stub(self):
        result = runner.invoke(connectors_app, ["inspect", "github"])
        assert result.exit_code == 0
        assert "github" in result.output
        assert "stub" in result.output.lower()

    def test_inspect_unknown_exits_nonzero(self):
        result = runner.invoke(connectors_app, ["inspect", "nonexistent"])
        assert result.exit_code != 0
        assert "Unknown connector" in result.output


# -------------------------------------------------------------------
# connectors dry-run
# -------------------------------------------------------------------


class TestConnectorsDryRun:
    def test_dry_run_local_files_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "doc.md"), "w") as f:
                f.write("# Hello")
            result = runner.invoke(
                connectors_app, ["dry-run", "local-files", "--path", tmpdir]
            )
            assert result.exit_code == 0

    def test_dry_run_shows_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "doc.md"), "w") as f:
                f.write("# Hello")
            result = runner.invoke(
                connectors_app, ["dry-run", "local-files", "--path", tmpdir]
            )
            assert "Would import: 1" in result.output

    def test_dry_run_notion_stub_exits_nonzero(self):
        result = runner.invoke(
            connectors_app, ["dry-run", "notion", "--path", "/tmp"]
        )
        assert result.exit_code != 0
        assert "stub" in result.output.lower()


# -------------------------------------------------------------------
# connectors import
# -------------------------------------------------------------------


class TestConnectorsImport:
    def test_import_local_files_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(
                os.path.join(tmpdir, ".decision_system", "connectors"),
                exist_ok=True,
            )
            with open(os.path.join(tmpdir, "doc.md"), "w") as f:
                f.write("# Hello")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    connectors_app, ["import", "local-files", "--path", tmpdir]
                )
                assert result.exit_code == 0
            finally:
                os.chdir(old_cwd)

    def test_import_shows_job_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(
                os.path.join(tmpdir, ".decision_system", "connectors"),
                exist_ok=True,
            )
            with open(os.path.join(tmpdir, "doc.md"), "w") as f:
                f.write("# Hello")
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = runner.invoke(
                    connectors_app, ["import", "local-files", "--path", tmpdir]
                )
                assert result.exit_code == 0
                assert "Import job" in result.output
            finally:
                os.chdir(old_cwd)

    def test_import_notion_stub_exits_nonzero(self):
        result = runner.invoke(
            connectors_app, ["import", "notion", "--path", "/tmp"]
        )
        assert result.exit_code != 0
        assert "stub" in result.output.lower()

    def test_import_unknown_exits_nonzero(self):
        result = runner.invoke(
            connectors_app, ["import", "nonexistent", "--path", "/tmp"]
        )
        assert result.exit_code != 0


# -------------------------------------------------------------------
# connectors inspect-jobs
# -------------------------------------------------------------------


class TestConnectorsInspectJobs:
    def test_inspect_jobs_empty_via_store(self):
        """Verify empty jobs list behavior via store (CLI preserves same logic)."""
        from decision_system.connectors.store import ConnectorJobStore
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs_dir = Path(tmpdir) / "jobs"
            jobs_dir.mkdir()
            store = ConnectorJobStore(jobs_dir=jobs_dir)
            assert store.load_all() == []

    def test_inspect_jobs_shows_data_via_store(self):
        """Verify job data is persisted and retrievable."""
        from decision_system.connectors.models import ConnectorImportJob
        from decision_system.connectors.store import ConnectorJobStore
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs_dir = Path(tmpdir) / "jobs"
            jobs_dir.mkdir()
            store = ConnectorJobStore(jobs_dir=jobs_dir)
            job = ConnectorImportJob(
                job_id="cli-test-001",
                connector_id="local-files",
                status="completed",
                source_path=tmpdir,
                imported_files=["a.md"],
                skipped_files=[],
                warnings=[],
                output_paths=["out/a.md"],
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            store.save(job)

            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].job_id == "cli-test-001"
            assert loaded[0].connector_id == "local-files"

    def test_inspect_jobs_json_via_store(self):
        """Verify JSON output of import job inspection."""
        from decision_system.connectors.models import ConnectorImportJob
        from decision_system.connectors.store import ConnectorJobStore
        from decision_system.connectors.inspector import inspect_import_job
        with tempfile.TemporaryDirectory() as tmpdir:
            jobs_dir = Path(tmpdir) / "jobs"
            jobs_dir.mkdir()
            store = ConnectorJobStore(jobs_dir=jobs_dir)
            job = ConnectorImportJob(
                job_id="json-test-001",
                connector_id="local-files",
                status="completed",
                source_path=tmpdir,
                imported_files=["a.md"],
                skipped_files=[],
                warnings=[],
                output_paths=[],
                created_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            store.save(job)

            payload = inspect_import_job(job)
            assert payload["job_id"] == "json-test-001"
            assert payload["imported_count"] == 1
            assert payload["skipped_count"] == 0
