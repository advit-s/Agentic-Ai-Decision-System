"""Judge interventions for war-room artifacts.

Deterministic rules only; no LLM calls. The judge inspects each artifact
and may raise interventions (flags) when rules are violated.
"""

from __future__ import annotations

from uuid import uuid4

from decision_system.war_room.models import (
    JudgeIntervention,
    WorkspaceArtifact,
)


def run_judge(artifacts: list[WorkspaceArtifact], run_id: str) -> list[JudgeIntervention]:
    """Review all workspace artifacts and return judge interventions.

    Rules (all deterministic):
    - If an artifact has no evidence_ids, no insight_ids, and no
      ontology_concepts: flag ``unsupported_claim`` at ``medium`` severity.
    - If any linked insight has critical severity: flag ``high_risk_insight``
      at ``high`` severity and require human review.
    - If any insight category is ``contradiction``: flag at ``critical``
      severity and require human review.
    - If confidence < 4 (on a 5-like scale expressed as ``low`` / ``medium``
      / ``high`` / ``critical``): create a warning at ``low`` severity.
    - The judge never claims final business truth.
    """
    from decision_system.insights.store import load_insights

    store = load_insights()
    insight_map = {i.insight_id: i for i in store.insights}
    interventions: list[JudgeIntervention] = []

    for artifact in artifacts:
        # Rule 1: unsupported artifact (no evidence, no insights, no ontology)
        has_support = bool(
            artifact.evidence_ids or artifact.insight_ids or artifact.ontology_concepts
        )
        if not has_support:
            interventions.append(
                JudgeIntervention(
                    intervention_id=str(uuid4()),
                    run_id=run_id,
                    target_artifact_id=artifact.artifact_id,
                    severity="medium",
                    reason=(
                        f"Artifact '{artifact.title}' provides no evidence, "
                        "insight, or ontology support."
                    ),
                    recommended_action="Add supporting evidence or mark as hypothesis.",
                    requires_human_review=False,
                )
            )

        # Rule 2: linked high/critical insights
        for iid in artifact.insight_ids:
            insight = insight_map.get(iid)
            if insight and insight.severity in ("high", "critical"):
                interventions.append(
                    JudgeIntervention(
                        intervention_id=str(uuid4()),
                        run_id=run_id,
                        target_artifact_id=artifact.artifact_id,
                        severity="high",
                        reason=(
                            f"Artifact '{artifact.title}' cites high-severity "
                            f"insight '{insight.title}' ({insight.severity})."
                        ),
                        recommended_action=(
                            "Review evidence backing this insight before acting "
                            "on the artifact conclusions."
                        ),
                        requires_human_review=True,
                    )
                )

        # Rule 3: contradiction insight
        for iid in artifact.insight_ids:
            insight = insight_map.get(iid)
            if insight and insight.category == "contradiction":
                interventions.append(
                    JudgeIntervention(
                        intervention_id=str(uuid4()),
                        run_id=run_id,
                        target_artifact_id=artifact.artifact_id,
                        severity="critical",
                        reason=(
                            f"Artifact '{artifact.title}' cites a contradiction "
                            f"insight ('{insight.title}')."
                        ),
                        recommended_action=(
                            "Resolve the contradiction before using this "
                            "artifact in decision-making."
                        ),
                        requires_human_review=True,
                    )
                )

        # Rule 4: low confidence warning
        if artifact.confidence == "low":
            interventions.append(
                JudgeIntervention(
                    intervention_id=str(uuid4()),
                    run_id=run_id,
                    target_artifact_id=artifact.artifact_id,
                    severity="low",
                    reason=(
                        f"Artifact '{artifact.title}' has low confidence; "
                        "conclusions should be treated cautiously."
                    ),
                    recommended_action="Gather additional evidence to raise confidence.",
                    requires_human_review=False,
                )
            )

    return interventions
