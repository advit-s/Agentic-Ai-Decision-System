"""Deterministic dispatcher for the v0.4 orchestration layer.

Maps a ProblemAnalysis onto a DispatchPlan: which tools to run, which
roles to assign, which artifacts to load, and in what order.

All logic is rule-based. No LLM call.
"""

from __future__ import annotations

from decision_system.orchestration.models import (
    DispatchPlan,
    ProblemAnalysis,
)

# ---------------------------------------------------------------------------
# Static tool registry: every tool in the project mapped to the categories
# it can handle, artifacts it reads/writes, and relevant roles.
# ---------------------------------------------------------------------------

_TOOLS: dict[str, dict] = {
    "init-data-catalog": {
        "categories": [],
        "artifacts_read": [],
        "artifacts_write": [
            "company_data/*/",
            "company_data/manifest.json",
        ],
        "roles": [],
    },
    "seed-demo-data": {
        "categories": [],
        "artifacts_read": [],
        "artifacts_write": [
            "company_data/*/demo_*.csv",
        ],
        "roles": [],
    },
    "import-datasets": {
        "categories": [],
        "artifacts_read": ["datasets/"],
        "artifacts_write": [
            "company_data/*/",
            ".decision_system/imports/import_manifest.json",
        ],
        "roles": [],
    },
    "profile-data": {
        "categories": [
            "financial",
            "customers",
            "sales",
            "marketing",
            "feedback",
            "products",
            "competitors",
            "operations",
            "analytics",
            "strategic",
        ],
        "artifacts_read": [
            "company_data/*/",
            "company_data/manifest.json",
        ],
        "artifacts_write": [
            ".decision_system/data_profiles/profiles.json",
        ],
        "roles": [],
    },
    "map-ontology": {
        "categories": [
            "financial",
            "customers",
            "sales",
            "marketing",
            "feedback",
            "products",
            "competitors",
            "operations",
            "analytics",
            "strategic",
        ],
        "artifacts_read": [
            ".decision_system/data_profiles/profiles.json",
        ],
        "artifacts_write": [
            ".decision_system/ontology/ontology_map.json",
        ],
        "roles": [],
    },
    "extract-graph": {
        "categories": [],
        "artifacts_read": [
            "company_docs/",
        ],
        "artifacts_write": [
            ".decision_system/graph/knowledge_graph.json",
        ],
        "roles": ["technical analyst"],
    },
    "detect-patterns": {
        "categories": [
            "financial",
            "customers",
            "sales",
            "marketing",
            "feedback",
            "products",
            "competitors",
            "operations",
            "analytics",
            "strategic",
        ],
        "artifacts_read": [
            ".decision_system/data_profiles/profiles.json",
            ".decision_system/ontology/ontology_map.json",
            ".decision_system/graph/knowledge_graph.json",
            "company_data/*/",
        ],
        "artifacts_write": [
            ".decision_system/insights/insights.json",
        ],
        "roles": [
            "risk analyst",
        ],
    },
}

# ---------------------------------------------------------------------------
# Category -> roles mapping
# ---------------------------------------------------------------------------

_ROLE_RULES: dict[str, list[str]] = {
    "financial": ["financial analyst", "risk analyst"],
    "customers": ["customer analyst", "sales analyst"],
    "sales": ["sales analyst", "customer analyst", "risk analyst"],
    "marketing": ["marketing analyst", "risk analyst"],
    "feedback": ["product analyst", "customer analyst", "risk analyst"],
    "products": ["product analyst", "sales analyst", "risk analyst"],
    "competitors": ["strategy analyst", "risk analyst"],
    "operations": ["operations analyst", "risk analyst"],
    "analytics": ["marketing analyst", "sales analyst", "risk analyst"],
    "strategic": ["strategy analyst", "judge / verifier"],
    "technical": ["technical analyst", "risk analyst"],
    "risk": ["risk analyst", "technical analyst", "judge / verifier"],
}


def _select_tools(analysis: ProblemAnalysis) -> tuple[list[str], list[str]]:
    """Return (selected_tools, skipped_tools)."""
    selected: list[str] = []
    skipped: list[str] = []
    cats = set(analysis.required_data_categories)

    # Stage 1: data preparation (always needed when categories are present)
    prep_tools = ["init-data-catalog", "seed-demo-data", "import-datasets"]
    for tool in prep_tools:
        selected.append(tool)

    # Stage 2: data profiling (if we have data categories)
    if cats:
        selected.append("profile-data")

    # Stage 3: ontology (if profiling is selected)
    if "profile-data" in selected:
        selected.append("map-ontology")

    # Stage 4: graph extraction (selected when strategic/technical/risk types)
    if analysis.decision_type in ("strategic", "technical", "risk"):
        selected.append("extract-graph")

    # Stage 5: pattern detection (if we have profiles or graph)
    if "profile-data" in selected or "extract-graph" in selected:
        selected.append("detect-patterns")

    skipped = [t for t in _TOOLS if t not in selected]
    return selected, skipped


def _select_roles(analysis: ProblemAnalysis) -> list[str]:
    """Return deduplicated relevant roles for the decision type."""
    seen: set[str] = set()
    roles: list[str] = []
    for cat in analysis.required_data_categories:
        for role in _ROLE_RULES.get(cat, []):
            if role not in seen:
                seen.add(role)
                roles.append(role)
    # Also include roles from problem analysis
    for role in analysis.relevant_roles:
        if role not in seen:
            seen.add(role)
            roles.append(role)
    return roles


def _select_artifacts(analysis: ProblemAnalysis) -> list[str]:
    """Return artifact paths likely needed for this run."""
    artifacts: list[str] = [
        ".decision_system/data_profiles/profiles.json",
        ".decision_system/ontology/ontology_map.json",
        ".decision_system/insights/insights.json",
        ".decision_system/graph/knowledge_graph.json",
    ]
    for cat in analysis.required_data_categories:
        artifacts.append(f"company_data/{cat}/")
    return artifacts


def _execution_order(selected_tools: list[str]) -> list[str]:
    """Enforce a deterministic execution ordering."""
    priority = [
        "init-data-catalog",
        "seed-demo-data",
        "import-datasets",
        "profile-data",
        "extract-graph",
        "map-ontology",
        "detect-patterns",
    ]
    ordered: list[str] = []
    seen: set[str] = set()
    for tool in priority:
        if tool in selected_tools and tool not in seen:
            ordered.append(tool)
            seen.add(tool)
    for tool in selected_tools:
        if tool not in seen:
            ordered.append(tool)
            seen.add(tool)
    return ordered


def build_dispatch_plan(analysis: ProblemAnalysis) -> DispatchPlan:
    """Build a DispatchPlan from a ProblemAnalysis."""

    selected, skipped = _select_tools(analysis)
    roles = _select_roles(analysis)
    artifacts = _select_artifacts(analysis)
    order = _execution_order(selected)

    return DispatchPlan(
        selected_tools=selected,
        selected_roles=roles,
        selected_artifacts=artifacts,
        execution_order=order,
        skipped_tools=skipped,
        missing_inputs=analysis.missing_capabilities,
    )
