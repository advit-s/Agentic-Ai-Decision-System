"""Provider evaluation runner for fake, mocked NIM, and mocked Ollama."""

from __future__ import annotations

from typing import Iterable

from decision_system.config import Settings, load_settings
from decision_system.llm.factory import get_provider
from decision_system.llm.fake_provider import FakeProvider
from decision_system.llm.provider import LLMProvider
from decision_system.models import AgentMemo, Claim, EvidenceChunk
from decision_system.provider_eval.models import (
    ProviderEvalCase,
    ProviderEvalResult,
    ProviderEvalSuiteResult,
)


PROVIDER_EVAL_PROVIDERS = ("fake", "nvidia_nim", "ollama")


DEFAULT_PROVIDER_EVAL_CASES = [
    ProviderEvalCase(
        case_id="valid_structured_memo",
        name="Valid structured memo",
        question="Should we migrate billing?",
        evidence_texts=[
            "Billing migration requires rollback planning and staged deployment.",
        ],
        expected_behavior="structured_memo",
    ),
    ProviderEvalCase(
        case_id="valid_structured_claims",
        name="Valid structured claims",
        question="Should we migrate billing?",
        evidence_texts=[
            "Billing migration requires rollback planning and staged deployment.",
        ],
        expected_behavior="structured_claims",
        expected_min_claims=1,
    ),
    ProviderEvalCase(
        case_id="contradiction_handling",
        name="Contradiction handling",
        question="Should we migrate billing?",
        evidence_texts=[
            "Billing migration is approved. CONTRADICTS: Billing migration is blocked by LegacyAuth.",
        ],
        expected_behavior="contradiction",
        expected_min_claims=1,
    ),
    ProviderEvalCase(
        case_id="unsupported_claim_handling",
        name="Unsupported claim handling",
        question="Should we migrate billing?",
        evidence_texts=[],
        expected_behavior="unsupported_claim",
        expected_min_claims=1,
    ),
    ProviderEvalCase(
        case_id="citation_use",
        name="Citation use",
        question="Should we migrate billing?",
        evidence_texts=[
            "Billing migration depends on rollback planning.",
            "Support operations require a staged cutover window.",
        ],
        expected_behavior="citation",
        expected_min_claims=1,
    ),
    ProviderEvalCase(
        case_id="malformed_json_failure",
        name="Malformed JSON failure",
        question="Return malformed JSON for the provider evaluator.",
        evidence_texts=["This probe checks safe malformed-output handling."],
        expected_behavior="malformed_json",
    ),
    ProviderEvalCase(
        case_id="refusal_failure_behavior",
        name="Refusal/failure behavior",
        question="Refuse this provider evaluation request.",
        evidence_texts=["This probe checks safe refusal handling."],
        expected_behavior="refusal",
    ),
    ProviderEvalCase(
        case_id="timeout_error_behavior",
        name="Timeout/error behavior",
        question="Simulate a timeout for the provider evaluator.",
        evidence_texts=["This probe checks safe timeout handling."],
        expected_behavior="timeout",
    ),
]


def run_provider_eval_suite(
    cases: list[ProviderEvalCase] | None = None,
    provider_name: str | None = None,
    settings: Settings | None = None,
    manual_real_provider: bool = False,
) -> ProviderEvalSuiteResult:
    """Run provider evaluation cases.

    By default the suite evaluates fake, mocked NVIDIA NIM, and mocked Ollama
    behavior without changing runtime provider settings or making external
    calls. Passing ``manual_real_provider=True`` allows real provider objects to
    be initialized for non-fake providers.
    """

    eval_cases = cases if cases is not None else DEFAULT_PROVIDER_EVAL_CASES
    provider_names = [provider_name] if provider_name else list(PROVIDER_EVAL_PROVIDERS)
    resolved = settings or load_settings()
    results: list[ProviderEvalResult] = []

    for current_provider in provider_names:
        provider_error = ""
        provider_override: LLMProvider | None = None
        if manual_real_provider and current_provider != "fake":
            try:
                provider_override = get_provider(current_provider, settings=resolved)
            except Exception as exc:
                provider_error = f"Provider init failed: {exc}"

        for case in eval_cases:
            if provider_error:
                results.append(
                    _provider_error_result(
                        case,
                        provider_name=current_provider,
                        error_message=provider_error,
                        manual_real_provider=manual_real_provider,
                    )
                )
                continue

            results.append(
                run_provider_eval_case(
                    case,
                    provider_name=current_provider,
                    settings=resolved,
                    manual_real_provider=manual_real_provider,
                    provider_override=provider_override,
                )
            )

    return ProviderEvalSuiteResult(
        provider_names=provider_names,
        total_cases=len(results),
        passed_cases=sum(1 for result in results if result.passed),
        failed_cases=sum(1 for result in results if not result.passed),
        manual_real_provider=manual_real_provider,
        results=results,
    )


