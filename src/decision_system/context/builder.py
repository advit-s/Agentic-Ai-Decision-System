"""DecisionContextBuilder assembles structured context for a question."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from decision_system.context.models import DecisionContext, InsightEvidence
from decision_system.context.selector import select_relevant_ontology_concepts, select_relevant_insights
from decision_system.insights.store import load_insights, DEFAULT_INSIGHTS_DIR
from decision_system.ontology.store import load_ontology, DEFAULT_ONTOLOGY_DIR
from decision_system.orchestration.store import load_latest_session, DEFAULT_RUNS_DIR
from decision_system.orchestration.planner import plan_data_tools_roles
from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.orchestration.models import ProblemAnalysis
from decision_system.graphing.store import load_knowledge_graph, DEFAULT_GRAPH_PATH
from decision_system.graphing.models import KnowledgeGraph


class DecisionContextBuilder:
    """Builds a DecisionContext from question and available local stores."""

    def __init__(self) -> None:
        pass

    def build(
        self,
        question: str,
        run_id: str | None = None,
        ontology_dir: Path | str | None = None,
        insights_dir: Path | str | None = None,
        orchestration_dir: Path | str | None = None,
        graph_path: Path | str | None = None,
    ) -> DecisionContext:
        """Build a DecisionContext for the given question.

        All directories default to standard .decision_system locations if not provided.
        """
        run_id = run_id or str(uuid4())

        # 1. Run deterministic problem analysis
        analysis = analyze_problem(question)
        analysis = plan_data_tools_roles(analysis)

        # 2. Load ontology map
        if ontology_dir:
            omap = load_ontology(ontology_dir)
        else:
            omap = load_ontology()

        # 3. Load insights
        if insights_dir:
            store = load_insights(insights_dir)
        else:
            store = load_insights()

        # 4. Load latest orchestration run
        if orchestration_dir:
            orch_session = load_latest_session(orchestration_dir)
        else:
            orch_session = load_latest_session()

        # 5. Load knowledge graph for graph signals
        if graph_path:
            graph = load_knowledge_graph(graph_path)
        else:
            graph = load_knowledge_graph()

        # 6. Select relevant ontology concepts
        relevant_concepts = select_relevant_ontology_concepts(analysis, omap, question)

        # 7. Select relevant insights
        relevant_insights = select_relevant_insights(analysis, store, question)

        # 8. Convert insights to InsightEvidence
        evidence_insights = []
        for insight in relevant_insights:
            evidence_insights.append(InsightEvidence(
                insight_id=insight.insight_id,
                title=insight.title,
                category=insight.category,
                severity=insight.severity,
                confidence=insight.confidence,
                evidence_summary=insight.evidence_summary,
                recommended_action=insight.recommended_action,
                ontology_concepts=insight.ontology_concepts,
                source_ids=insight.source_ids,
            ))

        # 9. Extract graph signals (top relationships)
        graph_signals = self._extract_graph_signals(graph)

        # 10. Build orchestration summary
        orchestration_summary = {}
        if orch_session:
            orchestration_summary = {
                "run_id": orch_session.run_id,
                "decision_type": orch_session.decision_type,
                "required_data_categories": orch_session.required_data_categories,
                "insight_count": orch_session.insight_count,
                "insights_by_severity": orch_session.insights_by_severity,
                "insights_by_category": orch_session.insights_by_category,
            }

        # 11. Build judge summary
        judge_summary = {}
        if orch_session and orch_session.judge_summary:
            judge_summary = orch_session.judge_summary

        # 12. Build human review items
        human_review_items = self._build_human_review_items(
            evidence_insights, judge_summary, store, analysis
        )

        return DecisionContext(
            run_id=run_id,
            question=question,
            problem_analysis=analysis.model_dump(mode="json"),
            relevant_data_categories=analysis.required_data_categories,
            relevant_storage_tiers=analysis.required_storage_tiers,
            relevant_ontology_concepts=relevant_concepts,
            relevant_insights=evidence_insights,
            graph_signals=graph_signals,
            orchestration_summary=orchestration_summary,
            judge_summary=judge_summary,
            human_review_items=human_review_items,
        )

    def _extract_graph_signals(self, graph: KnowledgeGraph) -> list[str]:
        """Extract human-readable signals from the knowledge graph."""
        signals = []
        # Top connected entities
        if graph.entities and graph.relationships:
            # Count connections per entity
            conn_count: dict[str, int] = {}
            for rel in graph.relationships:
                conn_count[rel.source_entity_id] = conn_count.get(rel.source_entity_id, 0) + 1
                conn_count[rel.target_entity_id] = conn_count.get(rel.target_entity_id, 0) + 1

            # Sort by connection count
            entity_map = {e.entity_id: e for e in graph.entities}
            sorted_entities = sorted(
                [(eid, count) for eid, count in conn_count.items()],
                key=lambda x: x[1],
                reverse=True,
            )

            for eid, count in sorted_entities[:5]:
                entity = entity_map.get(eid)
                if entity:
                    signals.append(f"{entity.name} ({entity.entity_type}) has {count} connections")

            # Contradiction relationships
            for rel in graph.relationships:
                if rel.relation_type == "contradicts":
                    src = entity_map.get(rel.source_entity_id)
                    tgt = entity_map.get(rel.target_entity_id)
                    if src and tgt:
                        signals.append(f"CONTRADICTION: {src.name} contradicts {tgt.name}")

        return signals

    def _build_human_review_items(
        self,
        insights: list[InsightEvidence],
        judge_summary: dict,
        store,
        analysis: ProblemAnalysis,
    ) -> list[str]:
        """Build human review items from insights and judge summary."""
        items = []

        # High/critical insights
        for insight in insights:
            if insight.severity in ("high", "critical"):
                items.append(
                    f"High-severity insight: {insight.title} ({insight.category}, {insight.severity}) - {insight.recommended_action}"
                )

        # Contradiction insights
        for insight in insights:
            if insight.category == "contradiction":
                items.append(
                    f"Contradiction detected: {insight.title} - {insight.recommended_action}"
                )

        # Low confidence judge
        if judge_summary.get("confidence_level") == "low":
            items.append("Judge confidence is low; verify findings before acting.")

        # Judge human review items
        for item in judge_summary.get("human_review_required", []):
            items.append(f"Judge flag: {item}")

        # Missing data signals (high severity missing data insights)
        for insight in insights:
            if insight.category == "missing_data" and insight.severity in ("high", "critical"):
                items.append(f"Missing data: {insight.evidence_summary}")


        # Deduplicate
        seen = set()
        deduped = []
        for item in items:
            if item not in seen:
                seen.add(item)
                deduped.append(item)

        return deduped
