"""Deterministic problem analyzer for v0.4.

Maps a business question to required data categories, tools, roles,
ontology concepts, storage tiers, and any missing capabilities.
"""

from __future__ import annotations

from decision_system.orchestration.models import (
    DecisionType,
    ProblemAnalysis,
)

# ---------------------------------------------------------------------------
# Keyword -> decision_type mapping (ordered by length so more specific matches
# are checked first).
# ---------------------------------------------------------------------------

_DECISION_TYPE_KEYWORDS: list[tuple[list[str], DecisionType]] = [
    (["money", "profit", "revenue", "cost", "loss", "margin", "expense"], "financial"),
    (
        ["customer", "churn", "retention", "loyalty", "segment", "ltv", "clv"],
        "customer",
    ),
    (["sales", "region", "lead", "pipeline", "quota", "territory"], "sales"),
    (
        ["marketing", "ad", "channel", "roas", "campaign", "impressions", "ctr"],
        "marketing",
    ),
    (
        ["complaint", "ticket", "refund", "feedback", "sentiment", "nps"],
        "feedback",
    ),
    (["product", "return", "usage", "feature", "catalog", "inventory"], "product"),
    (
        ["competitor", "pricing", "market share", "competitive"],
        "competitor",
    ),
    (
        [
            "delivery",
            "manufacturing",
            "inventory",
            "bottleneck",
            "supply chain",
            "logistics",
        ],
        "operations",
    ),
    (
        ["website", "app", "traffic", "conversion", "bounce", "session", "page"],
        "analytics",
    ),
    (
        ["goal", "strategy", "objective", "market", "resource", "initiative"],
        "strategic",
    ),
    (["system", "technical", "architecture", "integration", "api"], "technical"),
    (["risk", "threat", "vulnerability", "compliance", "security"], "risk"),
]

# Second pass: broader terms
_BROADER_KEYWORDS: list[tuple[list[str], DecisionType]] = [
    (["financial", "revenue", "expense", "profit", "margin"], "financial"),
    (["customer", "client", "buyer", "user"], "customer"),
    (["sales", "leads", "opportunities"], "sales"),
    (["marketing", "ads", "channels"], "marketing"),
    (["complaint", "review", "ticket", "feedback"], "feedback"),
    (["product", "catalog", "inventory"], "product"),
    (["competitor", "price war", "benchmark"], "competitor"),
    (
        ["operations", "delivery", "bottleneck", "delay", "manufacturing"],
        "operations",
    ),
    (["analytics", "website", "app", "conversion", "bounce"], "analytics"),
    (
        ["goal", "strategy", "objective", "strategic", "initiative"],
        "strategic",
    ),
    (["system", "technical", "architecture"], "technical"),
    (["risk", "threat", "vulnerability", "compliance"], "risk"),
]

# ---------------------------------------------------------------------------
# Per-decision-type: data categories, tools, roles, ontology concepts, tiers
# ---------------------------------------------------------------------------

