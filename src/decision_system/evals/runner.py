"""Local evaluation runner for the fixed decision workflow."""

import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from decision_system.evals.models import EvalCase, EvalMetrics, EvalResult, EvalSuiteResult
from decision_system.graph.workflow import build_workflow
from decision_system.rag.chunker import chunk_documents
from decision_system.rag.loader import load_documents
from decision_system.rag.vector_store import index_chunks


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CASES_DIR = PROJECT_ROOT / "evals" / "cases"
DEFAULT_RESULTS_DIR = PROJECT_ROOT / "evals" / "results"


def load_eval_cases(cases_dir: Path | str = DEFAULT_CASES_DIR) -> list[EvalCase]:
    """Load evaluation case JSON files from disk."""

    case_path = Path(cases_dir)
    cases = [
        EvalCase.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(case_path.glob("*.json"))
    ]
    return sorted(cases, key=lambda case: case.case_id)


def run_eval_suite(cases: list[EvalCase] | None = None) -> EvalSuiteResult:
    """Run all configured evaluation cases."""

    eval_cases = cases if cases is not None else load_eval_cases()
    results = [run_eval_case(case) for case in eval_cases]
    return EvalSuiteResult(
        passed=all(result.passed for result in results),
        cases=results,
    )


def run_eval_case(case: EvalCase) -> EvalResult:
    """Run one case through temporary indexing and the normal workflow."""

    with tempfile.TemporaryDirectory(
        prefix=f"decision-eval-{case.case_id}-",
        ignore_cleanup_errors=True,
    ) as tmp:
        try:
            tmp_path = Path(tmp)
            docs_dir = tmp_path / "docs"
            store_dir = tmp_path / "chroma"
            docs_dir.mkdir(parents=True, exist_ok=True)
            _write_case_documents(case, docs_dir)

            documents = load_documents(docs_dir)
            chunks = chunk_documents(documents)
            collection_name = f"eval_{case.case_id}"
            index_chunks(chunks, store_dir=store_dir, collection_name=collection_name)

            with _temporary_settings(docs_dir, store_dir, collection_name):
                run_id = f"eval-{case.case_id}-{uuid4()}"
                result = build_workflow().invoke(
                    {
                        "run_id": run_id,
                        "question": case.question,
                        "top_k": 6,
                        "provider": "fake",
                    }
                )
        finally:
            _clear_chroma_system_cache()

    metrics = _collect_metrics(result)
    failures = _check_expectations(case, metrics)
    return EvalResult(
        case_id=case.case_id,
        question=case.question,
        passed=not failures,
        failures=failures,
        run_id=str(result["run_id"]),
        metrics=metrics,
    )


