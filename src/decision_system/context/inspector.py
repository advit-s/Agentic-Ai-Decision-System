"""Inspection rendering for DecisionContext."""

from __future__ import annotations

from typing import Any

from decision_system.context.models import DecisionContext, InsightEvidence


def inspect_context(context: DecisionContext) -> dict[str, Any]:
    """Extract a summary for rendering."""
    return {
        "run_id": context.run_id,
        "question": context.question,
        "decision_type": context.problem_analysis.get("decision_type", "unknown"),
        "relevant_data_categories": context.relevant_data_categories,
        "relevant_storage_tiers": context.relevant_storage_tiers,
        "ontology_concepts": [
            {
                "concept_id": c["concept_id"],
                "name": c["name"],
                "type": c.get("type", "unknown"),
                "required": c.get("required", False),
            }
            for c in context.relevant_ontology_concepts
        ],
        "insights": [
            {
                "insight_id": i.insight_id,
                "title": i.title,
                "category": i.category,
                "severity": i.severity,
                "confidence": i.confidence,
                "evidence_summary": i.evidence_summary,
                "recommended_action": i.recommended_action,
                "ontology_concepts": i.ontology_concepts,
                "source_ids": i.source_ids,
            }
            for i in context.relevant_insights
        ],
        "graph_signals": context.graph_signals,
        "orchestration_available": bool(context.orchestration_summary),
        "orchestration_summary": context.orchestration_summary,
        "judge_confidence": context.judge_summary.get("confidence_level", "unknown"),
        "judge_key_findings": context.judge_summary.get("key_findings", []),
        "judge_human_review": context.judge_summary.get("human_review_required", []),
        "human_review_items": context.human_review_items,
        "created_at": context.created_at,
    }


def render_context_inspection(summary: dict[str, Any]) -> str:
    """Render context summary as Markdown."""
    lines = [
        "# Decision Context",
        "",
        f"**Run ID:** {summary['run_id']}",
        f"**Question:** {summary['question']}",
        f"**Decision Type:** {summary['decision_type']}",
        f"**Created:** {summary['created_at']}",
        "",
    ]

    if summary["relevant_data_categories"]:
        lines.append("## Relevant Data Categories")
        lines.extend(f"- {c}" for c in summary["relevant_data_categories"])
        lines.append("")

    if summary["relevant_storage_tiers"]:
        lines.append("## Relevant Storage Tiers")
        lines.extend(f"- {t}" for t in summary["relevant_storage_tiers"])
        lines.append("")

    if summary["ontology_concepts"]:
        lines.append("## Relevant Ontology Concepts")
        for c in summary["ontology_concepts"]:
            required_mark = " *(required)*" if c["required"] else ""
            lines.append(f"- **{c['concept_id']}** ({c['type']}): {c['name']}{required_mark}")
        lines.append("")

    if summary["insights"]:
        lines.append("## Relevant Insights")
        for i in summary["insights"]:
            lines.extend([
                f"### {i['title']} [{i['severity'].upper()}]",
                f"- **Insight ID:** {i['insight_id']}",
                f"- **Category:** {i['category']}",
                f"- **Confidence:** {i['confidence']}",
                f"- **Evidence:** {i['evidence_summary']}",
                f"- **Recommended Action:** {i['recommended_action']}",
                f"- **Ontology Concepts:** {', '.join(i['ontology_concepts']) or '(none)'}",
                f"- **Source IDs:** {', '.join(i['source_ids']) or '(none)'}",
                "",
            ])
        lines.append("")

    if summary["graph_signals"]:
        lines.append("## Graph Signals")
        for s in summary["graph_signals"]:
            lines.append(f"- {s}")
        lines.append("")

    if summary["orchestration_available"]:
        lines.append("## Orchestration Summary")
        lines.append(f"- **Run ID:** {summary['orchestration_summary'].get('run_id', 'unknown')}")
        lines.append(f"- **Decision Type:** {summary['orchestration_summary'].get('decision_type', 'unknown')}")
        lines.append(f"- **Insight Count:** {summary['orchestration_summary'].get('insight_count', 0)}")
        by_sev = summary['orchestration_summary'].get('insights_by_severity', {})
        if by_sev:
            lines.append("- **Insights by Severity:**")
            for sev, count in sorted(by_sev.items()):
                lines.append(f"  - {sev}: {count}")
        lines.append("")

    if summary["judge_confidence"] != "unknown":
        lines.append("## Judge Summary")
        lines.append(f"- **Confidence:** {summary['judge_confidence']}")
        if summary["judge_key_findings"]:
            lines.append("- **Key Findings:**")
            for f in summary["judge_key_findings"]:
                lines.append(f"  - {f}")
        if summary["judge_human_review"]:
            lines.append("- **Human Review Required:**")
            for r in summary["judge_human_review"]:
                lines.append(f"  - {r}")
        lines.append("")

    if summary["human_review_items"]:
        lines.append("## Human Review Items (Context)")
        for item in summary["human_review_items"]:
            lines.append(f"- {item}")
        lines.append("")

    return "\n".join(lines).rstrip()
