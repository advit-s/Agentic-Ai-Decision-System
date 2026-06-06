"""Insight detection endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, ApiStatusResponse, to_jsonable
from decision_system.data_catalog.store import load_profiles
from decision_system.graphing.store import load_knowledge_graph
from decision_system.insights.detectors import run_detectors
from decision_system.insights.store import load_insights, save_insights


router = APIRouter(tags=["insights"])


@router.post("/insights/detect", response_model=ApiRunResponse)
def detect_insights() -> ApiRunResponse:
    store = run_detectors(
        profiles=load_profiles(),
        graph=load_knowledge_graph(),
    )
    saved_path = save_insights(store)
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed",
        data={
            "insight_count": len(store.insights),
            "insights_by_severity": dict(store.severity_counts()),
            "insights_by_category": dict(store.category_counts()),
            "saved_path": str(saved_path),
            "insights": to_jsonable(store.insights),
        },
    )


@router.get("/insights", response_model=ApiStatusResponse)
def get_insights() -> ApiStatusResponse:
    store = load_insights()
    return ApiStatusResponse(
        status="ok",
        service="decision-system-api",
        data=to_jsonable(store),
    )