def save_eval_results(
    suite_result: EvalSuiteResult,
    results_dir: Path | str = DEFAULT_RESULTS_DIR,
) -> EvalSuiteResult:
    """Save suite results under `evals/results/` and return updated metadata."""

    output_dir = Path(results_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"eval-results-{timestamp}.json"
    saved_result = suite_result.model_copy(update={"saved_result_path": str(output_path.resolve())})
    output_path.write_text(saved_result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return saved_result


def render_eval_report(suite_result: EvalSuiteResult) -> str:
    """Render a concise text report for CLI output."""

    lines = [
        "Evaluation Report",
        f"Overall: {'PASS' if suite_result.passed else 'FAIL'}",
        "",
        "Cases:",
    ]
    for result in suite_result.cases:
        status = "PASS" if result.passed else "FAIL"
        metrics = result.metrics
        lines.append(
            "- "
            f"{result.case_id}: {status} "
            f"(verified={metrics.verified_claims}, "
            f"unsupported={metrics.unsupported_claims}, "
            f"contradicted={metrics.contradicted_claims}, "
            f"confidence={metrics.confidence_level}, "
            f"human_review={metrics.human_review_required})"
        )
        for failure in result.failures:
            lines.append(f"  - {failure}")
    if suite_result.saved_result_path:
        lines.extend(["", f"Saved results: {suite_result.saved_result_path}"])
    return "\n".join(lines)


def _write_case_documents(case: EvalCase, docs_dir: Path) -> None:
    for document in case.documents:
        filename = Path(document.filename)
        if filename.name != document.filename:
            raise ValueError(f"Eval document filename must not include a path: {document.filename}")
        (docs_dir / document.filename).write_text(document.text, encoding="utf-8")


def _collect_metrics(workflow_result: dict) -> EvalMetrics:
    evidence = workflow_result.get("retrieved_evidence", [])
    claims = workflow_result.get("claims", [])
    final_report = workflow_result["final_report"]
    markdown = final_report.markdown
    return EvalMetrics(
        retrieved_evidence=len(evidence),
        source_filenames=sorted({chunk.source_filename for chunk in evidence}),
        verified_claims=sum(1 for claim in claims if claim.status == "verified"),
        unsupported_claims=sum(1 for claim in claims if claim.status == "unsupported"),
        contradicted_claims=sum(1 for claim in claims if claim.status == "contradicted"),
        evidence_citations=len(final_report.evidence_citations),
        confidence_level=final_report.confidence_level,
        human_review_required=bool(final_report.human_review_required),
        report_sections_present=[
            section for section in _known_report_sections() if section in markdown
        ],
    )


def _check_expectations(case: EvalCase, metrics: EvalMetrics) -> list[str]:
    expectations = case.expectations
    failures: list[str] = []

    missing_sources = [
        filename
        for filename in expectations.required_source_filenames
        if filename not in metrics.source_filenames
    ]
    if missing_sources:
        failures.append(f"Missing required source filenames: {', '.join(missing_sources)}")

    if metrics.verified_claims < expectations.min_verified_claims:
        failures.append(
            f"Expected at least {expectations.min_verified_claims} verified claim(s), "
            f"got {metrics.verified_claims}."
        )
    if metrics.unsupported_claims < expectations.min_unsupported_claims:
        failures.append(
            f"Expected at least {expectations.min_unsupported_claims} unsupported claim(s), "
            f"got {metrics.unsupported_claims}."
        )
    if metrics.contradicted_claims < expectations.min_contradicted_claims:
        failures.append(
            f"Expected at least {expectations.min_contradicted_claims} contradicted claim(s), "
            f"got {metrics.contradicted_claims}."
        )
    if metrics.evidence_citations < expectations.min_evidence_citations:
        failures.append(
            f"Expected at least {expectations.min_evidence_citations} evidence citation(s), "
            f"got {metrics.evidence_citations}."
        )
    if metrics.human_review_required != expectations.human_review_required:
        failures.append(
            f"Expected human_review_required={expectations.human_review_required}, "
            f"got {metrics.human_review_required}."
        )
    if (
        expectations.expected_confidence_level is not None
        and metrics.confidence_level != expectations.expected_confidence_level
    ):
        failures.append(
            f"Expected confidence {expectations.expected_confidence_level}, "
            f"got {metrics.confidence_level}."
        )

    missing_sections = [
        section
        for section in expectations.required_report_sections
        if section not in metrics.report_sections_present
    ]
    if missing_sections:
        failures.append(f"Missing required report sections: {', '.join(missing_sections)}")

    return failures


def _known_report_sections() -> list[str]:
    return [
        "## Recommendation",
        "## Options",
        "## Evidence Citations",
        "## Risks",
        "## Contradictions",
        "## Unsupported Assumptions",
        "## Confidence Level",
        "## Human Review Required",
        "## Decision Question",
    ]


def _clear_chroma_system_cache() -> None:
    try:
        from chromadb.api.shared_system_client import SharedSystemClient

        SharedSystemClient.clear_system_cache()
    except Exception:
        pass


@contextmanager
def _temporary_settings(docs_dir: Path, store_dir: Path, collection_name: str):
    env_keys = {
        "DECISION_DOCS_DIR": str(docs_dir),
        "DECISION_STORE_DIR": str(store_dir),
        "DECISION_COLLECTION": collection_name,
        "DECISION_PROVIDER": "fake",
    }
    previous = {key: os.environ.get(key) for key in env_keys}
    try:
        os.environ.update(env_keys)
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
