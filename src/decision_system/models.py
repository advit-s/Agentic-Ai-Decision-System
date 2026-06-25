"""Shared typed models for evidence, claims, memos, and reports.

These Pydantic models are the contracts between retrieval, bounded agents,
verification, and report generation. Keeping these shapes explicit is what
lets v0.1 avoid passing unstructured agent chat into the final report.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

ClaimStatus = Literal[
    "pending",
    "supported",
    "verified",
    "unsupported",
    "contradicted",
    "uncertain",
    "needs_review",
    "approved",
    "rejected",
]
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
    workspace_id: str | None = None


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
    Claims are linked to workspace, execution, workflow, and node for traceability.
    """

    claim_id: str
    run_id: str
    workspace_id: str | None = None
    execution_id: str | None = None
    workflow_id: str | None = None
    node_id: str | None = None
    source_agent: str
    claim_text: str
    claim_type: Literal[
        "technical",
        "risk",
        "option",
        "recommendation",
        "assumption",
        "fact",
        "metric",
        "prediction",
        "decision",
        "unknown",
    ]
    status: ClaimStatus = "pending"
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    verification_notes: str = ""
    review_required: bool = False
    review_status: str | None = None
    evidence_quality: str | None = None
    verification_method: str | None = None
    graph_node_refs: list[str] = Field(
        default_factory=list, description="Referenced graph entity node IDs"
    )
    graph_edge_refs: list[str] = Field(
        default_factory=list, description="Referenced graph relationship edge IDs"
    )
    risk_refs: list[str] = Field(default_factory=list, description="Referenced WorkspaceRisk IDs")
    metric_refs: list[str] = Field(
        default_factory=list, description="Referenced WorkspaceMetric IDs"
    )
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceQuality(BaseModel):
    """Evidence quality assessment for a verified claim."""

    evidence_count: int = 0
    resolved_evidence_count: int = 0
    missing_evidence_count: int = 0
    source_count: int = 0
    has_direct_reference: bool = False
    has_cross_source_support: bool = False
    has_contradiction: bool = False
    recency_score: float | None = None
    coverage_score: float = 0.0
    quality_label: Literal["strong", "moderate", "weak", "missing", "contradicted"] = "missing"


class ContradictionRecord(BaseModel):
    """A contradiction detected between two evidence sources or between a claim and evidence."""

    contradiction_id: str
    workspace_id: str | None = None
    claim_id: str | None = None
    source_id_a: str
    chunk_id_a: str
    source_id_b: str
    chunk_id_b: str
    type: Literal[
        "metric_conflict",
        "opposite_status",
        "date_conflict",
        "risk_conflict",
        "claim_contradicted",
        "statement_conflict",
    ] = "statement_conflict"
    description: str
    severity: Literal["low", "medium", "high"] = "medium"
    confidence: Literal["low", "medium", "high"] = "medium"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VerificationSummary(BaseModel):
    """Summary of verification results for a workspace or execution."""

    total_claims: int = 0
    supported_claims: int = 0
    contradicted_claims: int = 0
    unsupported_claims: int = 0
    uncertain_claims: int = 0
    needs_review_claims: int = 0
    average_confidence: float = 0.0
    evidence_coverage_score: float = 0.0
    strong_evidence_count: int = 0
    moderate_evidence_count: int = 0
    weak_evidence_count: int = 0
    missing_evidence_count: int = 0
    contradiction_count: int = 0


class VerificationResult(BaseModel):
    """The verifier's decision for one claim.

    This separates verification notes from the claim itself while preserving the
    evidence IDs that supported or contradicted the statement.
    """

    claim_id: str
    status: Literal[
        "supported",
        "verified",
        "unsupported",
        "contradicted",
        "uncertain",
        "needs_review",
    ]
    evidence_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    verification_notes: str
    verification_method: str | None = None


class ReportClaimEntry(BaseModel):
    """A single claim as it appears in a trust report."""

    claim_id: str
    claim_text: str
    status: ClaimStatus = "pending"
    confidence: ConfidenceLevel = "low"
    evidence_quality: str | None = None
    verification_method: str | None = None
    verification_reason: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    review_required: bool = False
    graph_node_refs: list[str] = Field(default_factory=list)
    graph_edge_refs: list[str] = Field(default_factory=list)
    risk_refs: list[str] = Field(default_factory=list)
    metric_refs: list[str] = Field(default_factory=list)


class EvidenceTableEntry(BaseModel):
    """Evidence entry in the report evidence table."""

    evidence_id: str
    source_name: str
    snippet: str
    supports_claim_ids: list[str] = Field(default_factory=list)
    contradicts_claim_ids: list[str] = Field(default_factory=list)


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
    verification_summary: VerificationSummary | None = None
    supported_claims: list[ReportClaimEntry] = Field(default_factory=list)
    contradicted_claims: list[ReportClaimEntry] = Field(default_factory=list)
    unsupported_claims: list[ReportClaimEntry] = Field(default_factory=list)
    uncertain_claims: list[ReportClaimEntry] = Field(default_factory=list)
    needs_review_claims: list[ReportClaimEntry] = Field(default_factory=list)
    evidence_table: list[EvidenceTableEntry] = Field(default_factory=list)
    contradiction_records: list[ContradictionRecord] = Field(default_factory=list)
    human_review_required: list[str] = Field(default_factory=list)
    markdown: str
