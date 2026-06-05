"""Tests for the provider experiment module."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.config import Settings
from decision_system.llm.fake_provider import FakeProvider
from decision_system.llm.factory import get_provider
from decision_system.models import AgentMemo, Claim, EvidenceChunk
from decision_system.provider_experiments.models import (
    ProviderExperimentCase,
    ProviderExperimentResult,
    ProviderExperimentSuiteResult,
)
from decision_system.provider_experiments.runner import (
    _make_evidence,
    load_eval_cases,
    run_experiment_case,
    run_experiment_suite,
)
from decision_system.provider_experiments.store import (
    load_latest_provider_results,
    save_experiment_results,
)
from decision_system.provider_experiments.inspector import (
    inspect_provider_experiments,
    render_provider_experiments,
)

runner = CliRunner()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _settings(provider="fake", api_key="", model="", ollama_model="", **kw):
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider=provider,
        nvidia_api_key=api_key,
        nvidia_nim_model=model or "deepseek-ai/deepseek-v4-flash",
        nvidia_temperature=0.0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
        nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
        ollama_base_url="http://localhost:11434",
        ollama_model=ollama_model,
        ollama_temperature=0.0,
        ollama_max_tokens=2048,
        ollama_timeout_seconds=60,
        **kw,
    )


# ------------------------------------------------------------------
# Model tests
# ------------------------------------------------------------------

class TestProviderExperimentModels:
    def test_case_defaults(self):
        case = ProviderExperimentCase(
            case_id="c1", question="Q?", evidence_texts=["e1"],
        )
        assert case.case_id == "c1"
        assert case.provider_name == "fake"
        assert case.expected_min_claims == 0

    def test_result_defaults(self):
        result = ProviderExperimentResult(case_id="c1", provider_name="fake", status="passed")
        assert result.technical_memo_valid is False
        assert result.claim_count == 0
        assert isinstance(result.created_at, str) or result.created_at is not None

    def test_suite_result_defaults(self):
        suite = ProviderExperimentSuiteResult(provider_name="fake")
        assert suite.total_cases == 0
        assert suite.passed_cases == 0
        assert suite.skipped_cases == 0

    def test_suite_result_with_results(self):
        result = ProviderExperimentResult(
            case_id="c1", provider_name="fake", status="passed",
            technical_memo_valid=True, risk_memo_valid=True, claims_valid=True, claim_count=2,
        )
        suite = ProviderExperimentSuiteResult(
            provider_name="fake", total_cases=1, passed_cases=1, failed_cases=0, results=[result],
        )
        assert suite.passed_cases == 1
        assert len(suite.results) == 1


# ------------------------------------------------------------------
# _make_evidence helper
# ------------------------------------------------------------------

class TestMakeEvidence:
    def test_empty_texts(self):
        chunks = _make_evidence([])
        assert chunks == []

    def test_single_text(self):
        chunks = _make_evidence(["hello"])
        assert len(chunks) == 1
        assert chunks[0].text == "hello"
        assert chunks[0].evidence_id == "exp-e00"

    def test_multiple_texts(self):
        chunks = _make_evidence(["a", "b", "c"])
        assert len(chunks) == 3
        assert [c.evidence_id for c in chunks] == ["exp-e00", "exp-e01", "exp-e02"]
        assert [c.source_filename for c in chunks] == ["experiment.txt"] * 3


# ------------------------------------------------------------------
# run_experiment_case tests
# ------------------------------------------------------------------

class TestRunExperimentCase:
    def test_fake_provider_passes(self):
        case = ProviderExperimentCase(
            case_id="billing_migration",
            question="Should we migrate billing?",
            evidence_texts=["Billing migration requires rollback planning."],
            expected_min_claims=1,
            expected_evidence_ids=["exp-e00"],
            provider_name="fake",
        )
        settings = _settings()
        result = run_experiment_case(case, settings=settings)
        assert result.status == "passed"
        assert result.technical_memo_valid is True
        assert result.risk_memo_valid is True
        assert result.claims_valid is True
        assert result.claim_count >= 1
        assert result.errors == []

    def test_unknown_provider_skips(self):
        case = ProviderExperimentCase(
            case_id="c1", question="Q?", evidence_texts=[], provider_name="unknown",
        )
        result = run_experiment_case(case, settings=_settings())
        assert result.status == "skipped"
        assert result.errors != []

    def test_ollama_missing_model_skips(self):
        case = ProviderExperimentCase(
            case_id="c1", question="Q?", evidence_texts=[], provider_name="ollama",
        )
        result = run_experiment_case(case, settings=_settings(provider="ollama", ollama_model=""))
        assert result.status == "skipped"
        assert any("OLLAMA_MODEL" in e for e in result.errors)

    def test_empty_evidence_returns_nonempty_report(self):
        case = ProviderExperimentCase(
            case_id="empty_context", question="Should we migrate billing?", evidence_texts=[],
        )
        result = run_experiment_case(case, settings=_settings())
        assert result.status == "passed"
        assert result.technical_memo_valid is True
        # fake provider returns claims even with empty evidence
        assert result.claims_valid is True

    def test_expected_min_claims_is_enforced(self):
        case = ProviderExperimentCase(
            case_id="too_many_expected",
            question="Should we migrate billing?",
            evidence_texts=[],
            expected_min_claims=99,
            provider_name="fake",
        )

        result = run_experiment_case(case, settings=_settings())

        assert result.status == "failed"
        assert any("expected_min_claims" in error for error in result.errors)

    def test_expected_evidence_ids_are_enforced(self):
        case = ProviderExperimentCase(
            case_id="missing_expected_evidence",
            question="Should we migrate billing?",
            evidence_texts=["Billing migration requires rollback planning."],
            expected_min_claims=1,
            expected_evidence_ids=["missing-evidence"],
            provider_name="fake",
        )

        result = run_experiment_case(case, settings=_settings())

        assert result.status == "failed"
        assert any("expected evidence IDs" in error for error in result.errors)


# ------------------------------------------------------------------
# run_experiment_suite tests
# ------------------------------------------------------------------

class TestRunExperimentSuite:
    def test_suite_aggregation(self):
        cases = [
            ProviderExperimentCase(
                case_id="c1", question="Q1?", evidence_texts=["text1"], provider_name="fake",
            ),
            ProviderExperimentCase(
                case_id="c2", question="Q2?", evidence_texts=[], provider_name="fake",
            ),
        ]
        suite = run_experiment_suite(cases, provider_name="fake", settings=_settings())
        assert suite.total_cases == 2
        # Both should pass with fake provider
        assert suite.passed_cases >= 1
        assert suite.skipped_cases == 0

    def test_suite_overrides_case_provider(self):
        case = ProviderExperimentCase(
            case_id="c1", question="Q?", evidence_texts=[], provider_name="nvidia_nim",
        )
        # Suite forces provider to fake, so it should pass
        suite = run_experiment_suite([case], provider_name="fake", settings=_settings())
        assert suite.provider_name == "fake"
        assert suite.passed_cases == 1

    def test_suite_counts_skipped_cases(self):
        case = ProviderExperimentCase(
            case_id="c1",
            question="Q?",
            evidence_texts=[],
            provider_name="ollama",
        )

        suite = run_experiment_suite(
            [case],
            provider_name="ollama",
            settings=_settings(provider="ollama", ollama_model=""),
        )

        assert suite.total_cases == 1
        assert suite.skipped_cases == 1

    def test_suite_result_rejects_unknown_fields(self):
        with pytest.raises(ValidationError):
            ProviderExperimentSuiteResult(
                provider_name="fake",
                total_cases=1,
                passed_cases=1,
                failed_cases=0,
                skipped_cases=0,
                unknown_count=99,
            )


# ------------------------------------------------------------------
# load_eval_cases tests
# ------------------------------------------------------------------

class TestLoadEvalCases:
    def test_loads_provider_cases(self):
        cases = load_eval_cases()
        # Should find the 3 provider cases
        assert len(cases) >= 1
        case_ids = [c.case_id for c in cases]
        assert "billing_migration" in case_ids

    def test_cases_are_provider_experiment_case(self):
        cases = load_eval_cases()
        for case in cases:
            assert isinstance(case, ProviderExperimentCase)


# ------------------------------------------------------------------
# store tests
# ------------------------------------------------------------------

class TestProviderExperimentStore:
    def test_save_and_load(self, tmp_path):
        result = ProviderExperimentResult(
            case_id="c1", provider_name="fake", status="passed",
            technical_memo_valid=True, risk_memo_valid=True, claims_valid=True, claim_count=1,
        )
        suite = ProviderExperimentSuiteResult(
            provider_name="fake", total_cases=1, passed_cases=1, failed_cases=0, results=[result],
        )
        saved = save_experiment_results(suite, results_dir=tmp_path)
        assert saved.exists()

        loaded = load_latest_provider_results("fake", results_dir=tmp_path)
        assert loaded is not None
        assert loaded.provider_name == "fake"
        assert loaded.passed_cases == 1

    def test_no_results_returns_none(self, tmp_path):
        loaded = load_latest_provider_results("ghost", results_dir=tmp_path)
        assert loaded is None


# ------------------------------------------------------------------
# inspector tests
# ------------------------------------------------------------------

class TestProviderExperimentInspector:
    def test_inspect(self):
        result = ProviderExperimentResult(
            case_id="c1", provider_name="fake", status="passed",
            technical_memo_valid=True, claims_valid=True, claim_count=1,
        )
        suite = ProviderExperimentSuiteResult(
            provider_name="fake", total_cases=1, passed_cases=1, failed_cases=0, results=[result],
        )
        summary = inspect_provider_experiments(suite)
        assert summary["provider_name"] == "fake"
        assert summary["passed_cases"] == 1
        assert len(summary["results"]) == 1

    def test_render(self):
        result = ProviderExperimentResult(
            case_id="c1", provider_name="fake", status="passed",
        )
        suite = ProviderExperimentSuiteResult(
            provider_name="fake", total_cases=1, passed_cases=1, failed_cases=0, results=[result],
        )
        output = render_provider_experiments(suite)
        assert "fake" in output
        assert "PASS" in output


# ------------------------------------------------------------------
# CLI tests
# ------------------------------------------------------------------


class TestProviderExperimentCli:
    def test_provider_health_exits_zero(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        result = runner.invoke(app, ["provider-health"])

        assert result.exit_code == 0
        assert "fake: always available" in result.output
        assert "nvidia_nim: incomplete" in result.output
        assert "ollama: incomplete" in result.output

    def test_provider_smoke_fake_exits_zero(self):
        result = runner.invoke(app, ["provider-smoke", "--provider", "fake"])

        assert result.exit_code == 0
        assert "Smoke test PASSED" in result.output

    def test_eval_provider_fake_exits_zero(self):
        result = runner.invoke(app, ["eval-provider", "--provider", "fake"])

        assert result.exit_code == 0
        assert "# Provider Experiment: fake" in result.output
        assert "Passed: 3" in result.output

    def test_eval_provider_nim_missing_config_skips(self, monkeypatch):
        monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)

        result = runner.invoke(app, ["eval-provider", "--provider", "nvidia_nim"])

        assert result.exit_code == 0
        assert "Skipping: nvidia_nim is not configured" in result.output

    def test_eval_provider_ollama_missing_config_skips(self, monkeypatch):
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        result = runner.invoke(app, ["eval-provider", "--provider", "ollama"])

        assert result.exit_code == 0
        assert "Skipping: ollama is not configured" in result.output

    def test_eval_provider_unknown_provider_fails(self):
        result = runner.invoke(app, ["eval-provider", "--provider", "wizard"])

        assert result.exit_code == 1
        assert "Unknown provider 'wizard'" in result.output
