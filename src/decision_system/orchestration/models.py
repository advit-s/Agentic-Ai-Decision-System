"""Pydantic models for the v0.4 orchestration layer."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Storage Tier
# ---------------------------------------------------------------------------


class StorageTier(BaseModel):
    """One of four common storage tiers used to reason about data lifecycle."""

    tier_id: str
    name: str
    description: str
    artifacts: list[str] = Field(default_factory=list)
    purpose: str


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class DecisionSession(BaseModel):
    """Record of a single orchestration run."""

    session_id: str
    run_id: str
    question: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    context_summary: str = ""
    required_data_categories: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    relevant_roles: list[str] = Field(default_factory=list)
    storage_tiers_used: list[str] = Field(default_factory=list)
    decision_type: str = "general"
    execution_order: list[str] = Field(default_factory=list)
    skipped_tools: list[str] = Field(default_factory=list)
    selected_artifacts: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    ontology_concept_count: int = 0
    mapped_column_count: int = 0
    insight_count: int = 0
    insights_by_severity: dict[str, int] = Field(default_factory=dict)
    insights_by_category: dict[str, int] = Field(default_factory=dict)
    judge_summary: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Problem Analysis
# ---------------------------------------------------------------------------

DecisionType = Literal[
    "financial",
    "customer",
    "sales",
    "marketing",
    "feedback",
    "product",
    "competitor",
    "operations",
    "analytics",
    "strategic",
    "technical",
    "risk",
    "general",
]


class ProblemAnalysis(BaseModel):
    """Deterministic analysis of what a business question requires."""

    question: str
    decision_type: DecisionType = "general"
    required_data_categories: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    relevant_roles: list[str] = Field(default_factory=list)
    required_ontology_concepts: list[str] = Field(default_factory=list)
    required_storage_tiers: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    analysis_notes: str = ""


# ---------------------------------------------------------------------------
# Dispatch Plan
# ---------------------------------------------------------------------------


class DispatchPlan(BaseModel):
    """Deterministic tool / role / artifact selection plan."""

    selected_tools: list[str] = Field(default_factory=list)
    selected_roles: list[str] = Field(default_factory=list)
    selected_artifacts: list[str] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    skipped_tools: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Judge Summary
# ---------------------------------------------------------------------------


class JudgeSummary(BaseModel):
    """Deterministic post-run verdict (no LLM required)."""

    run_id: str
    confidence_level: Literal["low", "medium", "high"] = "medium"
    key_findings: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_data: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    human_review_required: list[str] = Field(default_factory=list)
