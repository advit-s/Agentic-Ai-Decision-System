"""Tests for decision context package."""

from decision_system.context.builder import DecisionContextBuilder
from decision_system.context.inspector import inspect_context, render_context_inspection
from decision_system.context.models import DecisionContext, InsightEvidence
from decision_system.context.selector import (
    select_relevant_insights,
    select_relevant_ontology_concepts,
)
from decision_system.context.store import load_context, save_context

# --- Model tests ---


def test_insight_evidence_model():
    evidence = InsightEvidence(
        insight_id="test-001",
        title="High revenue risk",
        category="revenue_risk",
        severity="high",
        confidence="medium",
        evidence_summary="Expense ratio above 90%",
        recommended_action="Review cost structure",
        ontology_concepts=["revenue", "expense", "profit_margin"],
        source_ids=["demo_financials"],
    )
    assert evidence.insight_id == "test-001"
    assert evidence.severity == "high"
    assert evidence.ontology_concepts == ["revenue", "expense", "profit_margin"]


# --- Selector tests ---


def test_select_relevant_ontology_concepts_empty():
    """Selector handles empty ontology gracefully."""
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="test",
        decision_type="financial",
        required_ontology_concepts=["revenue", "expense"],
    )
    from decision_system.ontology.models import OntologyMap

    empty_map = OntologyMap()
    result = select_relevant_ontology_concepts(analysis, empty_map, "test question")
    assert result == []


def test_select_relevant_ontology_concepts_matches():
    """Selector returns concepts matching required + keywords."""
    from decision_system.ontology.models import OntologyConcept, OntologyMap
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="Where are we losing money?",
        decision_type="financial",
        required_ontology_concepts=["revenue", "expense", "profit_margin"],
    )
    omap = OntologyMap(
        concepts=[
            OntologyConcept(concept_id="revenue", name="Revenue", concept_type="metric"),
            OntologyConcept(concept_id="expense", name="Expense", concept_type="metric"),
            OntologyConcept(
                concept_id="profit_margin", name="Profit Margin", concept_type="metric"
            ),
            OntologyConcept(concept_id="customer", name="Customer", concept_type="entity"),
        ]
    )
    result = select_relevant_ontology_concepts(analysis, omap, "Where are we losing money?")
    concept_ids = [c["concept_id"] for c in result]
    assert "revenue" in concept_ids
    assert "expense" in concept_ids
    assert "profit_margin" in concept_ids
    # customer not in required, so not included
    assert "customer" not in concept_ids


def test_select_relevant_insights_empty():
    """Selector handles empty insight store gracefully."""
    from decision_system.insights.models import InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="test",
        decision_type="financial",
        required_data_categories=["financial"],
    )
    empty_store = InsightStore()
    result = select_relevant_insights(analysis, empty_store, "test question")
    assert result == []


def test_select_relevant_insights_financial_question():
    """Financial insights selected for money/revenue/loss questions."""
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="Where are we losing money?",
        decision_type="financial",
        required_data_categories=["financial"],
    )
    store = InsightStore(
        insights=[
            Insight(
                insight_id="rev-risk-1",
                title="High expense ratio",
                category="revenue_risk",
                severity="high",
                confidence="high",
                source_ids=["demo_financials"],
                evidence_summary="Expense ratio 95%",
                recommended_action="Review costs",
                ontology_concepts=["revenue", "expense"],
            ),
            Insight(
                insight_id="cust-risk-1",
                title="Customer churn high",
                category="customer_concentration",
                severity="medium",
                confidence="medium",
                source_ids=["demo_customers"],
                evidence_summary="Churn 15%",
                recommended_action="Retention campaign",
                ontology_concepts=["customer"],
            ),
        ]
    )
    result = select_relevant_insights(analysis, store, "Where are we losing money?")
    assert len(result) == 1
    assert result[0].insight_id == "rev-risk-1"


