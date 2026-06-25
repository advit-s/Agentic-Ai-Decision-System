"""End-to-end orchestration workflow for v0.4.

Ties together: session creation -> problem analysis -> planning ->
dispatch plan -> sandbox execution -> judge summary -> persistence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from decision_system._data_root import get_data_root
from decision_system.data_catalog.models import (
    DataProfileStore,
)
from decision_system.insights.models import InsightStore
from decision_system.ontology.mapper import map_profiles_to_ontology
from decision_system.orchestration.dispatcher import build_dispatch_plan
from decision_system.orchestration.judge import build_judge_summary
from decision_system.orchestration.planner import plan_data_tools_roles
from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.orchestration.sandbox import sandbox_execute
from decision_system.orchestration.session import create_session
from decision_system.orchestration.store import save_decision_session


def _default_runs_dir() -> Path:
    """Return the default runs directory (lazy)."""
    return get_data_root() / "orchestration" / "runs"


def run_orchestration(
    question: str,
    *,
    base_data_root: Path | str | None = None,
    save: bool = True,
) -> dict[str, Any]:
    """Run the full orchestration pipeline for *question*.

    Returns a dict with all intermediate and final results.
    """
    if base_data_root is None:
        base_data_root = get_data_root() / "graph"

    # 1. Session
    session = create_session(question)

    # 2. Problem analysis
    analysis = analyze_problem(question)
    analysis = plan_data_tools_roles(analysis, base_data_root=base_data_root)

    # 3. Dispatch plan
    dispatch = build_dispatch_plan(analysis)

    # 4. Sandbox execution
    context: dict[str, Any] = {
        "base_data_root": base_data_root,
    }

    # 4a. Load profiles
    try:
        profiles = sandbox_execute("read_profiles", context)
    except Exception:  # noqa: BLE001
        profiles = DataProfileStore()
    context["profiles"] = profiles

    # 4b. Load graph
    try:
        graph = sandbox_execute("read_graph", context)
    except Exception:  # noqa: BLE001
        from decision_system.graphing.models import KnowledgeGraph

        graph = KnowledgeGraph()
    context["knowledge_graph"] = graph

    # 4c. Load and save ontology
    ontology_map = map_profiles_to_ontology(profiles)
    context["ontology_map"] = ontology_map
    sandbox_execute("save_ontology", context)

    # 4d. Run detectors
    insights = sandbox_execute(
        "run_detectors",
        {"profiles": profiles, "knowledge_graph": graph, "csv_root": base_data_root},
    )
    assert isinstance(insights, InsightStore), "run_detectors must return InsightStore"
    context["insights"] = insights
    sandbox_execute("save_insights", context)

    # 5. Judge summary
    missing_data_items = []
    for profile in profiles.profiles:
        for col in profile.columns:
            if col.missing_pct > 0.20:
                missing_data_items.append(
                    f"{profile.filename}: '{col.name}' is {col.missing_pct:.0%} missing"
                )

    judge = build_judge_summary(
        run_id=session.run_id,
        insights=insights,
        missing_data_items=missing_data_items,
    )

    # 6. Build result
    result = {
        "run_id": session.run_id,
        "session_id": session.session_id,
        "question": question,
        "status": "completed",
        "decision_type": analysis.decision_type,
        "analysis_notes": analysis.analysis_notes,
        "required_data_categories": analysis.required_data_categories,
        "required_tools": dispatch.selected_tools,
        "execution_order": dispatch.execution_order,
        "skipped_tools": dispatch.skipped_tools,
        "relevant_roles": dispatch.selected_roles,
        "selected_artifacts": dispatch.selected_artifacts,
        "storage_tiers_used": analysis.required_storage_tiers,
        "missing_inputs": dispatch.missing_inputs,
        "ontology_concept_count": len(ontology_map.concepts),
        "mapped_column_count": len(ontology_map.column_mappings),
        "insight_count": len(insights.insights),
        "insights_by_severity": dict(insights.severity_counts()),
        "insights_by_category": dict(insights.category_counts()),
        "judge": {
            "run_id": judge.run_id,
            "confidence_level": judge.confidence_level,
            "key_findings": judge.key_findings[:10],
            "risks": judge.risks[:10],
            "missing_data": judge.missing_data,
            "recommended_next_actions": judge.recommended_next_actions[:10],
            "human_review_required": judge.human_review_required[:10],
        },
        "saved_path": None,
    }

    if save:
        session.required_data_categories = analysis.required_data_categories
        session.required_tools = dispatch.selected_tools
        session.relevant_roles = dispatch.selected_roles
        session.status = "completed"
        session.storage_tiers_used = analysis.required_storage_tiers
        session.context_summary = analysis.analysis_notes
        session.decision_type = analysis.decision_type
        session.execution_order = dispatch.execution_order
        session.skipped_tools = dispatch.skipped_tools
        session.selected_artifacts = dispatch.selected_artifacts
        session.missing_inputs = dispatch.missing_inputs
        session.ontology_concept_count = result["ontology_concept_count"]
        session.mapped_column_count = result["mapped_column_count"]
        session.insight_count = result["insight_count"]
        session.insights_by_severity = result["insights_by_severity"]
        session.insights_by_category = result["insights_by_category"]
        session.judge_summary = result["judge"]
        saved = save_decision_session(session)
        result["saved_path"] = str(saved)

    return result


def run_orchestration_dict(question: str, **kwargs: Any) -> dict[str, Any]:
    """Public wrapper matching the expected function signature in tests."""
    return run_orchestration(question, **kwargs)
