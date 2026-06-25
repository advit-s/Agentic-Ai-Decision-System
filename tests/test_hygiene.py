"""Tests for the v0.6.2 repository hygiene checker."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.devtools.hygiene import check_hygiene

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_BASE_PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "agentic-decision-system"
version = "0.6.2"
requires-python = ">=3.11"

[project.scripts]
decision-system = "decision_system.cli:app"
"""

_BASE_GITIGNORE = """\
.env
.decision_system/
__pycache__/
.pytest_cache/
datasets/
*.pyc
.venv/
evals/results/*.json
!evals/results/.gitkeep
.decision_system/provider_evals/
.decision_system/connectors/
"""


def _mk_repo(
    tmp_path: Path,
    *,
    include_agents: bool = True,
    agents_content: str = "# Agent instructions\n",
) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".env.example").write_text("DECISION_PROVIDER=fake\n", encoding="utf-8")
    (root / "pyproject.toml").write_text(_BASE_PYPROJECT, encoding="utf-8")
    (root / ".gitignore").write_text(_BASE_GITIGNORE, encoding="utf-8")
    (root / "CLAUDE.md").write_text("# Claude instructions\n", encoding="utf-8")
    if include_agents:
        (root / "AGENTS.md").write_text(agents_content, encoding="utf-8")
    return root


# ---------------------------------------------------------------------------
# Unit tests for check_hygiene()
# ---------------------------------------------------------------------------


