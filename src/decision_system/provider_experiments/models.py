"""Provider experiment models for comparing fake, NIM, and Ollama outputs."""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProviderExperimentCase(BaseModel):
    """One reproducible experiment case for provider comparison."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    question: str
    evidence_texts: list[str] = Field(default_factory=list)
    expected_min_claims: int = 0
    expected_evidence_ids: list[str] = Field(default_factory=list)
    provider_name: str = "fake"


class ProviderExperimentResult(BaseModel):
    """Result of running one experiment case against one provider."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    provider_name: str
    status: Literal["passed", "failed", "skipped"]
    technical_memo_valid: bool = False
    risk_memo_valid: bool = False
    claims_valid: bool = False
    claim_count: int = 0
    errors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProviderExperimentSuiteResult(BaseModel):
    """Aggregated result across all cases for one provider."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    results: list[ProviderExperimentResult] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
