"""Minimal connector API endpoints for v1.1."""

from __future__ import annotations

from pathlib import Path
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

# ---------------------------------------------------------------------------
# Safe-path helpers
# ---------------------------------------------------------------------------

_BLOCKED_ABSOLUTE_PREFIXES: tuple[str, ...] = (
    "/tmp",
    "/etc",
    "/root",
    "/home",
    "/var",
    "/usr",
    "/bin",
    "/sbin",
    "/proc",
    "/sys",
    "/dev",
    "/boot",
    "/opt",
)


def _reject_connector_path(path_str: str) -> str:
    """Validate a connector path — reject dangerous roots and traversal."""
    path = Path(path_str)

    # Reject path-traversal components.
    if ".." in path_str:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsafe_path",
                "message": "Connector path must not contain path-traversal (..) elements",
                "details": {"path": path_str},
            },
        )

    # Reject blocked absolute paths.
    if path.is_absolute():
        resolved_str = str(path.resolve())
        for prefix in _BLOCKED_ABSOLUTE_PREFIXES:
            if resolved_str == prefix or resolved_str.startswith(prefix + "/"):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "unsafe_path",
                        "message": f"Connector path must not be a system directory ({prefix}...)",
                        "details": {"path": path_str},
                    },
                )

    return path_str


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
    # Validate path safety before passing to backend.
    _reject_connector_path(request.path)
    try:
        result = _run_dry_run(connector_id, request.path)
    except (OSError, PermissionError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Connector dry-run failed: {exc}",
        )
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
    # Validate path safety before passing to backend.
    _reject_connector_path(request.path)
    try:
        result = _run_import(connector_id, request.path)
    except (OSError, PermissionError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Connector import failed: {exc}",
        )
    return {"result": inspect_import_job(result.job)}
