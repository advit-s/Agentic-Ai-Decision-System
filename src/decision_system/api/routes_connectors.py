"""Minimal connector API endpoints for v1.1."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from decision_system.connectors.inspector import (
    inspect_dry_run_result,
    inspect_import_job,
)
from decision_system.connectors.import_jobs import (
    run_dry_run as _run_dry_run,
)
from decision_system.connectors.import_jobs import (
    run_import as _run_import,
)
from decision_system.connectors.registry import (
    get_connector_definition,
    get_registry,
    list_connectors,
)
from decision_system.connectors.store import load_jobs

router = APIRouter(prefix="/connectors", tags=["connectors"])


class DryRunRequest(BaseModel):
    path: str


class ImportRequest(BaseModel):
    path: str


def _serialize_definition(definition: Any) -> dict[str, Any]:
    return {
        "connector_id": definition.connector_id,
        "name": definition.name,
        "connector_type": definition.connector_type.value,
        "status": definition.status.value,
        "description": definition.description,
        "capabilities": [c.value for c in definition.capabilities],
        "requires_secrets": definition.requires_secrets,
        "supports_dry_run": definition.supports_dry_run,
        "supports_import": definition.supports_import,
        "is_stub": definition.is_stub,
    }


@router.get("")
def list_connectors_api() -> dict[str, Any]:
    """List all registered connectors."""
    registry = get_registry()
    connectors = [_serialize_definition(d) for d in registry.list_connectors()]
    return {"connectors": connectors}


@router.get("/jobs")
def list_connector_jobs() -> dict[str, Any]:
    """List all connector import jobs."""
    jobs = load_jobs()
    return {
        "jobs": [
            inspect_import_job(job)
            for job in jobs
        ]
    }


@router.get("/{connector_id}")
def get_connector(connector_id: str) -> dict[str, Any]:
    """Inspect a single connector."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    return {"definition": _serialize_definition(definition)}


@router.post("/{connector_id}/dry-run")
def dry_run_connector(connector_id: str, request: DryRunRequest) -> dict[str, Any]:
    """Run a connector dry-run."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    if definition.is_stub:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_id}' is a stub and does not support dry-run in v1.1.",
        )
    result = _run_dry_run(connector_id, request.path)
    return {"result": inspect_dry_run_result(result)}


@router.post("/{connector_id}/import")
def import_connector(connector_id: str, request: ImportRequest) -> dict[str, Any]:
    """Run a connector import."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    if definition.is_stub:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_id}' is a stub and does not support import in v1.1.",
        )
    result = _run_import(connector_id, request.path)
    return {"result": inspect_import_job(result.job)}
