"""v1.28 Connector API endpoints — full CRUD, test, list items, import, jobs.

All connectors are read-only, workspace-scoped, audited, and permission-gated.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from decision_system.api.models import to_jsonable
from decision_system.connectors.audit import (
    record_connector_created,
    record_connector_deleted,
    record_connector_items_listed,
    record_connector_tested,
    record_connector_updated,
)
from decision_system.connectors.config_store import (
    get_config_store,
)
from decision_system.connectors.import_jobs import (
    run_dry_run as _run_dry_run,
)
from decision_system.connectors.import_jobs import (
    run_import as _run_import,
)
from decision_system.connectors.import_jobs import (
    run_import_v2,
    run_list_items,
    run_test_connection,
)
from decision_system.connectors.inspector import (
    inspect_dry_run_result,
    inspect_import_job,
)
from decision_system.connectors.models import (
    ConnectorSecretRef,
    ConnectorType,
)
from decision_system.connectors.registry import (
    get_connector_definition,
    get_registry,
)
from decision_system.connectors.store import load_jobs as _load_jobs
from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import (
    require_permission,
    require_workspace_permission,
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


@router.get("/connectors/schemas")
def list_connector_schemas() -> dict[str, Any]:
    """Return all connector setup schemas for UI rendering."""
    from decision_system.connectors.setup_schemas import list_setup_schemas

    schemas = list_setup_schemas()
    return {"schemas": [s.model_dump(mode="json") for s in schemas]}


@router.get("/connectors/{connector_id}/schema")
def get_connector_schema(connector_id: str) -> dict[str, Any]:
    """Return the setup schema for a specific connector type."""
    from decision_system.connectors.setup_schemas import get_setup_schema

    schema = get_setup_schema(connector_id)
    if schema is None:
        raise HTTPException(
            status_code=404, detail=f"No schema found for connector '{connector_id}'"
        )
    return {"schema": schema.model_dump(mode="json")}


@router.get("/connectors/{connector_id}/credential-status")
def get_connector_credential_status(connector_id: str) -> dict[str, Any]:
    """Return safe credential status (no token values exposed)."""
    from decision_system.connectors.registry import get_credential_status

    status = get_credential_status(connector_id)
    return {"credential_status": status or {}}


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
        ConnectorSecretRef(**s) if isinstance(s, dict) else s for s in request.secret_refs
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
            ConnectorSecretRef(**s) if isinstance(s, dict) else s for s in request.secret_refs
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
    result = {
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
    # Attach setup schema if available (v1.30)
    try:
        from decision_system.connectors.setup_schemas import get_setup_schema

        schema = get_setup_schema(definition.connector_id)
        if schema:
            result["setup_schema"] = schema.model_dump(mode="json")
        else:
            result["setup_schema"] = None
    except Exception:
        result["setup_schema"] = None
    return result


# ---------------------------------------------------------------------------
# v1.29 Sync API endpoints
# ---------------------------------------------------------------------------


class SyncScheduleCreateRequest(BaseModel):
    enabled: bool = True
    schedule_type: str = "manual"
    interval_minutes: int | None = None
    cron_expression: str | None = None
    metadata: dict[str, Any] = {}


class SyncScheduleUpdateRequest(BaseModel):
    enabled: bool | None = None
    schedule_type: str | None = None
    interval_minutes: int | None = None
    cron_expression: str | None = None
    metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Manual sync trigger
# ---------------------------------------------------------------------------


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/sync")
def trigger_connector_sync(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_SYNC)),
) -> dict[str, Any]:
    """Manually trigger a sync for a connector.

    Requires connector.sync permission.
    Returns incremental sync results.
    """
    from decision_system.connectors.import_jobs import run_sync

    result = run_sync(
        connector_id=connector_id,
        workspace_id=workspace_id,
    )
    return {"result": result}


# ---------------------------------------------------------------------------
# Sync state inspection
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}/sync-state")
def get_connector_sync_state(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """Get sync state for all items in a connector."""
    from decision_system.connectors.sync_state import get_sync_state_store

    store = get_sync_state_store()
    state = store.get_sync_state(workspace_id, connector_id)
    return {
        "sync_state": [s.model_dump(mode="json") for s in state],
        "count": len(state),
    }


# ---------------------------------------------------------------------------
# Sync schedule CRUD
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}/sync-schedules")
def list_sync_schedules(
    workspace_id: str,
    connector_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List sync schedules for a connector."""
    from decision_system.connectors.schedule import get_schedule_store

    store = get_schedule_store()
    schedules = store.list_schedules(workspace_id, connector_id)
    return {
        "schedules": [s.model_dump(mode="json") for s in schedules],
        "count": len(schedules),
    }


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/sync-schedules")
def create_sync_schedule(
    workspace_id: str,
    connector_id: str,
    request: SyncScheduleCreateRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_SCHEDULE)),
) -> dict[str, Any]:
    """Create a sync schedule for a connector.

    Requires connector.schedule permission.
    """
    from decision_system.connectors.audit import record_schedule_created
    from decision_system.connectors.schedule import (
        ConnectorSchedule,
        get_schedule_store,
    )

    store = get_schedule_store()
    schedule = ConnectorSchedule(
        workspace_id=workspace_id,
        connector_id=connector_id,
        enabled=request.enabled,
        schedule_type=request.schedule_type,
        interval_minutes=request.interval_minutes,
        cron_expression=request.cron_expression,
        metadata=request.metadata,
    )
    schedule = store.create_schedule(workspace_id, schedule)

    record_schedule_created(
        connector_id=connector_id,
        schedule_id=schedule.schedule_id,
        workspace_id=workspace_id,
    )

    return {"schedule": schedule.model_dump(mode="json")}


