"""Deterministic column-to-ontology mapping engine for v0.4.

Uses column names (case-insensitive) and dataset category to map raw CSV
columns to ontology concepts. No LLM call is required — rules are
simple exact/synonym lookups.
"""

from __future__ import annotations

from collections import defaultdict

from decision_system.data_catalog.models import DatasetProfile, DataCategory
from decision_system.ontology.models import (
    ColumnMapping,
    OntologyConcept,
    OntologyMap,
    ConceptType,
)

# ---------------------------------------------------------------------------
# Default ontology concepts
# ---------------------------------------------------------------------------

DEFAULT_CONCEPTS: list[OntologyConcept] = [
    OntologyConcept(concept_id="revenue", name="Revenue", concept_type="metric", description="Gross or net revenue", aliases=["total_revenue"]),
    OntologyConcept(concept_id="expense", name="Expense", concept_type="metric", description="Business expenses / costs"),
    OntologyConcept(concept_id="profit_margin", name="Profit Margin", concept_type="metric", description="Gross or net profit margin", aliases=["gross_margin", "net_margin"]),
    OntologyConcept(concept_id="product", name="Product", concept_type="entity", description="Product or service name"),
    OntologyConcept(concept_id="customer", name="Customer", concept_type="entity", description="Customer or consumer"),
    OntologyConcept(concept_id="customer_segment", name="Customer Segment", concept_type="entity", description="Customer segment / tier / vertical", aliases=["segment", "tier"]),
    OntologyConcept(concept_id="customer_lifetime_value", name="Customer Lifetime Value", concept_type="metric", description="Customer CLV / LTV", aliases=["lifetime_value", "ltv", "clv"]),
    OntologyConcept(concept_id="city", name="City", concept_type="signal", description="City / locality"),
    OntologyConcept(concept_id="region", name="Region", concept_type="signal", description="Geographic region"),
    OntologyConcept(concept_id="sales_amount", name="Sales Amount", concept_type="metric", description="Sales transaction amount"),
    OntologyConcept(concept_id="lead_source", name="Lead Source", concept_type="signal", description="Marketing lead / traffic source", aliases=["channel", "traffic_source", "source_channel"]),
    OntologyConcept(concept_id="marketing_channel", name="Marketing Channel", concept_type="signal", description="Marketing channel name"),
    OntologyConcept(concept_id="marketing_spend", name="Marketing Spend", concept_type="metric", description="Marketing spend / ad spend"),
    OntologyConcept(concept_id="click_count", name="Click Count", concept_type="metric", description="Number of clicks"),
    OntologyConcept(concept_id="conversion_count", name="Conversion Count", concept_type="metric", description="Number of conversions / leads / purchases"),
    OntologyConcept(concept_id="conversion_rate", name="Conversion Rate", concept_type="metric", description="Conversion rate (decimal)", aliases=["conversion_rate_pct"]),
    OntologyConcept(concept_id="bounce_rate", name="Bounce Rate", concept_type="signal", description="Bounce rate (decimal)", aliases=["bounce_rate_pct"]),
    OntologyConcept(concept_id="refund_requested", name="Refund Requested", concept_type="signal", description="Whether a refund was requested"),
    OntologyConcept(concept_id="sentiment", name="Sentiment", concept_type="signal", description="Feedback sentiment"),
    OntologyConcept(concept_id="complaint_issue", name="Complaint Issue", concept_type="signal", description="Type of complaint / issue", aliases=["issue_type", "problem_type", "ticket_type"]),
    OntologyConcept(concept_id="competitor_price", name="Competitor Price", concept_type="metric", description="Competitor's price"),
    OntologyConcept(concept_id="our_price", name="Our Price", concept_type="metric", description="Our / company price", aliases=["company_price", "list_price"]),
    OntologyConcept(concept_id="review_score", name="Review Score", concept_type="metric", description="Competitor or product review score", aliases=["rating", "review_rating"]),
    OntologyConcept(concept_id="operational_delay", name="Operational Delay", concept_type="metric", description="Average delay in days", aliases=["delay_days", "avg_delay"]),
    OntologyConcept(concept_id="bottleneck", name="Bottleneck", concept_type="risk", description="Process bottleneck flag", aliases=["is_bottleneck"]),
    OntologyConcept(concept_id="strategic_goal", name="Strategic Goal", concept_type="entity", description="Strategic initiative or goal", aliases=["objective", "initiative", "goal"]),
    OntologyConcept(concept_id="constraint", name="Constraint", concept_type="risk", description="Constraint or blocker"),
    OntologyConcept(concept_id="owner", name="Owner", concept_type="entity", description="Person or team who owns something", aliases=["owned_by", "lead", "responsible"]),
    OntologyConcept(concept_id="dependency", name="Dependency", concept_type="relationship", description="Technical or business dependency"),
    OntologyConcept(concept_id="contradiction", name="Contradiction", concept_type="risk", description="Contradictory statement or decision"),
    OntologyConcept(concept_id="risk", name="Risk", concept_type="risk", description="Generic risk signal", aliases=["risk_factor"]),
]

