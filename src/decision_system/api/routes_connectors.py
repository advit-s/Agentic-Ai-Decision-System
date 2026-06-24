"""v1.28 Connector API endpoints — full CRUD, test, list items, import, jobs.

All connectors are read-only, workspace-scoped, audited, and permission-gated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from decision_system.api.models import to_jsonable
from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import (
    require_permission,
    require_workspace_permission,
)

from decision_system.connectors.config_store import (
    ConnectorConfigStore,
    get_config_store,
    reset_config_store,
)
from decision_system.connectors.inspector import (
    inspect_dry_run_result,
    inspect_import_job,
)
from decision_system.connectors.import_jobs import (
    run_dry_run as _run_dry_run,
    run_import as _run_import,
    run_import_v2,
    run_test_connection,
    run_list_items,
)
from decision_system.connectors.models import (
    ConnectorConfig,
    ConnectorConfigStatus,
    ConnectorMode,
    ConnectorSecretRef,
    ConnectorType,
)
from decision_system.connectors.registry import (
    get_connector_definition,
    get_registry,
    list_connectors,
)
from decision_system.connectors.store import load_jobs as _load_jobs
from decision_system.connectors.audit import (
    record_connector_created,
    record_connector_updated,
    record_connector_deleted,
    record_connector_tested,
    record_connector_items_listed,
)

router = APIRouter(tags=["connectors"])


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------


class ConnectorCreateRequest(BaseModel):
    name: str
    connector_type: str
    workspace_id: str | None = None
    config: dict[str, Any] = {}
    secret_refs: list[dict[str, Any]] = []


class ConnectorUpdateRequest(BaseModel):
    name: str | None = None
    config: dict[str, Any] | None = None
    secret_refs: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class TestConnectionResponse(BaseModel):
    success: bool
    message: str
    details: dict[str, Any] = {}


class ImportRequest(BaseModel):
    item_ids: list[str] | None = None


# ---------------------------------------------------------------------------
# Safe-path helpers (v1.1 compatibility)
# ---------------------------------------------------------------------------

_BLOCKED_ABSOLUTE_PREFIXES: tuple[str, ...] = (
    "/tmp", "/etc", "/root", "/home", "/var", "/usr",
    "/bin", "/sbin", "/proc", "/sys", "/dev", "/boot", "/opt",
)


def _reject_connector_path(path_str: str) -> str:
    path = Path(path_str)
    if ".." in path_str:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsafe_path",
                "message": "Connector path must not contain path-traversal (..) elements",
                "details": {"path": path_str},
            },
        )
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


# ---------------------------------------------------------------------------
# Connector definition endpoints (read-only registry)
# ---------------------------------------------------------------------------


@router.get("/connectors")
def list_connectors_api(
    _user: LocalUser = Depends(require_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List all registered connector definitions."""
    registry = get_registry()
    connectors = [_serialize_definition(d) for d in registry.list_connectors()]
    return {"connectors": connectors}


@router.get("/connectors/jobs")
def list_connector_jobs_v1() -> dict[str, Any]:
    """List all connector import jobs (v1.1 backward compat)."""
    jobs = _load_jobs()
    return {"jobs": [inspect_import_job(j) for j in jobs]}


@router.get("/connectors/{connector_id}")
def get_connector(
    connector_id: str,
    _user: LocalUser = Depends(require_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """Inspect a single connector definition."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    return {"definition": _serialize_definition(definition)}


# ---------------------------------------------------------------------------
# Connector config CRUD (workspace-scoped)
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/connectors")
def list_connector_configs(
    workspace_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List connector configs for a workspace."""
    store = get_config_store()
    configs = store.list_by_workspace(workspace_id)
    return {
        "connectors": [c.to_api_response(include_secrets=False) for c in configs],
        "count": len(configs),
    }


@router.post("/workspaces/{workspace_id}/connectors")
def create_connector_config(
    workspace_id: str,
    request: ConnectorCreateRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_MANAGE)),
) -> dict[str, Any]:
    """Create a new connector config in a workspace."""
    # Validate connector type
    try:
        connector_type = ConnectorType(request.connector_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_connector_type",
                "message": f"Invalid connector type: {request.connector_type}",
                "valid_types": [t.value for t in ConnectorType],
            },
        )

    # Validate it's a real connector (not stub/unavailable)
    definition = get_connector_definition(connector_type.value)
    if definition is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unknown_connector_type",
                "message": f"Unknown connector type: {request.connector_type}",
            },
        )
    if definition.is_stub:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "connector_unavailable",
                "message": f"Connector '{request.connector_type}' is not available in v1.28",
            },
        )

    store = get_config_store()
    secret_refs = [
        ConnectorSecretRef(**s) if isinstance(s, dict) else s
        for s in request.secret_refs
    ]
    cfg = store.create(
        name=request.name,
        connector_type=connector_type,
        config=request.config,
        workspace_id=workspace_id,
        secret_refs=secret_refs,
    )

    record_connector_created(
        connector_id=cfg.connector_id,
        name=cfg.name,
        connector_type=cfg.connector_type.value,
        workspace_id=workspace_id,
    )

    return {"connector": cfg.to_api_response(include_secrets=False)}


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}")
def get_connector_config(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """Get a single connector config."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Connector config not found")
    return {"connector": cfg.to_api_response(include_secrets=False)}


@router.put("/workspaces/{workspace_id}/connectors/{connector_id}")
def update_connector_config(
    workspace_id: str,
    connector_id: str,
    request: ConnectorUpdateRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_MANAGE)),
) -> dict[str, Any]:
    """Update a connector config."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Connector config not found")

    if request.name is not None:
        cfg.name = request.name
    if request.config is not None:
        cfg.config = request.config
    if request.secret_refs is not None:
        cfg.secret_refs = [
            ConnectorSecretRef(**s) if isinstance(s, dict) else s
            for s in request.secret_refs
        ]
    if request.metadata is not None:
        cfg.metadata = request.metadata

    store.save(cfg)

    record_connector_updated(
        connector_id=cfg.connector_id,
        name=cfg.name,
        workspace_id=workspace_id,
    )

    return {"connector": cfg.to_api_response(include_secrets=False)}


