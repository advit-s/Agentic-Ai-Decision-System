"""FastAPI router for workflow management and execution."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.dag import DAGValidator
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.scheduler import (
    ScheduleDefinition,
    ScheduleStore,
    SchedulerService,
    TriggerType,
)
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)
from decision_system.workflow_engine.stream import emit_event

# In-memory stores for API usage (persist for server lifetime)
_api_store_dir = Path(tempfile.mkdtemp())
_registry = create_default_registry()
_workflow_store = JSONWorkflowStore(_api_store_dir)
_execution_store = JSONExecutionStore(_api_store_dir)
_engine = DAGEngine(registry=_registry, workflow_store=_workflow_store, execution_store=_execution_store)
_engine.on_event(emit_event)

# Schedule store and background scheduler (started via app lifespan)
_schedule_store = ScheduleStore(_api_store_dir)
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
    nodes: list[dict[str, Any]] = []
    connections: list[dict[str, str]] = []


class NodeTypesResponse(BaseModel):
    node_types: list[dict[str, Any]]


class CreateScheduleRequest(BaseModel):
    workflow_id: str
    trigger_type: str = "cron"
    trigger_config: dict[str, Any] = {}
    enabled: bool = True


class UpdateScheduleRequest(BaseModel):
    workflow_id: str | None = None
    trigger_type: str | None = None
    trigger_config: dict[str, Any] | None = None
    enabled: bool | None = None


# --- Route helpers ---

_TRIGGER_TYPE_MAP: dict[str, TriggerType] = {
    "decision_system.trigger_cron": TriggerType.CRON,
    "decision_system.trigger_webhook": TriggerType.WEBHOOK,
    "decision_system.trigger_file_watch": TriggerType.FILE_WATCH,
}


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
    """Auto-create/update/delete schedules to match trigger nodes in a workflow.

    Called after a workflow is saved or updated.
    """
    existing = _schedule_store.list(workflow_id=workflow_id)
    existing_by_node: dict[str, ScheduleDefinition] = {}
    for s in existing:
        node_id = s.trigger_config.get("_node_id", "")
        if node_id:
            existing_by_node[node_id] = s

    # Process each node
    seen_node_ids: set[str] = set()
    for node in nodes:
        trigger_config = _node_to_trigger_config(node)
        if trigger_config is None:
            continue

        seen_node_ids.add(node.id)
        trigger_type = _TRIGGER_TYPE_MAP[node.type]

        if node.id in existing_by_node:
            # Update existing schedule
            s = existing_by_node[node.id]
            s.trigger_config = trigger_config
            s.trigger_type = trigger_type
            _schedule_store.save(s)
        else:
            # Create new schedule
            schedule = ScheduleDefinition(
                workflow_id=workflow_id,
                trigger_type=trigger_type,
                trigger_config=trigger_config,
            )
            _schedule_store.save(schedule)

    # Delete orphaned schedules (node removed from workflow)
    for node_id, s in existing_by_node.items():
        if node_id not in seen_node_ids:
            _schedule_store.delete(s.id)


# --- Routes ---

@router.get("/workflows/nodes")
def list_node_types() -> NodeTypesResponse:
    """List all available node types with their schemas."""
    types = _registry.list_types()
    return NodeTypesResponse(
        node_types=[t.model_dump() for t in types],
    )


@router.post("/workflows")
def create_workflow(req: CreateWorkflowRequest) -> dict[str, Any]:
    """Create a new workflow definition."""
    nodes = [NodeConfig(**n) for n in req.nodes]
    connections = [Connection(**c) for c in req.connections]
    wf = WorkflowDefinition(
        name=req.name,
        description=req.description,
        nodes=nodes,
        connections=connections,
    )
    _workflow_store.save(wf)
    # Auto-create schedules for trigger nodes
    _sync_workflow_schedules(wf.id, nodes)
    return wf.model_dump()


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
def update_workflow(workflow_id: str, req: CreateWorkflowRequest) -> dict[str, Any]:
    """Update an existing workflow definition."""
    existing = _workflow_store.load(workflow_id)
    if existing is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    nodes = [NodeConfig(**n) for n in req.nodes]
    connections = [Connection(**c) for c in req.connections]
    wf = WorkflowDefinition(
        id=workflow_id,
        name=req.name,
        description=req.description,
        nodes=nodes,
        connections=connections,
        version=1,
    )
    _workflow_store.save(wf)
    # Sync schedules for trigger nodes (creates/updates/deletes as needed)
    _sync_workflow_schedules(workflow_id, nodes)
    return wf.model_dump()


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str) -> dict[str, str]:
    """Delete a workflow definition."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    _workflow_store.delete(workflow_id)
    return {"status": "deleted", "id": workflow_id}


@router.post("/workflows/{workflow_id}/execute")
def execute_workflow(
    workflow_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a workflow definition."""
    wf = _workflow_store.load(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

    errors = DAGValidator.validate(wf)
    if errors:
        raise HTTPException(status_code=400, detail={
            "error": "Workflow validation failed",
            "errors": [str(e) for e in errors],
        })

    inputs = (body or {}).get("inputs", {})
    state = asyncio.run(_engine.execute(wf, global_inputs=inputs))

    return {
        "execution_id": state.execution_id,
        "status": state.status,
        "workflow_id": state.workflow_id,
        "error": state.error,
    }


@router.get("/executions/{execution_id}")
def get_execution_state(execution_id: str) -> dict[str, Any]:
    """Get the state of a workflow execution."""
    state = _execution_store.load(execution_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Execution '{execution_id}' not found")
    return state.model_dump()


@router.websocket("/executions/{execution_id}/stream")
async def execution_event_stream(
    websocket: WebSocket, execution_id: str
) -> None:
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

    # Validate the referenced workflow exists
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
    """Receive a webhook trigger and execute the matching schedule's workflow.

    Looks up a schedule with ``trigger_type='webhook'`` whose
    ``trigger_config['webhook_path']`` matches the received path.
    """
    from decision_system.workflow_engine.scheduler.triggers import validate_webhook_path

    # Find matching webhook schedule
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

        results.append({
            "schedule_id": schedule.id,
            "workflow_id": schedule.workflow_id,
            "execution_id": state.execution_id,
            "status": state.status,
        })

    return {"triggered": len(results), "executions": results}