# ---------------------------------------------------------------------------
# Column-name -> concept mapping rules
# ---------------------------------------------------------------------------
# Ordered list of (column_name_lower, concept_id)
# First match wins.

COLUMN_RULES: list[tuple[str, str]] = [
    # Financial
    ("revenue", "revenue"),
    ("total_revenue", "revenue"),
    ("gross_revenue", "revenue"),
    ("net_revenue", "revenue"),
    ("monthly_revenue", "revenue"),
    ("expenses", "expense"),
    ("total_expenses", "expense"),
    ("cost", "expense"),
    ("costs", "expense"),
    ("spend", "expense"),
    ("operating_expenses", "expense"),
    ("profit_margin", "profit_margin"),
    ("margin", "profit_margin"),
    ("gross_margin", "profit_margin"),
    ("net_margin", "profit_margin"),
    # Product
    ("product", "product"),
    ("product_name", "product"),
    ("product_id", "product"),
    ("item", "product"),
    ("item_name", "product"),
    # Customer
    ("customer", "customer"),
    ("customer_id", "customer"),
    ("customer_name", "customer"),
    ("lifetime_value", "customer_lifetime_value"),
    ("ltv", "customer_lifetime_value"),
    ("clv", "customer_lifetime_value"),
    ("segment", "customer_segment"),
    ("customer_segment", "customer_segment"),
    ("tier", "customer_segment"),
    ("city", "city"),
    ("region", "region"),
    ("country", "region"),
    ("industry", "customer_segment"),
    ("vertical", "customer_segment"),
    # Sales
    ("sales_amount", "sales_amount"),
    ("amount", "sales_amount"),
    ("total_amount", "sales_amount"),
    ("order_amount", "sales_amount"),
    ("unit_price", "our_price"),
    ("quantity", "product"),
    ("units_sold", "product"),
    ("units", "product"),
    ("qty_sold", "product"),
    ("quantity_sold", "product"),
    # Marketing
    ("lead_source", "lead_source"),
    ("marketing_channel", "marketing_channel"),
    ("channel", "marketing_channel"),
    ("campaign_channel", "marketing_channel"),
    ("traffic_source", "lead_source"),
    ("source_channel", "lead_source"),
    ("source", "lead_source"),
    ("marketing_spend", "marketing_spend"),
    ("ad_spend", "marketing_spend"),
    ("spend", "marketing_spend"),
    ("clicks", "click_count"),
    ("click_count", "click_count"),
    ("conversions", "conversion_count"),
    ("converted", "conversion_count"),
    ("leads", "conversion_count"),
    ("conversion_count", "conversion_count"),
    ("conversion_rate", "conversion_rate"),
    ("conversion_rate_pct", "conversion_rate"),
    ("bounce_rate", "bounce_rate"),
    ("bounce_rate_pct", "bounce_rate"),
    ("sessions", "conversion_rate"),
    ("page_sessions", "conversion_rate"),
    ("visits", "conversion_rate"),
    # Feedback
    ("refund_requested", "refund_requested"),
    ("refund", "refund_requested"),
    ("requested_refund", "refund_requested"),
    ("sentiment", "sentiment"),
    ("tone", "sentiment"),
    ("issue_type", "complaint_issue"),
    ("issue", "complaint_issue"),
    ("ticket_type", "complaint_issue"),
    ("problem_type", "complaint_issue"),
    # Competitor
    ("competitor_price", "competitor_price"),
    ("competitor", "competitor_price"),
    ("our_price", "our_price"),
    ("company_price", "our_price"),
    ("list_price", "our_price"),
    ("review_score", "review_score"),
    ("rating", "review_score"),
    ("review_rating", "review_score"),
    ("product_category", "product"),
    ("category", "product"),
    # Operations
    ("average_delay_days", "operational_delay"),
    ("delay_days", "operational_delay"),
    ("avg_delay", "operational_delay"),
    ("delay", "operational_delay"),
    ("bottleneck", "bottleneck"),
    ("is_bottleneck", "bottleneck"),
    ("process_name", "bottleneck"),
    ("process", "bottleneck"),
    ("operation", "bottleneck"),
    ("cost", "expense"),
    ("monthly_cost", "expense"),
    ("avg_cost", "expense"),
    ("return_rate", "risk"),
    ("returns", "risk"),
    ("return_ratio", "risk"),
    # Strategic
    ("goal", "strategic_goal"),
    ("objective", "strategic_goal"),
    ("initiative", "strategic_goal"),
    ("strategy", "strategic_goal"),
    ("priority", "strategic_goal"),
    ("priority_level", "strategic_goal"),
    ("tier", "strategic_goal"),
    ("constraint", "constraint"),
    ("blocker", "constraint"),
    ("risk_factor", "risk"),
    ("owner", "owner"),
    ("owned_by", "owner"),
    ("lead", "owner"),
    ("responsible", "owner"),
    ("team", "owner"),
    ("page", "conversion_rate"),
    ("page_path", "conversion_rate"),
    ("url", "conversion_rate"),
    ("landing_page", "conversion_rate"),
    ("traffic_source", "lead_source"),
    ("month", "revenue"),
    ("period", "revenue"),
    ("date", "revenue"),
    ("date_month", "revenue"),
]

