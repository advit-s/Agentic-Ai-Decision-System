"""Planner for v0.4 orchestration.

Takes a ProblemAnalysis and returns enriched planning metadata:
a refined tool list, concrete artifact paths, and a human-readable
context_summary string.
"""

from __future__ import annotations

from pathlib import Path

from decision_system.orchestration.models import (
    ProblemAnalysis,
)


def _artifact_paths_for_categories(categories: list[str]) -> list[str]:
    """Return on-disk artifact paths that feed into orchestration."""
    paths: list[str] = []

    # Always-relevant base paths
    paths.append(".decision_system/data_profiles/profiles.json")
    paths.append(".decision_system/ontology/ontology_map.json")
    paths.append(".decision_system/insights/insights.json")
    paths.append(".decision_system/graph/knowledge_graph.json")

    # Category-specific CSV roots
    for cat in categories:
        paths.append(f"company_data/{cat}/")
        paths.append(f".decision_system/data_profiles/profiles.json#{cat}")

    return paths


def _default_context_summary(analysis: ProblemAnalysis, artifact_paths: list[str]) -> str:
    parts = [
        f"Question: '{analysis.question}'",
        f"Decision type: {analysis.decision_type}",
        f"Data categories: {', '.join(analysis.required_data_categories) or 'none'}",
        f"Ontology concepts: {', '.join(analysis.required_ontology_concepts) or 'none'}",
        f"Tools: {len(analysis.required_tools)} selected",
        f"Roles: {', '.join(analysis.relevant_roles) or 'none'}",
        f"Artifacts: {len(artifact_paths)} paths",
    ]
    return " | ".join(parts)


def plan_data_tools_roles(
    analysis: ProblemAnalysis,
    base_data_root: Path | str = "company_data",
) -> ProblemAnalysis:
    """Enrich *analysis* with artifact paths and a context summary.

    Returns a new ProblemAnalysis with the same core fields plus a
    populated *analysis_notes* field that doubles as a human-readable
    context_summary ready for the session record.
    """

    artifact_paths = _artifact_paths_for_categories(analysis.required_data_categories)
    existing = " ".join(analysis.analysis_notes.split()).strip()

    extra_notes = f"Artifact paths: {'; '.join(artifact_paths)}. Base data root: {base_data_root}."

    # Merge notes without duplication
    if existing:
        combined = f"{existing} {extra_notes}"
    else:
        combined = extra_notes

    # Return a new instance with updated analysis_notes
    return analysis.model_copy(
        update={
            "analysis_notes": combined,
        }
    )
