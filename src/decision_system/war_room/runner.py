"""Run the full war-cabinet pipeline."""

from __future__ import annotations

from uuid import uuid4

from decision_system.war_room.context_builder import build_higher_context
from decision_system.war_room.dispatcher import build_dispatch_spec
from decision_system.war_room.judge import run_judge
from decision_system.war_room.models import (
    AgentRunResult,
    CommonWorkspace,
    PersonalAgentContext,
    WarRoomRun,
    WorkspaceArtifact,
)
from decision_system.war_room.sandbox import sandboxed_read
from decision_system.war_room.store import save_war_room_run


def run_war_room(question: str) -> WarRoomRun:
    """Execute the full war-room pipeline for *question*.

    Steps:
    1. Build immutable higher context.
    2. Dispatch roles and create personal contexts.
    3. Create append-only common workspace.
    4. Run deterministic simulated specialist agents.
    5. Run judge over workspace artifacts.
    6. Return complete WarRoomRun record.
    7. Persist to disk.
    """
    # 1. Higher context
    higher_context = build_higher_context(question)

    # 2. Dispatch spec (includes personal contexts)
    dispatch_spec = build_dispatch_spec(question, higher_context=higher_context)

    # 3. Workspace
    workspace = CommonWorkspace(run_id=higher_context.run_id)

    # 4. Simulated agent runs
    agent_results = []
    for role in dispatch_spec.dispatch_order:
        personal_ctx = _find_personal_context(dispatch_spec, role)
        artifacts = _simulate_agent(personal_ctx, higher_context)
        for artifact in artifacts:
            workspace.add_artifact(artifact)
        result = AgentRunResult(
            agent_id=personal_ctx.agent_id,
            role_name=role,
            status="completed",
            artifacts_created=len(artifacts),
        )
        agent_results.append(result)

    # 5. Judge
    interventions = run_judge(list(workspace.artifacts), higher_context.run_id)

    # 6. Final summary
    human_review_count = sum(1 for i in interventions if i.requires_human_review)
    summary_parts = [
        "War-room complete for: {}".format(question),
        "Roles dispatched: {}".format(len(dispatch_spec.dispatch_order)),
        "Artifacts created: {}".format(len(workspace.artifacts)),
        "Judge interventions: {}".format(len(interventions)),
        "Human review required: {}".format(human_review_count),
    ]
    final_summary = " | ".join(summary_parts)

    run = WarRoomRun(
        run_id=higher_context.run_id,
        question=question,
        higher_context=higher_context,
        dispatch_spec=dispatch_spec,
        workspace=workspace,
        agent_results=agent_results,
        judge_interventions=interventions,
        final_summary=final_summary,
    )

    # 7. Persist
    save_war_room_run(run)
    return run


def _find_personal_context(spec, role=None):
    """Return the PersonalAgentContext for *role*, or a fallback."""
    for ctx in spec.personal_contexts:
        if ctx.role_name == role:
            return ctx
    # Fallback - should not happen if dispatch spec is consistent
    return PersonalAgentContext(
        agent_id="fallback-{}".format(role),
        role_name=role,
        role_type=role,
        assigned_task="Analyse: {}".format(spec.higher_context.question),
        perspective="General analysis.",
        higher_context_ref=spec.higher_context.run_id,
    )


