"""FastAPI router for workflow management and execution."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from decision_system.identity.models import LocalUser, Permission, UserRole
from decision_system.identity.permissions import (
    get_current_user,
    require_permission,
    role_is_at_least,
    user_has_permission,
)
from decision_system.identity.settings import load_settings
from decision_system.security.audit import log_audit_event
from decision_system.workflow_engine.engine.dag import DAGValidator
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.models import (
    Connection,
    ExecutionState,
    NodeConfig,
    WorkflowDefinition,
)
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.providers.store import ProviderStore
from decision_system.workflow_engine.scheduler import (
    ScheduleDefinition,
    SchedulerService,
    ScheduleStore,
    TriggerType,
)
from decision_system.workflow_engine.stores.claim_store import JSONClaimStore
from decision_system.workflow_engine.stores.json_store import (
    JSONExecutionStore,
    JSONWorkflowStore,
)
from decision_system.workflow_engine.stores.version_store import JSONVersionStore
from decision_system.workflow_engine.stream import emit_event

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Persistent data directory — replaces tempfile.mkdtemp()
# ---------------------------------------------------------------------------


def _get_data_dir() -> Path:
    """Return the configured data directory for workflow engine state.

    Uses the ``DECISION_SYSTEM_DATA_DIR`` environment variable when set,
    otherwise falls back to ``.decision_system/`` in the current working
    directory.
    """
    raw = os.environ.get("DECISION_SYSTEM_DATA_DIR", "")
    if raw:
        d = Path(raw).expanduser().resolve()
    else:
        d = Path.cwd() / ".decision_system"
    d.mkdir(parents=True, exist_ok=True)
    return d


_data_dir = _get_data_dir()
_api_store_dir = _data_dir / "workflow_engine"
_api_store_dir.mkdir(parents=True, exist_ok=True)

_registry = create_default_registry()
_workflow_store = JSONWorkflowStore(_api_store_dir)
_execution_store = JSONExecutionStore(_api_store_dir)
_version_store = JSONVersionStore(_api_store_dir)
_claim_store = JSONClaimStore(_data_dir)
_provider_store = ProviderStore()
_engine = DAGEngine(
    registry=_registry,
    workflow_store=_workflow_store,
    execution_store=_execution_store,
    provider_store=_provider_store,
)
_engine.on_event(emit_event)

# Schedule store and background scheduler (started via app lifespan)
_schedule_store = ScheduleStore(_api_store_dir / "schedules")
_scheduler = SchedulerService(
    schedule_store=_schedule_store,
    dag_engine=_engine,
    poll_interval=30.0,
)

router = APIRouter(tags=["workflows"])


# --- Request/Response models ---


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    workspace_id: str | None = None
    nodes: list[dict[str, Any]] = []
    connections: list[dict[str, str]] = []


class CreateClaimRequest(BaseModel):
    """Validated request model for creating a claim."""

    claim_text: str
    source_agent: str = "api"
    claim_type: str = "assumption"
    status: str | None = None
    confidence: str | None = None
    workspace_id: str | None = None
    execution_id: str | None = None
    workflow_id: str | None = None
    node_id: str | None = None
    run_id: str | None = None
    evidence_ids: list[str] | None = None
    source_ids: list[str] | None = None
    chunk_ids: list[str] | None = None
    evidence_snippets: list[str] | None = None
    contradicting_evidence_ids: list[str] | None = None
    review_required: bool | None = None
    review_status: str | None = None
    metadata: dict[str, str] | None = None


class NodeTypesResponse(BaseModel):
    node_types: list[dict[str, Any]]


class CreateScheduleRequest(BaseModel):
    workflow_id: str
    workspace_id: str | None = None
    trigger_type: str = "cron"
    trigger_config: dict[str, Any] = {}
    enabled: bool = True


class UpdateScheduleRequest(BaseModel):
    workflow_id: str | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    enabled: bool | None = None


class ResolveReviewRequest(BaseModel):
    """Request body for resolving a review."""

    action: str
    notes: str = ""
    modified_data: dict[str, Any] | None = None
    reviewed_by: str | None = None


# --- Route helpers ---

_TRIGGER_TYPE_MAP: dict[str, TriggerType] = {
    "decision_system.trigger_cron": TriggerType.CRON,
    "decision_system.trigger_webhook": TriggerType.WEBHOOK,
    "decision_system.trigger_file_watch": TriggerType.FILE_WATCH,
}


def _compute_content_hash(wf: WorkflowDefinition) -> str:
    """Compute a content hash for change detection."""
    content = wf.model_dump_json(
        exclude={"id", "version", "created_at", "updated_at"}, sort_keys=True
    )
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def _enrich_execution(state: ExecutionState) -> dict[str, Any]:
    """Compute derived fields on an execution state before returning."""
    data = state.model_dump(mode="json")
    data["node_count"] = len(state.node_states)
    data["completed_node_count"] = sum(
        1 for ns in state.node_states.values() if ns.status == "completed"
    )
    data["failed_node_count"] = sum(1 for ns in state.node_states.values() if ns.status == "failed")
    # Compute duration
    if state.started_at:
        end = state.completed_at or datetime.now(timezone.utc)
        data["duration_ms"] = (end - state.started_at).total_seconds() * 1000
    else:
        data["duration_ms"] = None
    return data


def _node_to_trigger_config(node: NodeConfig) -> dict[str, Any] | None:
    """Extract trigger config from a trigger node, or None if not a trigger type."""
    trigger_type = _TRIGGER_TYPE_MAP.get(node.type)
    if trigger_type is None:
        return None

    cfg: dict[str, Any] = {"_node_id": node.id}
    if trigger_type == TriggerType.CRON:
        cfg["expression"] = node.config.get("expression", "")
    elif trigger_type == TriggerType.WEBHOOK:
        cfg["webhook_path"] = node.config.get("webhook_path", "")
    elif trigger_type == TriggerType.FILE_WATCH:
        cfg["directory"] = node.config.get("directory", "")
        cfg["pattern"] = node.config.get("pattern", "*")
    return cfg


def _sync_workflow_schedules(workflow_id: str, nodes: list[NodeConfig]) -> None:
    """Auto-create/update/delete schedules to match trigger nodes in a workflow."""
    existing = _schedule_store.list(workflow_id=workflow_id)
    existing_by_node: dict[str, ScheduleDefinition] = {}
    for s in existing:
        node_id = s.trigger_config.get("_node_id", "")
        if node_id:
            existing_by_node[node_id] = s

    seen_node_ids: set[str] = set()
    for node in nodes:
        trigger_config = _node_to_trigger_config(node)
        if trigger_config is None:
            continue

        seen_node_ids.add(node.id)
        trigger_type = _TRIGGER_TYPE_MAP[node.type]

        if node.id in existing_by_node:
            s = existing_by_node[node.id]
            s.trigger_config = trigger_config
            s.trigger_type = trigger_type
            _schedule_store.save(s)
        else:
            schedule = ScheduleDefinition(
                workflow_id=workflow_id,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
            )
            _schedule_store.save(schedule)

    for node_id, s in existing_by_node.items():
        if node_id not in seen_node_ids:
            _schedule_store.delete(s.id)


# --- Workflow CRUD Routes ---


@router.get("/workflows/nodes")
def list_node_types() -> NodeTypesResponse:
    """List all available node types with their schemas."""
    types = _registry.list_types()
    return NodeTypesResponse(
        node_types=[t.model_dump() for t in types],
    )


@router.post("/workflows")
def create_workflow(
    req: CreateWorkflowRequest,
    user: LocalUser = Depends(require_permission(Permission.WORKFLOW_CREATE)),
) -> dict[str, Any]:
    """Create a new workflow definition and snapshot version 1."""
    nodes = [NodeConfig(**n) for n in req.nodes]
    connections = [Connection(**c) for c in req.connections]
    wf = WorkflowDefinition(
        name=req.name,
        description=req.description,
        workspace_id=req.workspace_id,
        nodes=nodes,
        connections=connections,
    )
    _workflow_store.save(wf)

    # Create version 1
    _version_store.create_version(
        workflow_id=wf.id,
        definition=wf.model_dump(mode="json"),
        change_summary="Initial creation",
    )

    _sync_workflow_schedules(wf.id, nodes)

    # Audit event for workflow creation
    try:
        from decision_system.security.audit import log_audit_event

        log_audit_event(
            {
                "event_type": "workflow_created",
                "workflow_id": wf.id,
                "workflow_name": wf.name,
            }
        )
    except Exception:
        pass

    result = wf.model_dump()
    result["version_count"] = 1
    return result


@router.get("/workflows")
def list_workflows() -> dict[str, list[dict[str, Any]]]:
    """List all saved workflow definitions."""
    workflows = _workflow_store.list()
    return {"workflows": [w.model_dump() for w in workflows]}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict[str, Any]:
    """Get a workflow definition by ID."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return wf.model_dump()


