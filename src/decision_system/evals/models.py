"""Typed models for local evaluation cases and results."""

from typing import Literal

from pydantic import BaseModel, Field

from decision_system.models import ConfidenceLevel


class EvalDocument(BaseModel):
    """A temporary local document used by one evaluation case."""

    filename: str
    text: str


class EvalExpectations(BaseModel):
    """Expected measurable behavior for one evaluation case."""

    required_source_filenames: list[str] = Field(default_factory=list)
    min_verified_claims: int = 0
    min_unsupported_claims: int = 0
    min_contradicted_claims: int = 0
    min_evidence_citations: int = 0
    human_review_required: bool
    expected_confidence_level: ConfidenceLevel | None = None
    required_report_sections: list[str] = Field(default_factory=list)


class EvalCase(BaseModel):
    """A repeatable offline evaluation case."""

    case_id: str
    question: str
    documents: list[EvalDocument] = Field(default_factory=list)
    expectations: EvalExpectations


class EvalMetrics(BaseModel):
    """Observed workflow metrics for one evaluation run."""

    retrieved_evidence: int
    source_filenames: list[str] = Field(default_factory=list)
    verified_claims: int
    unsupported_claims: int
    contradicted_claims: int
    evidence_citations: int
    confidence_level: ConfidenceLevel
    human_review_required: bool
    report_sections_present: list[str] = Field(default_factory=list)


class EvalResult(BaseModel):
    """Pass/fail result for one evaluation case."""

    case_id: str
    question: str
    passed: bool
    failures: list[str] = Field(default_factory=list)
    run_id: str
    metrics: EvalMetrics


class EvalSuiteResult(BaseModel):
    """Aggregated result for a set of evaluation cases."""

    passed: bool
    cases: list[EvalResult]
    saved_result_path: str | None = None


EvalStatus = Literal["PASS", "FAIL"]