def _simulate_agent(personal_ctx, higher_context, *args, **kwargs):
    """Deterministic artifact generator for a single agent role.

    Reads local stores via the sandbox and produces structured artifacts
    with evidence/insight/ontology references.  No LLM is called.
    """
    if args or kwargs:
        raise TypeError(
            "_simulate_agent() takes 3 positional arguments but {} were given".format(2 + len(args))
        )

    insights_store = sandboxed_read("insights", {})
    profile_store = sandboxed_read("profiles", {})

    cats: list = getattr(higher_context, "required_data_categories", None) or []
    relevant_insight_ids = list(dict.fromkeys(getattr(higher_context, "relevant_insight_ids", [])))
    for insight in insights_store.insights:
        if not cats:
            if insight.insight_id in getattr(higher_context, "relevant_insight_ids", []):
                if insight.insight_id not in relevant_insight_ids:
                    relevant_insight_ids.append(insight.insight_id)
        else:
            for cat in cats:
                if cat.lower() in getattr(insight, "category", "").lower():
                    if insight.insight_id not in relevant_insight_ids:
                        relevant_insight_ids.append(insight.insight_id)
                    break

    relevant_evidence_ids = []
    ontology_concepts_out = list(getattr(higher_context, "required_ontology_concepts", []))
    for profile in profile_store.profiles:
        for col in profile.columns:
            for concept in ontology_concepts_out:
                if concept.lower() in getattr(col, "name", "").lower():
                    relevant_evidence_ids.append("profile:{}:{}".format(profile.filename, col.name))
                    break

    source_files = ["company_data/{}/".format(cat) for cat in cats[:3]] or ["(none)"]

    title = _ARTIFACT_TITLES.get(
        personal_ctx.role_type, "{} analysis".format(personal_ctx.role_type)
    )
    artifact_types = {
        "financial_analyst": "analysis",
        "risk_analyst": "risk_assessment",
        "marketing_analyst": "analysis",
        "technical_analyst": "dependency",
    }
    art_type = artifact_types.get(personal_ctx.role_type, "general")

    content_lines = [
        "# {}".format(title),
        "",
        "## Question",
        higher_context.question,
        "",
        "## Perspective",
        personal_ctx.perspective,
        "",
        "## Assigned Task",
        personal_ctx.assigned_task,
        "",
        "## Findings",
    ]
    _add_findings(content_lines, personal_ctx, higher_context, insights_store, profile_store)
    content_lines.extend(
        [
            "",
            "## Evidence / Data Referenced",
            "- Evidence IDs: {}".format(", ".join(relevant_evidence_ids[:5]) or "none"),
            "- Insight IDs: {}".format(", ".join(relevant_insight_ids[:5]) or "none"),
            "- Ontology concepts: {}".format(", ".join(ontology_concepts_out[:5]) or "none"),
            "- Source data: {}".format(", ".join(source_files)),
            "",
            "## Limitations",
            "- This artifact is a deterministic simulation, not an LLM-generated analysis.",
            "- Conclusions are structured placeholders reflecting available local data signals.",
            "- No agent-to-agent debate is performed.",
        ]
    )
    content = "\n".join(content_lines)

    artifact = WorkspaceArtifact(
        artifact_id=str(uuid4()),
        run_id=higher_context.run_id,
        author_agent_id=personal_ctx.agent_id,
        artifact_type=art_type,
        title=title,
        content=content,
        evidence_ids=relevant_evidence_ids,
        insight_ids=relevant_insight_ids,
        ontology_concepts=ontology_concepts_out,
        confidence="medium",
    )
    return [artifact]


def _add_findings(lines, ctx, higher_context, insights_store, profile_store, **kwargs):
    """Append role-specific findings to *lines* in place."""
    cats = getattr(higher_context, "required_data_categories", None) or []

    rt = getattr(ctx, "role_type", "")
    if rt == "risk_analyst":
        _add_risk_findings(lines, insights_store, cats)
    elif rt == "financial_analyst":
        _add_financial_findings(lines, profile_store, insights_store, cats)
    elif rt == "marketing_analyst":
        _add_marketing_findings(lines, insights_store, cats)
    elif rt == "technical_analyst":
        _add_technical_findings(lines, insights_store)
    else:
        lines.append(
            "- General signal: review available data categories and ontology "
            "concepts before taking action."
        )
        for profile in profile_store.profiles:
            cats_used = (
                [c for c in cats if c in getattr(profile, "filename", "").lower()] if cats else []
            )
            if cats_used:
                lines.append(
                    "- Profile '{}': {} rows, {} columns.".format(
                        profile.filename,
                        profile.row_count,
                        len(profile.columns),
                    )
                )


