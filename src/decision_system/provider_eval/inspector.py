"""Inspect and render provider evaluation results."""

from __future__ import annotations

from decision_system.provider_eval.models import ProviderEvalSuiteResult


def inspect_provider_eval_suite(suite: ProviderEvalSuiteResult) -> dict:
    """Return a JSON-friendly summary for provider evaluation results."""

    return {
        "provider_names": suite.provider_names,
        "total_cases": suite.total_cases,
        "passed_cases": suite.passed_cases,
        "failed_cases": suite.failed_cases,
        "manual_real_provider": suite.manual_real_provider,
        "saved_result_path": suite.saved_result_path,
        "results": [
            {
                "provider_name": result.provider_name,
                "case_id": result.case_id,
                "passed": result.passed,
                "schema_valid": result.schema_valid,
                "json_valid": result.json_valid,
                "citation_grounded": result.citation_grounded,
                "hallucination_risk": result.hallucination_risk,
                "contradiction_handled": result.contradiction_handled,
                "unsupported_claims_handled": result.unsupported_claims_handled,
                "error_message": result.error_message,
                "notes": result.notes,
            }
            for result in suite.results
        ],
    }


def render_provider_eval_suite(suite: ProviderEvalSuiteResult) -> str:
    """Render provider evaluation results as a compact Markdown report."""

    lines = [
        "# Provider Evaluation",
        "",
        f"Providers: {', '.join(suite.provider_names) or 'none'}",
        (
            f"Total: {suite.total_cases} | "
            f"Passed: {suite.passed_cases} | "
            f"Failed: {suite.failed_cases}"
        ),
        f"Manual real provider mode: {suite.manual_real_provider}",
        "",
        "## Results",
        "",
    ]
    for result in suite.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(
            f"- {result.provider_name}/{result.case_id}: {status} "
            f"(schema={result.schema_valid}, json={result.json_valid}, "
            f"citation={result.citation_grounded}, "
            f"hallucination={result.hallucination_risk}, "
            f"contradiction={result.contradiction_handled}, "
            f"unsupported={result.unsupported_claims_handled})"
        )
        if result.error_message:
            lines.append(f"  - ERROR: {result.error_message}")
        for note in result.notes:
            lines.append(f"  - NOTE: {note}")
    if suite.saved_result_path:
        lines.extend(["", f"Saved results: {suite.saved_result_path}"])
    return "\n".join(lines)

