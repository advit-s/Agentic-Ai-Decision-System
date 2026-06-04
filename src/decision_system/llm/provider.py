"""Provider protocol for bounded analyst behavior.

The workflow depends on this shape instead of a specific model vendor. The
`FakeProvider` remains the default for offline tests and local smoke runs.
"""

from typing import Protocol

from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk


class LLMProvider(Protocol):
    """Protocol every decision-system provider must satisfy."""

    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo:
        """Return a structured technical memo for the question and evidence."""

        ...

    def risk_memo(
        self,
        question: str,
        evidence: list[EvidenceChunk],
        technical_memo: AgentMemo,
    ) -> AgentMemo:
        """Return a structured risk/red-team memo."""

        ...

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        """Convert structured memos into claim-ledger records."""

        ...

    def write_report(
        self,
        question: str,
        claims: list[Claim],
        evidence: list[EvidenceChunk],
    ) -> DecisionReport:
        """Optional provider report method; the local renderer owns reports."""

        ...
