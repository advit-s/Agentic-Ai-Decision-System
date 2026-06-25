"""Provider experiment inspector and renderer."""

from __future__ import annotations

from decision_system.provider_experiments.models import ProviderExperimentSuiteResult


def inspect_provider_experiments(suite: ProviderExperimentSuiteResult) -> dict:
    """Return a summary dict for a provider experiment suite result."""
    return {
        "provider_name": suite.provider_name,
        "total_cases": suite.total_cases,
        "passed_cases": suite.passed_cases,
        "failed_cases": suite.failed_cases,
        "skipped_cases": getattr(suite, "skipped_cases", 0),
        "results": [
            {
                "case_id": r.case_id,
                "status": r.status,
                "technical_memo_valid": r.technical_memo_valid,
                "risk_memo_valid": r.risk_memo_valid,
                "claims_valid": r.claims_valid,
                "claim_count": r.claim_count,
                "errors": r.errors,
            }
            for r in suite.results
        ],
    }


def render_provider_experiments(suite: ProviderExperimentSuiteResult) -> str:
    """Render a provider experiment suite as a human-readable string."""
    lines = [
        f"# Provider Experiment: {suite.provider_name}",
        "",
        f"Total: {suite.total_cases} | Passed: {suite.passed_cases} | Failed: {suite.failed_cases} | Skipped: {getattr(suite, 'skipped_cases', 0)}",
        "",
    ]
    for result in suite.results:
        status_icon = (
            "PASS"
            if result.status == "passed"
            else "SKIP"
            if result.status == "skipped"
            else "FAIL"
        )
        lines.append(
            f"- [{status_icon}] {result.case_id}: "
            f"tech={result.technical_memo_valid} risk={result.risk_memo_valid} "
            f"claims={result.claims_valid} (count={result.claim_count})"
        )
        for error in result.errors:
            lines.append(f"  - ERROR: {error}")
    return "\n".join(lines)
