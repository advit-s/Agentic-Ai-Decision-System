from decision_system.agents.base import default_provider
from decision_system.llm.provider import LLMProvider
from decision_system.models import AgentMemo, EvidenceChunk


def run_technical_analysis(
    question: str,
    evidence: list[EvidenceChunk],
    provider: LLMProvider | None = None,
) -> AgentMemo:
    selected_provider = provider or default_provider()
    return selected_provider.technical_memo(question, evidence)
