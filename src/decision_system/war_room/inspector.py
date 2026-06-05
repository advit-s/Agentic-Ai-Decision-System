"""Inspection helpers for war-room runs."""

from __future__ import annotations

from decision_system.war_room.models import WarRoomRun


def inspect_war_room(run: WarRoomRun) -> dict[str, object]:
    """Return an inspectable summary of a WarRoomRun."""
    artifacts_summary = []
    if run.workspace:
        for art in run.workspace.artifacts:
            role = ""
            for res in run.agent_results:
                if res.agent_id == art.author_agent_id:
                    role = res.role_name
                    break
            artifacts_summary.append({
                "title": art.title,
                "role": role,
                "confidence": art.confidence,
                "evidence_ids": art.evidence_ids,
                "insight_ids": art.insight_ids,
            })

    return {
        "run_id": str(run.run_id),
        "question": str(run.question),
        "roles": list(run.dispatch_spec.dispatch_order) if run.dispatch_spec else [],
        "skipped_roles": list(run.dispatch_spec.skipped_roles) if run.dispatch_spec else [],
        "artifact_count": len(run.workspace.artifacts) if run.workspace else 0,
        "judge_intervention_count": len(run.judge_interventions),
        "human_review_required": sum(
            1 for i in run.judge_interventions if i.requires_human_review
        ),
        "final_summary": run.final_summary,
        "higher_context_summary": _summarise_higher_context(run.higher_context),
        "artifacts": artifacts_summary,
        "interventions": [
            {
                "severity": i.severity,
                "reason": i.reason,
                "requires_human_review": i.requires_human_review,
                "target_artifact_id": i.target_artifact_id,
            }
            for i in run.judge_interventions
        ],
    }


def render_inspection(summary: dict[str, object]) -> str:
    """Render a war-room summary dict as a human-readable Markdown string."""
    lines = ["# War-Cabinet Inspection", ""]
    for key in ("run_id", "question", "roles", "artifact_count",
                "judge_intervention_count", "human_review_required",
                "final_summary"):
        val = summary.get(key)
        if isinstance(val, list | tuple):
            val = _format_sequence(val)
        lines.append(f"**{key.replace('_', ' ').title()}**: {val}")
    if summary.get("higher_context_summary"):
        lines.append("")
        lines.append("## Higher Context Summary")
        ctx = summary["higher_context_summary"]
        lines.append(f"- Data categories: {_format_sequence(ctx.get('data_categories'))}")
        lines.append(f"- Ontology concepts: {_format_sequence(ctx.get('ontology_concepts'))}")
        lines.append(f"- Insight IDs: {_format_sequence(ctx.get('insight_ids'))}")
        lines.append(f"- Storage tiers: {_format_sequence(ctx.get('storage_tiers'))}")
    lines.append("")
    if summary.get("artifact_count") and int(summary.get("artifact_count", 0)) > 0:
        lines.append("## Artifacts")
        for artifact in summary.get("artifacts", []):
            lines.append(
                f"- **{artifact['title']}** "
                f"({artifact['role']}, confidence={artifact['confidence']})"
            )
    lines.append("")
    if summary.get("judge_intervention_count"):
        jic = int(summary.get("judge_intervention_count", 0))
        if jic > 0:
            lines.append("## Judge Interventions")
            for intervention in summary.get("interventions", []):
                lines.append(
                    f"- [{intervention['severity'].upper()}] "
                    f"{intervention['reason']}"
                )
                if intervention.get("requires_human_review"):
                    lines.append("  - *WARNING: human review required.*")
    return "\n".join(lines).rstrip()


def _format_sequence(value: object) -> str:
    if not value:
        return "none"
    if isinstance(value, list | tuple | set):
        return ", ".join(str(item) for item in value) or "none"
    return str(value)


def _summarise_higher_context(
    higher_context,
) -> dict[str, object]:
    if higher_context is None:
        return {}
    return {
        "data_categories": higher_context.required_data_categories,
        "ontology_concepts": higher_context.required_ontology_concepts,
        "insight_ids": higher_context.relevant_insight_ids,
        "storage_tiers": higher_context.relevant_storage_tiers,
    }
