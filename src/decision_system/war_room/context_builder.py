"""Build immutable HigherContext for a war-room run."""

from __future__ import annotations

from uuid import uuid4

from decision_system.context.builder import DecisionContextBuilder
from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.orchestration.session import create_session
from decision_system.war_room.models import HigherContext


def build_higher_context(question: str) -> HigherContext:
    """Create an immutable HigherContext for the given question.

    Steps:
    1. Analyse the question via the deterministic problem analyser.
    2. Build a DecisionContext for richer signals (handles missing stores).
    3. Assemble the frozen ``HigherContext``.
    """
    analysis = analyze_problem(question)

    # Build richer context from local stores (may be empty on first run)
    try:
        builder = DecisionContextBuilder()
        decision_context = builder.build(question=question)
        relevant_insight_ids = [i.insight_id for i in decision_context.relevant_insights]
        relevant_storage_tiers = decision_context.relevant_storage_tiers
        ontology_concepts = [
            c.get("concept_id", "") if isinstance(c, dict) else str(c)
            for c in decision_context.relevant_ontology_concepts
        ]
        categories = decision_context.relevant_data_categories
        summary_parts = [decision_context.judge_summary.get("summary", "")]
    except Exception:  # noqa: BLE001  # pragma: no cover - defensive
        relevant_insight_ids = []
        relevant_storage_tiers = analysis.required_storage_tiers
        ontology_concepts = analysis.required_ontology_concepts
        categories = analysis.required_data_categories
        summary_parts = []

    summary_parts.append(analysis.analysis_notes)
    decision_context_summary = " ".join(s for s in summary_parts if s)

    # Use the orchestration run_id as the war-room run_id for traceability
    run_id = create_session(question).run_id

    return HigherContext(
        run_id=run_id,
        question=question,
        problem_analysis=analysis.model_dump(mode="json"),
        decision_context_summary=decision_context_summary,
        required_data_categories=categories,
        required_ontology_concepts=ontology_concepts,
        relevant_insight_ids=relevant_insight_ids,
        relevant_storage_tiers=relevant_storage_tiers,
        constraints=["All outputs must cite evidence or insight IDs", "No destructive tool actions"],
        allowed_tools=["read_profiles", "read_graph", "read_insights", "read_context", "save_artifact"],
        evidence_requirements={"minimum_sources": 1, "must_cite_insight_ids": True},
    )
