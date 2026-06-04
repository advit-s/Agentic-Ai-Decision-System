from typing import TypedDict

from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk, VerificationResult


class WorkflowState(TypedDict, total=False):
    run_id: str
    question: str
    top_k: int
    provider: str
    retrieved_evidence: list[EvidenceChunk]
    technical_memo: AgentMemo
    risk_memo: AgentMemo
    claims: list[Claim]
    verification_results: list[VerificationResult]
    final_report: DecisionReport
    errors: list[str]
