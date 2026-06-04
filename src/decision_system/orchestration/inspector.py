"""Inspection helpers for the v0.4 orchestration layer."""

from __future__ import annotations

from decision_system.orchestration.models import (
    DispatchPlan,
    ProblemAnalysis,
)


def inspect_problem_analysis(analysis: ProblemAnalysis) -> dict[str, object]:
    """Return a summary dict from a ProblemAnalysis."""

    return {
        "question": analysis.question,
        "decision_type": analysis.decision_type,
        "required_data_categories": analysis.required_data_categories,
        "required_tools": analysis.required_tools,
        "relevant_roles": analysis.relevant_roles,
        "required_ontology_concepts": analysis.required_ontology_concepts,
        "required_storage_tiers": analysis.required_storage_tiers,
        "missing_capabilities": analysis.missing_capabilities,
        "analysis_notes": analysis.analysis_notes,
    }


def inspect_dispatch_plan(plan: DispatchPlan) -> dict[str, object]:
    """Return a summary dict from a DispatchPlan."""

    return {
        "selected_tools": plan.selected_tools,
        "execution_order": plan.execution_order,
        "selected_roles": plan.selected_roles,
        "selected_artifacts": plan.selected_artifacts,
        "skipped_tools": plan.skipped_tools,
        "missing_inputs": plan.missing_inputs,
    }


def render_problem_analysis(summary: dict[str, object]) -> str:
    """Render a ProblemAnalysis summary as Markdown."""

    lines: list[str] = ["# Problem Analysis", ""]
    lines.append(f"**Question:** {summary.get('question', '?')}")
    lines.append(f"**Decision type:** {summary.get('decision_type', '?')}")
    lines.append("")

    cats = summary.get("required_data_categories", [])
    if cats:
        lines.append("## Required Data Categories")
        lines.append("")
        for cat in cats:
            lines.append(f"- {cat}")
        lines.append("")

    tools = summary.get("required_tools", [])
    if tools:
        lines.append("## Required Tools")
        lines.append("")
        for tool in tools:
            lines.append(f"- `{tool}`")
        lines.append("")

    roles = summary.get("relevant_roles", [])
    if roles:
        lines.append("## Relevant Roles")
        lines.append("")
        for role in roles:
            lines.append(f"- {role}")
        lines.append("")

    concepts = summary.get("required_ontology_concepts", [])
    if concepts:
        lines.append("## Ontology Concepts")
        lines.append("")
        for c in concepts:
            lines.append(f"- {c}")
        lines.append("")

    tiers = summary.get("required_storage_tiers", [])
    if tiers:
        lines.append("## Storage Tiers")
        lines.append("")
        for t in tiers:
            lines.append(f"- {t}")
        lines.append("")

    missing = summary.get("missing_capabilities", [])
    if missing:
        lines.append("## Missing Capabilities")
        lines.append("")
        for m in missing:
            lines.append(f"- {m}")
        lines.append("")

    notes = summary.get("analysis_notes", "")
    if notes:
        lines.append("## Analysis Notes")
        lines.append("")
        lines.append(str(notes))
        lines.append("")

    return "\n".join(lines)


def render_dispatch_plan(summary: dict[str, object]) -> str:
    """Render a DispatchPlan summary as Markdown."""

    lines: list[str] = ["# Dispatch Plan", ""]

    order = summary.get("execution_order", [])
    if order:
        lines.append("## Execution Order")
        lines.append("")
        for idx, tool in enumerate(order, start=1):
            lines.append(f"{idx}. `{tool}`")
        lines.append("")

    selected = summary.get("selected_tools", [])
    if selected:
        lines.append("## Selected Tools")
        lines.append("")
        for tool in selected:
            marker = " **selected**" if tool in order else ""
            lines.append(f"- `{tool}`{marker}")
        lines.append("")

    skipped = summary.get("skipped_tools", [])
    if skipped:
        lines.append("## Skipped Tools")
        lines.append("")
        for tool in skipped:
            lines.append(f"- `{tool}`")
        lines.append("")

    roles = summary.get("selected_roles", [])
    if roles:
        lines.append("## Selected Roles")
        lines.append("")
        for role in roles:
            lines.append(f"- {role}")
        lines.append("")

    artifacts = summary.get("selected_artifacts", [])
    if artifacts:
        lines.append("## Artifacts")
        lines.append("")
        for art in artifacts:
            lines.append(f"- `{art}`")
        lines.append("")

    missing = summary.get("missing_inputs", [])
    if missing:
        lines.append("## Missing Inputs")
        lines.append("")
        for m in missing:
            lines.append(f"- {m}")
        lines.append("")

    return "\n".join(lines)
