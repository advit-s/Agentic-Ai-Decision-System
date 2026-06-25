"""Deterministic role dispatch for the war-room.

Maps a question (via the existing problem analysis) to a set of specialist
roles following the dispatch rules from the task spec.  No LLM is called.
"""

from __future__ import annotations

from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.war_room.models import (
    AgentDispatchSpec,
    HigherContext,
    PersonalAgentContext,
)

_ROLE_SELECTION: dict[str, list[str]] = {
    "financial": ["financial_analyst", "risk_analyst"],
    "customer": ["customer_analyst", "risk_analyst"],
    "sales": ["sales_analyst", "product_analyst"],
    "marketing": ["marketing_analyst", "financial_analyst"],
    "feedback": ["customer_analyst", "product_analyst", "risk_analyst"],
    "product": ["sales_analyst", "product_analyst"],
    "competitor": ["strategy_analyst", "risk_analyst"],
    "operations": ["operations_analyst", "risk_analyst"],
    "analytics": ["marketing_analyst", "product_analyst"],
    "technical": ["technical_analyst", "risk_analyst"],
    "strategic": ["strategy_analyst", "risk_analyst", "legal_analyst"],
    "risk": ["risk_analyst", "technical_analyst"],
    "legal": ["legal_analyst", "risk_analyst"],
    "general": [],
}

_FOCUS_AREAS: dict[str, list[str]] = {
    "financial_analyst": [
        "revenue trends",
        "margin analysis",
        "cost drivers",
        "expense breakdown",
    ],
    "customer_analyst": [
        "customer segments",
        "churn signals",
        "retention metrics",
        "LTV trends",
    ],
    "sales_analyst": [
        "pipeline health",
        "lead conversion",
        "territory performance",
        "quota attainment",
    ],
    "marketing_analyst": [
        "channel ROI",
        "campaign efficiency",
        "ad spend trends",
        "conversion rates",
    ],
    "product_analyst": [
        "feature adoption",
        "return rates",
        "catalog performance",
        "usage trends",
    ],
    "operations_analyst": [
        "delivery timelines",
        "bottlenecks",
        "inventory levels",
        "supply chain risks",
    ],
    "strategy_analyst": [
        "market positioning",
        "competitive landscape",
        "strategic gaps",
        "resource allocation",
    ],
    "technical_analyst": [
        "system dependencies",
        "architecture risks",
        "integration points",
        "tech debt",
    ],
    "legal_analyst": [
        "compliance gaps",
        "contractual obligations",
        "privacy regulations",
        "licensing",
    ],
    "risk_analyst": [
        "risk registers",
        "vulnerability signals",
        "mitigation status",
        "human-review items",
    ],
}

_PERSPECTIVES: dict[str, str] = {
    "financial_analyst": "Evaluate financial signals and monetary impact.",
    "customer_analyst": "Assess customer-facing drivers and retention risks.",
    "sales_analyst": "Review sales pipeline and lead-to-revenue conversion.",
    "marketing_analyst": "Assess marketing channel efficiency and ROI.",
    "product_analyst": "Evaluate product performance and feature signals.",
    "operations_analyst": "Review operational efficiency and delivery signals.",
    "strategy_analyst": "Consider strategic positioning and long-term risks.",
    "technical_analyst": "Assess technical architecture and dependency risks.",
    "legal_analyst": "Evaluate compliance and legal risk exposure.",
    "risk_analyst": "Identify and quantify cross-cutting risks.",
}

_ARTIFACT_TITLES: dict[str, str] = {
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

_ALLOWED_TOOLS: list[str] = [
    "read_context",
    "read_profiles",
    "read_graph",
    "read_insights",
    "save_artifact",
]

_ALL_ROLES: list[str] = sorted(
    {role for selected_roles in _ROLE_SELECTION.values() for role in selected_roles}
)


def build_dispatch_spec(
    question: str,
    higher_context: HigherContext | None = None,
) -> AgentDispatchSpec:
    """Build a deterministic AgentDispatchSpec for *question*.

    Returns a spec with selected personal contexts, dispatch order, skipped
    roles, and any missing inputs.
    """
    if higher_context is None:
        from decision_system.war_room.context_builder import build_higher_context

        higher_context = build_higher_context(question)

    analysis = analyze_problem(question)
    decision_type = str(
        higher_context.problem_analysis.get("decision_type") or analysis.decision_type
    )

    # Select roles
    selected_roles = list(_ROLE_SELECTION.get(decision_type, []))

    # Deduplicated dispatch order = selected_roles preserves insertion order
    skipped_roles = [r for r in _ALL_ROLES if r not in selected_roles]

    missing_inputs = _detect_missing_inputs(selected_roles, higher_context)

    # Build personal contexts
    personal_contexts = [
        _build_personal_context(role, decision_type, higher_context) for role in selected_roles
    ]

    dispatch_order = selected_roles

    return AgentDispatchSpec(
        run_id=higher_context.run_id,
        higher_context=higher_context,
        personal_contexts=personal_contexts,
        dispatch_order=dispatch_order,
        skipped_roles=skipped_roles,
        missing_inputs=missing_inputs,
    )


def _detect_missing_inputs(selected_roles: list[str], ctx: HigherContext) -> list[str]:
    """Return simple messages when required inputs are absent."""
    missing: list[str] = []
    if not ctx.required_data_categories:
        missing.append("No data categories available from analysis.")
    if not ctx.required_ontology_concepts:
        missing.append("No ontology concepts mapped yet (run map-ontology first).")
    if not ctx.relevant_insight_ids:
        missing.append("No relevant insights detected (run detect-patterns first).")
    if not selected_roles:
        missing.append("No specialist roles matched (question may be too general).")
    return missing


def _build_personal_context(
    role: str,
    decision_type: str,
    higher_context: HigherContext,
) -> PersonalAgentContext:
    """Create a PersonalAgentContext for one role."""
    agent_id = f"{role}-{higher_context.run_id[:8]}"
    task = _ARTIFACT_TITLES.get(role, f"{role} analysis")
    return PersonalAgentContext(
        agent_id=agent_id,
        role_name=role,
        role_type=role,
        assigned_task=f"Produce the '{task}' artifact for question: {higher_context.question}",
        perspective=_PERSPECTIVES.get(role, "General-purpose analysis."),
        allowed_tools=list(_ALLOWED_TOOLS),
        focus_areas=_FOCUS_AREAS.get(role, []),
        higher_context_ref=higher_context.run_id,
        private_notes=f"Decision type: {decision_type}.",
        output_requirements={
            "artifact_title": task,
            "must_cite_evidence": True,
            "must_cite_insight_ids": True,
        },
    )