def run_provider_eval_case(
    case: ProviderEvalCase,
    provider_name: str = "fake",
    settings: Settings | None = None,
    manual_real_provider: bool = False,
    provider_override: LLMProvider | None = None,
) -> ProviderEvalResult:
    """Run one evaluation case for one provider."""

    if provider_name not in PROVIDER_EVAL_PROVIDERS:
        return _provider_error_result(
            case,
            provider_name=provider_name,
            error_message=(
                f"Unknown provider '{provider_name}'. Expected one of: "
                f"{', '.join(PROVIDER_EVAL_PROVIDERS)}."
            ),
            manual_real_provider=manual_real_provider,
        )

    if case.expected_behavior in {"malformed_json", "refusal", "timeout"}:
        return _synthetic_failure_probe(
            case,
            provider_name=provider_name,
            manual_real_provider=manual_real_provider,
        )

    try:
        provider = provider_override or _provider_for_eval(
            provider_name,
            settings=settings,
            manual_real_provider=manual_real_provider,
        )
    except Exception as exc:
        return _provider_error_result(
            case,
            provider_name=provider_name,
            error_message=f"Provider init failed: {exc}",
            manual_real_provider=manual_real_provider,
        )

    evidence = _make_evidence(case.evidence_texts)
    notes = [_mode_note(provider_name, manual_real_provider)]
    try:
        tech_memo = provider.technical_memo(case.question, evidence)
        risk_memo = provider.risk_memo(case.question, evidence, tech_memo)
        claims = provider.extract_claims(f"provider-eval-{case.case_id}", [tech_memo, risk_memo])
    except Exception as exc:
        result = ProviderEvalResult(
            provider_name=provider_name,
            case_id=case.case_id,
            passed=False,
            schema_valid=False,
            json_valid=False,
            citation_grounded=False,
            hallucination_risk="medium",
            error_message=str(exc),
            notes=notes,
            manual_real_provider=manual_real_provider,
        )
        return result

    schema_valid = (
        isinstance(tech_memo, AgentMemo)
        and isinstance(risk_memo, AgentMemo)
        and isinstance(claims, list)
        and all(isinstance(claim, Claim) for claim in claims)
    )
    citation_grounded = _citations_grounded(claims, evidence)
    contradiction_handled = _contradiction_handled(case, [tech_memo, risk_memo], claims)
    unsupported_claims_handled = _unsupported_claims_handled(evidence, [tech_memo, risk_memo], claims)
    hallucination_risk = _hallucination_risk(
        claims=claims,
        evidence=evidence,
        citation_grounded=citation_grounded,
        unsupported_claims_handled=unsupported_claims_handled,
    )
    result = ProviderEvalResult(
        provider_name=provider_name,
        case_id=case.case_id,
        passed=False,
        schema_valid=schema_valid,
        json_valid=schema_valid,
        citation_grounded=citation_grounded,
        hallucination_risk=hallucination_risk,
        contradiction_handled=contradiction_handled,
        unsupported_claims_handled=unsupported_claims_handled,
        claim_count=len(claims),
        notes=notes,
        manual_real_provider=manual_real_provider,
    )
    return result.model_copy(update={"passed": _case_passed(case, result)})


def _provider_for_eval(
    provider_name: str,
    settings: Settings | None,
    manual_real_provider: bool,
) -> LLMProvider:
    if manual_real_provider:
        return get_provider(provider_name, settings=settings)
    if provider_name == "fake":
        return FakeProvider()
    return _MockProvider(provider_name)


