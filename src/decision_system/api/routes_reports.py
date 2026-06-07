"""Decision report endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter

from decision_system.api.models import ApiReportResponse, AskRequest, api_error, to_jsonable
from decision_system.config import load_settings
from decision_system.context.builder import DecisionContextBuilder
from decision_system.context.models import DecisionContext
from decision_system.context.store import save_context
from decision_system.graph.workflow import build_workflow
from decision_system.llm.factory import get_provider
from decision_system.models import DecisionReport
from decision_system.reports.renderer import render_decision_report

router = APIRouter(tags=["reports"])


def _save_run(result: dict) -> Path:
    runs_dir = Path(".decision_system") / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_path = runs_dir / f"{result['run_id']}.json"
    run_path.write_text(
        json.dumps(to_jsonable(result), indent=2) + "\n",
        encoding="utf-8",
    )
    return run_path.resolve()


def _report_context(
    context: DecisionContext,
    *,
    include_insights: bool,
    include_orchestration: bool,
) -> DecisionContext:
    human_review_items = list(context.human_review_items)
    if not include_orchestration:
        human_review_items = [
            item
            for item in human_review_items
            if not item.startswith("Judge ")
        ]

    return DecisionContext(
        run_id=context.run_id,
        question=context.question,
        problem_analysis=context.problem_analysis,
        relevant_data_categories=context.relevant_data_categories,
        relevant_storage_tiers=context.relevant_storage_tiers,
        relevant_ontology_concepts=context.relevant_ontology_concepts,
        relevant_insights=context.relevant_insights if include_insights else [],
        graph_signals=context.graph_signals if include_insights or include_orchestration else [],
        orchestration_summary=context.orchestration_summary if include_orchestration else {},
        judge_summary=context.judge_summary if include_orchestration else {},
        human_review_items=human_review_items,
        created_at=context.created_at,
    )


try:
    import chromadb as _chromadb
except ImportError:  # pragma: no cover
    _chromadb = None  # type: ignore[assignment]


@router.post("/ask", response_model=ApiReportResponse)
def ask(request: AskRequest) -> ApiReportResponse:
    settings = load_settings()
    active_provider = (request.provider or settings.provider).strip().lower()
    try:
        get_provider(active_provider, settings=settings)
    except Exception as exc:
        raise api_error(
            400,
            "provider_not_ready",
            f"Provider '{active_provider}' is not ready: {exc}",
        ) from exc

    run_id = str(uuid4())
    graph_input: dict[str, object] = {
        "run_id": run_id,
        "question": request.question,
        "top_k": request.top_k,
    }
    if request.provider is not None:
        graph_input["provider"] = active_provider

    context: DecisionContext | None = None
    saved_context_path: Path | None = None
    if request.include_insights or request.orchestrated or request.save_context:
        context = DecisionContextBuilder().build(
            question=request.question,
            run_id=run_id,
        )
        if request.save_context:
            saved_context_path = save_context(context)

    try:
        result = build_workflow().invoke(graph_input)
    except Exception as exc:
        if _chromadb and isinstance(exc, _chromadb.errors.NotFoundError):
            raise api_error(
                400,
                "missing_index",
                "No document index found. Run decision-system index first, "
                "or add documents to company_docs/.",
            ) from exc
        raise

    if context is not None and (request.include_insights or request.orchestrated):
        report = result.get("final_report")
        if isinstance(report, DecisionReport):
            result["final_report"] = render_decision_report(
                question=request.question,
                run_id=str(result.get("run_id", context.run_id)),
                claims=result.get("claims", []),
                context=_report_context(
                    context,
                    include_insights=request.include_insights,
                    include_orchestration=request.orchestrated,
                ),
            )

    saved_run_path = _save_run(result) if request.save_run else None
    report = result["final_report"]
    data = {
        "retrieved_evidence": to_jsonable(result.get("retrieved_evidence", [])),
        "claims": to_jsonable(result.get("claims", [])),
        "verification_results": to_jsonable(result.get("verification_results", [])),
    }
    if context is not None:
        data["decision_context"] = to_jsonable(context)
    if saved_context_path is not None:
        data["saved_context_path"] = str(saved_context_path)
    if saved_run_path is not None:
        data["saved_run_path"] = str(saved_run_path)

    return ApiReportResponse(
        run_id=str(result.get("run_id", run_id)),
        question=request.question,
        status="completed",
        report=to_jsonable(report),
        data=data,
    )
