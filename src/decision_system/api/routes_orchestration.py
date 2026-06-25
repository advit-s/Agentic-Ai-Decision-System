"""Orchestration endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, QuestionRequest, to_jsonable
from decision_system.orchestration.planner import plan_data_tools_roles
from decision_system.orchestration.problem_analyzer import analyze_problem
from decision_system.orchestration.workflow import run_orchestration

router = APIRouter(tags=["orchestration"])


@router.post("/orchestration/analyze", response_model=ApiRunResponse)
def analyze_orchestration(request: QuestionRequest) -> ApiRunResponse:
    analysis = plan_data_tools_roles(analyze_problem(request.question))
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed",
        data=to_jsonable(analysis),
    )


@router.post("/orchestration/run", response_model=ApiRunResponse)
def run_orchestration_endpoint(request: QuestionRequest) -> ApiRunResponse:
    result = run_orchestration(request.question, save=True)
    return ApiRunResponse(
        run_id=str(result["run_id"]),
        status=str(result.get("status", "completed")),
        data=to_jsonable(result),
    )
