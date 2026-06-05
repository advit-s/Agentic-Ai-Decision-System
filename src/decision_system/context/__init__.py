"""Decision context package for v0.5 insight-aware reports."""

from decision_system.context.models import InsightEvidence, DecisionContext
from decision_system.context.builder import DecisionContextBuilder
from decision_system.context.selector import select_relevant_ontology_concepts, select_relevant_insights
from decision_system.context.store import save_context, load_context, DEFAULT_CONTEXT_DIR
from decision_system.context.inspector import inspect_context, render_context_inspection

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