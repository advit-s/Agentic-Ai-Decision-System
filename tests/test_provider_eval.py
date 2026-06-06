"""Tests for the v0.7.1 provider evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.provider_eval.inspector import render_provider_eval_suite
from decision_system.provider_eval.models import (
    ProviderEvalCase,
    ProviderEvalResult,
    ProviderEvalSuiteResult,
    ProviderOutputQuality,
)
from decision_system.provider_eval.runner import (
    DEFAULT_PROVIDER_EVAL_CASES,
    PROVIDER_EVAL_PROVIDERS,
    run_provider_eval_case,
    run_provider_eval_suite,
)
from decision_system.provider_eval.store import (
    DEFAULT_PROVIDER_EVAL_RESULTS_PATH,
    load_provider_eval_results,
    save_provider_eval_results,
)


runner = CliRunner()


def test_provider_eval_models_have_expected_defaults():
    case = ProviderEvalCase(
        case_id="valid_structured_memo",
        name="Valid structured memo",
        question="Should we migrate billing?",
        evidence_texts=["Billing migration requires rollback planning."],
        expected_behavior="structured_memo",
    )
    quality = ProviderOutputQuality()
    result = ProviderEvalResult(
        provider_name="fake",
        case_id=case.case_id,
        passed=True,
        schema_valid=True,
        json_valid=True,
        citation_grounded=True,
        hallucination_risk="low",
    )

    assert case.provider_names == ["fake", "nvidia_nim", "ollama"]
    assert quality.schema_valid is False
    assert quality.hallucination_risk == "medium"
    assert result.error_message == ""
    assert result.notes == []


def test_default_provider_eval_cases_cover_required_behaviors():
    case_ids = {case.case_id for case in DEFAULT_PROVIDER_EVAL_CASES}

    assert case_ids == {
        "valid_structured_memo",
        "valid_structured_claims",
        "contradiction_handling",
        "unsupported_claim_handling",
        "citation_use",
        "malformed_json_failure",
        "refusal_failure_behavior",
        "timeout_error_behavior",
    }


def test_fake_provider_eval_runs_fully_offline_and_passes_all_cases():
    suite = run_provider_eval_suite(provider_name="fake")

    assert suite.provider_names == ["fake"]
    assert suite.total_cases == len(DEFAULT_PROVIDER_EVAL_CASES)
    assert suite.passed_cases == suite.total_cases
    assert suite.failed_cases == 0
    assert all(result.provider_name == "fake" for result in suite.results)
    assert all(result.passed for result in suite.results)


def test_default_provider_eval_compares_fake_and_mocked_optional_providers():
    suite = run_provider_eval_suite()

    assert suite.provider_names == list(PROVIDER_EVAL_PROVIDERS)
    assert suite.total_cases == len(DEFAULT_PROVIDER_EVAL_CASES) * 3
    assert suite.passed_cases == suite.total_cases
    assert suite.manual_real_provider is False
    assert {result.provider_name for result in suite.results} == {
        "fake",
        "nvidia_nim",
        "ollama",
    }
    assert any("mocked provider" in " ".join(result.notes) for result in suite.results)


def test_mocked_ollama_and_nim_do_not_require_configuration(monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    nim_suite = run_provider_eval_suite(provider_name="nvidia_nim")
    ollama_suite = run_provider_eval_suite(provider_name="ollama")

    assert nim_suite.failed_cases == 0
    assert ollama_suite.failed_cases == 0


def test_malformed_json_case_is_recorded_as_safe_expected_failure():
    case = next(
        case
        for case in DEFAULT_PROVIDER_EVAL_CASES
        if case.case_id == "malformed_json_failure"
    )

    result = run_provider_eval_case(case, provider_name="ollama")

    assert result.passed is True
    assert result.json_valid is False
    assert result.schema_valid is False
    assert "malformed JSON" in result.error_message
    assert result.hallucination_risk == "low"


def test_citation_case_scores_grounded_citations():
    case = next(
        case
        for case in DEFAULT_PROVIDER_EVAL_CASES
        if case.case_id == "citation_use"
    )

    result = run_provider_eval_case(case, provider_name="nvidia_nim")

    assert result.passed is True
    assert result.citation_grounded is True
    assert result.hallucination_risk == "low"


def test_contradiction_and_unsupported_cases_score_specific_handling():
    contradiction = next(
        case
        for case in DEFAULT_PROVIDER_EVAL_CASES
        if case.case_id == "contradiction_handling"
    )
    unsupported = next(
        case
        for case in DEFAULT_PROVIDER_EVAL_CASES
        if case.case_id == "unsupported_claim_handling"
    )

    contradiction_result = run_provider_eval_case(contradiction, provider_name="fake")
    unsupported_result = run_provider_eval_case(unsupported, provider_name="fake")

    assert contradiction_result.contradiction_handled is True
    assert unsupported_result.unsupported_claims_handled is True


def test_unknown_provider_is_rejected():
    suite = run_provider_eval_suite(provider_name="ghost")

    assert suite.failed_cases == len(DEFAULT_PROVIDER_EVAL_CASES)
    assert all(result.provider_name == "ghost" for result in suite.results)
    assert all("Unknown provider" in result.error_message for result in suite.results)


def test_save_and_load_provider_eval_results(tmp_path: Path):
    suite = ProviderEvalSuiteResult(
        provider_names=["fake"],
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        results=[
            ProviderEvalResult(
                provider_name="fake",
                case_id="valid_structured_memo",
                passed=True,
                schema_valid=True,
                json_valid=True,
                citation_grounded=True,
                hallucination_risk="low",
            )
        ],
    )

    output_path = tmp_path / "provider_eval_results.json"
    saved = save_provider_eval_results(suite, output_path=output_path)
    loaded = load_provider_eval_results(output_path=output_path)

    assert saved == output_path.resolve()
    assert loaded is not None
    assert loaded.saved_result_path == str(output_path.resolve())
    assert loaded.provider_names == ["fake"]


def test_load_provider_eval_results_returns_none_when_missing(tmp_path: Path):
    assert load_provider_eval_results(tmp_path / "missing.json") is None


def test_render_provider_eval_suite_includes_scores():
    suite = ProviderEvalSuiteResult(
        provider_names=["fake"],
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        results=[
            ProviderEvalResult(
                provider_name="fake",
                case_id="citation_use",
                passed=True,
                schema_valid=True,
                json_valid=True,
                citation_grounded=True,
                hallucination_risk="low",
            )
        ],
    )

    output = render_provider_eval_suite(suite)

    assert "# Provider Evaluation" in output
    assert "fake/citation_use: PASS" in output
    assert "schema=True" in output
    assert "json=True" in output
    assert "citation=True" in output


def test_cli_eval_providers_default_exits_zero():
    result = runner.invoke(app, ["eval-providers"])

    assert result.exit_code == 0
    assert "# Provider Evaluation" in result.output
    assert "Providers: fake, nvidia_nim, ollama" in result.output
    assert "Failed: 0" in result.output


def test_cli_eval_providers_single_provider_exits_zero():
    result = runner.invoke(app, ["eval-providers", "--provider", "ollama"])

    assert result.exit_code == 0
    assert "Providers: ollama" in result.output
    assert "ollama/valid_structured_memo: PASS" in result.output
    assert "fake/valid_structured_memo" not in result.output


def test_cli_eval_providers_json_outputs_structured_json():
    result = runner.invoke(app, ["eval-providers", "--provider", "fake", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["provider_names"] == ["fake"]
    assert payload["failed_cases"] == 0
    assert payload["manual_real_provider"] is False
    assert payload["results"][0]["provider_name"] == "fake"


def test_cli_eval_providers_save_results_writes_fixed_ignored_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["eval-providers", "--provider", "fake", "--save-results"])

    assert result.exit_code == 0
    output_path = tmp_path / DEFAULT_PROVIDER_EVAL_RESULTS_PATH
    assert output_path.exists()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["saved_result_path"] == str(output_path.resolve())
    assert payload["provider_names"] == ["fake"]


def test_cli_inspect_provider_evals_reads_saved_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    eval_result = runner.invoke(app, ["eval-providers", "--provider", "fake", "--save-results"])
    inspect_result = runner.invoke(app, ["inspect-provider-evals"])

    assert eval_result.exit_code == 0
    assert inspect_result.exit_code == 0
    assert "# Provider Evaluation" in inspect_result.output
    assert "Providers: fake" in inspect_result.output


def test_cli_inspect_provider_evals_handles_missing_results(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["inspect-provider-evals"])

    assert result.exit_code == 0
    assert "No provider evaluation results found" in result.output


def test_manual_real_provider_flag_is_explicit(monkeypatch):
    calls: list[str] = []

    def fake_get_provider(provider_name, settings=None):
        calls.append(provider_name)
        raise RuntimeError("real provider should not be called in this test")

    monkeypatch.setattr("decision_system.provider_eval.runner.get_provider", fake_get_provider)

    mocked_suite = run_provider_eval_suite(provider_name="nvidia_nim")
    real_suite = run_provider_eval_suite(
        provider_name="nvidia_nim",
        manual_real_provider=True,
    )

    assert calls == ["nvidia_nim"]
    assert mocked_suite.failed_cases == 0
    assert real_suite.failed_cases == len(DEFAULT_PROVIDER_EVAL_CASES)
