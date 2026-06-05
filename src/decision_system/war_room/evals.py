"""v0.6.1 War-room offline evaluation models, quality gates, and runner."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from decision_system.war_room.models import (
    AgentDispatchSpec,
    CommonWorkspace,
    HigherContext,
    WarRoomRun,
)

WarRoomEvalStatus = Literal["PASS", "FAIL"]


class WarRoomEvalCase(BaseModel):
    """Expected configuration for one war-room evaluation case."""

    case_id: str
    question: str
    expected_roles: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    expected_data_categories: list[str] = Field(default_factory=list)
    min_artifact_count: int = 1
    requires_judge_summary: bool = True
    human_review_required_allowed: bool = True


class WarRoomQualityGateResult(BaseModel):
    """Structured result for one war-room quality gate."""

    name: str
    passed: bool
    detail: str


class WarRoomEvalResult(BaseModel):
    """Per-case war-room eval result."""

    case_id: str
    passed: bool
    quality_gates: list[WarRoomQualityGateResult] = Field(default_factory=list)
    role_match: bool
    tool_match: bool
    data_category_match: bool
    artifact_count_passed: bool
    judge_summary_present: bool
    no_crash: bool
    notes: list[str] = Field(default_factory=list)


class WarRoomEvalSuiteResult(BaseModel):
    """Aggregated result for a war-room eval suite."""

    total_cases: int
    passed_cases: int
    failed_cases: int
    results: list[WarRoomEvalResult]
    created_at: str
    saved_path: str | None = None


def check_higher_context_exists(run: WarRoomRun | None) -> tuple[bool, str]:
    """Gate: higher context is present in the run."""

    if run is None or run.higher_context is None:
        return False, "Higher context is missing."
    return True, "Higher context present."


def check_higher_context_immutable(
    higher_context: HigherContext | None,
) -> tuple[bool, str]:
    """Gate: HigherContext rejects top-level and nested mutation."""

    if higher_context is None:
        return False, "Higher context is None."

    try:
        higher_context.run_id = "tampered"  # type: ignore[misc]
    except Exception:
        pass
    else:
        return False, "HigherContext top-level mutation succeeded unexpectedly."

    try:
        higher_context.required_data_categories += ("tampered",)
    except Exception:
        pass
    else:
        return False, "HigherContext tuple field mutation succeeded unexpectedly."

    try:
        higher_context.problem_analysis["tampered"] = True
    except TypeError:
        pass
    else:
        return False, "HigherContext nested dictionary mutation succeeded unexpectedly."

    return True, "HigherContext rejects top-level and nested mutation."


def check_personal_contexts_reference_higher(
    spec: AgentDispatchSpec | None,
) -> tuple[bool, str]:
    """Gate: each personal context references the higher context run_id."""

    if spec is None:
        return False, "Dispatch spec is missing."
    if not spec.personal_contexts:
        return True, "No personal contexts (no roles selected); acceptable."
    hc_run_id = spec.higher_context.run_id if spec.higher_context else None
    if not hc_run_id:
        return False, "Higher context run_id is missing."
    mismatches = [
        pc.agent_id
        for pc in spec.personal_contexts
        if pc.higher_context_ref != hc_run_id
    ]
    if mismatches:
        return False, f"Personal contexts missing higher_context_ref: {mismatches}"
    return True, "All personal contexts reference higher context."


def check_artifact_count(
    workspace: CommonWorkspace | None,
    min_count: int = 1,
) -> tuple[bool, str]:
    """Gate: artifact count meets the minimum."""

    actual = len(workspace.artifacts) if workspace else 0
    if actual < min_count:
        return False, f"Artifact count {actual} is below minimum {min_count}."
    return True, f"Artifact count {actual} >= {min_count}."


def check_workspace_append_only(run: WarRoomRun | None) -> tuple[bool, str]:
    """Gate: CommonWorkspace rejects external mutation."""

    if run is None or run.workspace is None:
        return False, "Workspace is missing."
    workspace = run.workspace
    if not isinstance(workspace.artifacts, tuple):
        return False, "Workspace artifacts is not a tuple."

    try:
        workspace.artifacts = ()  # type: ignore[misc]
    except Exception:
        pass
    else:
        return False, "Workspace artifact replacement succeeded unexpectedly."

    if hasattr(workspace.artifacts, "append"):
        return False, "Workspace artifacts exposes append; expected immutable tuple."

    return True, "Workspace rejects external mutation and stores tuple artifacts."


def check_judge_summary(run: WarRoomRun | None) -> tuple[bool, str]:
    """Gate: judge was executed; interventions may be empty."""

    if run is None:
        return False, "Run is None."
    if run.judge_interventions is None:
        return False, "Judge was not executed (judge_interventions is None)."
    return True, "Judge summary present."


def check_human_review_for_contradictions(
    run: WarRoomRun | None,
) -> tuple[bool, str]:
    """Gate: high/critical judge interventions require human review."""

    if run is None or not run.judge_interventions:
        return True, "No interventions; no review required."
    offenders = [
        intervention.intervention_id
        for intervention in run.judge_interventions
        if intervention.severity in ("high", "critical")
        and not intervention.requires_human_review
    ]
    if offenders:
        return False, f"High/critical interventions lack human review: {offenders}"
    return True, "High/critical interventions require human review."


def check_no_external_apis(run: WarRoomRun | None) -> tuple[bool, str]:
    """Gate: artifacts do not contain evidence of external API calls."""

    if run is None:
        return True, "No run; trivially passes."
    artifact_text = " ".join(
        artifact.content
        for artifact in (run.workspace.artifacts if run.workspace else ())
    ).lower()
    blocked = {"api.openai.com", "api.anthropic.com", "http://", "https://"}
    hits = [pattern for pattern in blocked if pattern in artifact_text]
    if hits:
        return False, f"Artifact content contains external API references: {hits}"
    return True, "No external API references found."


def check_no_unbounded_chat(run: WarRoomRun | None) -> tuple[bool, str]:
    """Gate: artifacts are bounded and do not look like chat transcripts."""

    if run is None or not run.workspace:
        return True, "No workspace; trivially passes."
    max_artifact_length = 20_000
    chat_markers = (
        "\nuser:",
        "\nassistant:",
        "\nagent:",
        "\nagent 1:",
        "\nagent a:",
        "\nspecialist:",
        "\ntranscript:",
        "chat transcript:",
    )
    for artifact in run.workspace.artifacts:
        combined_length = len(artifact.title) + len(artifact.content)
        if combined_length > max_artifact_length:
            return False, (
                f"Artifact '{artifact.title}' is {combined_length} chars, "
                f"exceeds {max_artifact_length}. Possible unbounded chat."
            )
        lowered = f"\n{artifact.content}".lower()
        hits = [marker.strip() for marker in chat_markers if marker in lowered]
        if hits:
            return False, (
                f"Artifact '{artifact.title}' contains chat transcript markers: {hits}"
            )
    return True, "All artifacts are bounded and non-transcript shaped."


def run_quality_gates(
    run: WarRoomRun | None,
    min_artifact_count: int = 1,
) -> list[WarRoomQualityGateResult]:
    """Run all quality gates against a war-room run."""

    higher_context = run.higher_context if run else None
    dispatch_spec = run.dispatch_spec if run else None
    workspace = run.workspace if run else None

    raw_gates: list[tuple[str, tuple[bool, str]]] = [
        ("higher_context_exists", check_higher_context_exists(run)),
        ("higher_context_immutable", check_higher_context_immutable(higher_context)),
        (
            "personal_context_reference",
            check_personal_contexts_reference_higher(dispatch_spec),
        ),
        ("artifact_count", check_artifact_count(workspace, min_artifact_count)),
        ("workspace_append_only", check_workspace_append_only(run)),
        ("judge_summary", check_judge_summary(run)),
        ("human_review_contradictions", check_human_review_for_contradictions(run)),
        ("no_external_apis", check_no_external_apis(run)),
        ("no_unbounded_chat", check_no_unbounded_chat(run)),
    ]
    return [
        WarRoomQualityGateResult(name=name, passed=passed, detail=detail)
        for name, (passed, detail) in raw_gates
    ]


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WR_CASES_DIR = PROJECT_ROOT / "evals" / "war_room_cases"
DEFAULT_WR_RESULTS_DIR = PROJECT_ROOT / ".decision_system" / "evals"
DEFAULT_WR_RESULTS_PATH = DEFAULT_WR_RESULTS_DIR / "war_room_results.json"


def load_war_room_eval_cases(
    cases_dir: Path | str = DEFAULT_WR_CASES_DIR,
) -> list[WarRoomEvalCase]:
    """Load war-room evaluation case JSON files from disk."""

    case_path = Path(cases_dir)
    if not case_path.exists():
        return []
    cases = [
        WarRoomEvalCase.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(case_path.glob("*.json"))
    ]
    return sorted(cases, key=lambda case: case.case_id)


def run_war_room_eval_case(case: WarRoomEvalCase) -> WarRoomEvalResult:
    """Run one war-room eval case through the actual war-room pipeline."""

    try:
        from decision_system.war_room.runner import run_war_room as _run_war_room

        run = _run_war_room(case.question)
        higher_context = run.higher_context
        dispatch_spec = run.dispatch_spec

        quality_gates = run_quality_gates(run, case.min_artifact_count)
        gate_results = {gate.name: gate.passed for gate in quality_gates}
        gates_passed = all(gate.passed for gate in quality_gates)

        expected_roles = set(case.expected_roles)
        actual_roles = set(dispatch_spec.dispatch_order if dispatch_spec else [])
        role_match = expected_roles.issubset(actual_roles) if expected_roles else True

        expected_tools = set(case.expected_tools)
        actual_tools = set(higher_context.allowed_tools if higher_context else [])
        tool_match = expected_tools.issubset(actual_tools) if expected_tools else True

        expected_categories = set(case.expected_data_categories)
        actual_categories = set(
            higher_context.required_data_categories if higher_context else []
        )
        data_category_match = (
            expected_categories.issubset(actual_categories)
            if expected_categories
            else True
        )

        artifact_count_passed = gate_results.get("artifact_count", False)
        judge_summary_present = (
            gate_results.get("judge_summary", False)
            if case.requires_judge_summary
            else True
        )
        no_crash = True

        notes: list[str] = []
        if not role_match:
            notes.append(
                f"Expected roles {sorted(expected_roles)}, got {sorted(actual_roles)}."
            )
        if not tool_match:
            notes.append(
                f"Expected tools {sorted(expected_tools)}, got {sorted(actual_tools)}."
            )
        if not data_category_match:
            notes.append(
                "Expected data categories "
                f"{sorted(expected_categories)}, got {sorted(actual_categories)}."
            )
        for gate in quality_gates:
            if not gate.passed:
                notes.append(f"Gate '{gate.name}' failed: {gate.detail}")

        passed = (
            role_match
            and tool_match
            and data_category_match
            and artifact_count_passed
            and judge_summary_present
            and no_crash
            and gates_passed
        )

        return WarRoomEvalResult(
            case_id=case.case_id,
            passed=passed,
            quality_gates=quality_gates,
            role_match=role_match,
            tool_match=tool_match,
            data_category_match=data_category_match,
            artifact_count_passed=artifact_count_passed,
            judge_summary_present=judge_summary_present,
            no_crash=no_crash,
            notes=notes,
        )
    except Exception as exc:
        return WarRoomEvalResult(
            case_id=case.case_id,
            passed=False,
            quality_gates=[],
            role_match=False,
            tool_match=False,
            data_category_match=False,
            artifact_count_passed=False,
            judge_summary_present=False,
            no_crash=False,
            notes=[f"Crash during eval: {exc}"],
        )


def run_war_room_eval_suite(
    cases: list[WarRoomEvalCase] | None = None,
) -> WarRoomEvalSuiteResult:
    """Run all war-room eval cases and return a suite result."""

    if cases is None:
        cases = load_war_room_eval_cases()
    results = [run_war_room_eval_case(case) for case in cases]
    passed_count = sum(1 for result in results if result.passed)
    return WarRoomEvalSuiteResult(
        total_cases=len(cases),
        passed_cases=passed_count,
        failed_cases=len(cases) - passed_count,
        results=results,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


def render_war_room_eval_report(suite: WarRoomEvalSuiteResult) -> str:
    """Render a text report suitable for CLI output."""

    overall = "PASS" if suite.total_cases > 0 and suite.failed_cases == 0 else "FAIL"
    lines = [
        "War-Room Evaluation Report",
        f"Overall: {overall}",
        "",
        "Cases:",
    ]
    for result in suite.results:
        status = "PASS" if result.passed else "FAIL"
        dimensions = (
            f"roles={result.role_match}, "
            f"tools={result.tool_match}, "
            f"categories={result.data_category_match}, "
            f"artifacts={result.artifact_count_passed}, "
            f"judge={result.judge_summary_present}, "
            f"no_crash={result.no_crash}"
        )
        lines.append(f"- {result.case_id}: {status} ({dimensions})")
        failed_gates = [gate.name for gate in result.quality_gates if not gate.passed]
        if failed_gates:
            lines.append(f"  - Failed gates: {', '.join(failed_gates)}")
        for note in result.notes:
            lines.append(f"  - {note}")
    lines.append("")
    lines.append(
        f"Passed: {suite.passed_cases}/{suite.total_cases}"
        f" | Failed: {suite.failed_cases}"
    )
    if suite.saved_path:
        lines.append(f"Saved results: {suite.saved_path}")
    return "\n".join(lines)


def save_war_room_eval_results(
    suite: WarRoomEvalSuiteResult,
    results_dir: Path | str = DEFAULT_WR_RESULTS_DIR,
) -> WarRoomEvalSuiteResult:
    """Save war-room eval results to the fixed audit path."""

    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "war_room_results.json"
    saved_suite = suite.model_copy(
        update={"saved_path": str(output_path.resolve())}
    )
    output_path.write_text(
        saved_suite.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    return saved_suite