@router.put("/workspaces/{workspace_id}/connectors/{connector_id}/sync-schedules/{schedule_id}")
def update_sync_schedule(
    workspace_id: str,
    connector_id: str,
    schedule_id: str,
    request: SyncScheduleUpdateRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_SCHEDULE)),
) -> dict[str, Any]:
    """Update a sync schedule."""
    from decision_system.connectors.audit import record_schedule_updated
    from decision_system.connectors.schedule import get_schedule_store

    store = get_schedule_store()
    schedule = store.get_schedule(workspace_id, connector_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    if request.enabled is not None:
        schedule.enabled = request.enabled
    if request.schedule_type is not None:
        schedule.schedule_type = request.schedule_type
    if request.interval_minutes is not None:
        schedule.interval_minutes = request.interval_minutes
    if request.cron_expression is not None:
        schedule.cron_expression = request.cron_expression
    if request.metadata is not None:
        schedule.metadata = request.metadata

    store.update_schedule(workspace_id, schedule)

    record_schedule_updated(
        connector_id=connector_id,
        schedule_id=schedule_id,
        workspace_id=workspace_id,
    )

    return {"schedule": schedule.model_dump(mode="json")}


@router.delete("/workspaces/{workspace_id}/connectors/{connector_id}/sync-schedules/{schedule_id}")
def delete_sync_schedule(
    workspace_id: str,
    connector_id: str,
    schedule_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_SCHEDULE)),
) -> dict[str, Any]:
    """Delete a sync schedule."""
    from decision_system.connectors.audit import record_schedule_deleted
    from decision_system.connectors.schedule import get_schedule_store

    store = get_schedule_store()
    deleted = store.delete_schedule(workspace_id, connector_id, schedule_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Schedule not found")

    record_schedule_deleted(
        connector_id=connector_id,
        schedule_id=schedule_id,
        workspace_id=workspace_id,
    )

    return {"status": "deleted", "schedule_id": schedule_id}


# ---------------------------------------------------------------------------
# System: run all due sync schedules
# ---------------------------------------------------------------------------


@router.post("/connector-sync/run-due")
def run_due_sync_schedules(
    _user: LocalUser = Depends(require_permission(Permission.CONNECTOR_SCHEDULE)),
) -> dict[str, Any]:
    """Find and run all due connector sync schedules.

    Requires connector.schedule permission.
    Intended for use by a local cron or timer.
    """
    from decision_system.connectors.sync_runner import get_sync_runner

    runner = get_sync_runner()
    results = runner.run_due_schedules()

    return {
        "results": [
            {
                "connector_id": r.connector_id,
                "workspace_id": r.workspace_id,
                "status": r.status,
                "items_new": r.items_new,
                "items_changed": r.items_changed,
                "items_unchanged": r.items_unchanged,
                "items_failed": r.items_failed,
                "items_deleted_remote": r.items_deleted_remote,
                "duration_ms": r.duration_ms,
                "job_id": r.job_id,
                "error": r.error,
            }
            for r in results
        ],
        "count": len(results),
    }


# ---------------------------------------------------------------------------
# Toggle schedule (convenience)
# ---------------------------------------------------------------------------


@router.post(
    "/workspaces/{workspace_id}/connectors/{connector_id}/sync-schedules/{schedule_id}/toggle"
)
def toggle_sync_schedule(
    workspace_id: str,
    connector_id: str,
    schedule_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_SCHEDULE)),
) -> dict[str, Any]:
    """Toggle a sync schedule's enabled state."""
    from decision_system.connectors.audit import record_schedule_toggled
    from decision_system.connectors.schedule import get_schedule_store

    store = get_schedule_store()
    schedule = store.toggle_schedule(workspace_id, connector_id, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    record_schedule_toggled(
        connector_id=connector_id,
        schedule_id=schedule_id,
        enabled=schedule.enabled,
        workspace_id=workspace_id,
    )

    return {"schedule": schedule.model_dump(mode="json")}


# ---------------------------------------------------------------------------
# v1.31 Connector reliability endpoints: paginated items, cancel, resume, pause
# ---------------------------------------------------------------------------


class PaginatedItemsRequest(BaseModel):
    page: int = 1
    page_size: int = 50
    path: str = ""


@router.get("/workspaces/{workspace_id}/connectors/{connector_id}/items-paginated")
def list_connector_items_paginated(
    workspace_id: str,
    connector_id: str,
    page: int = 1,
    page_size: int = 50,
    path: str = "",
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_READ)),
) -> dict[str, Any]:
    """List items from a connector with pagination (v1.31)."""
    from decision_system.connectors.import_jobs import run_list_items_paginated

    result = run_list_items_paginated(
        connector_id=connector_id,
        path=path,
        page=page,
        page_size=page_size,
        workspace_id=workspace_id,
    )

    record_connector_items_listed(
        connector_id=connector_id,
        item_count=len(result.items),
        workspace_id=workspace_id,
    )

    return {
        "items": [to_jsonable(i) for i in result.items],
        "page": result.page,
        "page_size": result.page_size,
        "total_count": result.total_count,
        "has_more": result.has_more,
        "next_cursor": result.next_cursor,
    }


