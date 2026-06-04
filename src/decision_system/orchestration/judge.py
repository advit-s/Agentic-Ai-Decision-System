"""Deterministic judge / verifier summary for v0.4.

No LLM is required. The judge summarises the run's insights, flags
human-review items, and assigns a conservative confidence level.
"""

from __future__ import annotations

from typing import Any

from decision_system.insights.models import (
    Insight,
    InsightStore,
    InsightSeverity,
)
from decision_system.orchestration.models import (
    JudgeSummary,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _highest_severity(insights: list[Insight]) -> InsightSeverity:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    ranked = sorted(insights, key=lambda i: order.get(i.severity, 99))
    return ranked[0].severity if ranked else "medium"


def _insights_by_severity(
    insights: list[Insight],
) -> dict[InsightSeverity, list[Insight]]:
    buckets: dict[InsightSeverity, list[Insight]] = {
        "critical": [],
        "high": [],
        "medium": [],
        "low": [],
    }
    for ins in insights:
        buckets[ins.severity].append(ins)
    return buckets


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------


def build_judge_summary(
    *,
    run_id: str,
    insights: InsightStore | list[Insight] | None = None,
    missing_data_items: list[str] | None = None,
) -> JudgeSummary:
    """Build a deterministic JudgeSummary from run data.

    Parameters
    ----------
    run_id:
        The orchestration run id.
    insights:
        Detected insights (InsightStore or raw list).
    missing_data_items:
        Any detected gaps in data availability.
    """

    if insights is None:
        insights = InsightStore()
    if isinstance(insights, InsightStore):
        insight_list = insights.insights
    else:
        insight_list = insights or []

    by_sev = _insights_by_severity(insight_list)

    key_findings: list[str] = []
    for sev in ("critical", "high", "medium", "low"):
        for ins in by_sev[sev]:
            key_findings.append(f"[{sev.upper()}] {ins.title}: {ins.description}")

    risks: list[str] = [
        ins.recommended_action for ins in insight_list if ins.recommended_action
    ]

    human_review: list[str] = []

    # Require human review for high/critical insights
    for ins in by_sev["critical"] + by_sev["high"]:
        human_review.append(
            f"{ins.insight_id} ({ins.category}, {ins.severity}): "
            f"{ins.title}"
        )

    # Require human review for contradictions
    for ins in insight_list:
        if ins.category == "contradiction":
            human_review.append(
                f"{ins.insight_id} (contradiction): {ins.title}"
            )

    # Confidence: start medium, downgrade for missing data
    confidence: str = "medium"
    if missing_data_items and len(missing_data_items) > 0:
        confidence = "low"
    if not insight_list:
        confidence = "low"

    return JudgeSummary(
        run_id=run_id,
        confidence_level=confidence,
        key_findings=key_findings[:20],
        risks=risks[:20],
        missing_data=missing_data_items or [],
        recommended_next_actions=risks[:10],
        human_review_required=human_review[:20],
    )