def test_select_relevant_insights_customer_question():
    """Customer insights selected for customer/churn questions; high-severity also included."""
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="Why are customers churning?",
        decision_type="customer",
        required_data_categories=["customers"],
    )
    store = InsightStore(
        insights=[
            Insight(
                insight_id="rev-risk-1",
                title="High expense ratio",
                category="revenue_risk",
                severity="high",
                confidence="high",
                source_ids=["demo_financials"],
                evidence_summary="Expense ratio 95%",
                recommended_action="Review costs",
                ontology_concepts=["revenue", "expense"],
            ),
            Insight(
                insight_id="cust-risk-1",
                title="Customer churn high",
                category="customer_concentration",
                severity="medium",
                confidence="medium",
                source_ids=["demo_customers"],
                evidence_summary="Churn 15%",
                recommended_action="Retention campaign",
                ontology_concepts=["customer"],
            ),
        ]
    )
    result = select_relevant_insights(analysis, store, "Why are customers churning?")
    # High-severity insights are always included; customer insight matches by keywords
    insight_ids = {i.insight_id for i in result}
    assert "cust-risk-1" in insight_ids
    assert "rev-risk-1" in insight_ids  # high severity always included


def test_select_relevant_insights_marketing_question():
    """Marketing insights selected for marketing/ROAS questions."""
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="What is our marketing ROAS?",
        decision_type="marketing",
        required_data_categories=["marketing"],
    )
    store = InsightStore(
        insights=[
            Insight(
                insight_id="mktg-risk-1",
                title="Low ROAS on paid search",
                category="marketing_roi_risk",
                severity="high",
                confidence="high",
                source_ids=["demo_marketing"],
                evidence_summary="ROAS 0.8x",
                recommended_action="Optimize campaigns",
                ontology_concepts=["marketing_spend", "conversion_rate"],
            ),
        ]
    )
    result = select_relevant_insights(analysis, store, "What is our marketing ROAS?")
    assert len(result) == 1
    assert result[0].insight_id == "mktg-risk-1"


def test_select_relevant_insights_high_severity_always_included():
    """High/critical severity insights included even with weak keyword match."""
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="General strategy question",
        decision_type="strategic",
        required_data_categories=["strategic"],
    )
    store = InsightStore(
        insights=[
            Insight(
                insight_id="critical-ops-1",
                title="Critical operations bottleneck",
                category="operations_bottleneck",
                severity="critical",
                confidence="high",
                source_ids=["demo_operations"],
                evidence_summary="Payment reconciliation takes 8 days",
                recommended_action="Automate process",
                ontology_concepts=["operational_delay", "bottleneck"],
            ),
            Insight(
                insight_id="low-mktg-1",
                title="Minor marketing issue",
                category="marketing_roi_risk",
                severity="low",
                confidence="low",
                source_ids=["demo_marketing"],
                evidence_summary="CTR slightly down",
                recommended_action="Monitor",
                ontology_concepts=["click_count"],
            ),
        ]
    )
    result = select_relevant_insights(analysis, store, "General strategy question")
    # critical insight should be included despite category mismatch
    insight_ids = {i.insight_id for i in result}
    assert "critical-ops-1" in insight_ids
    # low severity not included without category match
    assert "low-mktg-1" not in insight_ids


def test_select_relevant_insights_contradiction_creates_human_review():
    """Contradiction insights create human review items."""
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.orchestration.problem_analyzer import ProblemAnalysis

    analysis = ProblemAnalysis(
        question="Should we migrate billing?",
        decision_type="technical",
        required_data_categories=[],
    )
    store = InsightStore(
        insights=[
            Insight(
                insight_id="contradiction-1",
                title="Conflicting claims about billing migration",
                category="contradiction",
                severity="high",
                confidence="high",
                source_ids=["graph"],
                evidence_summary="Risk claim vs safe migration claim",
                recommended_action="Investigate",
                ontology_concepts=["contradiction", "risk"],
            ),
        ]
    )
    result = select_relevant_insights(analysis, store, "Should we migrate billing?")
    assert len(result) == 1
    # The builder will use this to create human review items
    assert result[0].category == "contradiction"