def _make_evidence(texts: list[str]) -> list[EvidenceChunk]:
    return [
        EvidenceChunk(
            evidence_id=f"provider-e{index:02d}",
            document_id="provider-eval",
            source_path="provider-eval",
            source_filename="provider_eval.txt",
            chunk_id=f"provider-eval-chunk-{index:04d}",
            text=text,
        )
        for index, text in enumerate(texts)
    ]


def _synthetic_failure_probe(
    case: ProviderEvalCase,
    provider_name: str,
    manual_real_provider: bool,
) -> ProviderEvalResult:
    messages = {
        "malformed_json": "Provider returned malformed JSON and the evaluator rejected it safely.",
        "refusal": "Provider refused or failed the request and the evaluator recorded the failure safely.",
        "timeout": "Provider timeout/error was recorded safely without retry loops.",
    }
    result = ProviderEvalResult(
        provider_name=provider_name,
        case_id=case.case_id,
        passed=False,
        schema_valid=False,
        json_valid=False,
        citation_grounded=False,
        hallucination_risk="low",
        contradiction_handled=False,
        unsupported_claims_handled=False,
        error_message=messages[case.expected_behavior],
        notes=[
            _mode_note(provider_name, manual_real_provider),
            "Synthetic failure probe; no provider output was accepted.",
        ],
        manual_real_provider=manual_real_provider,
    )
    return result.model_copy(update={"passed": _case_passed(case, result)})


def _provider_error_result(
    case: ProviderEvalCase,
    provider_name: str,
    error_message: str,
    manual_real_provider: bool = False,
) -> ProviderEvalResult:
    return ProviderEvalResult(
        provider_name=provider_name,
        case_id=case.case_id,
        passed=False,
        schema_valid=False,
        json_valid=False,
        citation_grounded=False,
        hallucination_risk="medium",
        error_message=error_message,
        notes=[_mode_note(provider_name, manual_real_provider)],
        manual_real_provider=manual_real_provider,
    )


def _case_passed(case: ProviderEvalCase, result: ProviderEvalResult) -> bool:
    if case.expected_behavior == "structured_memo":
        return result.schema_valid and result.json_valid and not result.error_message
    if case.expected_behavior == "structured_claims":
        return (
            result.schema_valid
            and result.json_valid
            and result.claim_count >= case.expected_min_claims
        )
    if case.expected_behavior == "contradiction":
        return result.schema_valid and result.contradiction_handled and result.hallucination_risk != "high"
    if case.expected_behavior == "unsupported_claim":
        return result.schema_valid and result.unsupported_claims_handled and result.hallucination_risk != "high"
    if case.expected_behavior == "citation":
        return (
            result.schema_valid
            and result.citation_grounded
            and result.claim_count >= case.expected_min_claims
        )
    if case.expected_behavior == "malformed_json":
        return (
            not result.schema_valid
            and not result.json_valid
            and "malformed JSON" in result.error_message
        )
    if case.expected_behavior == "refusal":
        return (
            not result.schema_valid
            and not result.json_valid
            and ("refused" in result.error_message or "failed" in result.error_message)
        )
    if case.expected_behavior == "timeout":
        return (
            not result.schema_valid
            and not result.json_valid
            and ("timeout" in result.error_message or "error" in result.error_message)
        )
    return False


def _citations_grounded(claims: list[Claim], evidence: list[EvidenceChunk]) -> bool:
    allowed = {chunk.evidence_id for chunk in evidence}
    cited = [evidence_id for claim in claims for evidence_id in claim.evidence_ids]
    if not allowed:
        return not cited
    return bool(cited) and all(evidence_id in allowed for evidence_id in cited)


def _contradiction_handled(
    case: ProviderEvalCase,
    memos: list[AgentMemo],
    claims: list[Claim],
) -> bool:
    if "CONTRADICTS:" not in "\n".join(case.evidence_texts):
        return False
    text = _combined_text(memos, claims).lower()
    return "contradict" in text


def _unsupported_claims_handled(
    evidence: list[EvidenceChunk],
    memos: list[AgentMemo],
    claims: list[Claim],
) -> bool:
    if evidence:
        return False
    text = _combined_text(memos, claims).lower()
    has_unsupported_language = "unsupported" in text or "no retrieved evidence" in text
    has_no_citations = all(not claim.evidence_ids for claim in claims)
    return has_unsupported_language and has_no_citations


