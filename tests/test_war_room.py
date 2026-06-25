"""Tests for the v0.6 war-cabinet agent context protocol.

All tests run offline without real LLM or API keys.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.insights.models import Insight, InsightStore
from decision_system.insights.store import save_insights
from decision_system.war_room.context_builder import build_higher_context
from decision_system.war_room.dispatcher import build_dispatch_spec
from decision_system.war_room.judge import run_judge
from decision_system.war_room.models import (
    CommonWorkspace,
    HigherContext,
    PersonalAgentContext,
    WarRoomRun,
    WorkspaceArtifact,
)
from decision_system.war_room.runner import run_war_room
from decision_system.war_room.sandbox import validate_tool_call
from decision_system.war_room.store import (
    load_latest_run,
    load_war_room_run,
)

# ================================================================
# Dispatcher / dispatch tests
# ================================================================


class TestDispatch:
    def test_financial_question_selects_financial_and_risk(self):
        spec = build_dispatch_spec("Where are we losing money?")
        assert "financial_analyst" in spec.dispatch_order
        assert "risk_analyst" in spec.dispatch_order

    def test_marketing_question_selects_marketing(self):
        spec = build_dispatch_spec("Which marketing channel has the best ROAS?")
        roles = spec.dispatch_order
        assert "marketing_analyst" in roles

    def test_technical_question_selects_technical(self):
        spec = build_dispatch_spec("Analyze system dependencies.")
        assert "technical_analyst" in spec.dispatch_order

    def test_general_fallback_produces_empty_dispatch(self):
        spec = build_dispatch_spec("What is the weather?")
        assert spec.dispatch_order == []
        assert spec.skipped_roles

    def test_skipped_roles_are_role_ids_not_decision_types(self):
        spec = build_dispatch_spec("Where are we losing money?")
        assert "customer_analyst" in spec.skipped_roles
        assert "customer" not in spec.skipped_roles

    def test_higher_context_is_immutable(self):
        ctx = build_higher_context("Where are we losing money?")
        with pytest.raises(Exception):
            ctx.run_id = "malicious-override"

    def test_personal_context_references_higher_context(self):
        spec = build_dispatch_spec("Where are we losing money?")
        assert spec.higher_context.run_id == spec.run_id
        for pc in spec.personal_contexts:
            assert pc.higher_context_ref == spec.higher_context.run_id
            assert "read_context" in pc.allowed_tools

    def test_plan_war_room_exits_zero(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["plan-war-room", "Where are we losing money?"])
        assert result.exit_code == 0

    def test_run_war_room_saves_json(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        saved = tmp_path / ".decision_system" / "war_room" / "runs" / f"{run.run_id}.json"
        assert saved.exists()

    def test_inspect_war_room_exits_zero(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        summary = _inspect_war_room(run)
        rendered = _render_war_room_inspection(summary)
        assert "# War-Cabinet Inspection" in rendered

        runner = CliRunner()
        result = runner.invoke(app, ["inspect-war-room"])
        assert result.exit_code == 0


# ================================================================
# HigherContext immutability tests
# ================================================================


class TestHigherContextImmutability:
    def test_frozen_model_rejects_field_mutation(self):
        hc = HigherContext(
            run_id="run-immutable-test",
            question="test question",
            created_at="2026-06-05T00:00:00+00:00",
        )
        with pytest.raises(Exception):
            hc.run_id = "different-run-id"

    def test_deep_context_rejects_nested_mutation(self):
        hc = HigherContext(
            run_id="run-deep-immutable-test",
            question="test question",
            problem_analysis={"decision_type": "financial", "nested": {"x": 1}},
            required_data_categories=["financial"],
            evidence_requirements={"minimum_sources": 1},
            created_at="2026-06-05T00:00:00+00:00",
        )
        with pytest.raises(Exception):
            hc.required_data_categories += ("sales",)
        with pytest.raises(TypeError):
            hc.problem_analysis["decision_type"] = "risk"
        with pytest.raises(TypeError):
            hc.problem_analysis["nested"]["x"] = 2

    def test_personal_context_is_read_only(self):
        pc = PersonalAgentContext(
            agent_id="agent-1",
            role_name="risk_analyst",
            role_type="risk_analyst",
            allowed_tools=["read_context"],
            output_requirements={"must_cite_evidence": True},
        )
        with pytest.raises(Exception):
            pc.role_name = "financial_analyst"
        with pytest.raises(AttributeError):
            pc.allowed_tools.append("read_profiles")
        with pytest.raises(TypeError):
            pc.output_requirements["must_cite_evidence"] = False


# ================================================================
# CommonWorkspace append-only tests
# ================================================================


class TestCommonWorkspace:
    def test_add_artifact_increases_count(self):
        ws = CommonWorkspace(run_id="r1")
        initial = len(ws.artifacts)
        ws.add_artifact(
            WorkspaceArtifact(
                artifact_id="a1",
                run_id="r1",
                title="First",
                content="c1",
                confidence="medium",
            )
        )
        assert len(ws.artifacts) == initial + 1

    def test_multiple_adds_preserve_order(self):
        ws = CommonWorkspace(run_id="r1")
        for i in range(4):
            ws.add_artifact(
                WorkspaceArtifact(
                    artifact_id="a{}".format(i),
                    run_id="r1",
                    title="T{}".format(i),
                    content="C{}".format(i),
                    confidence="medium",
                )
            )
        ids = [a.artifact_id for a in ws.artifacts]
        assert ids == ["a0", "a1", "a2", "a3"]

    def test_workspace_rejects_external_mutation(self):
        ws = CommonWorkspace(run_id="r1")
        artifact = WorkspaceArtifact(
            artifact_id="a1",
            run_id="r1",
            title="First",
            content="c1",
            confidence="medium",
        )
        ws.add_artifact(artifact)
        with pytest.raises(Exception):
            ws.artifacts = ()
        with pytest.raises(AttributeError):
            ws.artifacts.clear()

    def test_workspace_rejects_wrong_run_artifact(self):
        ws = CommonWorkspace(run_id="r1")
        with pytest.raises(ValueError):
            ws.add_artifact(
                WorkspaceArtifact(
                    artifact_id="a1",
                    run_id="other-run",
                    title="Wrong run",
                    content="c1",
                    confidence="medium",
                )
            )


# ================================================================
# Sandbox validation tests
# ================================================================


class TestSandboxValidation:
    def test_allowed_tool_passes(self):
        assert validate_tool_call("read_profiles") is True
        assert validate_tool_call("read_graph") is True

    def test_destructive_blocked(self):
        assert validate_tool_call("delete something") is False

    def test_http_blocked(self):
        assert validate_tool_call("http://evil.com") is False
        assert validate_tool_call("https://api.example.com") is False


# ================================================================
# Judge intervention tests
# ================================================================


def _make_artifact(
    a_id="art-1",
    title="T",
    insight_ids=None,
    evidence_ids=None,
    ontology_concepts=None,
    confidence="medium",
):
    return WorkspaceArtifact(
        artifact_id=a_id,
        run_id="r1",
        title=title,
        evidence_ids=list(evidence_ids or []),
        insight_ids=list(insight_ids or []),
        ontology_concepts=list(ontology_concepts or []),
        confidence=confidence,
    )


class TestJudgeInterventions:
    def test_unsupported_artifact_creates_intervention(self):
        artifact = _make_artifact(a_id="x", title="Bare", confidence="medium")
        interventions = run_judge([artifact], "run-1")
        assert len(interventions) == 1
        assert interventions[0].severity == "medium"

    def test_contradiction_insight_creates_intervention(self):
        insight = Insight(
            insight_id="ins-con-1",
            title="CONTRADICTION",
            category="contradiction",
            severity="high",
            confidence="medium",
            source_type="graph",
            source_ids=["g1"],
        )
        store = InsightStore(insights=[insight])
        save_insights(store)

        artifact = _make_artifact(
            a_id="a1",
            title="T",
            insight_ids=["ins-con-1"],
            confidence="medium",
        )
        interventions = run_judge([artifact], "run-1")
        assert any(i.severity == "critical" for i in interventions)

    def test_high_severity_insight_creates_intervention(self):
        insight = Insight(
            insight_id="ins-high",
            title="HIGH RISK",
            category="revenue_risk",
            severity="high",
            confidence="medium",
            source_type="profile",
            source_ids=["p1"],
        )
        store = InsightStore(insights=[insight])
        save_insights(store)

        artifact = _make_artifact(
            a_id="a2",
            title="T2",
            insight_ids=["ins-high"],
            confidence="medium",
        )
        interventions = run_judge([artifact], "run-1")
        assert any(i.severity == "high" for i in interventions)


# ================================================================
# Runner integration tests
# ================================================================


class TestWarRoomRunner:
    def test_run_war_room_completes(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        assert run.run_id
        assert run.question == "Where are we losing money?"
        assert isinstance(run.higher_context, HigherContext)
        assert run.higher_context.run_id == run.run_id
        assert run.dispatch_spec.run_id == run.run_id
        assert run.workspace.run_id == run.run_id
        for pc in run.dispatch_spec.personal_contexts:
            assert pc.higher_context_ref == run.run_id

    def test_run_war_room_creates_artifacts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        assert len(run.workspace.artifacts) >= 1
        for artifact in run.workspace.artifacts:
            assert artifact.title
            assert artifact.content

    def test_run_war_room_judge_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        assert isinstance(run.judge_interventions, list)
        for ji in run.judge_interventions:
            assert ji.reason

    def test_run_war_room_judge_sees_higher_context_insights(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        insight = Insight(
            insight_id="ins-high-financial",
            title="High financial risk",
            category="revenue_risk",
            severity="high",
            confidence="medium",
            source_type="profile",
            source_ids=["demo_financials"],
        )
        save_insights(InsightStore(insights=[insight]))

        run = run_war_room("Where are we losing money?")

        assert any(
            "ins-high-financial" in artifact.insight_ids for artifact in run.workspace.artifacts
        )
        assert any(intervention.requires_human_review for intervention in run.judge_interventions)

    def test_run_war_room_creates_war_room_run(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        assert isinstance(run, WarRoomRun)
        assert run.dispatch_spec is not None
        assert len(run.dispatch_spec.dispatch_order) >= 1

    def test_run_war_room_saves_to_disk(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run = run_war_room("Where are we losing money?")
        loaded = load_war_room_run(run.run_id)
        assert loaded is not None
        assert loaded.question == "Where are we losing money?"

    def test_load_latest_run(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        run_war_room("Where are we losing money?")
        latest = load_latest_run()
        assert latest is not None
        assert latest.question == "Where are we losing money?"


# ================================================================
# Inspection helpers (used by tests and CLI)
# ================================================================


def _inspect_war_room(run):
    from decision_system.war_room.inspector import inspect_war_room

    return inspect_war_room(run)


def _render_war_room_inspection(summary):
    from decision_system.war_room.inspector import render_inspection

    return render_inspection(summary)


# ================================================================
# Fixtures
# ================================================================


@pytest.fixture(autouse=True)
def _reset_insights(tmp_path, monkeypatch):
    """Reset the insight store between tests so judge state is clean."""
    monkeypatch.chdir(tmp_path)
    yield
    save_insights(InsightStore())
