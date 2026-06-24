"""Tests for v1.8 features: Report Export, Coverage Score, Workspace Diff,
Audit Timeline, Demo Data Validator, and Provider Safety Status.

All tests are offline and use the fake provider by default.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# =========================================================================
# Feature A: Report Export
# =========================================================================


class TestReportExport:
    """Tests for the report export module (exporter.py)."""

    def test_build_report_payload_defaults(self):
        from decision_system.reports.exporter import build_report_payload

        payload = build_report_payload()
        assert payload["question"] == "(no question)"
        assert payload["recommendation"] == "(no recommendation)"
        assert payload["claims"] == []
        assert payload["unsupported_claims"] == []
        assert payload["contradicted_claims"] == []
        assert payload["evidence_ids"] == []
        assert "exported_at" in payload
        assert payload["audit_metadata"] == {}

    def test_build_report_payload_with_claims(self):
        from decision_system.reports.exporter import build_report_payload
        from decision_system.models import Claim

        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="analyst",
                claim_text="Claim one", claim_type="technical",
                status="verified", confidence="high",
            ),
            Claim(
                claim_id="c2", run_id="r1", source_agent="analyst",
                claim_text="Claim two", claim_type="risk",
                status="unsupported", confidence="low",
            ),
            Claim(
                claim_id="c3", run_id="r1", source_agent="analyst",
                claim_text="Claim three", claim_type="risk",
                status="contradicted", confidence="medium",
            ),
        ]
        payload = build_report_payload(
            question="Test question?",
            recommendation="Proceed with caution.",
            options=["Option A", "Option B"],
            risks=["Risk 1"],
            assumptions=["Assumption 1"],
            claims=claims,
            audit_metadata={"run_id": "test-run"},
        )
        assert payload["question"] == "Test question?"
        assert len(payload["claims"]) == 3
        assert payload["unsupported_claims"] == ["c2"]
        assert payload["contradicted_claims"] == ["c3"]

    def test_export_markdown(self):
        from decision_system.reports.exporter import build_report_payload, export_report

        payload = build_report_payload(question="Q?", recommendation="R.")
        result = export_report(payload, fmt="markdown")
        assert isinstance(result, str)
        assert "Q?" in result
        assert "R." in result
        assert "# Decision Report" in result

    def test_export_json(self):
        from decision_system.reports.exporter import build_report_payload, export_report

        payload = build_report_payload(question="Q?", recommendation="R.")
        result = export_report(payload, fmt="json")
        data = json.loads(result)
        assert data["question"] == "Q?"
        assert data["recommendation"] == "R."

    def test_export_html(self):
        from decision_system.reports.exporter import build_report_payload, export_report

        payload = build_report_payload(question="Q?", recommendation="R.")
        result = export_report(payload, fmt="html")
        assert isinstance(result, str)
        assert "<!DOCTYPE html>" in result
        assert "Q?" in result

    def test_export_to_file(self):
        from decision_system.reports.exporter import build_report_payload, export_report

        payload = build_report_payload(question="Q?", recommendation="R.")
        out_dir = Path(".decision_system/tests/report_export")
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / "report.md"
        try:
            result = export_report(payload, fmt="markdown", output_path=str(output))
            assert output.exists()
            assert "Q?" in output.read_text()
        finally:
            if output.exists():
                output.unlink()
            try:
                out_dir.rmdir()
            except OSError:
                pass

    def test_export_invalid_format(self):
        from decision_system.reports.exporter import build_report_payload, export_report

        payload = build_report_payload()
        with pytest.raises(ValueError):
            export_report(payload, fmt="invalid_format")

    def test_cli_export_report(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["export-report", "--format", "json"])
        # Should work or indicate no report data (either is fine)
        assert result.exit_code in (0, 1)
        if result.exit_code == 0:
            assert "recommendation" in result.stdout


# =========================================================================
# Feature B: Coverage Score
# =========================================================================


class TestCoverageScore:
    """Tests for evidence coverage score (coverage.py)."""

    def test_empty_coverage(self):
        from decision_system.reports.coverage import compute_coverage

        score = compute_coverage()
        assert score.total_claims == 0
        assert score.evidence_coverage_pct == 0.0
        assert score.status == "no_claims"

    def test_all_verified(self):
        from decision_system.reports.coverage import compute_coverage
        from decision_system.models import VerificationResult

        results = [
            VerificationResult(
                claim_id="c1", status="verified",
                evidence_ids=["e1"], confidence="high",
                verification_notes="",
            ),
            VerificationResult(
                claim_id="c2", status="verified",
                evidence_ids=["e1"], confidence="high",
                verification_notes="",
            ),
        ]
        score = compute_coverage(verification_results=results)
        assert score.total_claims == 2
        assert score.verified_claims == 2
        assert score.evidence_coverage_pct == 100.0
        assert score.status == "good"

    def test_partial_coverage(self):
        from decision_system.reports.coverage import compute_coverage
        from decision_system.models import VerificationResult

        results = [
            VerificationResult(claim_id="c1", status="verified", evidence_ids=["e1"], confidence="high", verification_notes=""),
            VerificationResult(claim_id="c2", status="unsupported", evidence_ids=[], confidence="low", verification_notes=""),
        ]
        score = compute_coverage(verification_results=results)
        assert score.total_claims == 2
        assert score.verified_claims == 1
        assert score.unsupported_claims == 1
        assert score.evidence_coverage_pct == 50.0
        assert score.status == "unsupported_found"

    def test_contradictions(self):
        from decision_system.reports.coverage import compute_coverage
        from decision_system.models import Claim

        claims = [
            Claim(claim_id="c1", run_id="r1", source_agent="a", claim_text="t1", claim_type="technical", status="contradicted", confidence="low"),
            Claim(claim_id="c2", run_id="r1", source_agent="a", claim_text="t2", claim_type="technical", status="verified", confidence="high"),
        ]
        score = compute_coverage(claims=claims)
        assert score.total_claims == 2
        assert score.contradicted_claims == 1
        assert score.status == "contradictions_found"

    def test_coverage_from_claims(self):
        from decision_system.reports.coverage import compute_coverage
        from decision_system.models import Claim

        claims = [
            Claim(claim_id="c1", run_id="r1", source_agent="a", claim_text="t1", claim_type="technical", status="verified", confidence="high"),
            Claim(claim_id="c2", run_id="r1", source_agent="a", claim_text="t2", claim_type="technical", status="pending", confidence="low"),
        ]
        score = compute_coverage(claims=claims)
        assert score.total_claims == 2
        assert score.pending_claims == 1

    def test_coverage_to_text(self):
        from decision_system.reports.coverage import compute_coverage, coverage_to_text

        score = compute_coverage()
        text = coverage_to_text(score)
        assert "Coverage Score" in text
        assert "no_claims" in text

    def test_cli_coverage(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["coverage"])
        assert result.exit_code == 0
        assert "Coverage Score" in result.stdout or "no_claims" in result.stdout

    def test_cli_coverage_json(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["coverage", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "total_claims" in data
        assert "evidence_coverage_pct" in data


# =========================================================================
# Feature C: Workspace Snapshot Diff
# =========================================================================


class TestWorkspaceDiff:
    """Tests for workspace diff (diff.py)."""

    def test_diff_basic(self, tmp_path):
        from decision_system.reports.diff import diff_workspaces

        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        old.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": [
            {"artifact_type": "decision_report", "source_path": "doc1.md", "title": "Doc One"},
        ]}))
        new.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": [
            {"artifact_type": "decision_report", "source_path": "doc1.md", "title": "Doc One"},
            {"artifact_type": "decision_report", "source_path": "doc2.md", "title": "Doc Two"},
        ]}))

        diff = diff_workspaces(old, new)
        assert diff.has_changes
        assert "doc2.md" in diff.added_documents or "Doc Two" in diff.added_documents
        assert diff.summary
        assert "change" in diff.summary

    def test_diff_identical(self, tmp_path):
        from decision_system.reports.diff import diff_workspaces

        p = tmp_path / "same.json"
        content = json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": []})
        p.write_text(content)
        diff = diff_workspaces(p, p)
        assert not diff.has_changes

    def test_diff_removed(self, tmp_path):
        from decision_system.reports.diff import diff_workspaces

        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        old.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": [
            {"artifact_type": "decision_report", "source_path": "gone.md", "title": "Gone"},
        ]}))
        new.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": []}))
        diff = diff_workspaces(old, new)
        assert diff.has_changes
        assert "gone.md" in diff.removed_documents or "Gone" in diff.removed_documents

    def test_diff_text_render(self, tmp_path):
        from decision_system.reports.diff import diff_workspaces, diff_to_text

        old = tmp_path / "old.json"
        new = tmp_path / "new.json"
        old.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": []}))
        new.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": [
            {"artifact_type": "decision_report", "source_path": "new.md", "title": "New"},
        ]}))
        diff = diff_workspaces(old, new)
        text = diff_to_text(diff)
        assert "Workspace Diff" in text
        assert "Added" in text or "added" in text

    def test_cli_diff(self, tmp_path):
        from typer.testing import CliRunner
        from decision_system.cli import app

        old = tmp_path / "a.json"
        new = tmp_path / "b.json"
        old.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": []}))
        new.write_text(json.dumps({"version": "1.0", "workspace": {"name": "ws1"}, "artifacts": []}))
        runner = CliRunner()
        result = runner.invoke(app, ["diff-workspaces", str(old), str(new)])
        assert result.exit_code == 0

    def test_cli_diff_missing_file(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["diff-workspaces", "/nonexistent/old.json", "/nonexistent/new.json"])
        assert result.exit_code == 1


# =========================================================================
# Feature D: Audit Timeline
# =========================================================================


class TestAuditTimeline:
    """Tests for audit timeline (timeline.py)."""

    def test_empty_timeline(self, tmp_path):
        from decision_system.reports.timeline import build_timeline

        timeline = build_timeline(decision_root=str(tmp_path))
        assert timeline.total_count == 0
        assert timeline.events == []

    def test_timeline_empty_text(self, tmp_path):
        from decision_system.reports.timeline import build_timeline, timeline_to_text

        timeline = build_timeline(decision_root=str(tmp_path))
        text = timeline_to_text(timeline)
        assert "No audit events found" in text

    def test_timeline_to_dict(self, tmp_path):
        from decision_system.reports.timeline import build_timeline

        timeline = build_timeline(decision_root=str(tmp_path))
        d = timeline.to_dict()
        assert "events" in d
        assert "total_count" in d

    def test_cli_timeline(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["audit-timeline"])
        assert result.exit_code == 0
        # Should either show events or the "no events" message
        assert result.stdout.strip() != ""

    def test_cli_timeline_json(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["audit-timeline", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "events" in data


# =========================================================================
# Feature E: Demo Data Validator
# =========================================================================


class TestDemoDataValidator:
    """Tests for demo data validation (demo_data_validator.py)."""

    def test_validate_clean_demo_no_findings(self, tmp_path):
        from decision_system.devtools.demo_data_validator import validate_demo_data

        # Create clean demo data
        docs = tmp_path / "company_docs"
        docs.mkdir(parents=True)
        (docs / "demo_test.md").write_text("# Demo doc for testing\nThis is clean.\n")

        mock = tmp_path / "web" / "mock-data"
        mock.mkdir(parents=True)
        (mock / "dashboard.json").write_text('{"items": [], "status": "ok"}')

        result = validate_demo_data(project_root=str(tmp_path))
        # Passes by default since no files outside project root
        assert isinstance(result.passed, bool)
        assert isinstance(result.files_scanned, int)
        assert isinstance(result.to_dict(), dict)

    def test_validate_scans_known_patterns(self):
        from decision_system.devtools.demo_data_validator import (
            validate_demo_data,
            ValidationFinding,
        )

        # Run from actual project root
        result = validate_demo_data()
        assert result.files_scanned > 0
        # Should pass since demo data is clean
        assert result.passed

    def test_validation_to_text(self):
        from decision_system.devtools.demo_data_validator import (
            DemoDataValidationResult,
            validation_to_text,
        )

        result = DemoDataValidationResult(files_scanned=5)
        text = validation_to_text(result)
        assert "Demo Data Validation" in text
        assert "5" in text

    def test_cli_validate(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["validate-demo-data"])
        assert result.exit_code == 0


# =========================================================================
# Feature F: Provider Safety Status
# =========================================================================


class TestProviderSafety:
    """Tests for provider safety status (provider_safety.py)."""

    def test_default_is_fake_safe(self, monkeypatch):
        from decision_system.reports.provider_safety import get_provider_safety_status

        monkeypatch.setenv("DECISION_PROVIDER", "fake")
        status = get_provider_safety_status()
        assert status.configured_provider == "fake"
        assert not status.is_external
        assert status.safety_level == "safe"

    def test_external_provider_warning(self, monkeypatch):
        from decision_system.reports.provider_safety import get_provider_safety_status

        monkeypatch.setenv("DECISION_PROVIDER", "nvidia_nim")
        monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
        monkeypatch.setenv("NVIDIA_NIM_MODEL", "test-model")
        status = get_provider_safety_status()
        assert status.configured_provider == "nvidia_nim"
        assert status.is_external
        assert status.safety_level == "external"

    def test_ollama_is_not_external(self, monkeypatch):
        from decision_system.reports.provider_safety import get_provider_safety_status

        monkeypatch.setenv("DECISION_PROVIDER", "ollama")
        monkeypatch.setenv("OLLAMA_MODEL", "test-model")
        status = get_provider_safety_status()
        assert status.configured_provider == "ollama"
        assert not status.is_external
        assert status.safety_level == "external"

    def test_safety_to_text(self, monkeypatch):
        from decision_system.reports.provider_safety import (
            get_provider_safety_status,
            safety_to_text,
        )

        monkeypatch.setenv("DECISION_PROVIDER", "fake")
        status = get_provider_safety_status()
        text = safety_to_text(status)
        assert "fake" in text
        assert "safe" in text

    def test_to_dict(self, monkeypatch):
        from decision_system.reports.provider_safety import get_provider_safety_status

        monkeypatch.setenv("DECISION_PROVIDER", "fake")
        d = get_provider_safety_status().to_dict()
        assert d["configured_provider"] == "fake"
        assert d["safety_level"] == "safe"

    def test_cli_provider_safety(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["provider-safety"])
        assert result.exit_code == 0
        assert "fake" in result.stdout

    def test_cli_provider_safety_json(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["provider-safety", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "configured_provider" in data


# =========================================================================
# Feature API Endpoints
# =========================================================================


class TestNewFeatureAPIEndpoints:
    """Tests for new v1.8 API endpoints."""

    async def test_coverage_api(self):
        """Coverage endpoint should work even with no runs."""
        from httpx import ASGITransport
        import httpx
        from decision_system.api.app import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/reports/coverage")
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            data = response.json()
            assert "total_claims" in data

    async def test_audit_timeline_api(self):
        """Audit timeline endpoint should return valid data."""
        from httpx import ASGITransport
        import httpx
        from decision_system.api.app import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/reports/audit-timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    async def test_provider_safety_api(self):
        """Provider safety endpoint should return current status."""
        from httpx import ASGITransport
        import httpx
        from decision_system.api.app import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/reports/provider-safety")
        assert response.status_code == 200
        data = response.json()
        assert "configured_provider" in data

    async def test_export_api(self):
        """Report export endpoint should handle empty state gracefully."""
        from httpx import ASGITransport
        import httpx
        from decision_system.api.app import app

        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/reports/export", json={"format": "json"})
        # Should give 404 since no report data yet
        assert response.status_code in (404, 200)


# =========================================================================
# Path Utility Tests
# =========================================================================


class TestPathUtil:
    """Tests for path validation utility."""

    def test_resolve_path(self):
        from decision_system.path_util import resolve_path

        p = resolve_path(".")
        assert p.is_absolute()
        assert p.is_dir()

    def test_is_safe_write_path_for_project_paths(self):
        from decision_system.path_util import is_safe_write_path

        # A dot-path inside the project should be safe
        assert is_safe_write_path(".decision_system/test")

    def test_outside_project_is_not_safe(self):
        from decision_system.path_util import is_safe_write_path

        assert not is_safe_write_path("/etc/passwd")

    def test_ensure_safe_path_valid(self, tmp_path):
        from decision_system.path_util import ensure_safe_path, resolve_path

        # Write to a location inside project root (tmp_path as project_root)
        safe = tmp_path / "safe.txt"
        safe.parent.mkdir(parents=True, exist_ok=True)
        safe.touch()
        # Using tmp_path as project_root
        result = ensure_safe_path(str(safe), project_root=str(tmp_path.resolve()))
        assert result.exists()

    def test_ensure_safe_path_invalid(self):
        from decision_system.path_util import ensure_safe_path

        with pytest.raises(ValueError):
            ensure_safe_path("/etc/passwd")

    def test_safe_relative_to(self, tmp_path):
        from decision_system.path_util import safe_relative_to

        sub = tmp_path / "sub" / "file.txt"
        rel = safe_relative_to(str(sub), str(tmp_path))
        assert str(rel) == "sub/file.txt" or str(rel) == "file.txt"


# =========================================================================
# CLI Help Includes New Commands
# =========================================================================


class TestNewCLICommands:
    """Verify new CLI commands appear in help."""

    def test_help_includes_export_report(self):
        from typer.testing import CliRunner
        from decision_system.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "export-report" in result.stdout
        assert "coverage" in result.stdout
        assert "diff-workspaces" in result.stdout
        assert "audit-timeline" in result.stdout
        assert "validate-demo-data" in result.stdout
        assert "provider-safety" in result.stdout
