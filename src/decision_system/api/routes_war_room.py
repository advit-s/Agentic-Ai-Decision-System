"""War-room protocol endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, ApiStatusResponse, QuestionRequest, to_jsonable
from decision_system.war_room.dispatcher import build_dispatch_spec
from decision_system.war_room.runner import run_war_room
from decision_system.war_room.store import load_latest_run


router = APIRouter(tags=["war-room"])


@router.post("/war-room/plan", response_model=ApiRunResponse)
def plan_war_room(request: QuestionRequest) -> ApiRunResponse:
    spec = build_dispatch_spec(request.question)
    return ApiRunResponse(
        run_id=spec.run_id,
        status="completed",
        data=to_jsonable(spec),
    )


@router.post("/war-room/run", response_model=ApiRunResponse)
def run_war_room_endpoint(request: QuestionRequest) -> ApiRunResponse:
    run = run_war_room(request.question)
    return ApiRunResponse(
        run_id=run.run_id,
        status="completed",
        data=to_jsonable(run),
    )


@router.get("/war-room/latest")
def latest_war_room_run() -> ApiRunResponse | ApiStatusResponse:
    run = load_latest_run()
    if run is None:
        return ApiStatusResponse(
            status="empty",
            service="decision-system-api",
            data={},
        )
    return ApiRunResponse(
        run_id=run.run_id,
        status="ok",
        data=to_jsonable(run),
    )
