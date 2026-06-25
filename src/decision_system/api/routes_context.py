"""Decision context endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, QuestionRequest, to_jsonable
from decision_system.context.builder import DecisionContextBuilder

router = APIRouter(tags=["context"])


@router.post("/context/build", response_model=ApiRunResponse)
def build_context(request: QuestionRequest) -> ApiRunResponse:
    context = DecisionContextBuilder().build(question=request.question)
    return ApiRunResponse(
        run_id=context.run_id,
        status="completed",
        data=to_jsonable(context),
    )
