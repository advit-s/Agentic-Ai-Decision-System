"""Pydantic models for decision context."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


InsightSeverity = Literal["low", "medium", "high", "critical"]
ConfidenceLevel = Literal["low", "medium", "high"]


class InsightEvidence(BaseModel):
    """Lightweight view of an insight for report contexts."""

    model_config = {"extra": "forbid"}

    insight_id: str
    title: str = ""
    category: str = "unknown"
    severity: InsightSeverity = "medium"
    confidence: ConfidenceLevel = "medium"
    evidence_summary: str = ""
    recommended_action: str = ""
    ontology_concepts: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class DecisionContext(BaseModel):
    """Full decision context assembled for a question."""

    model_config = {"extra": "forbid"}

    run_id: str
    question: str
    problem_analysis: dict = Field(default_factory=dict)
    relevant_data_categories: list[str] = Field(default_factory=list)
    relevant_storage_tiers: list[str] = Field(default_factory=list)
    relevant_ontology_concepts: list[dict] = Field(default_factory=list)
    relevant_insights: list[InsightEvidence] = Field(default_factory=list)
    graph_signals: list[str] = Field(default_factory=list)
    orchestration_summary: dict = Field(default_factory=dict)
    judge_summary: dict = Field(default_factory=dict)
    human_review_items: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