# --- Store tests ---


def test_save_and_load_context(tmp_path):
    """Context can be saved and loaded."""
    context = DecisionContext(
        run_id="test-run-123",
        question="Test question",
        relevant_ontology_concepts=[{"concept_id": "revenue", "name": "Revenue"}],
    )
    save_path = save_context(context, store_dir=tmp_path / "contexts")
    assert save_path.exists()
    assert save_path.name == "test-run-123.json"

    loaded = load_context("test-run-123", store_dir=tmp_path / "contexts")
    assert loaded is not None
    assert loaded.run_id == "test-run-123"
    assert loaded.question == "Test question"
    assert loaded.relevant_ontology_concepts[0]["concept_id"] == "revenue"


def test_load_missing_context_returns_none(tmp_path):
    """Loading missing context returns None."""
    result = load_context("nonexistent", store_dir=tmp_path / "contexts")
    assert result is None


# --- Inspector tests ---


def test_inspect_context():
    """Inspect extracts key summary fields."""
    context = DecisionContext(
        run_id="test-123",
        question="Test question",
        problem_analysis={
            "decision_type": "financial",
            "required_data_categories": ["financial"],
        },
        relevant_data_categories=["financial"],
        relevant_storage_tiers=["tier_1", "tier_2"],
        relevant_ontology_concepts=[
            {
                "concept_id": "revenue",
                "name": "Revenue",
                "type": "metric",
                "required": True,
            },
            {
                "concept_id": "expense",
                "name": "Expense",
                "type": "metric",
                "required": True,
            },
        ],
        relevant_insights=[
            InsightEvidence(
                insight_id="ins-1",
                title="High expense ratio",
                category="revenue_risk",
                severity="high",
                confidence="high",
                evidence_summary="Expense ratio 95%",
                recommended_action="Review costs",
                ontology_concepts=["revenue", "expense"],
                source_ids=["demo_financials"],
            ),
        ],
        graph_signals=["Entity A depends on Entity B"],
        orchestration_summary={"run_id": "orch-1", "insight_count": 5},
        judge_summary={
            "confidence_level": "low",
            "human_review_required": ["Resolve contradictions"],
        },
        human_review_items=["Resolve contradicted claims before taking action."],
    )
    summary = inspect_context(context)

    assert summary["run_id"] == "test-123"
    assert summary["question"] == "Test question"
    assert summary["decision_type"] == "financial"
    assert summary["relevant_data_categories"] == ["financial"]
    assert len(summary["ontology_concepts"]) == 2
    assert len(summary["insights"]) == 1
    assert summary["insights"][0]["insight_id"] == "ins-1"
    assert summary["insights"][0]["severity"] == "high"
    assert len(summary["graph_signals"]) == 1
    assert summary["orchestration_available"] is True
    assert summary["judge_confidence"] == "low"
    assert len(summary["human_review_items"]) == 1


def test_render_context_inspection():
    """Render produces readable Markdown."""
    context = DecisionContext(
        run_id="test-123",
        question="Test question",
        problem_analysis={"decision_type": "financial"},
        relevant_ontology_concepts=[{"concept_id": "revenue", "name": "Revenue"}],
    )
    markdown = render_context_inspection(inspect_context(context))
    assert "Decision Context" in markdown
    assert "test-123" in markdown
    assert "Test question" in markdown


# --- Builder tests ---


