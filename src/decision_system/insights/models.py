"""Pydantic models for the deterministic insight engine."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Typed enumerations
# ---------------------------------------------------------------------------

InsightSeverity = Literal["low", "medium", "high", "critical"]

InsightCategory = Literal[
    "revenue_risk",
    "profit_margin_risk",
    "customer_concentration",
    "sales_channel_risk",
    "marketing_roi_risk",
    "feedback_risk",
    "product_risk",
    "competitor_risk",
    "operations_bottleneck",
    "analytics_conversion_risk",
    "data_quality",
    "missing_data",
    "dependency_risk",
    "contradiction",
    "strategic_gap",
    "security_risk",
    "unknown",
]

# ---------------------------------------------------------------------------
# Insight
# ---------------------------------------------------------------------------


class Insight(BaseModel):
    """A single pattern or vulnerability surfaced by the detection engine."""

    model_config = {"extra": "forbid"}

    insight_id: str
    title: str = ""
    description: str = Field(default="")
    category: InsightCategory = "unknown"
    severity: InsightSeverity = "medium"
    confidence: ConfidenceLevel = "medium"
    source_type: str = Field(default="unknown", description='"profile", "csv", "graph", or "mixed"')
    source_ids: list[str] = Field(default_factory=list, description="Dataset or evidence IDs backing this insight")
    evidence_summary: str = Field(default="", description="Human-readable summary of the evidence")
    recommended_action: str = Field(default="", description="Suggested follow-up for the stakeholder")
    ontology_concepts: list[str] = Field(default_factory=list, description="Ontology concept IDs relevant to this insight")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# Re-export ConfidenceLevel from the shared models module so detectors can
# import it from a single place without depending on the full data_catalog.
from decision_system.models import ConfidenceLevel  # noqa: E402  # pragma: no cover

# ---------------------------------------------------------------------------
# InsightStore
# ---------------------------------------------------------------------------


class InsightStore(BaseModel):
    """Container for all detected insights with metadata."""

    model_config = {"extra": "forbid"}

    insights: list[Insight] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # -- convenience helpers --------------------------------------------------

    def add(self, insight: Insight) -> None:
        """Append an insight, replacing any existing insight with the same id."""
        self.insights = [i for i in self.insights if i.insight_id != insight.insight_id]
        self.insights.append(insight)

    def severity_counts(self) -> dict[InsightSeverity, int]:
        counts: dict[str, int] = {}
        for i in self.insights:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts  # type: ignore[return-value]

    def category_counts(self) -> dict[InsightCategory, int]:
        counts: dict[str, int] = {}
        for i in self.insights:
            counts[i.category] = counts.get(i.category, 0) + 1
        return counts  # type: ignore[return-value]

    def sorted_by_severity(self) -> list[Insight]:
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        return sorted(self.insights, key=lambda i: order.get(i.severity, 99))
