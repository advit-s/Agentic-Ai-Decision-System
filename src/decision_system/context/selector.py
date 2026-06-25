"""Selection logic for ontology concepts and insights."""

from __future__ import annotations

from typing import Any

from decision_system.insights.models import Insight, InsightStore
from decision_system.ontology.models import OntologyConcept, OntologyMap
from decision_system.orchestration.problem_analyzer import ProblemAnalysis


# Category keywords for matching insights to questions
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "revenue_risk": ["money", "revenue", "loss", "profit", "expense", "cost", "margin"],
    "profit_margin_risk": ["margin", "profit", "profitability"],
    "customer_concentration": ["customer", "churn", "retention", "loyalty", "segment"],
    "sales_channel_risk": ["sales", "region", "lead", "pipeline", "quota", "territory"],
    "marketing_roi_risk": ["marketing", "ad", "channel", "roas", "campaign", "impressions", "ctr"],
    "feedback_risk": ["complaint", "ticket", "refund", "feedback", "sentiment", "nps"],
    "product_risk": ["product", "return", "usage", "feature", "catalog", "inventory"],
    "competitor_risk": ["competitor", "pricing", "market share", "competitive"],
    "operations_bottleneck": ["delivery", "manufacturing", "inventory", "bottleneck", "supply chain", "logistics", "delay"],
    "analytics_conversion_risk": ["website", "app", "traffic", "conversion", "bounce", "session", "page"],
    "data_quality": ["data quality", "quality", "warning"],
    "missing_data": ["missing", "null", "empty"],
    "dependency_risk": ["dependency", "depends", "coupling"],
    "contradiction": ["contradiction", "conflict", "contradict"],
    "strategic_gap": ["goal", "strategy", "objective", "strategic", "initiative", "target"],
    "security_risk": ["security", "vulnerability", "threat", "compliance"],
}


def _question_matches_category(question: str, category: str) -> bool:
    """Check if question keywords match an insight category."""
    q = question.lower()
    keywords = _CATEGORY_KEYWORDS.get(category, [])
    for kw in keywords:
        if kw in q:
            return True
    return False


def _data_category_matches_insight_category(data_categories: list[str], insight_category: str) -> bool:
    """Check if required data categories align with insight category."""
    category_to_data = {
        "revenue_risk": ["financial"],
        "profit_margin_risk": ["financial"],
        "customer_concentration": ["customers"],
        "sales_channel_risk": ["sales"],
        "marketing_roi_risk": ["marketing"],
        "feedback_risk": ["feedback"],
        "product_risk": ["products"],
        "competitor_risk": ["competitors"],
        "operations_bottleneck": ["operations"],
        "analytics_conversion_risk": ["analytics", "marketing"],
        "data_quality": [],
        "missing_data": [],
        "dependency_risk": [],
        "contradiction": [],
        "strategic_gap": ["strategic", "financial"],
        "security_risk": [],
    }
    relevant = category_to_data.get(insight_category, [])
    return any(dc in relevant for dc in data_categories)


def select_relevant_ontology_concepts(
    analysis: ProblemAnalysis,
    omap: OntologyMap,
    question: str,
) -> list[dict[str, Any]]:
    """Select ontology concepts relevant to the problem analysis and question."""
    if not omap.concepts:
        return []

    # Start with required concepts from problem analysis
    required_ids = set(analysis.required_ontology_concepts or [])
    q_lower = question.lower()

    # Add concepts whose aliases or names match question keywords
    matched_ids = set()
    for concept in omap.concepts:
        if concept.concept_id in required_ids:
            matched_ids.add(concept.concept_id)
            continue
        # Check aliases and name
        search_terms = [concept.name.lower()] + [a.lower() for a in concept.aliases]
        for term in search_terms:
            if term and term in q_lower:
                matched_ids.add(concept.concept_id)
                break

    # Return full concept dicts, prioritizing required
    result = []
    for concept in omap.concepts:
        if concept.concept_id in matched_ids:
            is_required = concept.concept_id in required_ids
            result.append({
                "concept_id": concept.concept_id,
                "name": concept.name,
                "type": concept.concept_type,
                "description": concept.description,
                "category": concept.category,
                "required": is_required,
            })

    # Sort: required first, then alphabetical
    result.sort(key=lambda x: (0 if x["required"] else 1, x["concept_id"]))
    return result


def select_relevant_insights(
    analysis: ProblemAnalysis,
    store: InsightStore,
    question: str,
) -> list[Insight]:
    """Select insights relevant to the problem analysis, question, and keywords."""
    if not store.insights:
        return []

    data_categories = analysis.required_data_categories or []
    q_lower = question.lower()

    selected = []
    for insight in store.insights:
        # Always include high/critical severity
        if insight.severity in ("high", "critical"):
            selected.append(insight)
            continue

        # Match by data category
        if _data_category_matches_insight_category(data_categories, insight.category):
            selected.append(insight)
            continue

        # Match by question keywords to category
        if _question_matches_category(q_lower, insight.category):
            selected.append(insight)
            continue

        # Match by ontology concept overlap
        required_concepts = set(analysis.required_ontology_concepts or [])
        if required_concepts and set(insight.ontology_concepts).intersection(required_concepts):
            selected.append(insight)
            continue

    # Deduplicate by insight_id
    seen = set()
    deduped = []
    for i in selected:
        if i.insight_id not in seen:
            seen.add(i.insight_id)
            deduped.append(i)

    # Sort by severity (critical first) then by category
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    deduped.sort(key=lambda i: (severity_order.get(i.severity, 99), i.category))
    return deduped
