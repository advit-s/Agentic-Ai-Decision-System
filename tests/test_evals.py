import json

from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.evals.runner import load_eval_cases, run_eval_case


def test_eval_cases_load_correctly():
    cases = load_eval_cases()

    case_ids = {case.case_id for case in cases}
    assert case_ids == {
        "billing_migration",
        "empty_context",
        "contradiction_case",
    }
    assert all(case.question for case in cases)
    assert all(case.expectations.required_report_sections for case in cases)


def test_billing_case_passes():
    case = next(case for case in load_eval_cases() if case.case_id == "billing_migration")

    result = run_eval_case(case)

    assert result.passed
    assert result.metrics.verified_claims >= 1
    assert "billing.md" in result.metrics.source_filenames
    assert result.metrics.evidence_citations >= 1
    assert not result.failures


def test_contradiction_case_detects_contradiction():
    case = next(case for case in load_eval_cases() if case.case_id == "contradiction_case")

    result = run_eval_case(case)

    assert result.passed
    assert result.metrics.contradicted_claims >= 1
    assert result.metrics.human_review_required
    assert result.metrics.confidence_level == "low"


def test_empty_context_stays_conservative():
    case = next(case for case in load_eval_cases() if case.case_id == "empty_context")

    result = run_eval_case(case)

    assert result.passed
    assert result.metrics.confidence_level == "low"
    assert result.metrics.unsupported_claims >= 1
    assert result.metrics.human_review_required


def test_cli_eval_exits_0_when_all_cases_pass():
    result = CliRunner().invoke(app, ["eval"])

    assert result.exit_code == 0
    assert "Evaluation Report" in result.output
    assert "billing_migration: PASS" in result.output
    assert "empty_context: PASS" in result.output
    assert "contradiction_case: PASS" in result.output


def test_cli_eval_json_emits_structured_json():
    result = CliRunner().invoke(app, ["eval", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["passed"] is True
    assert {case["case_id"] for case in payload["cases"]} == {
        "billing_migration",
        "empty_context",
        "contradiction_case",
    }
    assert all("metrics" in case for case in payload["cases"])
