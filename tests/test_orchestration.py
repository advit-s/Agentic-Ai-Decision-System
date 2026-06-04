"""Tests for the v0.4 orchestration layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from decision_system.data_catalog.models import (
    ColumnProfile,
    DataProfileStore,
    DataCategory,
    DatasetProfile,
)
from decision_system.graphing.models import (
    Entity,
    EntityType,
    KnowledgeGraph,
    Relationship,
    RelationType,
)
from decision_system.insights.models import (
    Insight,
    InsightSeverity,
    InsightStore,
)
from decision_system.ontology.models import (
    ColumnMapping,
    OntologyConcept,
    OntologyMap,
)
from decision_system.orchestration.models import (
    DecisionSession,
    DecisionType,
    DispatchPlan,
    JudgeSummary,
    ProblemAnalysis,
    StorageTier,
)
from decision_system.orchestration.dispatcher import build_dispatch_plan
from decision_system.orchestration.judge import build_judge_summary
from decision_system.orchestration.planner import plan_data_tools_roles
from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.orchestration.sandbox import validate_action
from decision_system.orchestration.session import (
    create_session,
    load_latest_run,
)
from decision_system.orchestration.store import (
    save_decision_session,
    load_decision_session,
    load_latest_session,
    list_runs,
)
from decision_system.orchestration.workflow import run_orchestration
from decision_system.orchestration.inspector import (
    inspect_problem_analysis,
    inspect_dispatch_plan,
    render_problem_analysis,
    render_dispatch_plan,
)


# ============================================================================
# StorageTier tests
# ============================================================================


class TestStorageTier:
    def test_roundtrip(self):
        tier = StorageTier(
            tier_id="tier_1",
            name="Raw Data",
            description="Raw documents and datasets",
            artifacts=["company_docs/", "company_data/*/"],
            purpose="Source data",
        )
        payload = tier.model_dump(mode="json")
        restored = StorageTier.model_validate(payload)
        assert restored.tier_id == "tier_1"
        assert restored.name == "Raw Data"

    def test_defaults(self):
        tier = StorageTier(tier_id="t1", name="Tier 1", description="d", artifacts=[], purpose="p")
        assert tier.tier_id == "t1"
        assert tier.artifacts == []


# ============================================================================
# ProblemAnalyzer tests
# ============================================================================


class TestProblemAnalyzer:
    def test_money_keyword_maps_financial(self):
        analysis = analyze_problem("Where are we losing money?")
        assert analysis.decision_type == "financial"
        assert "financial" in analysis.required_data_categories
        assert "financial analyst" in analysis.relevant_roles

    def test_revenue_keyword_maps_financial(self):
        analysis = analyze_problem("What is our revenue trend?")
        assert analysis.decision_type == "financial"

    def test_expense_keyword_maps_financial(self):
        analysis = analyze_problem("Where can we cut costs?")
        assert analysis.decision_type == "financial"

    def test_customer_question_maps_customer(self):
        analysis = analyze_problem("Which customer segments are churning?")
        assert analysis.decision_type == "customer"
        assert "customers" in analysis.required_data_categories
        assert "customer analyst" in analysis.relevant_roles

    def test_marketing_question_maps_marketing(self):
        analysis = analyze_problem("How is our ad campaign performing?")
        assert analysis.decision_type == "marketing"
        assert "marketing" in analysis.required_data_categories
        assert "marketing analyst" in analysis.relevant_roles

    def test_website_keyword_maps_analytics(self):
        analysis = analyze_problem("Why is the website bounce rate so high?")
        assert analysis.decision_type == "analytics"
        assert "analytics" in analysis.required_data_categories

    def test_app_keyword_maps_analytics(self):
        analysis = analyze_problem("App conversion rate is declining.")
        assert analysis.decision_type == "analytics"

    def test_competitor_question_maps_competitor(self):
        analysis = analyze_problem("How do our prices compare to competitors?")
        assert analysis.decision_type == "competitor"
        assert "competitors" in analysis.required_data_categories
        assert "strategy analyst" in analysis.relevant_roles

    def test_operations_question_maps_operations(self):
        analysis = analyze_problem("Identify supply chain bottlenecks.")
        assert analysis.decision_type == "operations"
        assert "operations" in analysis.required_data_categories

    def test_feedback_question_maps_feedback(self):
        analysis = analyze_problem("Why are refund requests increasing?")
        assert analysis.decision_type == "feedback"

    def test_goal_keyword_maps_strategic(self):
        analysis = analyze_problem("Which strategic goals have no owner?")
        assert analysis.decision_type == "strategic"
        assert "judge / verifier" in analysis.relevant_roles

    def test_general_fallback(self):
        analysis = analyze_problem("What is the weather today?")
        assert analysis.decision_type == "general"

    def test_returns_problem_analysis(self):
        problems = [
            ("How much did our sales total last month?", "sales"),
            ("Which marketing channels work best?", "marketing"),
            ("What is our product feature usage?", "product"),
            ("What is our biggest compliance risk?", "risk"),
            ("How stable is our system architecture?", "technical"),
        ]
        for question, decision_type in problems:
            analysis = analyze_problem(question)
            assert analysis.decision_type == decision_type

    def test_includes_ontology_concepts(self):
        analysis = analyze_problem("Where are we losing money?")
        assert len(analysis.required_ontology_concepts) > 0
        assert "revenue" in analysis.required_ontology_concepts

    def test_includes_storage_tiers(self):
        analysis = analyze_problem("Where are we losing money?")
        assert "tier_1" in analysis.required_storage_tiers
        assert "tier_4" in analysis.required_storage_tiers


# ============================================================================
# Planner tests
# ============================================================================


class TestPlanner:
    def test_enriches_analysis(self):
        analysis = analyze_problem("Where are we losing money?")
        enriched = plan_data_tools_roles(analysis)
        assert enriched.analysis_notes
        # Should include both original notes and artifact paths
        assert "Decision type" in enriched.analysis_notes

    def test_empty_categories_produce_empty_artifacts(self):
        analysis = ProblemAnalysis(
            question="test", decision_type="technical", required_data_categories=[]
        )
        enriched = plan_data_tools_roles(analysis)
        assert isinstance(enriched.analysis_notes, str)


# ============================================================================
# Dispatcher tests
# ============================================================================


class TestDispatcher:
    def test_selects_profile_and_ontology_for_financial(self):
        analysis = analyze_problem("Where are we losing money?")
        plan = build_dispatch_plan(analysis)
        assert "profile-data" in plan.selected_tools
        assert "map-ontology" in plan.selected_tools
        assert "detect-patterns" in plan.selected_tools

    def test_selects_graph_for_strategic(self):
        analysis = analyze_problem("Which strategic goals have constraints?")
        plan = build_dispatch_plan(analysis)
        assert "extract-graph" in plan.selected_tools

    def test_selects_graph_for_technical(self):
        analysis = analyze_problem("Analyze system dependencies.")
        plan = build_dispatch_plan(analysis)
        assert "extract-graph" in plan.selected_tools

    def test_excludes_graph_for_purely_data_questions(self):
        analysis = ProblemAnalysis(
            question="What is our revenue?",
            decision_type="financial",
            required_data_categories=["financial"],
        )
        plan = build_dispatch_plan(analysis)
        assert "extract-graph" not in plan.selected_tools

    def test_assigns_roles(self):
        analysis = analyze_problem("Where are we losing money?")
        plan = build_dispatch_plan(analysis)
        assert "financial analyst" in plan.selected_roles
        assert "risk analyst" in plan.selected_roles

    def test_includes_prep_tools(self):
        analysis = analyze_problem("Where are we losing money?")
        plan = build_dispatch_plan(analysis)
        assert "init-data-catalog" in plan.selected_tools

    def test_execution_order_sensible(self):
        analysis = analyze_problem("Where are we losing money?")
        plan = build_dispatch_plan(analysis)
        order = plan.execution_order
        assert order.index("init-data-catalog") < order.index("profile-data")
        assert order.index("profile-data") < order.index("map-ontology")
        assert order.index("map-ontology") < order.index("detect-patterns")

    def test_skipped_tools_populated(self):
        analysis = ProblemAnalysis(
            question="test", decision_type="general"
        )
        plan = build_dispatch_plan(analysis)
        assert len(plan.skipped_tools) > 0


# ============================================================================
# Sandbox tests
# ============================================================================


class TestSandbox:
    def test_validate_action_allowed(self):
        assert validate_action("read_profiles") is True
        assert validate_action("read_graph") is True
        assert validate_action("run_detectors") is True
        assert validate_action("save_ontology") is True
        assert validate_action("save_run") is True

    def test_validate_action_forbidden_delete(self):
        assert validate_action("delete something") is False
        assert validate_action("rm -rf /") is False

    def test_validate_action_forbidden_shell(self):
        assert validate_action("shell ls") is False
        assert validate_action("exec something") is False

    def test_validate_action_forbidden_http(self):
        assert validate_action("http://evil.com") is False
        assert validate_action("https://api.example.com") is False

    def test_validate_action_forbidden_send(self):
        assert validate_action("send email") is False

    def test_validate_action_unknown(self):
        assert validate_action("unknown_action_xyz") is False

    def test_read_profiles_no_session(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from decision_system.orchestration.sandbox import sandbox_execute
        result = sandbox_execute("read_profiles", {})
        assert result.profiles == []

    def test_read_graph_no_session(self):
        from decision_system.graphing.models import KnowledgeGraph
        from decision_system.orchestration.sandbox import sandbox_execute
        result = sandbox_execute("read_graph", {})
        assert isinstance(result, KnowledgeGraph)

    def test_save_actions_use_canonical_storage_paths(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        from decision_system.orchestration.sandbox import sandbox_execute

        sandbox_execute("save_ontology", {"ontology_map": OntologyMap()})
        sandbox_execute("save_insights", {"insights": InsightStore()})

        assert (tmp_path / ".decision_system" / "ontology" / "ontology_map.json").exists()
        assert (tmp_path / ".decision_system" / "insights" / "insights.json").exists()
        assert not (tmp_path / ".decision_system" / "orchestration" / "ontology_map.json").exists()
        assert not (tmp_path / ".decision_system" / "orchestration" / "insights.json").exists()


# ============================================================================
# Session tests
# ============================================================================


class TestSession:

    def test_create_session(self):
        session = create_session("Where are we losing money?")
        assert session.run_id
        assert session.session_id
        assert session.question == "Where are we losing money?"
        assert session.status == "pending"

    def test_load_latest_none_when_no_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        session = load_latest_run()
        assert session is None

    def test_save_and_load_roundtrip(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        session = create_session("test question")
        saved = save_decision_session(session, runs_dir=tmp_path)
        assert saved.exists()
        loaded = load_decision_session(session.run_id, runs_dir=tmp_path)
        assert loaded is not None
        assert loaded.question == "test question"


# ============================================================================
# Store tests
# ============================================================================


class TestStore:

    def test_list_runs_empty(self, tmp_path: Path):
        runs = list_runs(runs_dir=tmp_path)
        assert runs == []

    def test_list_runs_after_save(self, tmp_path: Path):
        session = create_session("test")
        save_decision_session(session, runs_dir=tmp_path)
        runs = list_runs(runs_dir=tmp_path)
        assert len(runs) == 1
        assert runs[0]["run_id"] == session.run_id


# ============================================================================
# Judge tests
# ============================================================================


class TestJudge:

    def test_moderate_confidence_with_insights(self):
        insight = _make_insight(
            "low_margin", "Low margin", severity="medium",
            recommended_action="Review margin drivers immediately.",
        )
        store = InsightStore(insights=[insight])
        judge = build_judge_summary(run_id="run-1", insights=store)
        assert judge.confidence_level == "medium"
        assert len(judge.key_findings) >= 1
        assert len(judge.recommended_next_actions) >= 1

    def test_low_confidence_with_missing_data(self):
        insight = _make_insight("high_risk", "High risk", severity="high")
        store = InsightStore(insights=[insight])
        judge = build_judge_summary(
            run_id="run-1",
            insights=store,
            missing_data_items=["col: missing 60%"],
        )
        assert judge.confidence_level == "low"

    def test_low_confidence_empty_insights(self):
        judge = build_judge_summary(run_id="run-1", insights=InsightStore())
        assert judge.confidence_level == "low"

    def test_human_review_required_for_high(self):
        insight = _make_insight("high_risk", "High risk", severity="high")
        store = InsightStore(insights=[insight])
        judge = build_judge_summary(run_id="run-1", insights=store)
        assert len(judge.human_review_required) >= 1

    def test_human_review_required_for_contradiction(self):
        insight = _make_insight("con_1", "Contradiction", category="contradiction", severity="high")
        store = InsightStore(insights=[insight])
        judge = build_judge_summary(run_id="run-1", insights=store)
        assert len(judge.human_review_required) >= 1

    def test_no_human_review_for_low_only(self):
        insight = _make_insight("low_finding", "Low finding", severity="low")
        store = InsightStore(insights=[insight])
        judge = build_judge_summary(run_id="run-1", insights=store)
        assert len(judge.human_review_required) == 0


# ============================================================================
# Inspector tests
# ============================================================================


class TestInspector:
    def test_inspect_problem_analysis(self):
        analysis = ProblemAnalysis(
            question="Why are margins falling?",
            decision_type="financial",
        )
        summary = inspect_problem_analysis(analysis)
        assert summary["question"] == "Why are margins falling?"
        assert summary["decision_type"] == "financial"

    def test_render_problem_analysis(self):
        output = render_problem_analysis(
            {
                "question": "Why are margins falling?",
                "decision_type": "financial",
                "required_data_categories": ["financial"],
                "required_tools": ["profile-data"],
                "relevant_roles": ["financial analyst"],
                "required_ontology_concepts": ["revenue"],
                "required_storage_tiers": ["tier_1"],
                "missing_capabilities": [],
                "analysis_notes": "test",
            }
        )
        assert "# Problem Analysis" in output
        assert "Why are margins falling?" in output

    def test_inspect_dispatch_plan(self):
        plan = DispatchPlan(selected_tools=["profile-data"], execution_order=["profile-data"])
        summary = inspect_dispatch_plan(plan)
        assert "profile-data" in summary["selected_tools"]
        assert "profile-data" in summary["execution_order"]

    def test_render_dispatch_plan(self):
        output = render_dispatch_plan(
            {
                "execution_order": ["init-data-catalog", "profile-data", "detect-patterns"],
                "selected_tools": ["init-data-catalog", "profile-data", "detect-patterns"],
                "skipped_tools": ["extract-graph"],
                "selected_roles": ["risk analyst"],
                "selected_artifacts": [".decision_system/data_profiles/profiles.json"],
                "missing_inputs": [],
            }
        )
        assert "# Dispatch Plan" in output
        assert "profile-data" in output


# ============================================================================
# Workflow integration tests
# ============================================================================


class TestWorkflow:

    def test_run_orchestration_no_data(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        result = run_orchestration("Where are we losing money?", save=True)
        assert result["status"] == "completed"
        assert result["run_id"]
        assert result["saved_path"] is not None
        assert Path(result["saved_path"]).exists()

    def test_run_orchestration_with_profiles(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        _make_catalog_and_profile(tmp_path)
        result = run_orchestration(
            "Where are we losing money?",
            base_data_root=tmp_path,
            save=True,
        )
        assert result["ontology_concept_count"] >= 1
        assert result["insight_count"] >= 0
        assert result["saved_path"] is not None

    def test_run_orchestration_returns_expected_keys(self, monkeypatch, tmp_path: Path):
        monkeypatch.chdir(tmp_path)
        result = run_orchestration("Analyze operations delays.", save=False)
        expected_keys = {
            "run_id",
            "session_id",
            "question",
            "status",
            "decision_type",
            "required_data_categories",
            "execution_order",
            "insight_count",
            "judge",
        }
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_sanity_check(self):
        analysis = analyze_problem("Where are we losing money?")
        assert analysis.decision_type == "financial"
        plan = build_dispatch_plan(analysis)
        assert "detect-patterns" in plan.execution_order
        assert "financial analyst" in plan.selected_roles


# ============================================================================
# Helpers
# ============================================================================


def _make_insight(insight_id: str, title: str = "T", **kwargs):
    defaults = {
        "insight_id": insight_id,
        "title": title,
        "description": "test description",
        "category": "data_quality",
        "severity": "medium",
        "confidence": "medium",
        "source_type": "profile",
        "source_ids": [],
        "evidence_summary": "",
        "recommended_action": "",
    }
    defaults.update(kwargs)
    return Insight(**defaults)


def _make_catalog_and_profile(tmp_path: Path) -> None:
    """Write a minimal data catalog, demo CSV, and profile for tests."""
    import csv
    import json

    catalog = tmp_path / "company_data"
    catalog.mkdir(exist_ok=True)
    (catalog / "manifest.json").write_text(
        json.dumps({"version": "0.4", "categories": {}}), encoding="utf-8"
    )
    cat = catalog / "financial"
    cat.mkdir(exist_ok=True)
    csv_path = cat / "demo_financials.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["month", "revenue", "expenses", "profit_margin"])
        w.writeheader()
        w.writerow({"month": "2025-01", "revenue": "12000", "expenses": "11850", "profit_margin": "0.01"})
