"""Shared typed models for evidence, claims, memos, and reports.

These Pydantic models are the contracts between retrieval, bounded agents,
verification, and report generation. Keeping these shapes explicit is what
lets v0.1 avoid passing unstructured agent chat into the final report.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


ClaimStatus = Literal["pending", "verified", "unsupported", "contradicted"]
ConfidenceLevel = Literal["low", "medium", "high"]


class EvidenceChunk(BaseModel):
    """A retrievable document chunk with citation metadata.

    Inputs are created by the chunker or retriever. The model carries source
    filename and chunk IDs so later claims can cite exact evidence rather than
    vague document references.
    """

    evidence_id: str
    document_id: str
    source_path: str
    source_filename: str
    chunk_id: str
    text: str
    score: float | None = None


class AgentMemo(BaseModel):
    """Structured output from a bounded analyst role.

    v0.1 agents return memos instead of free-form conversations. Claims and
    citations from these memos are converted into the claim ledger before the
    report is written.
    """

    agent_name: str
    question: str
    summary: str
    claims: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    """A material statement that must be verified before final synthesis.

    Claims preserve their source agent, evidence links, status, confidence, and
    verification notes. Contradicted claims remain in the ledger for auditability.
    """

    claim_id: str
    run_id: str
    source_agent: str
    claim_text: str
    claim_type: Literal["technical", "risk", "option", "recommendation", "assumption"]
    status: ClaimStatus = "pending"
    evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    verification_notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationResult(BaseModel):
    """The verifier's decision for one claim.

    This separates verification notes from the claim itself while preserving the
    evidence IDs that supported or contradicted the statement.
    """

    claim_id: str
    status: Literal["verified", "unsupported", "contradicted"]
    evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    verification_notes: str


class DecisionReport(BaseModel):
    """Final decision brief returned by the CLI workflow.

    Reports are rendered from claim ledger state, not raw agent memo text. This
    keeps verified evidence, unsupported assumptions, and contradictions visible.
    """

    run_id: str
    question: str
    recommendation: str
    options: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    contradictions: list[Claim] = Field(default_factory=list)
    unsupported_assumptions: list[Claim] = Field(default_factory=list)
    confidence_level: ConfidenceLevel
    human_review_required: list[str] = Field(default_factory=list)
    markdown: str
