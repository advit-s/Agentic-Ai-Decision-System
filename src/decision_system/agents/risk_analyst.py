from decision_system.agents.base import default_provider
from decision_system.llm.provider import LLMProvider
from decision_system.models import AgentMemo, EvidenceChunk


def run_risk_analysis(
    question: str,
    evidence: list[EvidenceChunk],
    technical_memo: AgentMemo,
    provider: LLMProvider | None = None,
) -> AgentMemo:
    selected_provider = provider or default_provider()
    return selected_provider.risk_memo(question, evidence, technical_memo)