_TYPE_CONFIG: dict[str, dict[str, Any]] = {
    "financial": {
        "data_categories": ["financial"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "financial analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "revenue",
            "expense",
            "profit_margin",
            "strategic_goal",
            "constraint",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "customer": {
        "data_categories": ["customers"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "customer analyst",
            "sales analyst",
        ],
        "ontology_concepts": [
            "customer",
            "customer_segment",
            "customer_lifetime_value",
            "city",
            "region",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "sales": {
        "data_categories": ["sales"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "sales analyst",
            "customer analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "sales_amount",
            "lead_source",
            "customer",
            "region",
            "product",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "marketing": {
        "data_categories": ["marketing"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "marketing analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "marketing_channel",
            "marketing_spend",
            "click_count",
            "conversion_count",
            "conversion_rate",
            "bounce_rate",
            "lead_source",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "feedback": {
        "data_categories": ["feedback"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "product analyst",
            "customer analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "refund_requested",
            "sentiment",
            "complaint_issue",
            "customer",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "product": {
        "data_categories": ["products", "feedback"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "product analyst",
            "sales analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "product",
            "profit_margin",
            "customer",
            "competitor_price",
            "our_price",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "competitor": {
        "data_categories": ["competitors"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "strategy analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "competitor_price",
            "our_price",
            "review_score",
            "product",
            "market",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "operations": {
        "data_categories": ["operations"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "operations analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "operational_delay",
            "bottleneck",
            "dependency",
            "constraint",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "analytics": {
        "data_categories": ["analytics", "marketing"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
        ],
        "roles": [
            "marketing analyst",
            "sales analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "conversion_rate",
            "bounce_rate",
            "click_count",
            "conversion_count",
            "marketing_channel",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "strategic": {
        "data_categories": ["strategic", "financial"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "map-ontology",
            "detect-patterns",
            "extract-graph",
        ],
        "roles": [
            "strategy analyst",
            "financial analyst",
            "risk analyst",
            "judge / verifier",
        ],
        "ontology_concepts": [
            "strategic_goal",
            "constraint",
            "owner",
            "dependency",
            "contradiction",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "technical": {
        "data_categories": [],
        "tools": [
            "init-data-catalog",
            "extract-graph",
            "profile-data",
        ],
        "roles": [
            "technical analyst",
            "risk analyst",
        ],
        "ontology_concepts": [
            "dependency",
            "owner",
            "contradiction",
            "risk",
        ],
        "storage_tiers": ["tier_3"],
    },
    "risk": {
        "data_categories": ["financial", "operations", "feedback"],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
            "extract-graph",
            "detect-patterns",
        ],
        "roles": [
            "risk analyst",
            "technical analyst",
            "judge / verifier",
        ],
        "ontology_concepts": [
            "risk",
            "contradiction",
            "dependency",
            "constraint",
            "operational_delay",
            "bottleneck",
        ],
        "storage_tiers": ["tier_1", "tier_2", "tier_3", "tier_4"],
    },
    "general": {
        "data_categories": [],
        "tools": [
            "init-data-catalog",
            "seed-demo-data",
            "profile-data",
        ],
        "roles": [],
        "ontology_concepts": [],
        "storage_tiers": ["tier_2"],
    },
}


def _detect_decision_type(question: str) -> tuple[DecisionType, str]:
    """Return (decision_type, reason) for *question* using keyword rules."""
    q = question.lower()
    for keywords, dtype in _DECISION_TYPE_KEYWORDS:
        for kw in keywords:
            if kw in q:
                return dtype, f"matched keyword '{kw}'"
    for keywords, dtype in _BROADER_KEYWORDS:
        for kw in keywords:
            if kw in q:
                return dtype, f"matched broader keyword '{kw}'"
    return "general", "no keywords matched"


def analyze_problem(question: str) -> ProblemAnalysis:
    """Analyze *question* and return a ProblemAnalysis.

    All rules are deterministic keyword patterns. No LLM call.
    """
    dtype, reason = _detect_decision_type(question)
    config = _TYPE_CONFIG.get(dtype, _TYPE_CONFIG["general"])

    # Build analysis notes
    notes_parts = [f"Decision type '{dtype}' (matched: {reason})."]
    if config["data_categories"]:
        cats = ", ".join(config["data_categories"])
        notes_parts.append(f"Relevant data categories: {cats}.")
    missing = config.get("missing_capabilities", [])
    if missing:
        notes_parts.append(
            "Missing capabilities: "
            + ", ".join(missing)
            + "."
        )
    else:
        notes_parts.append("No missing capabilities identified.")

    return ProblemAnalysis(
        question=question,
        decision_type=dtype,
        required_data_categories=list(config["data_categories"]),
        required_tools=list(config["tools"]),
        relevant_roles=list(config["roles"]),
        required_ontology_concepts=list(config["ontology_concepts"]),
        required_storage_tiers=list(config["storage_tiers"]),
        missing_capabilities=list(config.get("missing_capabilities", [])),
        analysis_notes=" ".join(notes_parts),
    )