class CancelJobResponse(BaseModel):
    success: bool
    message: str


class JobActionResponse(BaseModel):
    success: bool
    message: str
    job_id: str | None = None
    status: str | None = None


@router.post("/workspaces/{workspace_id}/connector-jobs/{job_id}/cancel")
def cancel_connector_job(
    workspace_id: str,
    job_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_IMPORT)),
) -> dict[str, Any]:
    """Request cancellation of a running connector import job (v1.31)."""
    from decision_system.connectors.import_jobs import request_cancel_job

    result = request_cancel_job(job_id)
    return result


@router.post("/workspaces/{workspace_id}/connector-jobs/{job_id}/resume")
def resume_connector_job(
    workspace_id: str,
    job_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_IMPORT)),
) -> dict[str, Any]:
    """Resume a failed or paused connector import job (v1.31)."""
    from decision_system.connectors.import_jobs import resume_job

    result = resume_job(job_id)
    return result


@router.post("/workspaces/{workspace_id}/connector-jobs/{job_id}/pause")
def pause_connector_job(
    workspace_id: str,
    job_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_IMPORT)),
) -> dict[str, Any]:
    """Pause a running connector import job (v1.31)."""
    from decision_system.connectors.import_jobs import pause_job

    result = pause_job(job_id)
    return result


@router.post("/workspaces/{workspace_id}/connectors/{connector_id}/import-v3")
def import_connector_items_v3(
    workspace_id: str,
    connector_id: str,
    request: ImportRequest = ImportRequest(),
    batch_size: int = 50,
    _user: LocalUser = Depends(require_workspace_permission(Permission.CONNECTOR_IMPORT)),
) -> dict[str, Any]:
    """Enhanced import with batch processing, retry, dedup, and provenance (v1.31)."""
    from decision_system.connectors.import_jobs import run_import_v3

    result = run_import_v3(
        connector_id=connector_id,
        workspace_id=workspace_id,
        item_ids=request.item_ids,
        batch_size=batch_size,
    )
    return {"result": inspect_import_job(result.job)}