# Build lookup: lower(name) -> (concept_id, is_primary)
_RULES_LOOKUP: dict[str, str] = {}
_LOWERCASED: dict[str, str] = {}
for col_name, concept_id in COLUMN_RULES:
    low = col_name.lower()
    idx = len([r for r in COLUMN_RULES if r[0].lower() == low])
    _RULES_LOOKUP[low] = concept_id
    _LOWERCASED[col_name.lower()] = col_name

_CATEGORY_HINTS: dict[str, dict[str, str]] = {
    "financial": {"profit_margin": "profit_margin"},
    "marketing": {"revenue": "revenue", "spend": "marketing_spend", "channel": "marketing_channel"},
    "competitors": {"price": "competitor_price", "review": "review_score"},
    "operations": {"delay": "operational_delay"},
    "analytics": {"bounce": "bounce_rate", "conversion": "conversion_rate"},
}

# Build a concept_id -> OntologyConcept lookup
_CONCEPTS_BY_ID: dict[str, OntologyConcept] = {c.concept_id: c for c in DEFAULT_CONCEPTS}


def _match_concept(column_name: str, category: str) -> str | None:
    """Return a concept_id for *column_name* in *category*, or None."""
    low = column_name.lower().strip()
    exact = _RULES_LOOKUP.get(low)
    if exact:
        return exact
    # Partial match
    for rule_col, concept_id in COLUMN_RULES:
        if rule_col.lower() in low or low in rule_col.lower():
            return concept_id
    return None


def map_profiles_to_ontology(profiles) -> OntologyMap:
    """Map all columns in a DataProfileStore to ontology concepts.

    Returns an OntologyMap containing all default concepts plus
    ColumnMapping entries for every column found in the profiles.
    """
    omap = OntologyMap(concepts=list(DEFAULT_CONCEPTS))
    for profile in profiles.profiles:
        for col in profile.columns:
            concept_id = _match_concept(col.name, profile.category)
            if concept_id is None:
                continue
            concept = _CONCEPTS_BY_ID.get(concept_id)
            mapping = ColumnMapping(
                dataset_id=profile.dataset_id,
                source_filename=profile.filename,
                category=profile.category,
                column_name=col.name,
                mapped_concept_id=concept_id,
                mapped_concept_name=concept.name if concept else concept_id,
                confidence="high",
                reason=f"Column name '{col.name}' matches ontology concept '{concept_id}'",
            )
            omap.column_mappings.append(mapping)
    return omap
