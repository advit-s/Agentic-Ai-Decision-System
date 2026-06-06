"""Ontology endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, ApiStatusResponse, to_jsonable
from decision_system.data_catalog.store import load_profiles
from decision_system.ontology.mapper import map_profiles_to_ontology
from decision_system.ontology.store import load_ontology, save_ontology


router = APIRouter(tags=["ontology"])


@router.post("/ontology/map", response_model=ApiRunResponse)
def map_ontology() -> ApiRunResponse:
    omap = map_profiles_to_ontology(load_profiles())
    saved_path = save_ontology(omap)
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed",
        data={
            "concept_count": len(omap.concepts),
            "mapping_count": len(omap.column_mappings),
            "saved_path": str(saved_path),
            "ontology": to_jsonable(omap),
        },
    )


@router.get("/ontology", response_model=ApiStatusResponse)
def get_ontology() -> ApiStatusResponse:
    omap = load_ontology()
    return ApiStatusResponse(
        status="ok",
        service="decision-system-api",
        data=to_jsonable(omap),
    )
