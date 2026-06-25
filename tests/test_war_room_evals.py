"""Tests for war-room evaluation cases and quality gates (v0.6.1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from decision_system.cli import app
from decision_system.war_room.evals import (
    WarRoomEvalCase,
    WarRoomEvalResult,
    WarRoomEvalSuiteResult,
    check_artifact_count,
    check_higher_context_exists,
    check_higher_context_immutable,
    check_human_review_for_contradictions,
    check_human_review_not_blocked,
    check_judge_summary,
    check_no_external_apis,
    check_no_unbounded_chat,
    check_personal_contexts_reference_higher,
    check_workspace_append_only,
    load_war_room_eval_cases,
    render_war_room_eval_report,
    run_quality_gates,
    run_war_room_eval_case,
    save_war_room_eval_results,
)
from decision_system.war_room.models import (
    AgentDispatchSpec,
    CommonWorkspace,
    HigherContext,
    JudgeIntervention,
    PersonalAgentContext,
    WarRoomRun,
    WorkspaceArtifact,
)

runner = CliRunner()
PROJECT_ROOT = Path(__file__).resolve().parents[1]
WR_CASES_DIR = PROJECT_ROOT / "evals" / "war_room_cases"


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


class TestWarRoomEvalModels:
    def test_case_model(self):
        case = WarRoomEvalCase(
            case_id="test_case",
            question="Where are we losing money?",
            expected_roles=["financial_analyst", "risk_analyst"],
            expected_tools=["read_profiles", "save_artifact"],
            expected_data_categories=["financial"],
            min_artifact_count=1,
            requires_judge_summary=True,
            human_review_required_allowed=True,
        )
        assert case.case_id == "test_case"
        assert "financial_analyst" in case.expected_roles

    def test_case_roundtrip(self):
        original = WarRoomEvalCase(
            case_id="c",
            question="q",
            expected_roles=["x"],
            expected_tools=["y"],
            expected_data_categories=["z"],
            min_artifact_count=1,
        )
        raw = original.model_dump_json()
        loaded = WarRoomEvalCase.model_validate_json(raw)
        assert loaded.case_id == original.case_id

    def test_result_model_defaults(self):
        result = WarRoomEvalResult(
            case_id="x",
            passed=True,
            role_match=True,
            tool_match=True,
            data_category_match=True,
            artifact_count_passed=True,
            judge_summary_present=True,
            no_crash=True,
        )
        assert result.notes == []

    def test_suite_result_model(self):
        suite = WarRoomEvalSuiteResult(
            total_cases=3,
            passed_cases=2,
            failed_cases=1,
            results=[],
            created_at="2026-01-01T00:00:00Z",
        )
        assert suite.total_cases == 3
        assert suite.passed_cases == 2
        assert suite.failed_cases == 1


# ---------------------------------------------------------------------------
# Quality gate tests
# ---------------------------------------------------------------------------


class _FakeRun:
    """Minimal stand-in for WarRoomRun used in gate tests."""

    def __init__(self, hc=None, spec=None, ws=None, interventions=None):
        self.higher_context = hc
        self.dispatch_spec = spec
        self.workspace = ws
        self.judge_interventions = interventions or []


class _FakeSpec:
    def __init__(self, hc=None, pcs=None):
        self.higher_context = hc
        self.personal_contexts = pcs or []


def _hc() -> HigherContext:
    return HigherContext(
        run_id="test-run-123",
        question="Where are we losing money?",
        problem_analysis={"decision_type": "financial"},
        decision_context_summary="",
        required_data_categories=("financial",),
        required_ontology_concepts=(),
        relevant_insight_ids=(),
        relevant_storage_tiers=(),
        constraints=(),
        allowed_tools=(
            "read_profiles",
            "read_graph",
            "read_insights",
            "read_context",
            "save_artifact",
        ),
        evidence_requirements={},
        created_at="2026-01-01T00:00:00Z",
    )


def _artifact(aid: str, content: str = "Analysis.") -> WorkspaceArtifact:
    return WorkspaceArtifact(
        artifact_id=aid,
        run_id="test-run-123",
        author_agent_id=f"agent-{aid}",
        artifact_type="analysis",
        title=f"Artifact {aid}",
        content=content,
        evidence_ids=(),
        insight_ids=(),
        ontology_concepts=(),
        confidence="medium",
        created_at="2026-01-01T00:00:00Z",
    )


def _intervention(iid: str, requires_human_review: bool = False) -> JudgeIntervention:
    return JudgeIntervention(
        intervention_id=iid,
        run_id="test-run-123",
        target_artifact_id="a1",
        severity="critical",
        reason="Test intervention.",
        recommended_action="Review manually.",
        requires_human_review=requires_human_review,
    )


def _pc(hc: HigherContext) -> PersonalAgentContext:
    return PersonalAgentContext(
        agent_id="fa-test-run-1",
        role_name="financial_analyst",
        role_type="financial_analyst",
        assigned_task="t",
        perspective="p",
        allowed_tools=(),
        focus_areas=(),
        higher_context_ref=hc.run_id,
        private_notes="",
        output_requirements={},
    )


class TestQualityGates:
    def test_higher_context_exists_passes(self):
        run = _FakeRun(hc=_hc())
        passed, _ = check_higher_context_exists(run)
        assert passed is True

    def test_higher_context_exists_fails_no_run(self):
        passed, detail = check_higher_context_exists(None)
        assert passed is False
        assert "missing" in detail.lower()

    def test_higher_context_immutable_passes(self):
        hc = _hc()
        passed, _ = check_higher_context_immutable(hc)
        assert passed is True

    def test_higher_context_immutable_fails_none(self):
        passed, _ = check_higher_context_immutable(None)
        assert passed is False

    def test_personal_contexts_reference_higher(self):
        hc = _hc()
        spec = _FakeSpec(hc=hc, pcs=[_pc(hc)])
        passed, _ = check_personal_contexts_reference_higher(spec)
        assert passed is True

    def test_mismatched_personal_context_ref(self):
        hc = _hc()
        bad_pc = PersonalAgentContext(
            agent_id="x",
            role_name="x",
            role_type="unknown",
            assigned_task="t",
            perspective="p",
            allowed_tools=(),
            focus_areas=(),
            higher_context_ref="wrong-run-id",
            private_notes="",
            output_requirements={},
        )
        spec = _FakeSpec(hc=hc, pcs=[bad_pc])
        passed, _ = check_personal_contexts_reference_higher(spec)
        assert passed is False

    def test_artifact_count_passes(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1"), _artifact("a2")),
            created_at="d",
            updated_at="d",
        )
        passed, _ = check_artifact_count(ws, min_count=2)
        assert passed is True

    def test_artifact_count_fails(self):
        ws = CommonWorkspace(run_id="r", artifacts=(), created_at="d", updated_at="d")
        passed, _ = check_artifact_count(ws, min_count=2)
        assert passed is False

    def test_workspace_append_only_passes(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1"), _artifact("a2")),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_workspace_append_only(run)
        assert passed is True

    def test_judge_summary_passes(self):
        run = _FakeRun(hc=_hc())
        passed, detail = check_judge_summary(run)
        assert passed is True

    def test_human_review_for_contradictions_passes(self):
        hc = _hc()
        run = _FakeRun(
            hc=hc,
            interventions=[_intervention("i1", requires_human_review=True)],
        )
        passed, _ = check_human_review_for_contradictions(run)
        assert passed is True

    def test_no_external_apis_passes_clean(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1", content="Finances look okay."),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_no_external_apis(run)
        assert passed is True

    def test_no_external_apis_fails(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1", content="Call https://api.openai.com/v1."),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_no_external_apis(run)
        assert passed is False

    def test_no_unbounded_chat_passes(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1", content="Short."),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_no_unbounded_chat(run)
        assert passed is True

    def test_no_unbounded_chat_fails(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1", content="x" * 25_000),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_no_unbounded_chat(run)
        assert passed is False

    def test_no_unbounded_chat_fails_transcript_marker(self):
        ws = CommonWorkspace(
            run_id="r",
            artifacts=(_artifact("a1", content="User: hello"),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=_hc(), ws=ws)
        passed, _ = check_no_unbounded_chat(run)
        assert passed is False


class TestRunQualityGates:
    def test_all_gates_pass_healthy_run(self):
        hc = _hc()
        spec = _FakeSpec(hc=hc, pcs=[_pc(hc)])
        ws = CommonWorkspace(
            run_id="run-1",
            artifacts=(_artifact("a1"), _artifact("a2")),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=hc, spec=spec, ws=ws)
        results = run_quality_gates(run, min_artifact_count=2)
        failed = [r.name for r in results if not r.passed]
        assert failed == [], f"Unexpected failures: {failed}"

    def test_gate_fails_no_context(self):
        ws = CommonWorkspace(run_id="r", artifacts=(), created_at="d", updated_at="d")
        run = _FakeRun(ws=ws)  # hc=None by default
        results = run_quality_gates(run)
        failed_names = [r.name for r in results if not r.passed]
        assert "higher_context_exists" in failed_names

    def test_gate_fails_too_few_artifacts(self):
        hc = _hc()
        spec = _FakeSpec(hc=hc, pcs=[_pc(hc)])
        ws = CommonWorkspace(
            run_id="run-1",
            artifacts=(_artifact("a1"),),
            created_at="d",
            updated_at="d",
        )
        run = _FakeRun(hc=hc, spec=spec, ws=ws)
        results = run_quality_gates(run, min_artifact_count=3)
        failed_names = [r.name for r in results if not r.passed]
        assert "artifact_count" in failed_names

    # --- human_review_not_blocked gate ---

    def test_human_review_allowed_passes_even_with_intervention(self):
        hc = _hc()
        run = _FakeRun(
            hc=hc,
            interventions=[_intervention("i1", requires_human_review=True)],
        )
        results = run_quality_gates(run, human_review_required_allowed=True)
        failed_names = [r.name for r in results if not r.passed]
        assert "human_review_not_blocked" not in failed_names

    def test_human_review_blocked_no_interventions_passes(self):
        hc = _hc()
        run = _FakeRun(hc=hc, interventions=[])
        results = run_quality_gates(run, human_review_required_allowed=False)
        failed_names = [r.name for r in results if not r.passed]
        assert "human_review_not_blocked" not in failed_names

    def test_human_review_blocked_with_intervention_fails(self):
        hc = _hc()
        run = _FakeRun(
            hc=hc,
            interventions=[_intervention("i1", requires_human_review=True)],
        )
        results = run_quality_gates(run, human_review_required_allowed=False)
        failed_names = [r.name for r in results if not r.passed]
        assert "human_review_not_blocked" in failed_names

    def test_human_review_not_blocked_standalone_no_interventions(self):
        passed, _ = check_human_review_not_blocked(None, human_review_required_allowed=True)
        assert passed is True

    def test_human_review_not_blocked_standalone_none_run(self):
        passed, detail = check_human_review_not_blocked(None, human_review_required_allowed=False)
        assert passed is True
        assert "no intervention" in detail.lower()

    def test_eval_case_fails_when_human_review_is_disallowed(self, monkeypatch: pytest.MonkeyPatch):
        hc = _hc()
        pc = _pc(hc)
        spec = AgentDispatchSpec(
            run_id=hc.run_id,
            higher_context=hc,
            personal_contexts=[pc],
            dispatch_order=["financial_analyst"],
            skipped_roles=[],
            missing_inputs=[],
        )
        ws = CommonWorkspace(
            run_id=hc.run_id,
            artifacts=(_artifact("a1"),),
            created_at="d",
            updated_at="d",
        )
        run = WarRoomRun(
            run_id=hc.run_id,
            question=hc.question,
            higher_context=hc,
            dispatch_spec=spec,
            workspace=ws,
            judge_interventions=[_intervention("i1", requires_human_review=True)],
            final_summary="test",
        )

        import decision_system.war_room.runner as runner_module

        monkeypatch.setattr(runner_module, "run_war_room", lambda _question: run)

        case = WarRoomEvalCase(
            case_id="blocked_review_case",
            question=hc.question,
            expected_roles=["financial_analyst"],
            expected_tools=["read_profiles"],
            expected_data_categories=["financial"],
            min_artifact_count=1,
            human_review_required_allowed=False,
        )

        result = run_war_room_eval_case(case)

        assert result.passed is False
        assert any(
            gate.name == "human_review_not_blocked" and not gate.passed
            for gate in result.quality_gates
        )


# ---------------------------------------------------------------------------
# Case loading tests
# ---------------------------------------------------------------------------


class TestCaseLoading:
    def test_loads_all_six_cases(self):
        if not WR_CASES_DIR.exists():
            pytest.skip("war_room_cases directory not yet populated")
        cases = load_war_room_eval_cases()
        assert len(cases) == 6, f"Expected 6, got {len(cases)}"

    def test_case_ids(self):
        if not WR_CASES_DIR.exists():
            pytest.skip("war_room_cases directory not yet populated")
        cases = load_war_room_eval_cases()
        ids = {c.case_id for c in cases}
        expected = {
            "money_loss_case",
            "marketing_roi_case",
            "customer_churn_case",
            "dependency_risk_case",
            "competitor_risk_case",
            "missing_data_case",
        }
        assert ids == expected

    def test_all_cases_have_question(self):
        if not WR_CASES_DIR.exists():
            pytest.skip("war_room_cases directory not yet populated")
        cases = load_war_room_eval_cases()
        for case in cases:
            assert case.question, f"{case.case_id} has empty question"

    def test_json_roundtrip(self):
        if not WR_CASES_DIR.exists():
            pytest.skip("war_room_cases directory not yet populated")
        cases = load_war_room_eval_cases()
        for original in cases:
            raw = original.model_dump_json()
            reloaded = WarRoomEvalCase.model_validate_json(raw)
            assert reloaded.case_id == original.case_id


# ---------------------------------------------------------------------------
# Report rendering tests
# ---------------------------------------------------------------------------


class TestReportRendering:
    def test_render_all_pass(self):
        suite = WarRoomEvalSuiteResult(
            total_cases=2,
            passed_cases=2,
            failed_cases=0,
            results=[
                WarRoomEvalResult(
                    case_id="c1",
                    passed=True,
                    role_match=True,
                    tool_match=True,
                    data_category_match=True,
                    artifact_count_passed=True,
                    judge_summary_present=True,
                    no_crash=True,
                ),
            ],
            created_at="2026-01-01T00:00:00Z",
        )
        report = render_war_room_eval_report(suite)
        assert "PASS" in report
        assert "c1" in report

    def test_render_has_failure_count(self):
        suite = WarRoomEvalSuiteResult(
            total_cases=3,
            passed_cases=1,
            failed_cases=2,
            results=[],
            created_at="2026-01-01T00:00:00Z",
        )
        report = render_war_room_eval_report(suite)
        assert "FAIL" in report

    def test_save_results_writes_fixed_path(self, tmp_path):
        suite = WarRoomEvalSuiteResult(
            total_cases=1,
            passed_cases=1,
            failed_cases=0,
            results=[],
            created_at="2026-01-01T00:00:00Z",
        )

        saved = save_war_room_eval_results(suite, results_dir=tmp_path)

        expected = tmp_path / "war_room_results.json"
        assert expected.exists()
        assert saved.saved_path == str(expected.resolve())


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


class TestCLI:
    def test_eval_war_room_help(self):
        result = runner.invoke(app, ["eval-war-room", "--help"])
        assert result.exit_code == 0

    def test_eval_war_room_json_flag_accepted(self):
        result = runner.invoke(app, ["eval-war-room", "--json", "--save-results"])
        # Must not crash on flags (exit 0 or 1 depending on data state)
        assert result.exit_code in (0, 1)