def _add_risk_findings(lines, insights_store, cats):
    lines.append("- Risk perspective: reviewing insight signals for the selected domains.")
    high_insights = [
        i for i in insights_store.insights if getattr(i, "severity", "") in ("high", "critical")
    ]
    if high_insights:
        lines.append("- High-severity insights detected: {}".format(len(high_insights)))
        for ins in high_insights[:3]:
            lines.append(
                "  - [{}] {}: {}".format(
                    ins.severity.upper(),
                    ins.title,
                    getattr(ins, "evidence_summary", "") or getattr(ins, "recommended_action", ""),
                )
            )
    contradiction_insights = [
        i for i in insights_store.insights if getattr(i, "category", "") == "contradiction"
    ]
    if contradiction_insights:
        lines.append(
            "- Contradiction insights: {} - human review required before "
            "acting on conflicting data.".format(len(contradiction_insights))
        )
    if not high_insights and not contradiction_insights:
        lines.append("- No high/critical insights detected for the selected data categories.")


def _add_financial_findings(lines, profile_store, insights_store, cats):
    fin_profiles = [
        p for p in profile_store.profiles if "financial" in getattr(p, "filename", "").lower()
    ]
    if fin_profiles:
        pf = fin_profiles[0]
        numeric_cols = []
        stats = getattr(pf, "statistics", {})
        stats.get("columns", []) if isinstance(stats, dict) else []
        # Try the profile_store's column access
        for col in pf.columns:
            if getattr(col, "statistics", None):
                if "mean" in getattr(col, "statistics", {}):
                    numeric_cols.append(col.name)
        if not numeric_cols:
            for c in pf.columns:
                if c.dtype == "numeric":
                    numeric_cols.append(c.name)
        lines.append(
            "- Financial profile '{}': {} rows, numeric columns: {}.".format(
                pf.filename,
                pf.row_count,
                ", ".join(numeric_cols) or "none",
            )
        )
    fin_insights = [
        i
        for i in insights_store.insights
        if i.category in ("revenue_risk", "profit_margin_risk", "marketing_roi_risk")
    ]
    if fin_insights:
        for ins in fin_insights[:3]:
            lines.append(
                "- [{}] {}: {}".format(ins.severity.upper(), ins.title, ins.evidence_summary)
            )


def _add_marketing_findings(lines, insights_store, cats):
    mkt_insights = [
        i
        for i in insights_store.insights
        if i.category in ("marketing_roi_risk", "sales_channel_risk", "analytics_conversion_risk")
    ]
    if mkt_insights:
        for ins in mkt_insights[:3]:
            lines.append(
                "- [{}] {}: {}".format(ins.severity.upper(), ins.title, ins.evidence_summary)
            )
    if not mkt_insights:
        lines.append(
            "- No marketing-specific insights detected yet. "
            "Run detect-patterns with marketing data."
        )


def _add_technical_findings(lines, insights_store):
    dep_insights = [i for i in insights_store.insights if i.category == "dependency_risk"]
    if dep_insights:
        for ins in dep_insights[:3]:
            lines.append(
                "- [{}] {}: {}".format(ins.severity.upper(), ins.title, ins.evidence_summary)
            )
    if not dep_insights:
        lines.append(
            "- No dependency risks detected in the knowledge graph yet. "
            "Run extract-graph to build dependency signals."
        )


_ARTIFACT_TITLES = {
    "financial_analyst": "Financial risk signals",
    "customer_analyst": "Customer segment signals",
    "sales_analyst": "Sales pipeline signals",
    "marketing_analyst": "Marketing channel efficiency signals",
    "product_analyst": "Product performance signals",
    "operations_analyst": "Operational efficiency signals",
    "strategy_analyst": "Strategic positioning signals",
    "technical_analyst": "Dependency and architecture signals",
    "legal_analyst": "Legal and compliance signals",
    "risk_analyst": "Human review and uncertainty risks",
}