@router.put("/workflows/{workflow_id}")
def update_workflow(
    workflow_id: str,
    req: CreateWorkflowRequest,
    user: LocalUser = Depends(require_permission(Permission.WORKFLOW_UPDATE)),
) -> dict[str, Any]:
    """Update an existing workflow definition and create a new version."""
    existing = _workflow_store.load(workflow_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    nodes = [NodeConfig(**n) for n in req.nodes]
    connections = [Connection(**c) for c in req.connections]
    wf = WorkflowDefinition(
        id=workflow_id,
        name=req.name,
        description=req.description,
        workspace_id=req.workspace_id if req.workspace_id is not None else existing.workspace_id,
        nodes=nodes,
        connections=connections,
        version=existing.version + 1,
    )
    _workflow_store.save(wf)

    # Create a new version snapshot
    _version_store.create_version(
        workflow_id=workflow_id,
        definition=wf.model_dump(mode="json"),
        change_summary="Updated via API",
    )

    _sync_workflow_schedules(workflow_id, nodes)
    result = wf.model_dump()
    return result


@router.delete("/workflows/{workflow_id}")
def delete_workflow(
    workflow_id: str,
    user: LocalUser = Depends(require_permission(Permission.WORKFLOW_UPDATE)),
) -> dict[str, Any]:
    """Delete a workflow definition."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    _workflow_store.delete(workflow_id)

    # Audit event for workflow deletion
    try:
        from decision_system.security.audit import log_audit_event

        log_audit_event(
            {
                "event_type": "workflow_deleted",
                "workflow_id": workflow_id,
            }
        )
    except Exception:
        pass

    return {"status": "deleted", "id": workflow_id}


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    user: LocalUser = Depends(require_permission(Permission.WORKFLOW_EXECUTE)),
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a workflow definition."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    errors = DAGValidator.validate(wf)
    if errors:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Workflow validation failed",
                "errors": [str(e) for e in errors],
            },
        )

    # Determine the latest version ID for this execution
    latest_version = _version_store.get_latest_version_number(workflow_id)
    version_id = None
    if latest_version > 0:
        v = _version_store.load_version(workflow_id, latest_version)
        if v is not None:
            version_id = v.version_id

    inputs = (body or {}).get("inputs", {})

    # Determine workspace_id: request body > workflow definition > None
    workspace_id = (body or {}).get("workspace_id") or wf.workspace_id
    state = await _engine.execute(wf, global_inputs=inputs, workspace_id=workspace_id)

    # Link workflow version to execution
    if version_id:
        state.workflow_version_id = version_id
        _execution_store.save(state)

    # Basic audit event
    try:
        from decision_system.security.audit import log_audit_event

        log_audit_event(
            {
                "event_type": "workflow_executed",
                "workflow_id": workflow_id,
                "execution_id": state.execution_id,
                "status": state.status,
                "version_id": version_id,
            }
        )
    except Exception:
        pass

    return {
        "execution_id": state.execution_id,
        "status": state.status,
        "workflow_id": state.workflow_id,
        "workflow_version_id": version_id,
        "error": state.error,
        "review_id": state.review_id,
    }


# --- Workflow Version Routes ---


@router.get("/workflows/{workflow_id}/versions")
def list_workflow_versions(workflow_id: str) -> dict[str, list[dict[str, Any]]]:
    """List all versions of a workflow definition."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    versions = _version_store.list_versions(workflow_id)
    return {"versions": [v.model_dump(mode="json", exclude_none=True) for v in versions]}


@router.get("/workflows/{workflow_id}/versions/{version_id}")
def get_workflow_version(workflow_id: str, version_id: str) -> dict[str, Any]:
    """Get a specific workflow version by its version ID."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    # version_id could be a version UUID or a version number string
    versions = _version_store.list_versions(workflow_id)
    for v in versions:
        if v.version_id == version_id:
            return v.model_dump(mode="json", exclude_none=True)

    # Try as numeric version number
    try:
        num = int(version_id)
        v = _version_store.load_version(workflow_id, num)
        if v is not None:
            return v.model_dump(mode="json", exclude_none=True)
    except ValueError:
        pass

    raise HTTPException(
        status_code=404,
        detail=f"Version '{version_id}' not found for workflow '{workflow_id}'",
    )


# --- Execution Routes ---


@router.get("/executions/history")
def list_execution_history(
    workflow_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """List execution history with summary info.

    Query params:
        workflow_id (str, optional): Filter by workflow.
        limit (int): Max results (default 50).
        offset (int): Pagination offset (default 0).
    """
    all_states = _execution_store.list(workflow_id=workflow_id)
    # Sort by started_at descending, newest first
    all_states.sort(
        key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    # Paginate
    paged = all_states[offset : offset + limit]

    history = []
    for state in paged:
        entry = _enrich_execution(state)
        # Add workflow name if available
        wf = _workflow_store.load(state.workflow_id)
        entry["workflow_name"] = wf.name if wf else None
        entry["workflow_version_id"] = state.workflow_version_id
        # Claim count placeholder
        entry["claim_count"] = state.claim_count
        history.append(entry)

    return {"executions": history}


@router.delete("/executions/history/{execution_id}")
def delete_execution_history(execution_id: str) -> dict[str, str]:
    """Delete an execution history entry."""
    state = _execution_store.load(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

    # Delete execution events file if exists
    events_path = _api_store_dir / "events" / f"{execution_id}.json"
    if events_path.exists():
        events_path.unlink()

    _execution_store.delete(execution_id)
    return {"status": "deleted", "id": execution_id}


@router.get("/executions/{execution_id}")
def get_execution_state(execution_id: str) -> dict[str, Any]:
    """Get the state of a workflow execution."""
    state = _execution_store.load(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    return _enrich_execution(state)


@router.get("/executions/{execution_id}/detail")
def get_execution_detail(execution_id: str) -> dict[str, Any]:
    """Get detailed information about a workflow execution.

    Includes execution state, node states, event timeline, review requests,
    metrics summary, and linked workflow definition.
    """
    state = _execution_store.load(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

    # Build detail response
    enriched = _enrich_execution(state)
    enriched["execution_state"] = enriched.copy()

    # Include workflow definition snapshot
    wf = _workflow_store.load(state.workflow_id)
    enriched["workflow_definition"] = wf.model_dump(mode="json") if wf else None

    # Include workflow version if linked
    if state.workflow_version_id:
        enriched["workflow_version"] = _version_store.load_version_by_id(state.workflow_version_id)
        if enriched["workflow_version"] is not None:
            enriched["workflow_version"] = enriched["workflow_version"].model_dump(
                mode="json", exclude_none=True
            )

    # Node states detail
    enriched["node_states"] = {
        nid: ns.model_dump(mode="json") for nid, ns in state.node_states.items()
    }

    # Event timeline (from execution events store if available)
    enriched["event_timeline"] = _load_execution_events(execution_id)

    # Review requests for this execution
    enriched["review_requests"] = _load_execution_reviews(execution_id)

    # Metrics summary
    enriched["metrics_summary"] = state.metrics_summary

    # Real claim refs from claim store
    claims = _claim_store.list(execution_id=execution_id)
    enriched["claim_refs"] = [c.model_dump(mode="json") for c in claims]
    enriched["claim_summary"] = _claim_store.summary(execution_id=execution_id)

    # Audit refs (placeholder for Phase 6)
    enriched["audit_refs"] = []

    return enriched


@router.websocket("/executions/{execution_id}/stream")
async def execution_event_stream(websocket: WebSocket, execution_id: str) -> None:
    """WebSocket endpoint streaming execution events in real-time."""
    from decision_system.workflow_engine.stream import ExecutionEventStream

    await websocket.accept()
    try:
        stream = ExecutionEventStream(execution_id)
        async for event in stream:
            try:
                await websocket.send_json(event)
            except WebSocketDisconnect:
                break
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# --- Helper functions for execution detail ---


def _load_execution_events(execution_id: str) -> list[dict[str, Any]]:
    """Load persisted execution events for a given execution."""
    events_path = _api_store_dir / "events" / f"{execution_id}.json"
    if not events_path.exists():
        return []
    try:
        import json

        data = json.loads(events_path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_execution_event(execution_id: str, event: dict[str, Any]) -> None:
    """Persist a single execution event to the events store."""
    events_path = _api_store_dir / "events"
    events_path.mkdir(parents=True, exist_ok=True)
    filepath = events_path / f"{execution_id}.json"

    import json

    try:
        if filepath.exists():
            events = json.loads(filepath.read_text())
        else:
            events = []
        events.append(event)
        filepath.write_text(json.dumps(events, indent=2, default=str))
    except (json.JSONDecodeError, OSError):
        filepath.write_text(json.dumps([event], indent=2, default=str))


def _persist_execution_event(event: ExecutionEvent) -> None:
    """Handler that persists execution events to the event store."""
    _save_execution_event(event.execution_id, event.model_dump(mode="json"))


# Register the event persistence handler (must be after _save_execution_event definition)
_engine.on_event(_persist_execution_event)


def _load_execution_reviews(execution_id: str) -> list[dict[str, Any]]:
    """Load reviews associated with an execution."""
    from decision_system.workflow_engine.nodes.specialist.review_gate import (
        list_all_reviews,
    )

    all_reviews = list_all_reviews()
    return [r for r in all_reviews if r.get("execution_id") == execution_id]


# --- Schedule CRUD Routes ---


@router.post("/schedules")
def create_schedule(req: CreateScheduleRequest) -> dict[str, Any]:
    """Create a new schedule definition."""
    try:
        trigger_type = TriggerType(req.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger_type '{req.trigger_type}'. Must be one of: {[t.value for t in TriggerType]}",
        )

    wf = _workflow_store.load(req.workflow_id)
    if wf is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{req.workflow_id}' not found",
        )

    schedule = ScheduleDefinition(
        id=f"sch-{uuid4().hex[:12]}",
        workflow_id=req.workflow_id,
        trigger_type=trigger_type,
        trigger_config=req.trigger_config,
        enabled=req.enabled,
    )
    _schedule_store.save(schedule)
    return schedule.model_dump(mode="json", exclude_none=True)


@router.get("/schedules")
def list_schedules(workflow_id: str | None = None) -> dict[str, list[dict[str, Any]]]:
    """List all schedules, optionally filtered by workflow_id."""
    schedules = _schedule_store.list(workflow_id=workflow_id)
    return {"schedules": [s.model_dump(mode="json", exclude_none=True) for s in schedules]}


@router.get("/schedules/{schedule_id}")
def get_schedule(schedule_id: str) -> dict[str, Any]:
    """Get a schedule definition by ID."""
    schedule = _schedule_store.load(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    return schedule.model_dump(mode="json", exclude_none=True)


@router.put("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, req: UpdateScheduleRequest) -> dict[str, Any]:
    """Update an existing schedule definition."""
    schedule = _schedule_store.load(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")

    if req.workflow_id is not None:
        wf = _workflow_store.load(req.workflow_id)
        if wf is None:
            raise HTTPException(status_code=404, detail=f"Workflow '{req.workflow_id}' not found")
        schedule.workflow_id = req.workflow_id

    if req.trigger_type is not None:
        try:
            schedule.trigger_type = TriggerType(req.trigger_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger_type '{req.trigger_type}'",
            )

    if req.trigger_config is not None:
        schedule.trigger_config = req.trigger_config

    if req.enabled is not None:
        schedule.enabled = req.enabled

    _schedule_store.save(schedule)
    return schedule.model_dump(mode="json", exclude_none=True)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str) -> dict[str, str]:
    """Delete a schedule definition."""
    schedule = _schedule_store.load(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    _schedule_store.delete(schedule_id)
    return {"status": "deleted", "id": schedule_id}


@router.post("/schedules/{schedule_id}/toggle")
def toggle_schedule(schedule_id: str) -> dict[str, Any]:
    """Toggle a schedule's enabled/disabled state."""
    schedule = _schedule_store.load(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail=f"Schedule '{schedule_id}' not found")
    schedule.enabled = not schedule.enabled
    _schedule_store.save(schedule)
    return schedule.model_dump(mode="json", exclude_none=True)


# --- Webhook Receiver ---


@router.post("/webhook/{webhook_path:path}")
async def receive_webhook(
    webhook_path: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Receive a webhook trigger and execute the matching schedule's workflow."""
    from decision_system.workflow_engine.scheduler.triggers import validate_webhook_path

    schedules = _schedule_store.list(trigger_type=TriggerType.WEBHOOK)
    matched: list[ScheduleDefinition] = []
    for s in schedules:
        stored_path = s.trigger_config.get("webhook_path", "")
        if validate_webhook_path(webhook_path, stored_path):
            matched.append(s)

    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"No webhook schedule found for path '/{webhook_path}'",
        )

    results: list[dict[str, Any]] = []
    for schedule in matched:
        wf = _workflow_store.load(schedule.workflow_id)
        if wf is None:
            continue

        inputs = body or {}
        state = await _engine.execute(wf, global_inputs=inputs, schedule_id=schedule.id)
        _schedule_store.update_last_fired(schedule.id)

        results.append(
            {
                "schedule_id": schedule.id,
                "workflow_id": schedule.workflow_id,
                "execution_id": state.execution_id,
                "status": state.status,
            }
        )

    return {"triggered": len(results), "executions": results}


# --- Review Gate Routes ---


@router.get("/reviews")
def list_reviews(
    status: str | None = None,
    _user: LocalUser = Depends(require_permission(Permission.AUDIT_READ)),
) -> dict[str, list[dict[str, Any]]]:
    """List review records, optionally filtered by status.

    Query params:
        status (str, optional): Filter by status (e.g. ``pending_review``).
    """
    from decision_system.workflow_engine.nodes.specialist.review_gate import (
        list_all_reviews,
        list_pending_reviews,
    )

    if status == "pending_review":
        reviews = list_pending_reviews()
    else:
        reviews = list_all_reviews()

    return {"reviews": reviews}


@router.post("/reviews/{review_id}/resolve")
def resolve_review_endpoint(review_id: str, req: ResolveReviewRequest) -> dict[str, Any]:
    """Approve, reject, or request changes on a pending review.

    Requires review.resolve permission. Only users with reviewer or higher role
    can resolve reviews when review_requires_reviewer_role is enabled (default).

    Body:
        action: "approve" | "reject" | "request_changes"
        notes: str
        modified_data: dict (optional)
        reviewed_by: str (optional)
    """
    from decision_system.workflow_engine.nodes.specialist.review_gate import (
        resolve_review,
    )

    # Check permission
    current_user = get_current_user()
    if not user_has_permission(current_user, Permission.REVIEW_RESOLVE):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "permission_denied",
                "message": f"User '{current_user.user_id}' lacks review.resolve permission.",
            },
        )

    # Check role requirement if enabled
    if load_settings().review_requires_reviewer_role:
        if not role_is_at_least(current_user.role, UserRole.REVIEWER):
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "permission_denied",
                    "message": f"Role '{current_user.role.value}' cannot resolve reviews. Reviewer or higher required.",
                },
            )

    valid_actions = {"approve", "reject", "request_changes"}
    if req.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{req.action}'. Must be one of: {', '.join(sorted(valid_actions))}",
        )

    # Record the actor in the review resolution
    reviewer = req.reviewed_by or current_user.user_id

    try:
        result = resolve_review(
            review_id=review_id,
            action=req.action,
            notes=req.notes,
            modified_data=req.modified_data,
            reviewed_by=reviewer,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    if result is None:
        raise HTTPException(status_code=404, detail=f"Review '{review_id}' not found")

    # Audit event for review resolution with actor
    try:
        log_audit_event(
            {
                "event_type": "review_resolved",
                "review_id": review_id,
                "action": req.action,
                "reviewed_by": reviewer,
                "notes": req.notes or "",
            }
        )
    except Exception:
        pass

    return result


# --- Execution Resume Route ---


class ResumeExecutionRequest(BaseModel):
    action: str = "resume"
    modified_data: dict[str, Any] | None = None


@router.post("/executions/{execution_id}/resume")
async def resume_execution_endpoint(
    execution_id: str,
    req: ResumeExecutionRequest,
    user: LocalUser = Depends(require_permission(Permission.WORKFLOW_EXECUTE)),
) -> dict[str, Any]:
    """Resume a paused execution after a review gate.

    When a workflow is paused at a ReviewGateNode, this endpoint
    allows it to continue. Supports:
    - ``resume``: Continue execution; optional ``modified_data`` is passed downstream.
    - ``reject``: End the execution without running downstream nodes.

    Requires the execution to be in ``awaiting_review`` status.
    """
    state = _execution_store.load(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")

    if state.status != "awaiting_review":
        raise HTTPException(
            status_code=409,
            detail=f"Execution '{execution_id}' is not paused for review (status={state.status})",
        )

    action = req.action
    if action not in ("resume", "reject"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{action}'. Must be 'resume' or 'reject'.",
        )

    try:
        result = await _engine.resume(
            execution_id=execution_id,
            action="reject" if action == "reject" else "resume",
            modified_data=req.modified_data,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resume execution: {type(exc).__name__}: {exc}",
        )

    if result is None:
        raise HTTPException(
            status_code=409,
            detail=f"Execution '{execution_id}' could not be resumed",
        )

    return _enrich_execution(result)


@router.get("/workspaces/{workspace_id}/workflows")
def list_workspace_workflows(workspace_id: str) -> dict[str, list[dict[str, Any]]]:
    """List all workflows belonging to a workspace."""
    all_workflows = _workflow_store.list()
    filtered = [
        w.model_dump()
        for w in all_workflows
        if (w.model_dump().get("workspace_id") or None) == workspace_id or workspace_id == "_all_"
    ]
    return {"workflows": filtered}


@router.get("/workspaces/{workspace_id}/executions")
def list_workspace_executions(
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    """List executions belonging to a workspace."""
    all_states = _execution_store.list()
    filtered = [
        s for s in all_states if (s.workspace_id or None) == workspace_id or workspace_id == "_all_"
    ]
    filtered.sort(
        key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    paged = filtered[offset : offset + limit]
    return {"executions": [_enrich_execution(s) for s in paged]}


@router.get("/workspaces/{workspace_id}/reviews")
def list_workspace_reviews(
    workspace_id: str,
    status: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """List review records for a workspace.

    Query params:
        status (str, optional): Filter by review status.
    """
    from decision_system.workflow_engine.nodes.specialist.review_gate import (
        list_all_reviews,
        list_pending_reviews,
    )

    if status == "pending_review":
        reviews = list_pending_reviews()
    else:
        reviews = list_all_reviews()

    # Filter by workspace
    if workspace_id != "_all_":
        reviews = [r for r in reviews if r.get("workspace_id") == workspace_id]

    return {"reviews": reviews}


@router.get("/workspaces/{workspace_id}/overview")
def workspace_overview(workspace_id: str) -> dict[str, Any]:
    """Get a summary overview of a workspace."""
    # Workflow count
    all_wf = _workflow_store.list()
    wf_count = sum(
        1
        for w in all_wf
        if (w.model_dump().get("workspace_id") or None) == workspace_id or workspace_id == "_all_"
    )

    # Execution count
    all_execs = _execution_store.list()
    ws_execs = [
        s for s in all_execs if (s.workspace_id or None) == workspace_id or workspace_id == "_all_"
    ]
    exec_count = len(ws_execs)
    completed_count = sum(1 for s in ws_execs if s.status == "completed")
    failed_count = sum(1 for s in ws_execs if s.status == "failed")
    paused_count = sum(1 for s in ws_execs if s.status == "awaiting_review")

    # Review count
    from decision_system.workflow_engine.nodes.specialist.review_gate import (
        list_all_reviews,
    )

    all_reviews = list_all_reviews()
    if workspace_id != "_all_":
        all_reviews = [r for r in all_reviews if r.get("workspace_id") == workspace_id]
    pending_reviews = sum(1 for r in all_reviews if r.get("status") == "pending_review")

    # Schedule count
    schedules = _schedule_store.list()
    sched_count = len(schedules)

    # Claim summary
    claim_summary = _claim_store.summary(
        workspace_id=workspace_id if workspace_id != "_all_" else None
    )

    return {
        "workspace_id": workspace_id,
        "workflow_count": wf_count,
        "execution_count": exec_count,
        "completed_executions": completed_count,
        "failed_executions": failed_count,
        "paused_executions": paused_count,
        "pending_reviews": pending_reviews,
        "schedule_count": sched_count,
        "review_count": len(all_reviews),
        "claim_count": claim_summary["total"],
        "supported_claim_count": claim_summary["supported"],
        "contradicted_claim_count": claim_summary["contradicted"],
        "unsupported_claim_count": claim_summary["unsupported"],
        "uncertain_claim_count": claim_summary["uncertain"],
        "pending_claim_count": claim_summary["pending"],
        "evidence_coverage_score": claim_summary["evidence_coverage_score"],
    }


# ============================================================================
# Claim API routes (Phase 7 — durable claim store)
# ============================================================================


@router.get("/workspaces/{workspace_id}/claims")
def list_workspace_claims(workspace_id: str) -> dict[str, list[dict[str, Any]]]:
    """List all claims belonging to a workspace."""
    if workspace_id == "_all_":
        claims = _claim_store.list()
    else:
        claims = _claim_store.list(workspace_id=workspace_id)
    return {"claims": [c.model_dump(mode="json", exclude_none=True) for c in claims]}


@router.get("/executions/{execution_id}/claims")
def list_execution_claims(execution_id: str) -> dict[str, list[dict[str, Any]]]:
    """List all claims for a specific execution."""
    claims = _claim_store.list(execution_id=execution_id)
    return {"claims": [c.model_dump(mode="json", exclude_none=True) for c in claims]}


@router.get("/claims/{claim_id}")
def get_claim(claim_id: str) -> dict[str, Any]:
    """Get a single claim by ID."""
    claim = _claim_store.load(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found")
    return claim.model_dump(mode="json", exclude_none=True)


VALID_CLAIM_TYPES = {"technical", "risk", "option", "recommendation", "assumption"}
VALID_CLAIM_STATUSES = {
    "pending",
    "verified",
    "unsupported",
    "contradicted",
    "uncertain",
}


@router.post("/claims")
def create_claim(
    req: CreateClaimRequest,
    user: LocalUser = Depends(require_permission(Permission.CLAIM_VERIFY)),
) -> dict[str, Any]:
    """Create a new claim with validated input."""
    if not req.claim_text or not req.claim_text.strip():
        raise HTTPException(status_code=422, detail="claim_text is required and cannot be empty")
    if req.claim_type not in VALID_CLAIM_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid claim_type '{req.claim_type}'. Must be one of: {', '.join(sorted(VALID_CLAIM_TYPES))}",
        )

    claim = _claim_store.add_claim(
        claim_text=req.claim_text,
        source_agent=req.source_agent,
        claim_type=req.claim_type,
        workspace_id=req.workspace_id,
        execution_id=req.execution_id,
        workflow_id=req.workflow_id,
        node_id=req.node_id,
        run_id=req.run_id,
        status=req.status,
        confidence=req.confidence,
        evidence_ids=req.evidence_ids,
        source_ids=req.source_ids,
        chunk_ids=req.chunk_ids,
        evidence_snippets=req.evidence_snippets,
        contradicting_evidence_ids=req.contradicting_evidence_ids,
        review_required=req.review_required,
        review_status=req.review_status,
        metadata=req.metadata,
    )
    return claim.model_dump(mode="json", exclude_none=True)


@router.delete("/claims/{claim_id}")
def delete_claim(claim_id: str) -> dict[str, str]:
    """Delete a claim by ID."""
    claim = _claim_store.load(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found")
    _claim_store.delete(claim_id)
    return {"status": "deleted", "id": claim_id}


@router.get("/executions/{execution_id}/claim-summary")
def execution_claim_summary(execution_id: str) -> dict[str, Any]:
    """Get a summary of claim statuses for an execution."""
    return _claim_store.summary(execution_id=execution_id)
