"""Typed models for provider evaluation cases and results."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ProviderEvalBehavior = Literal[
    "structured_memo",
    "structured_claims",
    "contradiction",
    "unsupported_claim",
    "citation",
    "malformed_json",
    "refusal",
    "timeout",
]
HallucinationRisk = Literal["low", "medium", "high"]


def _default_provider_names() -> list[str]:
    return ["fake", "nvidia_nim", "ollama"]


class ProviderEvalCase(BaseModel):
    """One deterministic case for comparing provider behavior safely."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    name: str
    question: str
    evidence_texts: list[str] = Field(default_factory=list)
    expected_behavior: ProviderEvalBehavior
    expected_min_claims: int = 0
    provider_names: list[str] = Field(default_factory=_default_provider_names)


class ProviderOutputQuality(BaseModel):
    """Observed quality dimensions for provider output."""

    model_config = ConfigDict(extra="forbid")

    schema_valid: bool = False
    json_valid: bool = False
    citation_grounded: bool = False
    hallucination_risk: HallucinationRisk = "medium"
    contradiction_handled: bool = False
    unsupported_claims_handled: bool = False
    error_message: str = ""
    notes: list[str] = Field(default_factory=list)


class ProviderEvalResult(ProviderOutputQuality):
    """Pass/fail result for one provider and one evaluation case."""

    provider_name: str
    case_id: str
    passed: bool
    claim_count: int = 0
    manual_real_provider: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderEvalSuiteResult(BaseModel):
    """Aggregated provider evaluation result across providers and cases."""

    model_config = ConfigDict(extra="forbid")

    provider_names: list[str] = Field(default_factory=list)
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    manual_real_provider: bool = False
    results: list[ProviderEvalResult] = Field(default_factory=list)
    saved_result_path: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

