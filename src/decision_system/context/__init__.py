"""Decision context package for v0.5 insight-aware reports."""

from decision_system.context.builder import DecisionContextBuilder
from decision_system.context.inspector import inspect_context, render_context_inspection
from decision_system.context.models import DecisionContext, InsightEvidence
from decision_system.context.selector import (
    select_relevant_insights,
    select_relevant_ontology_concepts,
)
from decision_system.context.store import (
    DEFAULT_CONTEXT_DIR,
    load_context,
    save_context,
)

__all__ = [
    "InsightEvidence",
    "DecisionContext",
    "DecisionContextBuilder",
    "select_relevant_ontology_concepts",
    "select_relevant_insights",
    "save_context",
    "load_context",
    "DEFAULT_CONTEXT_DIR",
    "inspect_context",
    "render_context_inspection",
]
