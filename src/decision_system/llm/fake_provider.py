"""Deterministic offline provider used by default in v0.1.

This provider does not call a real LLM. It turns retrieved evidence into
structured memos and claims so the rest of the workflow can be tested without
API keys or network access.
"""

from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk


class FakeProvider:
    """Offline provider that preserves evidence citations per chunk."""

    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo:
        """Create a deterministic technical memo from retrieved evidence."""

        if evidence:
            return AgentMemo(
                agent_name="technical_analyst",
                question=question,
                summary=f"Technical analysis is based on {len(evidence)} retrieved evidence chunk(s).",
                claims=[
                    f"Technical decision should account for {chunk.evidence_id}: {chunk.text}"
                    for chunk in evidence
                ],
                risks=[],
                options=["Proceed with a staged plan", "Delay until missing evidence is reviewed"],
                cited_evidence_ids=[chunk.evidence_id for chunk in evidence],
            )

        return AgentMemo(
            agent_name="technical_analyst",
            question=question,
            summary="No retrieved evidence is available for technical analysis.",
            claims=["Technical feasibility is unsupported by retrieved evidence."],
            risks=[],
            options=["Request more evidence before deciding"],
            cited_evidence_ids=[],
        )

    def risk_memo(
        self,
        question: str,
        evidence: list[EvidenceChunk],
        technical_memo: AgentMemo,
    ) -> AgentMemo:
        """Create a deterministic risk memo from retrieved evidence."""

        if evidence:
            return AgentMemo(
                agent_name="risk_analyst",
                question=question,
                summary=f"Risk review challenges assumptions using {len(evidence)} retrieved evidence chunk(s).",
                claims=[
                    f"Risk review should verify operational impact in {chunk.evidence_id}: {chunk.text}"
                    for chunk in evidence
                ],
                risks=["Validate rollback, downtime, and stakeholder impact before action."],
                options=technical_memo.options,
                cited_evidence_ids=[chunk.evidence_id for chunk in evidence],
            )

        return AgentMemo(
            agent_name="risk_analyst",
            question=question,
            summary="Risk review found no retrieved evidence to support a confident decision.",
            claims=["Risk assessment is unsupported by retrieved evidence."],
            risks=["Decision confidence is low because no evidence was retrieved."],
            options=["Request more evidence before deciding"],
            cited_evidence_ids=[],
        )

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        """Convert memo claims into claim records with per-chunk citations."""

        claims: list[Claim] = []
        claim_number = 1

        for memo in memos:
            claim_type = "risk" if "risk" in memo.agent_name else "technical"
            for index, claim_text in enumerate(memo.claims):
                # Keep one claim tied to one chunk so verification can produce a
                # mix of verified and contradicted statuses in the same run.
                evidence_ids = (
                    [memo.cited_evidence_ids[index]]
                    if index < len(memo.cited_evidence_ids)
                    else []
                )
                claims.append(
                    Claim(
                        claim_id=f"claim-{claim_number:04d}",
                        run_id=run_id,
                        source_agent=memo.agent_name,
                        claim_text=claim_text,
                        claim_type=claim_type,
                        evidence_ids=evidence_ids,
                    )
                )
                claim_number += 1

        return claims

    def write_report(
        self,
        question: str,
        claims: list[Claim],
        evidence: list[EvidenceChunk],
    ) -> DecisionReport:
        """Reject provider-side report writing in v0.1.

        Report generation must go through the local renderer so it consumes the
        claim ledger rather than raw provider prose.
        """

        raise NotImplementedError("FakeProvider report writing is handled by the report renderer in v0.1.")
