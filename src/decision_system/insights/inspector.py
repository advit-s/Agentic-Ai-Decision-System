"""Inspection helpers for the deterministic insight store."""

from __future__ import annotations

from collections import Counter

from decision_system.insights.models import InsightCategory, InsightSeverity, InsightStore


def inspect_insights(store: InsightStore) -> dict[str, object]:
    """Compute summary statistics from an insight store."""

    total = len(store.insights)
    severity_counts: dict[InsightSeverity, int] = store.severity_counts()
    category_counts: dict[InsightCategory, int] = store.category_counts()
    top = store.sorted_by_severity()[:10]

    return {
        "total_insights": total,
        "severity_counts": dict(severity_counts),
        "category_counts": dict(category_counts),
        "top_insights": [
            {
                "insight_id": i.insight_id,
                "title": i.title,
                "severity": i.severity,
                "category": i.category,
            }
            for i in top
        ],
    }


def render_insight_inspection(summary: dict[str, object]) -> str:
    """Render the inspection summary as a human-readable string."""

    lines: list[str] = ["# Insight Inspection", ""]

    lines.append(f"Total insights: {summary['total_insights']}")
    lines.append("")

    sev: dict[str, int] = summary["severity_counts"]
    if sev:
        lines.append("## By Severity")
        lines.append("")
        for sev_name in ("critical", "high", "medium", "low"):
            count = sev.get(sev_name, 0)
            if count:
                lines.append(f"- **{sev_name}**: {count}")
        lines.append("")

    cat: dict[str, int] = summary["category_counts"]
    if cat:
        lines.append("## By Category")
        lines.append("")
        for cat_name, count in sorted(cat.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"- **{cat_name}**: {count}")
        lines.append("")

    top = summary.get("top_insights", [])
    if top:
        lines.append("## Top Insights (by severity)")
        lines.append("")
        for idx, item in enumerate(top, start=1):
            sev_badge = item["severity"].upper()
            lines.append(
                f"{idx}. [{sev_badge}] **{item['title']}** ({item['category']})"
            )
        lines.append("")

    if not lines:
        return "# Insight Inspection\n\nNo insights found."

    return "\n".join(lines)