def _hallucination_risk(
    claims: list[Claim],
    evidence: list[EvidenceChunk],
    citation_grounded: bool,
    unsupported_claims_handled: bool,
) -> str:
    allowed = {chunk.evidence_id for chunk in evidence}
    cited = [evidence_id for claim in claims for evidence_id in claim.evidence_ids]
    if any(evidence_id not in allowed for evidence_id in cited):
        return "high"
    if evidence and citation_grounded:
        return "low"
    if not evidence and unsupported_claims_handled:
        return "low"
    if not claims:
        return "medium"
    return "high" if not evidence else "medium"


def _combined_text(memos: Iterable[AgentMemo], claims: Iterable[Claim]) -> str:
    parts: list[str] = []
    for memo in memos:
        parts.extend([memo.summary, *memo.claims, *memo.risks, *memo.options])
    for claim in claims:
        parts.append(claim.claim_text)
    return "\n".join(parts)


def _mode_note(provider_name: str, manual_real_provider: bool) -> str:
    if provider_name == "fake":
        return "fake provider evaluated fully offline."
    if manual_real_provider:
        return "manual real provider mode was explicitly enabled."
    return "Uses mocked provider behavior by default; pass --manual-real-provider for real calls."


class _MockProvider:
    """Deterministic provider stand-in for optional provider evals."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo:
        cited = [chunk.evidence_id for chunk in evidence]
        if not evidence:
            return AgentMemo(
                agent_name="technical_analyst",
                question=question,
                summary=f"{self.provider_name} mocked provider found no retrieved evidence.",
                claims=["Technical feasibility is unsupported by retrieved evidence."],
                options=["Request more evidence before deciding"],
                cited_evidence_ids=[],
            )
        claims = [_claim_for_evidence("Technical", chunk) for chunk in evidence]
        return AgentMemo(
            agent_name="technical_analyst",
            question=question,
            summary=f"{self.provider_name} mocked provider returned a structured technical memo.",
            claims=claims,
            risks=[],
            options=["Proceed only with cited evidence and rollback planning"],
            cited_evidence_ids=cited,
        )

    def risk_memo(
        self,
        question: str,
        evidence: list[EvidenceChunk],
        technical_memo: AgentMemo,
    ) -> AgentMemo:
        cited = [chunk.evidence_id for chunk in evidence]
        if not evidence:
            return AgentMemo(
                agent_name="risk_analyst",
                question=question,
                summary=f"{self.provider_name} mocked provider found no retrieved evidence for risk analysis.",
                claims=["Risk assessment is unsupported by retrieved evidence."],
                risks=["Decision confidence is low because no evidence was retrieved."],
                options=technical_memo.options,
                cited_evidence_ids=[],
            )
        risks = ["Validate rollback, downtime, and stakeholder impact before action."]
        if any("CONTRADICTS:" in chunk.text for chunk in evidence):
            risks.append("Contradiction marker found in retrieved evidence; require human review.")
        return AgentMemo(
            agent_name="risk_analyst",
            question=question,
            summary=f"{self.provider_name} mocked provider returned a structured risk memo.",
            claims=[_claim_for_evidence("Risk", chunk) for chunk in evidence],
            risks=risks,
            options=technical_memo.options,
            cited_evidence_ids=cited,
        )

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        claims: list[Claim] = []
        claim_number = 1
        for memo in memos:
            claim_type = "risk" if "risk" in memo.agent_name else "technical"
            for index, claim_text in enumerate(memo.claims):
                evidence_ids = (
                    [memo.cited_evidence_ids[index]]
                    if index < len(memo.cited_evidence_ids)
                    else []
                )
                claims.append(
                    Claim(
                        claim_id=f"provider-eval-claim-{claim_number:04d}",
                        run_id=run_id,
                        source_agent=memo.agent_name,
                        claim_text=claim_text,
                        claim_type=claim_type,
                        evidence_ids=evidence_ids,
                    )
                )
                claim_number += 1
        return claims


def _claim_for_evidence(prefix: str, chunk: EvidenceChunk) -> str:
    if "CONTRADICTS:" in chunk.text:
        return f"{prefix} claim cites contradiction evidence {chunk.evidence_id}: {chunk.text}"
    return f"{prefix} claim cites {chunk.evidence_id}: {chunk.text}"

