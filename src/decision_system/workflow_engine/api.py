"""FastAPI router for workflow management and execution."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.dag import DAGValidator
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)

# In-memory stores for API usage (persist for server lifetime)
_api_store_dir = Path(tempfile.mkdtemp())
_registry = create_default_registry()
_workflow_store = JSONWorkflowStore(_api_store_dir)
_execution_store = JSONExecutionStore(_api_store_dir)
_engine = DAGEngine(registry=_registry, workflow_store=_workflow_store, execution_store=_execution_store)

router = APIRouter(tags=["workflows"])


# --- Request/Response models ---

class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    nodes: list[dict[str, Any]] = []
    connections: list[dict[str, str]] = []


class NodeTypesResponse(BaseModel):
    node_types: list[dict[str, Any]]


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