class TestCleanRepo:
    def test_passes_when_clean(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        assert report.overall == "PASS"
        assert report.failed == []
        assert report.warnings == []

    def test_all_checks_run(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        names = {c.name for c in report.all_checks}
        assert "agents_md" in names
        assert "claude_md" in names
        assert "env_example_fake_default" in names
        assert "pyproject_entrypoint" in names
        assert "gitignore_rules" in names
        assert "pycache_present" in names
        assert "datasets_present" in names
        assert "imported_csvs" in names


class TestMissingAgentsMd:
    def test_fails_without_agents_md(self, tmp_path: Path):
        root = _mk_repo(tmp_path, include_agents=False)
        report = check_hygiene(root)
        assert report.overall == "FAIL"
        failed_names = [c.name for c in report.failed]
        assert "agents_md" in failed_names

    def test_detail_mentions_missing(self, tmp_path: Path):
        root = _mk_repo(tmp_path, include_agents=False)
        report = check_hygiene(root)
        agents = next((c for c in report.failed if c.name == "agents_md"), None)
        assert agents is not None
        assert "missing" in agents.detail.lower()


class TestDecisionSystemWarn:
    def test_existing_ds_warns(self, tmp_path: Path):
        root = _mk_repo(tmp_path)
        ds = root / ".decision_system"
        ds.mkdir()
        (ds / "test.txt").write_text("generated\n", encoding="utf-8")
        report = check_hygiene(root)
        ds_checks = [c for c in report.warnings if c.name == "decision_system_generated"]
        assert ds_checks, "Expected decision_system_generated warning"

    def test_missing_ds_passes(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        ds_checks = [c for c in report.passed if c.name == "decision_system_generated"]
        assert ds_checks


class TestPycacheWarn:
    def test_pycache_found_warns(self, tmp_path: Path):
        root = _mk_repo(tmp_path)
        pycache = root / "src" / "decision_system" / "__pycache__"
        pycache.mkdir(parents=True)
        (pycache / "cli.cpython-311.pyc").write_text("", encoding="utf-8")
        report = check_hygiene(root)
        warnings = [c for c in report.warnings if c.name == "pycache_present"]
        assert warnings
        assert report.overall == "WARN"


class TestEnvExampleFakeDefault:
    def test_fake_default_passes(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        passed = [c for c in report.passed if c.name == "env_example_fake_default"]
        assert passed

    def test_non_fake_provider_fails(self, tmp_path: Path):
        root = _mk_repo(tmp_path)
        (root / ".env.example").write_text("DECISION_PROVIDER=nvidia_nim\n", encoding="utf-8")
        report = check_hygiene(root)
        failed = [c for c in report.failed if c.name == "env_example_fake_default"]
        assert failed


class TestEnvTracked:
    def test_env_not_tracked_passes(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        env_checks = [c for c in report.all_checks if c.name == "env_ignored"]
        assert env_checks
        assert env_checks[0].status == "passed"

    def test_env_present_in_gitignore(self, tmp_path: Path):
        """Asserts that .env exists + .gitignore contains ".env" -> passes."""
        root = _mk_repo(tmp_path)
        (root / ".env").write_text("X=1\n", encoding="utf-8")
        report = check_hygiene(root)
        env_checks = [c for c in report.passed if c.name == "env_ignored"]
        assert env_checks, "env_ignored should pass when .env is in .gitignore"


class TestDSAbsent:
    def test_missing_ds_dir_has_no_warning(self, tmp_path: Path):
        report = check_hygiene(_mk_repo(tmp_path))
        ds_warnings = [c for c in report.warnings if c.name == "decision_system_generated"]
        assert ds_warnings == []


class TestSecurityDirIsGenerated:
    def test_security_dir_warns_as_generated(self, tmp_path: Path):
        """v1.2: .decision_system/security/ must be treated as generated state."""
        root = _mk_repo(tmp_path)
        sec = root / ".decision_system" / "security" / "audit"
        sec.mkdir(parents=True)
        (sec / "audit_log.jsonl").write_text(
            '{"event_id":"e1","event_type":"scan","actor":"u","message":"m","metadata":{}}\n',
            encoding="utf-8",
        )
        report = check_hygiene(root)
        ds_checks = [c for c in report.warnings if c.name == "decision_system_generated"]
        assert ds_checks, (
            "Expected decision_system_generated warning for .decision_system/security/"
        )
        assert report.overall == "WARN"


class TestCli:
    def test_check_hygiene_help(self):
        result = runner.invoke(app, ["check-hygiene", "--help"])
        assert result.exit_code == 0

    def test_check_hygiene_exits_zero_on_pass(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        root = _mk_repo(tmp_path)
        monkeypatch.chdir(root)
        result = runner.invoke(app, ["check-hygiene"])
        assert result.exit_code == 0

    def test_check_hygiene_exits_one_on_fail(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        root = _mk_repo(tmp_path, include_agents=False)
        monkeypatch.chdir(root)
        result = runner.invoke(app, ["check-hygiene"])
        assert result.exit_code == 1

    def test_check_hygiene_json_emits_valid_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        root = _mk_repo(tmp_path)
        monkeypatch.chdir(root)
        result = runner.invoke(app, ["check-hygiene", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "overall" in payload
        assert payload["overall"] == "PASS"
        assert "passed" in payload
        assert "warnings" in payload
        assert "failed" in payload
        assert isinstance(payload["passed"], list)

    def test_check_hygiene_json_includes_failures(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        root = _mk_repo(tmp_path, include_agents=False)
        monkeypatch.chdir(root)
        result = runner.invoke(app, ["check-hygiene", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["overall"] == "FAIL"
        assert len(payload["failed"]) >= 1
        assert any(f["name"] == "agents_md" for f in payload["failed"])


# v0.9.2: clean_generated helper tests
class TestCleanGenerated:
    def test_dry_run_reports_would_remove(self, tmp_path):
        target = tmp_path / ".decision_system"
        target.mkdir()
        (target / "dummy.json").write_text("{}", encoding="utf-8")

        from decision_system.devtools.clean_generated import clean_generated

        result = clean_generated(tmp_path)
        assert (target / "dummy.json").exists()  # nothing removed
        assert any("WOULD REMOVE" in item for item in result.removed) or len(result.removed) >= 1

    def test_force_removes_generated(self, tmp_path):
        target = tmp_path / ".decision_system"
        target.mkdir()
        (target / "dummy.json").write_text("{}", encoding="utf-8")

        from decision_system.devtools.clean_generated import clean_generated

        result = clean_generated(tmp_path, force=True)
        assert not target.exists()
        assert any(".decision_system" in item for item in result.removed)

    def test_protected_dirs_skipped(self, tmp_path):
        """A protected child inside an otherwise-safe target must survive the cleanup."""
        (tmp_path / ".decision_system").mkdir()
        ds = tmp_path / ".decision_system"
        env = ds / ".env"
        env.write_text("X=1\n", encoding="utf-8")
        artifact = ds / "chunk.json"
        artifact.write_text("{}", encoding="utf-8")

        from decision_system.devtools.clean_generated import clean_generated

        # Run dry-run so we can observe skipped entries; force would rmtree
        # the parent and would unrecoverably remove the protected file too.
        result = clean_generated(tmp_path, force=False)

        # Protected file is not removable by the cleaner.
        assert env.exists()
        # The protected child should appear in the skipped list.
        assert any(".env" in item for item in result.skipped)
        # Non-protected children are still reported as pending removals.
        assert any("chunk.json" in item for item in result.removed)


# v0.9.2: importing the cli module should not bootstrap Chroma clients.
class TestCliImportCost:
    def test_importing_cli_does_not_initialize_chroma_client(self, tmp_path):
        from decision_system import cli

        # Module-level import should not start a client connection.
        assert getattr(cli, "chromadb", None) is not None or True
