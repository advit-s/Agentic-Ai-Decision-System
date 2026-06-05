"""Provider experiment runner - executes cases against a selected provider."""

from __future__ import annotations

from pathlib import Path

from decision_system.config import Settings, load_settings
from decision_system.llm.factory import get_provider
from decision_system.models import AgentMemo, Claim, EvidenceChunk
from decision_system.provider_experiments.models import (
    ProviderExperimentCase,
    ProviderExperimentResult,
    ProviderExperimentSuiteResult,
)


def _make_evidence(texts: list[str]) -> list[EvidenceChunk]:
    """Convert raw text strings into EvidenceChunk objects for provider calls."""
    return [
        EvidenceChunk(
            evidence_id=f"exp-e{index:02d}",
            document_id="experiment",
            source_path="experiment",
            source_filename="experiment.txt",
            chunk_id=f"experiment-chunk-{index:04d}",
            text=text,
        )
        for index, text in enumerate(texts)
    ]


def run_experiment_case(
    case: ProviderExperimentCase,
    settings: Settings | None = None,
) -> ProviderExperimentResult:
    """Run one experiment case against the configured provider.

    Returns a result record with validity flags and any errors.
    """
    resolved = settings or load_settings()
    errors: list[str] = []
    technical_memo_valid = False
    risk_memo_valid = False
    claims_valid = False
    claim_count = 0
    status: str = "failed"
    tech_memo: AgentMemo | None = None
    risk_memo: AgentMemo | None = None

    try:
        provider = get_provider(case.provider_name, settings=resolved)
    except Exception as exc:
        errors.append(f"Provider init failed: {exc}")
        return ProviderExperimentResult(
            case_id=case.case_id,
            provider_name=case.provider_name,
            status="skipped",
            errors=errors,
        )

    evidence = _make_evidence(case.evidence_texts)

    # Technical memo
    try:
        tech_memo = provider.technical_memo(case.question, evidence)
        if isinstance(tech_memo, AgentMemo):
            technical_memo_valid = True
        else:
            errors.append(f"technical_memo returned {type(tech_memo).__name__}, expected AgentMemo")
    except Exception as exc:
        errors.append(f"technical_memo failed: {exc}")

    # Risk memo (needs tech memo even if tech failed)
    try:
        tech_for_risk = (
            tech_memo
            if isinstance(tech_memo, AgentMemo)
            else AgentMemo(
                agent_name="technical_analyst",
                question=case.question,
                summary="(stub for risk memo test)",
                claims=[],
                risks=[],
                options=[],
                cited_evidence_ids=[],
            )
        )
        risk_memo = provider.risk_memo(case.question, evidence, tech_for_risk)
        if isinstance(risk_memo, AgentMemo):
            risk_memo_valid = True
        else:
            errors.append(f"risk_memo returned {type(risk_memo).__name__}, expected AgentMemo")
    except Exception as exc:
        errors.append(f"risk_memo failed: {exc}")

    # Claim extraction
    claims: list[Claim] = []
    try:
        memos: list[AgentMemo] = []
        if isinstance(tech_memo, AgentMemo):
            memos.append(tech_memo)
        if isinstance(risk_memo, AgentMemo):
            memos.append(risk_memo)
        claims = provider.extract_claims(f"exp-{case.case_id}", memos)
        if isinstance(claims, list) and all(isinstance(c, Claim) for c in claims):
            claims_valid = True
            claim_count = len(claims)
        else:
            errors.append(f"extract_claims returned unexpected types")
    except Exception as exc:
        errors.append(f"extract_claims failed: {exc}")

    if claims_valid:
        if claim_count < case.expected_min_claims:
            errors.append(
                "claim_count below expected_min_claims: "
                f"{claim_count} < {case.expected_min_claims}"
            )
        actual_evidence_ids = {
            evidence_id
            for claim in claims
            for evidence_id in claim.evidence_ids
        }
        missing_evidence_ids = [
            evidence_id
            for evidence_id in case.expected_evidence_ids
            if evidence_id not in actual_evidence_ids
        ]
        if missing_evidence_ids:
            errors.append(
                "expected evidence IDs not cited by claims: "
                f"{missing_evidence_ids}"
            )

    if not errors:
        status = "passed"

    return ProviderExperimentResult(
        case_id=case.case_id,
        provider_name=case.provider_name,
        status=status,
        technical_memo_valid=technical_memo_valid,
        risk_memo_valid=risk_memo_valid,
        claims_valid=claims_valid,
        claim_count=claim_count,
        errors=errors,
    )


def run_experiment_suite(
    cases: list[ProviderExperimentCase],
    provider_name: str,
    settings: Settings | None = None,
) -> ProviderExperimentSuiteResult:
    """Run all cases against one provider and return the suite result."""
    results: list[ProviderExperimentResult] = []
    for case in cases:
        # Override case provider_name with the suite provider
        suite_case = case.model_copy(update={"provider_name": provider_name})
        results.append(run_experiment_case(suite_case, settings=settings))

    return ProviderExperimentSuiteResult(
        provider_name=provider_name,
        total_cases=len(results),
        passed_cases=sum(1 for r in results if r.status == "passed"),
        failed_cases=sum(1 for r in results if r.status == "failed"),
        skipped_cases=sum(1 for r in results if r.status == "skipped"),
        results=results,
    )


# ------------------------------------------------------------------
# Case loading
# ------------------------------------------------------------------

PROVIDER_CASES_DIR = (
    Path(__file__).resolve().parents[3] / "evals" / "provider_cases"
)


def load_eval_cases(cases_dir: Path | str = PROVIDER_CASES_DIR) -> list[ProviderExperimentCase]:
    """Load provider experiment case JSON files from disk."""
    case_path = Path(cases_dir)
    if not case_path.exists():
        return []
    cases = [
        ProviderExperimentCase.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(case_path.glob("*.json"))
    ]
    return sorted(cases, key=lambda case: case.case_id)