@router.delete("/workspaces/{workspace_id}/connectors/{connector_id}")
def delete_connector_config(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_MANAGE)),
) -> dict[str, Any]:
    """Delete a connector config."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None:
        raise HTTPException(status_code=404, detail="Connector config not found")

    store.delete(workspace_id, connector_id)

    record_connector_deleted(
        connector_id=connector_id,
        name=cfg.name,
        workspace_id=workspace_id,
    )

    return {"status": "deleted", "connector_id": connector_id}


# ---------------------------------------------------------------------------
# Connector operations: test, list items, import
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/test")
def test_connector(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """Test a connector's connection."""
    result = run_test_connection(
        connector_id=connector_id,
        workspace_id=workspace_id,
    )

    record_connector_tested(
        connector_id=connector_id,
        success=result.get("success", False),
        workspace_id=workspace_id,
    )

    return {"result": result}


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}/items")
def list_connector_items(
    workspace_id: str,
    connector_id: str,
    path: str = "",
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List items available from a connector."""
    items = run_list_items(
        connector_id=connector_id,
        path=path,
        workspace_id=workspace_id,
    )

    record_connector_items_listed(
        connector_id=connector_id,
        item_count=len(items),
        workspace_id=workspace_id,
    )

    return {
        "items": [to_jsonable(i) for i in items],
        "count": len(items),
    }


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/import")
def import_connector_items(
    workspace_id: str,
    connector_id: str,
    request: ImportRequest = ImportRequest(),
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_IMPORT)),
) -> dict[str, Any]:
    """Import selected (or all) items from a connector into the workspace."""
    result = run_import_v2(
        connector_id=connector_id,
        workspace_id=workspace_id,
        item_ids=request.item_ids,
    )
    return {"result": inspect_import_job(result.job)}


# ---------------------------------------------------------------------------
# Import job history
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/connector-jobs")
def list_connector_jobs(
    workspace_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List connector import jobs for a workspace."""
    jobs = _load_jobs()
    # Filter by workspace_id
    ws_jobs = [j for j in jobs if j.workspace_id == workspace_id or j.workspace_id is None]
    return {"jobs": [inspect_import_job(j) for j in ws_jobs]}


@router.get("/workspaces/{workspace_id}/connector-jobs/{job_id}")
def get_connector_job(
    workspace_id: str,
    job_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """Get a single connector import job."""
    from decision_system.connectors.store import get_job
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return {"job": inspect_import_job(job)}


# ---------------------------------------------------------------------------
# v1.1 backward-compatible endpoints
# ---------------------------------------------------------------------------


class DryRunRequest(BaseModel):
    path: str


@router.post("/connectors/{connector_id}/dry-run")
def dry_run_connector(connector_id: str, request: DryRunRequest) -> dict[str, Any]:
    """Run a connector dry-run (v1.1 backward compat)."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    if definition.is_stub:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_id}' is a stub and does not support dry-run in v1.1.",
        )
    _reject_connector_path(request.path)
    try:
        result = _run_dry_run(connector_id, request.path)
    except (OSError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=f"Connector dry-run failed: {exc}")
    return {"result": inspect_dry_run_result(result)}


@router.post("/connectors/{connector_id}/import")
def import_connector_v1(connector_id: str, request: ImportRequest) -> dict[str, Any]:
    """Run a connector import (v1.1 backward compat)."""
    definition = get_connector_definition(connector_id)
    if definition is None:
        raise HTTPException(status_code=404, detail=f"Unknown connector '{connector_id}'")
    if definition.is_stub:
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector_id}' is a stub and does not support import in v1.1.",
        )
    try:
        result = _run_import(connector_id, "")
    except (OSError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=f"Connector import failed: {exc}")
    return {"result": inspect_import_job(result.job)}


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


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
        "supports_list": definition.supports_list,
        "supports_test": definition.supports_test,
        "is_stub": definition.is_stub,
    }