def test_builder_handles_missing_ontology_gracefully(tmp_path):
    """Builder works when ontology map is missing."""
    builder = DecisionContextBuilder()
    # Point to empty dirs
    context = builder.build(
        question="Where are we losing money?",
        run_id="test-123",
        ontology_dir=tmp_path / "empty_ontology",
        insights_dir=tmp_path / "empty_insights",
        orchestration_dir=tmp_path / "empty_orchestration",
    )
    assert isinstance(context, DecisionContext)
    assert context.relevant_ontology_concepts == []
    assert context.relevant_insights == []
    assert context.orchestration_summary == {}


def test_builder_handles_missing_insights_gracefully(tmp_path):
    """Builder works when insights store is missing."""
    builder = DecisionContextBuilder()
    context = builder.build(
        question="Where are we losing money?",
        run_id="test-123",
        ontology_dir=tmp_path / "empty_ontology",
        insights_dir=tmp_path / "empty_insights",
        orchestration_dir=tmp_path / "empty_orchestration",
    )
    assert context.relevant_insights == []


def test_builder_selects_financial_insights_for_money_question(tmp_path):
    """Builder selects financial insights for money question."""
    # Create fake ontology
    from decision_system.ontology.models import OntologyConcept, OntologyMap

    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir(parents=True)
    omap = OntologyMap(
        concepts=[
            OntologyConcept(concept_id="revenue", name="Revenue", concept_type="metric"),
            OntologyConcept(concept_id="expense", name="Expense", concept_type="metric"),
        ]
    )
    (ontology_dir / "ontology_map.json").write_text(omap.model_dump_json(indent=2))

    # Create fake insights
    from decision_system.insights.models import Insight, InsightStore

    insights_dir = tmp_path / "insights"
    insights_dir.mkdir(parents=True)
    store = InsightStore(
        insights=[
            Insight(
                insight_id="rev-risk-1",
                title="High expense ratio",
                category="revenue_risk",
                severity="high",
                confidence="high",
                source_ids=["demo_financials"],
                evidence_summary="Expense ratio 95%",
                recommended_action="Review costs",
                ontology_concepts=["revenue", "expense"],
            ),
        ]
    )
    (insights_dir / "insights.json").write_text(store.model_dump_json(indent=2))

    builder = DecisionContextBuilder()
    context = builder.build(
        question="Where are we losing money?",
        run_id="test-123",
        ontology_dir=ontology_dir,
        insights_dir=insights_dir,
        orchestration_dir=tmp_path / "empty_orchestration",
    )

    assert len(context.relevant_insights) == 1
    assert context.relevant_insights[0].insight_id == "rev-risk-1"
    assert len(context.relevant_ontology_concepts) == 2


def test_builder_creates_human_review_from_contradiction(tmp_path):
    """Builder creates human review items from contradiction insights."""
    # Fake insights with contradiction
    from decision_system.insights.models import Insight, InsightStore
    from decision_system.ontology.models import OntologyMap

    insights_dir = tmp_path / "insights"
    insights_dir.mkdir(parents=True)
    store = InsightStore(
        insights=[
            Insight(
                insight_id="contradiction-1",
                title="Conflicting claims",
                category="contradiction",
                severity="high",
                confidence="high",
                source_ids=["graph"],
                evidence_summary="Claim A vs Claim B",
                recommended_action="Investigate",
                ontology_concepts=["contradiction"],
            ),
        ]
    )
    (insights_dir / "insights.json").write_text(store.model_dump_json(indent=2))

    ontology_dir = tmp_path / "ontology"
    ontology_dir.mkdir(parents=True)
    (ontology_dir / "ontology_map.json").write_text(OntologyMap().model_dump_json(indent=2))

    builder = DecisionContextBuilder()
    context = builder.build(
        question="Should we migrate billing?",
        run_id="test-123",
        ontology_dir=ontology_dir,
        insights_dir=insights_dir,
        orchestration_dir=tmp_path / "empty_orchestration",
    )

    assert len(context.human_review_items) >= 1
    # Contradiction should create human review
    assert any(
        "contradiction" in item.lower() or "conflict" in item.lower()
        for item in context.human_review_items
    )
