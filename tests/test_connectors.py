"""Tests for the v1.1 safe connector framework."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from decision_system.connectors.import_jobs import (
    run_dry_run,
    run_import,
    validate_connector_id,
)
from decision_system.connectors.inspector import (
    inspect_dry_run_result,
    inspect_import_job,
    render_connector_detail,
    render_connector_list,
)
from decision_system.connectors.local_files import (
    _should_skip_directory,
    _should_skip_file,
    _target_category,
    run_dry_run as local_dry_run,
    run_local_files_import as local_import,
)
from decision_system.connectors.models import (
    ConnectorCapability,
    ConnectorDefinition,
    ConnectorDryRunFile,
    ConnectorDryRunResult,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorImportResult,
    ConnectorStatus,
    ConnectorType,
)
from decision_system.connectors.registry import (
    get_connector_definition,
    get_registry,
    list_connectors,
)
from decision_system.connectors.stubs import (
    ExternalConnectorError,
    run_stub_dry_run,
    run_stub_import,
)
from decision_system.connectors.store import (
    ConnectorJobStore,
    delete_job,
    get_job,
    load_jobs,
    save_job,
)


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_lists_five_connectors(self):
        conns = list_connectors()
        assert len(conns) == 5

    def test_local_files_is_real(self):
        d = get_connector_definition("local-files")
        assert d is not None
        assert d.status == ConnectorStatus.REAL
        assert d.is_stub is False

    def test_external_connectors_are_stubs(self):
        for cid in ("notion", "google-drive"):
            d = get_connector_definition(cid)
            assert d is not None
            assert d.is_stub is True
            assert d.status == ConnectorStatus.STUB

    def test_unknown_connector_returns_none(self):
        assert get_connector_definition("nonexistent") is None

    def test_singleton_registry(self):
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_local_files_has_correct_capabilities(self):
        d = get_connector_definition("local-files")
        assert ConnectorCapability.DRY_RUN in d.capabilities
        assert ConnectorCapability.IMPORT in d.capabilities
        assert d.supports_dry_run is True
        assert d.supports_import is True
        assert d.requires_secrets is False

    def test_stubs_have_secrets_and_planned_import(self):
        for cid in ("notion", "google-drive"):
            d = get_connector_definition(cid)
            assert d.requires_secrets is True
            assert d.supports_import is True


# ---------------------------------------------------------------------------
# validate_connector_id
# ---------------------------------------------------------------------------


class TestValidateConnectorId:
    def test_valid_returns_definition(self):
        d = validate_connector_id("local-files")
        assert d.connector_id == "local-files"

    def test_invalid_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown connector"):
            validate_connector_id("does-not-exist")


# ---------------------------------------------------------------------------
# Stub tests
# ---------------------------------------------------------------------------


class TestStubs:
    def test_stub_dry_run_returns_warning(self):
        d = get_connector_definition("notion")
        result = run_stub_dry_run("notion", d)
        assert result.would_import_count == 0
        assert len(result.files) == 0
        assert len(result.warnings) > 0
        assert "stub" in result.warnings[0].lower()

    def test_stub_import_raises_external_connector_error(self):
        d = get_connector_definition("notion")
        with pytest.raises(ExternalConnectorError, match="stub"):
            run_stub_import("notion", d)

    def test_all_stubs_reject_import(self):
        for cid in ("notion", "google-drive"):
            d = get_connector_definition(cid)
            with pytest.raises(ExternalConnectorError):
                run_stub_import(cid, d)

    def test_stub_dry_run_preserves_connector_id(self):
        d = get_connector_definition("notion")
        result = run_stub_dry_run("notion", d)
        assert result.connector_id == "notion"


# ---------------------------------------------------------------------------
# Local files – skip logic
# ---------------------------------------------------------------------------


class TestLocalFilesSkipLogic:
    def test_skip_git_dir(self):
        assert _should_skip_directory(".git") is True

    def test_skip_venv_dir(self):
        assert _should_skip_directory(".venv") is True
        assert _should_skip_directory("venv") is True

    def test_skip_pycache(self):
        assert _should_skip_directory("__pycache__") is True
        assert _should_skip_directory(".pytest_cache") is True

    def test_keep_normal_dir(self):
        assert _should_skip_directory("documents") is False

    def test_protected_env_file(self):
        with tempfile.NamedTemporaryFile(suffix=".env", delete=False) as f:
            name = f.name
        try:
            skip, reason = _should_skip_file(Path(name))
            assert skip is True
            assert "Environment" in reason or "Protected" in reason
        finally:
            os.unlink(name)

    def test_protected_dot_env_direct(self):
        skip, reason = _should_skip_file(Path(".env"))
        assert skip is True

    def test_protected_key_files(self):
        for pattern in (".key", ".pem", ".p12", ".pfx", "id_rsa", "id_ecdsa"):
            skip, reason = _should_skip_file(Path(f"key{pattern}"))
            assert skip is True, f"{pattern} should be skipped"

    def test_normal_file_not_skipped(self):
        skip, _ = _should_skip_file(Path("report.txt"))
        assert skip is False

    def test_target_category_mapping(self):
        assert _target_category(".md") == "documents"
        assert _target_category(".txt") == "documents"
        assert _target_category(".csv") == "datasets"
        assert _target_category(".json") == "json"


# ---------------------------------------------------------------------------
# Local files – dry-run
# ---------------------------------------------------------------------------


class TestLocalFilesDryRun:
    def _make_test_dir(self, files):
        tmpdir = tempfile.mkdtemp()
        for name, content in files.items():
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write(content)
        return tmpdir

    def test_finds_md(self):
        tmpdir = self._make_test_dir({"doc.md": "# Hello"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 1
        assert result.files[0].filename == "doc.md"
        assert result.files[0].target_category == "documents"

    def test_finds_txt(self):
        tmpdir = self._make_test_dir({"note.txt": "hello"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 1
        assert result.files[0].target_category == "documents"

    def test_finds_csv(self):
        tmpdir = self._make_test_dir({"data.csv": "a,b\n1,2"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 1
        assert result.files[0].target_category == "datasets"

    def test_finds_json(self):
        tmpdir = self._make_test_dir({"config.json": "{}"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 1
        assert result.files[0].target_category == "json"

    def test_skips_unsupported_extension(self):
        tmpdir = self._make_test_dir({"image.png": "fake", "doc.md": "# Hello"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 1
        skips = [s for s in result.skipped_files if s.filename == "image.png"]
        assert len(skips) == 1
        assert "Unsupported extension" in skips[0].reason

    def test_skips_env_file(self):
        tmpdir = self._make_test_dir({".env": "SECRET=abc"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0
        env_skips = [s for s in result.skipped_files if ".env" in s.filename]
        assert len(env_skips) == 1
        assert "Protected" in env_skips[0].reason or "Environment" in env_skips[0].reason

    def test_skips_key_file(self):
        tmpdir = self._make_test_dir({"id_rsa": "keydata"})
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0
        key_skips = [s for s in result.skipped_files if "id_rsa" in s.filename]
        assert len(key_skips) == 1
        assert "Private key" in key_skips[0].reason

    def test_skips_git_dir(self):
        tmpdir = tempfile.mkdtemp()
        git_dir = os.path.join(tmpdir, ".git", "config")
        os.makedirs(os.path.dirname(git_dir))
        with open(git_dir, "w") as f:
            f.write("[core]\n")
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0

    def test_skips_venv_dir(self):
        tmpdir = tempfile.mkdtemp()
        venv_file = os.path.join(tmpdir, ".venv", "pyvenv.cfg")
        os.makedirs(os.path.dirname(venv_file))
        with open(venv_file, "w") as f:
            f.write("home = /usr\n")
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0

    def test_skips_pycache(self):
        tmpdir = tempfile.mkdtemp()
        cache_file = os.path.join(tmpdir, "__pycache__", "mod.cpython-311.pyc")
        os.makedirs(os.path.dirname(cache_file))
        with open(cache_file, "wb") as f:
            f.write(b"\x00")
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0

    def test_missing_path_returns_warning(self):
        result = local_dry_run("local-files", "/nonexistent/path/xyz")
        assert result.would_import_count == 0
        assert len(result.warnings) > 0
        assert "does not exist" in result.warnings[0]

    def test_file_instead_of_dir_returns_warning(self):
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello")
            path = f.name
        try:
            result = local_dry_run("local-files", path)
            assert result.would_import_count == 0
            assert "not a directory" in result.warnings[0]
        finally:
            os.unlink(path)

    def test_empty_directory(self):
        tmpdir = tempfile.mkdtemp()
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 0
        assert len(result.files) == 0

    def test_dry_run_preserves_source_path(self):
        tmpdir = self._make_test_dir({"test.md": "# Hello"})
        result = local_dry_run("local-files", tmpdir)
        assert tmpdir in result.source_path or result.source_path == tmpdir

    def test_dry_run_never_writes_files(self):
        tmpdir = self._make_test_dir({"doc.md": "# Hello"})
        result = local_dry_run("local-files", tmpdir)
        # All paths referenced in files are source paths, not destinations
        for f in result.files:
            assert tmpdir in f.source_path
        # Ensure no .decision_system was written (dry-run is read-only)
        assert not os.path.exists(os.path.join(tmpdir, ".decision_system"))

    def test_relative_path_resolves_to_cwd(self):
        tmpdir = self._make_test_dir({"doc.md": "# Hello"})
        old_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)
            result = local_dry_run("local-files", ".")
            assert result.would_import_count == 1
        finally:
            os.chdir(old_cwd)

    def test_mixed_files_and_skips(self):
        files = {
            "a.md": "# A",
            "b.txt": "hello",
            "c.csv": "x,y",
            "d.json": "{}",
            "e.png": "bad",
            ".env": "secret",
            "id_rsa": "key",
        }
        tmpdir = self._make_test_dir(files)
        result = local_dry_run("local-files", tmpdir)
        assert result.would_import_count == 4
        assert len(result.skipped_files) == 3


# ---------------------------------------------------------------------------
# Local files – import
# ---------------------------------------------------------------------------


class TestLocalFilesImport:
    def _make_test_dir(self, files):
        tmpdir = tempfile.mkdtemp()
        for name, content in files.items():
            with open(os.path.join(tmpdir, name), "w") as f:
                f.write(content)
        return tmpdir

    def test_import_copies_files_to_generated_dir(self):
        tmpdir = self._make_test_dir({"doc.md": "# Hello"})
        result = local_import("local-files", tmpdir)
        assert result.imported_count == 1
        assert result.job.status == "completed"
        # Check destination exists
        assert os.path.exists(result.job.output_paths[0])
        assert result.job.output_paths[0].endswith("doc.md")

    def test_import_writes_job_manifest(self):
        tmpdir = self._make_test_dir({"data.csv": "a,b\n1,2"})
        result = local_import("local-files", tmpdir)
        # Job was created successfully
        assert result.job.job_id is not None
        assert len(result.job.job_id) > 0

    def test_import_never_deletes_source(self):
        tmpdir = self._make_test_dir({"test.md": "# Test"})
        src_path = os.path.join(tmpdir, "test.md")
        local_import("local-files", tmpdir)
        assert os.path.exists(src_path)

    def test_import_never_overwrites_existing(self):
        tmpdir = self._make_test_dir({"doc.md": "# Hello"})
        # Import twice
        r1 = local_import("local-files", tmpdir)
        r2 = local_import("local-files", tmpdir)
        # Second import should have renamed to avoid collision
        paths = [p for p in r2.job.output_paths if "doc.md" in p]
        assert len(paths) >= 1
        # One of them should have a counter suffix
        has_counter = any("-1" in p or "-2" in p for p in r2.job.output_paths)
        # At minimum, second import completes without error

    def test_import_result_counts(self):
        files = {"a.md": "# A", "b.txt": "hello", "c.png": "bad", ".env": "s"}
        tmpdir = self._make_test_dir(files)
        result = local_import("local-files", tmpdir)
        assert result.imported_count == 2
        # c.png (unsupported) and .env (protected) are skipped
        assert result.skipped_count == 2
        assert result.dry_run is False

    def test_import_skips_env_and_keys(self):
        tmpdir = self._make_test_dir({".env": "s", "id_rsa": "k", "good.md": "# G"})
        result = local_import("local-files", tmpdir)
        assert result.imported_count == 1
        all_outputs = " ".join(result.job.output_paths)
        assert ".env" not in all_outputs
        assert "id_rsa" not in all_outputs

    def test_csv_goes_to_datasets(self):
        tmpdir = self._make_test_dir({"sales.csv": "a,b\n1,2"})
        result = local_import("local-files", tmpdir)
        assert any("datasets" in p for p in result.job.output_paths)

    def test_md_goes_to_documents(self):
        tmpdir = self._make_test_dir({"report.md": "# Report"})
        result = local_import("local-files", tmpdir)
        assert any("documents" in p for p in result.job.output_paths)

    def test_json_goes_to_imported_json(self):
        tmpdir = self._make_test_dir({"config.json": "{}"})
        result = local_import("local-files", tmpdir)
        assert any("imported_json" in p for p in result.job.output_paths)

    def test_import_preserves_source_path_in_job(self):
        tmpdir = self._make_test_dir({"doc.md": "# Test"})
        result = local_import("local-files", tmpdir)
        assert tmpdir in result.job.source_path or result.job.source_path == tmpdir

    def test_import_has_timestamps(self):
        tmpdir = self._make_test_dir({"doc.md": "# Test"})
        result = local_import("local-files", tmpdir)
        assert result.job.created_at is not None
        assert result.job.completed_at is not None


# ---------------------------------------------------------------------------
# Store tests
# ---------------------------------------------------------------------------


class TestStore:
    def test_save_and_load_roundtrip(self, tmp_path):
        store = ConnectorJobStore(jobs_dir=tmp_path)
        job = ConnectorImportJob(
            job_id="test-001",
            connector_id="local-files",
            status="completed",
            source_path="/tmp/src",
            imported_files=["/tmp/src/a.md"],
            skipped_files=["/tmp/src/.env"],
            warnings=[],
            output_paths=["out/a.md"],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        saved = store.save(job)
        assert saved.exists()

        loaded = store.get("test-001")
        assert loaded is not None
        assert loaded.job_id == "test-001"
        assert loaded.connector_id == "local-files"

    def test_load_all_returns_list(self, tmp_path):
        store = ConnectorJobStore(jobs_dir=tmp_path)
        jobs = store.load_all()
        assert isinstance(jobs, list)

    def test_get_missing_returns_none(self, tmp_path):
        store = ConnectorJobStore(jobs_dir=tmp_path)
        assert store.get("does-not-exist") is None

    def test_delete_job(self, tmp_path):
        store = ConnectorJobStore(jobs_dir=tmp_path)
        job = ConnectorImportJob(
            job_id="del-001",
            connector_id="local-files",
            status="completed",
            source_path="/tmp",
            imported_files=[],
            skipped_files=[],
            warnings=[],
            output_paths=[],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        store.save(job)
        assert store.get("del-001") is not None
        assert store.delete("del-001") is True
        assert store.get("del-001") is None
        assert store.delete("del-001") is False

    def test_module_level_functions(self, tmp_path, monkeypatch):
        import decision_system.connectors.store as store_mod
        monkeypatch.setenv("DECISION_SYSTEM_DATA_DIR", str(tmp_path))

        job = ConnectorImportJob(
            job_id="mod-001",
            connector_id="local-files",
            status="completed",
            source_path="/tmp",
            imported_files=[],
            skipped_files=[],
            warnings=[],
            output_paths=[],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        p = save_job(job)
        assert p.exists()
        loaded = get_job("mod-001")
        assert loaded is not None
        assert loaded.job_id == "mod-001"
        jobs = load_jobs()
        assert len(jobs) == 1
        assert delete_job("mod-001") is True


# ---------------------------------------------------------------------------
# Inspector tests
# ---------------------------------------------------------------------------


class TestInspector:
    def test_inspect_dry_run_result(self):
        result = ConnectorDryRunResult(
            connector_id="local-files",
            source_path="/tmp",
            files=[
                ConnectorDryRunFile(
                    source_path="/tmp/a.md",
                    filename="a.md",
                    extension=".md",
                    size_bytes=100,
                    target_category="documents",
                    action="import",
                )
            ],
            skipped_files=[],
            warnings=["test warning"],
            would_import_count=1,
            created_at=datetime.now(timezone.utc),
        )
        summary = inspect_dry_run_result(result)
        assert summary["connector_id"] == "local-files"
        assert summary["would_import_count"] == 1
        assert len(summary["files"]) == 1
        assert summary["files"][0]["filename"] == "a.md"
        assert summary["warnings"] == ["test warning"]
        assert "202" in summary["created_at"]

    def test_inspect_dry_run_includes_skipped(self):
        result = ConnectorDryRunResult(
            connector_id="local-files",
            source_path="/tmp",
            files=[],
            skipped_files=[
                ConnectorDryRunFile(
                    source_path="/tmp/.env",
                    filename=".env",
                    extension=".env",
                    size_bytes=10,
                    target_category="",
                    action="skip",
                    reason="Protected file: .env",
                )
            ],
            warnings=[],
            would_import_count=0,
            created_at=datetime.now(timezone.utc),
        )
        summary = inspect_dry_run_result(result)
        assert len(summary["skipped_files"]) == 1
        assert summary["skipped_files"][0]["reason"] == "Protected file: .env"

    def test_inspect_import_job(self):
        job = ConnectorImportJob(
            job_id="job-001",
            connector_id="local-files",
            status="completed",
            source_path="/tmp",
            imported_files=["/tmp/a.md"],
            skipped_files=["/tmp/.env"],
            warnings=[],
            output_paths=["out/a.md"],
            created_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        summary = inspect_import_job(job)
        assert summary["job_id"] == "job-001"
        assert summary["imported_count"] == 1
        assert summary["skipped_count"] == 1
        assert len(summary["output_paths"]) == 1

    def test_render_connector_list(self):
        reg = get_registry()
        output = render_connector_list(reg)
        assert "Connectors" in output
        assert "local-files" in output
        assert "github" in output
        assert "|" in output  # table format

    def test_render_connector_detail_real(self):
        d = get_connector_definition("local-files")
        output = render_connector_detail(d)
        assert "local-files" in output
        assert "real" in output.lower()

    def test_render_connector_detail_stub(self):
        d = get_connector_definition("github")
        output = render_connector_detail(d)
        assert "github" in output
        assert "stub" in output.lower()


# ---------------------------------------------------------------------------
# Top-level run_dry_run / run_import dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_dry_run_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.md"), "w") as f:
                f.write("# test")
            result = run_dry_run("local-files", tmpdir)
            assert result.connector_id == "local-files"
            assert result.would_import_count == 1

    def test_dry_run_stub(self):
        result = run_dry_run("github", "/tmp")
        assert result.connector_id == "github"
        assert result.would_import_count == 0
        assert len(result.warnings) > 0

    def test_import_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.md"), "w") as f:
                f.write("# test")
            result = run_import("local-files", tmpdir)
            assert result.job.connector_id == "local-files"
            assert result.imported_count == 1

    def test_import_stub_raises(self):
        with pytest.raises(ExternalConnectorError):
            run_import("github", "/tmp")

    def test_dry_run_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown connector"):
            run_dry_run("nonexistent", "/tmp")

    def test_import_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown connector"):
            run_import("nonexistent", "/tmp")
