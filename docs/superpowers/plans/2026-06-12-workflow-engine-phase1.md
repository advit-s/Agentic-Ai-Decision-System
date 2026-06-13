# Phase 1: Workflow Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core node abstraction, DAG execution engine, node registry, built-in node types (wrapping existing capabilities), JSON stores, CLI commands, and API routes for the n8n-level workflow platform.

**Architecture:** New `src/decision_system/workflow_engine/` package added alongside existing code. All existing CLI commands, LangGraph workflow, FastAPI routes, and 700+ tests remain untouched. The engine is a DAG-based async executor: nodes declare typed config/input/output schemas, are discovered via a registry, wired by named connections, topo-sorted into parallel layers, and executed via `asyncio.gather`. State is persisted as JSON files.

**Tech Stack:** Python 3.11+, Pydantic v2, asyncio, Typer, FastAPI, pytest

---

## File Structure

```
src/decision_system/workflow_engine/
    __init__.py                               # Package exports
    models.py                                 # WorkflowNode ABC + all Pydantic models
    nodes/
        __init__.py                           # Import all built-in nodes
        registry.py                           # NodeRegistry class
        builtin/
            __init__.py                       # Re-export all built-in nodes
            trigger_nodes.py                  # ManualTriggerNode, InputTextNode
            decision_nodes.py                 # RetrieveNode, TechAnalystNode, RiskAnalystNode,
                                              #   ExtractClaimsNode, VerifyClaimsNode, WriteReportNode
            data_nodes.py                     # ExtractGraphNode, ProfileDataNode, MapOntologyNode,
                                              #   DetectPatternsNode, WarRoomNode
            flow_nodes.py                     # FilterNode, MergeNode, CodeNode
    engine/
        __init__.py
        dag.py                                # DAGValidator, TopologicalSort
        executor.py                           # DAGEngine — main execution loop
        events.py                             # ExecutionEvent models
    stores/
        __init__.py
        base.py                               # WorkflowStore, ExecutionStore ABCs
        json_store.py                         # JSON file implementations
    cli.py                                    # workflow/execution Typer sub-app
    api.py                                    # FastAPI router
tests/
    test_workflow_engine/
        __init__.py
        test_models.py
        test_dag.py
        test_executor.py
        test_nodes.py
        test_stores.py
        test_cli.py
        test_api.py
```

## Task Dependency Graph

```
1 (scaffold)
  └─> 2 (models)
       ├─> 3 (events)
       ├─> 5 (stores)
       └─> 6 (node base + registry)
              ├─> 4 (dag engine)
              └─> 8-10 (builtin nodes)
                     ├─> 7 (executor)
                     ├─> 12 (CLI)
                     └─> 13 (API)
                            └─> 14 (integration test)
```

---

### Task 1: Package Scaffolding

**Files:**
- Create: `src/decision_system/workflow_engine/__init__.py`
- Create: `src/decision_system/workflow_engine/nodes/__init__.py`
- Create: `src/decision_system/workflow_engine/nodes/builtin/__init__.py`
- Create: `src/decision_system/workflow_engine/engine/__init__.py`
- Create: `src/decision_system/workflow_engine/stores/__init__.py`
- Create: `tests/test_workflow_engine/__init__.py`

- [ ] **Step 1: Create all __init__.py files**

Create the directory tree and all `__init__.py` files. Each `__init__.py` is minimal — just an empty file or a docstring. The main `__init__.py` will be populated in the final task.

```bash
mkdir -p src/decision_system/workflow_engine/nodes/builtin
mkdir -p src/decision_system/workflow_engine/engine
mkdir -p src/decision_system/workflow_engine/stores
mkdir -p tests/test_workflow_engine
```

Create `src/decision_system/workflow_engine/__init__.py`:
```python
"""Workflow engine — node SDK, DAG runtime, and execution engine."""
```

Create the other 5 `__init__.py` files as empty files or simple docstrings.

- [ ] **Step 2: Verify imports work**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -c "import decision_system.workflow_engine; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/decision_system/workflow_engine/ tests/test_workflow_engine/
git commit -m "feat(workflow): scaffold package directory tree"
```

---

### Task 2: Core Models

**Files:**
- Create: `src/decision_system/workflow_engine/models.py`
- Create: `tests/test_workflow_engine/test_models.py`

This file contains all Pydantic models for the workflow engine: `WorkflowNode` (ABC), `WorkflowDefinition`, `Connection`, `NodeConfig`, `ExecutionState`, `NodeExecutionState`, `ExecutionContext`, `ErrorPolicy`, `RetryConfig`, `NodeTypeInfo`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_models.py`:

```python
"""Tests for workflow engine core models."""

from datetime import datetime, timezone
from uuid import uuid4
import pytest
from pydantic import ValidationError

from decision_system.workflow_engine.models import (
    WorkflowNode,
    WorkflowDefinition,
    Connection,
    NodeConfig,
    ExecutionState,
    NodeExecutionState,
    ExecutionContext,
    ErrorPolicy,
    RetryConfig,
    NodeTypeInfo,
)


class TestConnection:
    def test_basic_connection(self):
        c = Connection(source_node="n1", target_node="n2")
        assert c.source_node == "n1"
        assert c.target_node == "n2"
        assert c.source_output == "default"
        assert c.target_input == "default"

    def test_named_ports(self):
        c = Connection(
            source_node="n1", source_output="verified",
            target_node="n2", target_input="claims",
        )
        assert c.source_output == "verified"
        assert c.target_input == "claims"


class TestNodeConfig:
    def test_minimal_config(self):
        nc = NodeConfig(id="n1", type="decision_system.retrieve")
        assert nc.id == "n1"
        assert nc.type == "decision_system.retrieve"
        assert nc.config == {}
        assert nc.label == ""

    def test_with_config(self):
        nc = NodeConfig(id="n1", type="decision_system.retrieve", config={"top_k": 5})
        assert nc.config == {"top_k": 5}


class TestWorkflowDefinition:
    def test_minimal_definition(self):
        wf = WorkflowDefinition(name="Test Workflow")
        assert wf.name == "Test Workflow"
        assert wf.version == 1
        assert wf.nodes == []
        assert wf.connections == []

    def test_with_nodes_and_connections(self):
        nodes = [
            NodeConfig(id="n1", type="decision_system.trigger_manual"),
            NodeConfig(id="n2", type="decision_system.retrieve"),
        ]
        conns = [Connection(source_node="n1", target_node="n2")]
        now = datetime.now(timezone.utc)
        wf = WorkflowDefinition(
            id=str(uuid4()),
            name="Test",
            nodes=nodes,
            connections=conns,
            created_at=now,
            updated_at=now,
        )
        assert len(wf.nodes) == 2
        assert len(wf.connections) == 1


class TestExecutionState:
    def test_default_status(self):
        state = ExecutionState(
            execution_id="e1", workflow_id="wf1",
        )
        assert state.status == "pending"

    def test_with_node_state(self):
        ns = NodeExecutionState(node_id="n1")
        assert ns.status == "pending"
        state = ExecutionState(
            execution_id="e1",
            workflow_id="wf1",
            node_states={"n1": ns},
        )
        assert state.node_states["n1"].status == "pending"

    def test_status_literals(self):
        with pytest.raises(ValidationError):
            ExecutionState(
                execution_id="e1", workflow_id="wf1",
                status="invalid_status",
            )


class TestExecutionContext:
    def test_basic_context(self):
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        assert ctx.workflow_id == "wf1"
        assert ctx.execution_id == "e1"
        assert ctx.provider == "fake"
        assert ctx.global_config == {}
        assert ctx.log == []


class TestErrorPolicy:
    def test_enum_values(self):
        assert ErrorPolicy.FAIL_WORKFLOW.value == "fail_workflow"
        assert ErrorPolicy.FAIL_NODE.value == "fail_node"
        assert ErrorPolicy.RETRY.value == "retry"
        assert ErrorPolicy.SKIP.value == "skip"


class TestRetryConfig:
    def test_defaults(self):
        rc = RetryConfig()
        assert rc.max_attempts == 3
        assert rc.base_delay == 1.0

    def test_custom(self):
        rc = RetryConfig(max_attempts=5, base_delay=2.0)
        assert rc.max_attempts == 5
        assert rc.base_delay == 2.0


class TestNodeTypeInfo:
    def test_basic_info(self):
        info = NodeTypeInfo(type="test.node", label="Test Node")
        assert info.type == "test.node"
        assert info.label == "Test Node"


class TestWorkflowNode:
    """Test that WorkflowNode ABC enforces the right contract."""

    def test_abstract_class_cannot_be_instantiated(self):
        with pytest.raises(TypeError):
            WorkflowNode(id="n1", type="test", label="Test")  # type: ignore

    def test_concrete_subclass_must_implement_abstract_methods(self):
        class IncompleteNode(WorkflowNode):
            pass

        with pytest.raises(TypeError):
            IncompleteNode(id="n1", type="test", label="Test")  # type: ignore
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_models.py -v 2>&1 | head -40
```

Expected: ImportError or ModuleNotFoundError for `models` module

- [ ] **Step 3: Write the models implementation**

Create `src/decision_system/workflow_engine/models.py`:

```python
"""Core models for the workflow engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class ErrorPolicy(str, Enum):
    """Error handling policy for node execution."""
    FAIL_WORKFLOW = "fail_workflow"
    FAIL_NODE = "fail_node"
    RETRY = "retry"
    SKIP = "skip"


class Connection(BaseModel):
    """A directed edge between two nodes in a workflow DAG."""
    source_node: str
    source_output: str = "default"
    target_node: str
    target_input: str = "default"


class NodeConfig(BaseModel):
    """Reference to a node instance within a workflow definition."""
    id: str
    type: str
    label: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    error_policy: ErrorPolicy = ErrorPolicy.FAIL_WORKFLOW
    retry_config: RetryConfig | None = None
    position_x: float = 0
    position_y: float = 0


class RetryConfig(BaseModel):
    """Retry configuration for node execution."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retryable_errors: list[str] = Field(default_factory=lambda: ["Timeout", "RateLimit"])


class WorkflowDefinition(BaseModel):
    """A complete workflow definition — the DAG blueprint."""
    version: int = 1
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    nodes: list[NodeConfig] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NodeExecutionState(BaseModel):
    """Execution state for a single node."""
    node_id: str
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "pending"
    inputs: dict[str, Any] | None = None
    outputs: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0


class ExecutionState(BaseModel):
    """Execution state for an entire workflow run."""
    execution_id: str
    workflow_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    node_states: dict[str, NodeExecutionState] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class ExecutionContext(BaseModel):
    """Shared context passed to every node during execution."""
    workflow_id: str
    execution_id: str
    provider: str = "fake"
    global_config: dict[str, Any] = Field(default_factory=dict)
    log: list[str] = Field(default_factory=list)


class NodeTypeInfo(BaseModel):
    """Metadata about a registered node type."""
    type: str
    label: str
    description: str = ""
    config_schema: dict[str, Any] = Field(default_factory=dict)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    categories: list[str] = Field(default_factory=list)


class WorkflowNode(ABC, BaseModel):
    """Abstract base class for all workflow node types.

    Subclasses must implement execute() and the three schema classmethods.
    """
    id: str
    type: str
    label: str = ""
    config: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def execute(self, inputs: dict[str, Any], ctx: ExecutionContext) -> dict[str, Any]:
        """Execute the node's logic. Returns output dict."""

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """JSON Schema for node configuration."""

    @classmethod
    @abstractmethod
    def get_input_schema(cls) -> dict[str, Any]:
        """JSON Schema for expected inputs (named ports)."""

    @classmethod
    @abstractmethod
    def get_output_schema(cls) -> dict[str, Any]:
        """JSON Schema for produced outputs (named ports)."""
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_models.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/models.py tests/test_workflow_engine/test_models.py
git commit -m "feat(workflow): add core Pydantic models"
```

---

### Task 3: Execution Events

**Files:**
- Create: `src/decision_system/workflow_engine/engine/events.py`
- Update: `tests/test_workflow_engine/test_models.py` (append event tests)

- [ ] **Step 1: Add event tests to test_models.py**

Append to `tests/test_workflow_engine/test_models.py`:

```python
class TestExecutionEvent:
    def test_node_started_event(self):
        event = ExecutionEvent(
            execution_id="e1",
            event_type="node_started",
            node_id="n1",
            data={"node_type": "test"},
        )
        assert event.execution_id == "e1"
        assert event.node_id == "n1"

    def test_event_type_literals(self):
        with pytest.raises(ValidationError):
            ExecutionEvent(
                execution_id="e1",
                event_type="invalid_event",
                data={},
            )

    def test_event_timestamp_auto(self):
        event = ExecutionEvent(
            execution_id="e1",
            event_type="workflow_completed",
            data={"status": "completed"},
        )
        assert event.timestamp is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_models.py::TestExecutionEvent -v
```

Expected: ImportError for `ExecutionEvent`

- [ ] **Step 3: Write the events module**

Create `src/decision_system/workflow_engine/engine/events.py`:

```python
"""Execution event models for streaming workflow progress."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    """A single event emitted during workflow execution."""
    execution_id: str
    event_type: Literal[
        "node_started", "node_completed", "node_failed",
        "workflow_completed", "workflow_failed", "log",
    ]
    node_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

Also add the import to `src/decision_system/workflow_engine/__init__.py`:

```python
"""Workflow engine — node SDK, DAG runtime, and execution engine."""

from decision_system.workflow_engine.engine.events import ExecutionEvent

__all__ = ["ExecutionEvent"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_models.py::TestExecutionEvent -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/engine/events.py
git commit -m "feat(workflow): add execution event models"
```

---

### Task 4: DAG Engine — Validator and Topological Sort

**Files:**
- Create: `src/decision_system/workflow_engine/engine/dag.py`
- Create: `tests/test_workflow_engine/test_dag.py`

This module provides `DAGValidator` (cycle detection, missing connection checks) and `TopologicalSort` (produce ordered execution layers for parallel dispatch).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_dag.py`:

```python
"""Tests for DAG validation and topological sort."""

import pytest
from uuid import UUID

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ErrorPolicy,
)
from decision_system.workflow_engine.engine.dag import (
    DAGValidator, TopologicalSort, DAGError,
    CyclicDAGError, MissingConnectionError,
)


def _make_wf(nodes: list[dict], connections: list[dict]) -> WorkflowDefinition:
    return WorkflowDefinition(
        id=str(UUID(int=0)),
        name="test",
        nodes=[NodeConfig(**n) for n in nodes],
        connections=[Connection(**c) for c in connections],
    )


class TestDAGError:
    def test_base_error(self):
        err = DAGError("something went wrong")
        assert str(err) == "something went wrong"
        assert isinstance(err, Exception)


class TestDAGValidator:
    def test_empty_workflow_valid(self):
        wf = _make_wf([], [])
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_single_node_valid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [],
        )
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_linear_chain_valid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [{"source_node": "n1", "target_node": "n2"}],
        )
        errors = DAGValidator.validate(wf)
        assert errors == []

    def test_self_loop_invalid(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n1", "target_node": "n1"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], CyclicDAGError)

    def test_cycle_invalid(self):
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
                {"source_node": "n3", "target_node": "n1"},
            ],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], CyclicDAGError)

    def test_missing_source_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n2", "target_node": "n1"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], MissingConnectionError)
        assert "n2" in str(errors[0])

    def test_missing_target_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [{"source_node": "n1", "target_node": "n3"}],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 1
        assert isinstance(errors[0], MissingConnectionError)
        assert "n3" in str(errors[0])

    def test_multiple_errors(self):
        """A cycle and a missing node should both be reported."""
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n1"},
                {"source_node": "missing", "target_node": "n1"},
            ],
        )
        errors = DAGValidator.validate(wf)
        assert len(errors) == 2


class TestTopologicalSort:
    def test_empty(self):
        layers = TopologicalSort.sort(WorkflowDefinition(name="test"))
        assert layers == []

    def test_single_node(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}],
            [],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"]]

    def test_linear_chain(self):
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [{"source_node": "n1", "target_node": "n2"}],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"], ["n2"]]

    def test_diamond_dag(self):
        """n1 feeds n2 and n3, both feed n4."""
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
                {"id": "n4", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n1", "target_node": "n3"},
                {"source_node": "n2", "target_node": "n4"},
                {"source_node": "n3", "target_node": "n4"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        # n1 must be first; n2 and n3 in same layer; n4 last
        assert layers[0] == ["n1"]
        assert set(layers[1]) == {"n2", "n3"}
        assert layers[2] == ["n4"]

    def test_independent_branches(self):
        """n1 -> n2 and n3 -> n4. n1/n3 are layer 0; n2/n4 layer 1."""
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
                {"id": "n4", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n3", "target_node": "n4"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        # Layer 0: {n1, n3} (no deps), Layer 1: {n2, n4}
        assert set(layers[0]) == {"n1", "n3"}
        assert set(layers[1]) == {"n2", "n4"}

    def test_disconnected_nodes(self):
        """Two nodes with no connection should both be in layer 0."""
        wf = _make_wf(
            [{"id": "n1", "type": "test"}, {"id": "n2", "type": "test"}],
            [],
        )
        layers = TopologicalSort.sort(wf)
        assert set(layers[0]) == {"n1", "n2"}

    def test_three_layer_dag(self):
        wf = _make_wf(
            [
                {"id": "n1", "type": "test"},
                {"id": "n2", "type": "test"},
                {"id": "n3", "type": "test"},
            ],
            [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        )
        layers = TopologicalSort.sort(wf)
        assert layers == [["n1"], ["n2"], ["n3"]]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_dag.py -v
```

Expected: ImportError for `dag` module

- [ ] **Step 3: Write the DAG module**

Create `src/decision_system/workflow_engine/engine/dag.py`:

```python
"""DAG validation and topological sort for workflow execution."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import list

from decision_system.workflow_engine.models import WorkflowDefinition


class DAGError(Exception):
    """Base error for DAG validation failures."""


class CyclicDAGError(DAGError):
    """Raised when the workflow graph contains a cycle."""


class MissingConnectionError(DAGError):
    """Raised when a connection references a non-existent node."""


class DAGValidator:
    """Validates a workflow DAG for structural correctness."""

    @staticmethod
    def validate(wf: WorkflowDefinition) -> list[DAGError]:
        """Validate the workflow DAG. Returns list of errors (empty = valid)."""
        errors: list[DAGError] = []
        node_ids = {n.id for n in wf.nodes}

        # Check for missing nodes in connections
        for conn in wf.connections:
            if conn.source_node not in node_ids:
                errors.append(MissingConnectionError(
                    f"Connection source node '{conn.source_node}' not found in workflow nodes"
                ))
            if conn.target_node not in node_ids:
                errors.append(MissingConnectionError(
                    f"Connection target node '{conn.target_node}' not found in workflow nodes"
                ))

        # Check for cycles (only if all nodes exist)
        if not errors:
            cycle = DAGValidator._find_cycle(wf)
            if cycle:
                errors.append(CyclicDAGError(
                    f"Workflow contains a cycle: {' -> '.join(cycle)}"
                ))

        return errors

    @staticmethod
    def _find_cycle(wf: WorkflowDefinition) -> list[str] | None:
        """Detect cycles using DFS. Returns the cycle path if found, else None."""
        graph: dict[str, list[str]] = defaultdict(list)
        for conn in wf.connections:
            graph[conn.source_node].append(conn.target_node)

        all_nodes = {n.id for n in wf.nodes}
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in all_nodes}
        parent: dict[str, str | None] = {n: None for n in all_nodes}

        def dfs(node: str) -> list[str] | None:
            color[node] = GRAY
            for neighbor in graph.get(node, []):
                if color.get(neighbor) == GRAY:
                    # Found a cycle — reconstruct it
                    path = [neighbor, node]
                    curr = node
                    while curr != neighbor and parent[curr] is not None:
                        curr = parent[curr]  # type: ignore[assignment]
                        if curr is not None:
                            path.append(curr)
                    path.reverse()
                    return path
                if color.get(neighbor) == WHITE:
                    parent[neighbor] = node
                    result = dfs(neighbor)
                    if result:
                        return result
            color[node] = BLACK
            return None

        for node in all_nodes:
            if color[node] == WHITE:
                result = dfs(node)
                if result:
                    return result
        return None


class TopologicalSort:
    """Produces ordered execution layers from a workflow DAG.

    Each layer is a set of independent nodes that can run in parallel.
    """

    @staticmethod
    def sort(wf: WorkflowDefinition) -> list[list[str]]:
        """Return layers of node IDs in execution order.

        Each inner list contains node IDs that can run concurrently.
        """
        # Build in-degree map and adjacency list
        in_degree: dict[str, int] = {n.id: 0 for n in wf.nodes}
        graph: dict[str, list[str]] = defaultdict(list)

        for conn in wf.connections:
            if conn.source_node in in_degree and conn.target_node in in_degree:
                graph[conn.source_node].append(conn.target_node)
                in_degree[conn.target_node] += 1

        # Kahn's algorithm — track layers
        layers: list[list[str]] = []
        # Current frontier: nodes with no remaining dependencies
        frontier = [n for n, deg in in_degree.items() if deg == 0]

        while frontier:
            layers.append(sorted(frontier))  # deterministic order
            next_frontier: list[str] = []
            for node in frontier:
                for neighbor in graph.get(node, []):
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_frontier.append(neighbor)
            frontier = next_frontier

        # If there are leftover nodes not in layers, we have a cycle
        sorted_count = sum(len(layer) for layer in layers)
        if sorted_count < len(in_degree):
            raise CyclicDAGError(
                f"Could not sort all nodes: {len(in_degree) - sorted_count} nodes "
                f"are part of a cycle"
            )

        return layers
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_dag.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/engine/dag.py tests/test_workflow_engine/test_dag.py
git commit -m "feat(workflow): add DAG validator and topological sort"
```

---

### Task 5: Store ABCs + JSON File Implementation

**Files:**
- Create: `src/decision_system/workflow_engine/stores/base.py`
- Create: `src/decision_system/workflow_engine/stores/json_store.py`
- Create: `tests/test_workflow_engine/test_stores.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_stores.py`:

```python
"""Tests for workflow and execution stores."""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import pytest

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ExecutionState, NodeExecutionState,
)
from decision_system.workflow_engine.stores.base import WorkflowStore, ExecutionStore
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)


class TestJSONWorkflowStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as td:
            yield JSONWorkflowStore(Path(td))

    @pytest.fixture
    def sample_wf(self):
        now = datetime.now(timezone.utc)
        return WorkflowDefinition(
            name="Test Workflow",
            nodes=[NodeConfig(id="n1", type="test.node")],
            connections=[Connection(source_node="n1", target_node="n1")],
            created_at=now,
            updated_at=now,
        )

    def test_save_and_load(self, store, sample_wf):
        store.save(sample_wf)
        loaded = store.load(sample_wf.id)
        assert loaded.name == sample_wf.name
        assert len(loaded.nodes) == 1

    def test_load_nonexistent(self, store):
        loaded = store.load("nonexistent")
        assert loaded is None

    def test_list(self, store, sample_wf):
        store.save(sample_wf)
        workflows = store.list()
        assert len(workflows) == 1
        assert workflows[0].name == "Test Workflow"

    def test_delete(self, store, sample_wf):
        store.save(sample_wf)
        store.delete(sample_wf.id)
        assert store.load(sample_wf.id) is None

    def test_delete_nonexistent(self, store):
        # Should not raise
        store.delete("nonexistent")

    def test_persistence_across_instances(self):
        """Data survives creating a new store instance."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            store1 = JSONWorkflowStore(path)
            now = datetime.now(timezone.utc)
            wf = WorkflowDefinition(
                name="Persist Test", created_at=now, updated_at=now,
            )
            store1.save(wf)
            store2 = JSONWorkflowStore(path)
            loaded = store2.load(wf.id)
            assert loaded is not None
            assert loaded.name == "Persist Test"


class TestJSONExecutionStore:
    @pytest.fixture
    def store(self):
        with tempfile.TemporaryDirectory() as td:
            yield JSONExecutionStore(Path(td))

    @pytest.fixture
    def sample_state(self):
        return ExecutionState(
            execution_id="exec1",
            workflow_id="wf1",
            status="completed",
            node_states={
                "n1": NodeExecutionState(
                    node_id="n1", status="completed", outputs={"result": 42},
                ),
            },
            started_at=datetime.now(timezone.utc),
        )

    def test_save_and_load(self, store, sample_state):
        store.save(sample_state)
        loaded = store.load("exec1")
        assert loaded is not None
        assert loaded.execution_id == "exec1"
        assert loaded.node_states["n1"].outputs == {"result": 42}

    def test_list_for_workflow(self, store, sample_state):
        store.save(sample_state)
        state2 = ExecutionState(
            execution_id="exec2", workflow_id="wf1",
        )
        store.save(state2)
        states = store.list("wf1")
        assert len(states) == 2

    def test_list_all(self, store, sample_state):
        store.save(sample_state)
        state2 = ExecutionState(
            execution_id="exec2", workflow_id="wf2",
        )
        store.save(state2)
        all_states = store.list()
        assert len(all_states) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_stores.py -v
```

Expected: ImportError for store modules

- [ ] **Step 3: Write the store modules**

Create `src/decision_system/workflow_engine/stores/base.py`:

```python
"""Abstract store interfaces for workflow definitions and execution states."""

from __future__ import annotations

from abc import ABC, abstractmethod

from decision_system.workflow_engine.models import (
    WorkflowDefinition, ExecutionState,
)


class WorkflowStore(ABC):
    """Persistent storage for workflow definitions."""

    @abstractmethod
    def save(self, workflow: WorkflowDefinition) -> None: ...

    @abstractmethod
    def load(self, workflow_id: str) -> WorkflowDefinition | None: ...

    @abstractmethod
    def list(self) -> list[WorkflowDefinition]: ...

    @abstractmethod
    def delete(self, workflow_id: str) -> None: ...


class ExecutionStore(ABC):
    """Persistent storage for execution states."""

    @abstractmethod
    def save(self, state: ExecutionState) -> None: ...

    @abstractmethod
    def load(self, execution_id: str) -> ExecutionState | None: ...

    @abstractmethod
    def list(self, workflow_id: str | None = None) -> list[ExecutionState]: ...
```

Create `src/decision_system/workflow_engine/stores/json_store.py`:

```python
"""JSON file-based implementations of workflow and execution stores."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from decision_system.workflow_engine.models import (
    WorkflowDefinition, ExecutionState,
)
from decision_system.workflow_engine.stores.base import (
    WorkflowStore, ExecutionStore,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str))


class JSONWorkflowStore(WorkflowStore):
    """Workflow store backed by JSON files under a directory."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "workflows"
        _ensure_dir(self._dir)

    def _path(self, workflow_id: str) -> Path:
        return self._dir / f"{workflow_id}.json"

    def _index_path(self) -> Path:
        return self._dir / "_index.json"

    def _load_index(self) -> list[str]:
        data = _read_json(self._index_path())
        return data if isinstance(data, list) else []

    def _save_index(self, ids: list[str]) -> None:
        _write_json(self._index_path(), ids)

    def save(self, workflow: WorkflowDefinition) -> None:
        _write_json(self._path(workflow.id), workflow.model_dump(mode="json"))
        ids = self._load_index()
        if workflow.id not in ids:
            ids.append(workflow.id)
            self._save_index(ids)

    def load(self, workflow_id: str) -> WorkflowDefinition | None:
        data = _read_json(self._path(workflow_id))
        if data is None:
            return None
        return WorkflowDefinition(**data)

    def list(self) -> list[WorkflowDefinition]:
        workflows: list[WorkflowDefinition] = []
        for wf_id in self._load_index():
            wf = self.load(wf_id)
            if wf is not None:
                workflows.append(wf)
        return workflows

    def delete(self, workflow_id: str) -> None:
        path = self._path(workflow_id)
        if path.exists():
            path.unlink()
        ids = self._load_index()
        if workflow_id in ids:
            ids.remove(workflow_id)
            self._save_index(ids)


class JSONExecutionStore(ExecutionStore):
    """Execution store backed by JSON files under a directory."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "executions"
        _ensure_dir(self._dir)

    def _path(self, execution_id: str) -> Path:
        return self._dir / f"{execution_id}.json"

    def save(self, state: ExecutionState) -> None:
        _write_json(self._path(state.execution_id), state.model_dump(mode="json"))

    def load(self, execution_id: str) -> ExecutionState | None:
        data = _read_json(self._path(execution_id))
        if data is None:
            return None
        return ExecutionState(**data)

    def list(self, workflow_id: str | None = None) -> list[ExecutionState]:
        states: list[ExecutionState] = []
        if not self._dir.exists():
            return states
        for f in sorted(self._dir.iterdir()):
            if f.suffix != ".json":
                continue
            state = self.load(f.stem)
            if state is not None:
                if workflow_id is None or state.workflow_id == workflow_id:
                    states.append(state)
        return states
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_stores.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/stores/ tests/test_workflow_engine/test_stores.py
git commit -m "feat(workflow): add workflow and execution stores (ABC + JSON)"
```

---

### Task 6: Node Base Class + Registry

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/base.py` (WorkflowNode was already defined in models.py — this provides the NodeRegistry)
- Create: `src/decision_system/workflow_engine/nodes/registry.py`
- Create: `tests/test_workflow_engine/test_nodes.py`

The WorkflowNode ABC is already in `models.py`. This task adds the `NodeRegistry` and a `BuiltinNode` convenience subclass.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_nodes.py`:

```python
"""Tests for node registry and base classes."""

import pytest

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext, NodeTypeInfo,
)
from decision_system.workflow_engine.nodes.registry import NodeRegistry


class SimpleNode(WorkflowNode):
    """Minimal concrete node for testing."""

    type: str = "test.simple"
    label: str = "Simple Node"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        return {"output": "hello"}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {"output": {"type": "string"}}}


class TestNodeRegistry:
    def test_register_and_get(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        node_cls = registry.get("test.simple")
        assert node_cls is SimpleNode

    def test_get_unknown_type(self):
        registry = NodeRegistry()
        with pytest.raises(KeyError, match="test.unknown"):
            registry.get("test.unknown")

    def test_list_types(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        types = registry.list_types()
        assert len(types) == 1
        assert types[0].type == "test.simple"
        assert types[0].label == "Simple Node"

    def test_duplicate_registration_raises(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(SimpleNode)

    def test_get_node_type_info_includes_schemas(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        info = registry.list_types()[0]
        assert info.config_schema == {"type": "object", "properties": {}}
        assert "input" in info.input_schema.get("properties", {})

    def test_instantiate_node_from_registry(self):
        registry = NodeRegistry()
        registry.register(SimpleNode)
        node = registry.instantiate("test.simple", id="n1")
        assert isinstance(node, SimpleNode)
        assert node.id == "n1"
        assert node.type == "test.simple"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: ImportError for `registry` module

- [ ] **Step 3: Write the registry module**

Create `src/decision_system/workflow_engine/nodes/registry.py`:

```python
"""Node registry — discovers, registers, and instantiates node types."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode, NodeTypeInfo, NodeConfig,
)


class NodeRegistry:
    """Thread-safe registry of all known node types.

    Node types are registered by calling register() with a WorkflowNode
    subclass. The registry can then look up types by name, list all types,
    and instantiate nodes from NodeConfig references.
    """

    def __init__(self) -> None:
        self._types: dict[str, type[WorkflowNode]] = {}

    def register(self, node_cls: type[WorkflowNode]) -> None:
        """Register a node type. Raises ValueError on duplicate."""
        node_type = getattr(node_cls, "type", None)
        if not node_type:
            raise ValueError(f"Node class {node_cls.__name__} must have a 'type' attribute")
        if node_type in self._types:
            raise ValueError(f"Node type '{node_type}' is already registered")
        self._types[node_type] = node_cls

    def get(self, node_type: str) -> type[WorkflowNode]:
        """Get a registered node class by type string. Raises KeyError if not found."""
        if node_type not in self._types:
            raise KeyError(f"Node type '{node_type}' not found in registry")
        return self._types[node_type]

    def list_types(self) -> list[NodeTypeInfo]:
        """List metadata for all registered node types."""
        result: list[NodeTypeInfo] = []
        for node_type, node_cls in sorted(self._types.items()):
            try:
                config_schema = node_cls.get_config_schema()
                input_schema = node_cls.get_input_schema()
                output_schema = node_cls.get_output_schema()
            except Exception:
                config_schema = {}
                input_schema = {}
                output_schema = {}
            result.append(NodeTypeInfo(
                type=node_type,
                label=getattr(node_cls, "label", node_type),
                description=getattr(node_cls, "__doc__", "") or "",
                config_schema=config_schema,
                input_schema=input_schema,
                output_schema=output_schema,
            ))
        return result

    def instantiate(self, node_type: str, **overrides: Any) -> WorkflowNode:
        """Create a node instance from a type string and overrides."""
        node_cls = self.get(node_type)
        return node_cls(**overrides)

    def __contains__(self, node_type: str) -> bool:
        return node_type in self._types
```

- [ ] **Step 4: Update __init__.py**

Edit `src/decision_system/workflow_engine/nodes/__init__.py`:

```python
"""Node definitions — base classes, registry, and built-in node types."""

from decision_system.workflow_engine.nodes.registry import NodeRegistry

__all__ = ["NodeRegistry"]
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/registry.py tests/test_workflow_engine/test_nodes.py
git commit -m "feat(workflow): add node registry with registration and instantiation"
```

---

### Task 7: DAG Executor

**Files:**
- Create: `src/decision_system/workflow_engine/engine/executor.py`
- Update: `tests/test_workflow_engine/test_executor.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_executor.py`:

```python
"""Tests for the DAG execution engine."""

import asyncio
from pathlib import Path
from datetime import datetime, timezone
import tempfile

import pytest

from decision_system.workflow_engine.models import (
    WorkflowNode, WorkflowDefinition, NodeConfig, Connection,
    ExecutionContext, ErrorPolicy, RetryConfig, NodeExecutionState,
)
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.engine.dag import DAGError
from decision_system.workflow_engine.nodes.registry import NodeRegistry
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)


class AddOneNode(WorkflowNode):
    """Adds 1 to the input value."""
    type: str = "test.add_one"
    label: str = "Add One"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        value = inputs.get("value", 0)
        return {"value": value + 1}

    @classmethod
    def get_config_schema(cls) -> dict: return {"type": "object", "properties": {}}
    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {"value": {"type": "number"}}}
    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {"value": {"type": "number"}}}


class MultiplyNode(WorkflowNode):
    """Multiplies the input value."""
    type: str = "test.multiply"
    label: str = "Multiply"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        value = inputs.get("value", 1)
        factor = self.config.get("factor", 2)
        return {"value": value * factor}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {"factor": {"type": "number"}}}
    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {"value": {"type": "number"}}}
    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {"value": {"type": "number"}}}


class FailingNode(WorkflowNode):
    """Always fails."""
    type: str = "test.fail"
    label: str = "Failing"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        raise ValueError("This node always fails")

    @classmethod
    def get_config_schema(cls) -> dict: return {"type": "object", "properties": {}}
    @classmethod
    def get_input_schema(cls) -> dict: return {"type": "object", "properties": {}}
    @classmethod
    def get_output_schema(cls) -> dict: return {"type": "object", "properties": {}}


class TestDAGEngine:
    @pytest.fixture
    def registry(self):
        r = NodeRegistry()
        r.register(AddOneNode)
        r.register(MultiplyNode)
        r.register(FailingNode)
        return r

    @pytest.fixture
    def stores(self):
        with tempfile.TemporaryDirectory() as td:
            yield (
                JSONWorkflowStore(Path(td)),
                JSONExecutionStore(Path(td)),
            )

    @pytest.fixture
    def engine(self, registry, stores):
        ws, es = stores
        return DAGEngine(registry=registry, workflow_store=ws, execution_store=es)

    def test_execute_empty_workflow(self, engine):
        wf = WorkflowDefinition(name="empty")
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states == {}

    def test_execute_single_node(self, engine):
        wf = WorkflowDefinition(
            name="single",
            nodes=[NodeConfig(id="n1", type="test.add_one", config={})],
            connections=[],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 5}))
        assert state.status == "completed"
        assert state.node_states["n1"].status == "completed"
        assert state.node_states["n1"].outputs == {"value": 6}

    def test_execute_linear_chain(self, engine):
        """n1 (add_one) -> n2 (multiply). Input 5 → +1 → ×2 = 12."""
        wf = WorkflowDefinition(
            name="chain",
            nodes=[
                NodeConfig(id="n1", type="test.add_one", config={}),
                NodeConfig(id="n2", type="test.multiply", config={"factor": 2}),
            ],
            connections=[Connection(source_node="n1", target_node="n2")],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 5}))
        assert state.status == "completed"
        assert state.node_states["n1"].outputs == {"value": 6}
        assert state.node_states["n2"].outputs == {"value": 12}

    def test_execute_diamond_dag(self, engine):
        """n1 -> n2 (×3), n1 -> n3 (+1), n2/n3 -> n4. 
        Input 2: n2=6, n3=3, n4 should receive n2's output (last writer)."""
        wf = WorkflowDefinition(
            name="diamond",
            nodes=[
                NodeConfig(id="n1", type="test.add_one", config={}),
                NodeConfig(id="n2", type="test.multiply", config={"factor": 3}),
                NodeConfig(id="n3", type="test.add_one", config={}),
            ],
            connections=[
                Connection(source_node="n1", target_node="n2"),
                Connection(source_node="n1", target_node="n3"),
            ],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 2}))
        assert state.status == "completed"
        # n2 and n3 ran in parallel (same layer)
        assert state.node_states["n2"].status == "completed"
        assert state.node_states["n3"].status == "completed"

    def test_execute_with_failing_node_fail_workflow(self, engine):
        wf = WorkflowDefinition(
            name="failing",
            nodes=[NodeConfig(id="n1", type="test.fail", config={})],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "failed"
        assert "This node always fails" in (state.error or "")

    def test_execute_with_skip_policy(self, engine):
        """A node with SKIP policy should be marked skipped, not fail the workflow."""
        wf = WorkflowDefinition(
            name="skip",
            nodes=[NodeConfig(
                id="n1", type="test.fail", config={},
                error_policy=ErrorPolicy.SKIP,
            )],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states["n1"].status == "skipped"

    def test_events_emitted_during_execution(self, engine):
        events = []
        engine.on_event(events.append)
        wf = WorkflowDefinition(
            name="events",
            nodes=[NodeConfig(id="n1", type="test.add_one", config={})],
        )
        asyncio.run(engine.execute(wf, global_inputs={"value": 1}))
        event_types = [e.event_type for e in events]
        assert "node_started" in event_types
        assert "node_completed" in event_types
        assert "workflow_completed" in event_types

    def test_execution_persisted(self, engine):
        wf = WorkflowDefinition(
            name="persist",
            nodes=[NodeConfig(id="n1", type="test.add_one", config={})],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 10}))
        loaded = engine.execution_store.load(state.execution_id)
        assert loaded is not None
        assert loaded.status == "completed"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_executor.py -v
```

Expected: ImportError for `executor` module

- [ ] **Step 3: Write the executor module**

Create `src/decision_system/workflow_engine/engine/executor.py`:

```python
"""DAG execution engine — runs workflows by dispatching nodes in dependency order."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, ExecutionState, NodeExecutionState,
    ExecutionContext, ErrorPolicy, RetryConfig,
)
from decision_system.workflow_engine.engine.dag import DAGValidator, TopologicalSort
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.nodes.registry import NodeRegistry
from decision_system.workflow_engine.stores.base import (
    WorkflowStore, ExecutionStore,
)


class DAGEngine:
    """Main workflow execution engine.

    Takes a WorkflowDefinition, validates the DAG, topologically sorts it,
    and executes nodes layer by layer with optional parallel dispatch.
    """

    def __init__(
        self,
        registry: NodeRegistry,
        workflow_store: WorkflowStore,
        execution_store: ExecutionStore,
    ) -> None:
        self.registry = registry
        self.workflow_store = workflow_store
        self.execution_store = execution_store
        self._event_handlers: list[Callable[[ExecutionEvent], None]] = []

    def on_event(self, handler: Callable[[ExecutionEvent], None]) -> None:
        """Register an event handler for execution events."""
        self._event_handlers.append(handler)

    def _emit(self, event: ExecutionEvent) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception:
                pass

    async def execute(
        self,
        workflow: WorkflowDefinition,
        global_inputs: dict[str, Any] | None = None,
    ) -> ExecutionState:
        """Execute a workflow definition. Returns the final ExecutionState."""
        state = ExecutionState(
            execution_id=str(uuid4()),
            workflow_id=workflow.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            node_states={n.id: NodeExecutionState(node_id=n.id) for n in workflow.nodes},
        )
        self.execution_store.save(state)

        try:
            # Validate
            errors = DAGValidator.validate(workflow)
            if errors:
                error_msg = "; ".join(str(e) for e in errors)
                state.status = "failed"
                state.error = error_msg
                state.completed_at = datetime.now(timezone.utc)
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="workflow_failed",
                    data={"error": error_msg},
                ))
                return state

            # Topo sort
            layers = TopologicalSort.sort(workflow)
            node_configs = {n.id: n for n in workflow.nodes}

            # Build dependency map for input routing
            deps: dict[str, list[tuple[str, str, str]]] = {n.id: [] for n in workflow.nodes}
            for conn in workflow.connections:
                if conn.target_node in deps:
                    deps[conn.target_node].append(
                        (conn.source_node, conn.source_output, conn.target_input)
                    )

            # Execute layer by layer
            for layer in layers:
                tasks = []
                for node_id in layer:
                    tasks.append(self._execute_node(
                        state, node_id, node_configs[node_id],
                        deps[node_id], global_inputs,
                    ))
                # Wait for all nodes in this layer
                await asyncio.gather(*tasks)

                # Check if we should stop (fail_workflow policy triggered)
                if state.status == "failed":
                    break

            if state.status == "running":
                state.status = "completed"
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_completed",
                data={"status": state.status},
            ))

        except Exception as exc:
            state.status = "failed"
            state.error = str(exc)
            state.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)
            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="workflow_failed",
                data={"error": str(exc)},
            ))

        return state

    async def _execute_node(
        self,
        state: ExecutionState,
        node_id: str,
        config: NodeConfig,
        dependencies: list[tuple[str, str, str]],
        global_inputs: dict[str, Any] | None,
    ) -> None:
        """Execute a single node: resolve inputs, dispatch, handle errors."""
        ns = state.node_states[node_id]
        ns.status = "running"
        ns.started_at = datetime.now(timezone.utc)
        ns.attempts += 1
        self.execution_store.save(state)

        self._emit(ExecutionEvent(
            execution_id=state.execution_id,
            event_type="node_started",
            node_id=node_id,
            data={"node_type": config.type},
        ))

        try:
            # Collect inputs from upstream nodes
            inputs: dict[str, Any] = {}
            if global_inputs:
                inputs.update(global_inputs)
            for src_node, src_output, target_input in dependencies:
                src_state = state.node_states.get(src_node)
                if src_state and src_state.outputs:
                    inputs[target_input] = src_state.outputs.get(src_output)

            ns.inputs = inputs

            # Instantiate and execute
            node_cls = self.registry.get(config.type)
            ctx = ExecutionContext(
                workflow_id=state.workflow_id,
                execution_id=state.execution_id,
            )
            node = node_cls(id=node_id, type=config.type, config=config.config)
            outputs = await node.execute(inputs, ctx)

            ns.outputs = outputs
            ns.status = "completed"
            ns.completed_at = datetime.now(timezone.utc)
            self.execution_store.save(state)

            self._emit(ExecutionEvent(
                execution_id=state.execution_id,
                event_type="node_completed",
                node_id=node_id,
                data={"outputs": outputs},
            ))

        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            ns.error = error_msg
            ns.completed_at = datetime.now(timezone.utc)

            if config.error_policy == ErrorPolicy.SKIP:
                ns.status = "skipped"
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "skipped"},
                ))

            elif config.error_policy == ErrorPolicy.RETRY:
                retry_cfg = config.retry_config or RetryConfig()
                if ns.attempts < retry_cfg.max_attempts:
                    delay = min(
                        retry_cfg.base_delay * (retry_cfg.backoff_multiplier ** (ns.attempts - 1)),
                        retry_cfg.max_delay,
                    )
                    await asyncio.sleep(delay)
                    # Recursive retry
                    await self._execute_node(state, node_id, config, dependencies, global_inputs)
                else:
                    ns.status = "failed"
                    state.status = "failed"
                    state.error = error_msg
                    self.execution_store.save(state)
                    self._emit(ExecutionEvent(
                        execution_id=state.execution_id,
                        event_type="node_failed",
                        node_id=node_id,
                        data={"error": error_msg, "action": "failed"},
                    ))

            elif config.error_policy == ErrorPolicy.FAIL_NODE:
                ns.status = "failed"
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "failed_continue"},
                ))

            else:  # FAIL_WORKFLOW (default)
                ns.status = "failed"
                state.status = "failed"
                state.error = error_msg
                self.execution_store.save(state)
                self._emit(ExecutionEvent(
                    execution_id=state.execution_id,
                    event_type="node_failed",
                    node_id=node_id,
                    data={"error": error_msg, "action": "failed_workflow"},
                ))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_executor.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/engine/executor.py tests/test_workflow_engine/test_executor.py
git commit -m "feat(workflow): add DAG executor with parallel layer dispatch and error handling"
```

---

### Task 8: Built-in Trigger + Flow Nodes

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/builtin/trigger_nodes.py`
- Create: `src/decision_system/workflow_engine/nodes/builtin/flow_nodes.py`
- Update: `tests/test_workflow_engine/test_nodes.py`

- [ ] **Step 1: Write the trigger nodes**

Create `src/decision_system/workflow_engine/nodes/builtin/trigger_nodes.py`:

```python
"""Built-in trigger and input node types."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class ManualTriggerNode(WorkflowNode):
    """Manual trigger — starts a workflow with provided inputs.
    This is the default trigger for on-demand workflow execution.
    """
    type: str = "decision_system.trigger_manual"
    label: str = "Manual Trigger"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        return {"triggered": True, **inputs}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "triggered": {"type": "boolean"},
            },
        }


class InputTextNode(WorkflowNode):
    """Provides a text input to the workflow.
    Useful for injecting question text, prompts, or configuration.
    """
    type: str = "decision_system.input_text"
    label: str = "Input Text"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        text = self.config.get("text", "")
        return {"text": text, "question": text}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "title": "Text",
                    "description": "The text to provide as input",
                },
            },
            "required": ["text"],
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "question": {"type": "string"},
            },
        }
```

- [ ] **Step 2: Write the flow nodes**

Create `src/decision_system/workflow_engine/nodes/builtin/flow_nodes.py`:

```python
"""Built-in flow control node types."""

from __future__ import annotations

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class FilterNode(WorkflowNode):
    """Conditionally passes data through based on a filter expression.
    If the condition evaluates to False, the node outputs the original
    inputs unchanged (pass-through).
    """
    type: str = "decision_system.filter"
    label: str = "Filter"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        field = self.config.get("field", "")
        operator = self.config.get("operator", "exists")
        value = self.config.get("value", None)

        target = inputs.get(field) if field else None
        passed = True  # pass through by default

        if field and target is not None:
            if operator == "exists":
                passed = True
            elif operator == "equals":
                passed = target == value
            elif operator == "not_equals":
                passed = target != value
            elif operator == "greater_than":
                try:
                    passed = float(target) > float(value)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    passed = False
            elif operator == "less_than":
                try:
                    passed = float(target) < float(value)  # type: ignore[arg-type]
                except (TypeError, ValueError):
                    passed = False
        elif field and target is None:
            passed = False

        return {
            "passed": passed,
            "filtered": not passed,
            **inputs,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "title": "Field",
                    "description": "Input field to check",
                },
                "operator": {
                    "type": "string",
                    "title": "Operator",
                    "enum": ["exists", "equals", "not_equals", "greater_than", "less_than"],
                    "default": "exists",
                },
                "value": {
                    "title": "Value",
                    "description": "Value to compare against",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "filtered": {"type": "boolean"},
            },
        }


class MergeNode(WorkflowNode):
    """Merges multiple upstream inputs into a single output.
    Merge strategies:
    - merge: shallow merge of all input dicts (later keys overwrite earlier)
    - concat: concatenate lists found at the specified field name
    """
    type: str = "decision_system.merge"
    label: str = "Merge"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        strategy = self.config.get("strategy", "merge")
        input_field = self.config.get("input_field", "default")

        if strategy == "merge":
            return {**inputs}
        elif strategy == "concat":
            items = []
            for key, value in inputs.items():
                if isinstance(value, list):
                    items.extend(value)
                elif isinstance(value, dict):
                    inner = value.get(input_field, [])
                    if isinstance(inner, list):
                        items.extend(inner)
            return {"items": items, "count": len(items)}
        return inputs

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "strategy": {
                    "type": "string",
                    "title": "Merge Strategy",
                    "enum": ["merge", "concat"],
                    "default": "merge",
                },
                "input_field": {
                    "type": "string",
                    "title": "Input Field",
                    "description": "Field name for concat strategy",
                    "default": "default",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "items": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class CodeNode(WorkflowNode):
    """Executes a user-provided Python code snippet.
    The code receives `inputs` dict and `ctx` (ExecutionContext) as locals.
    Must set `output` variable with the result dict.
    """
    type: str = "decision_system.code"
    label: str = "Code"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        source = self.config.get("source", "")
        if not source.strip():
            return inputs

        # Prepare safe locals
        local_vars: dict = {"inputs": inputs, "ctx": ctx, "output": {}}
        exec_globals: dict = {"__builtins__": __builtins__}

        try:
            exec(source.strip(), exec_globals, local_vars)  # nosec
            return local_vars.get("output", inputs)
        except Exception as exc:
            raise RuntimeError(f"Code execution error: {exc}") from exc

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "title": "Python Code",
                    "description": "Python code. Use `inputs` dict, set `output` dict.",
                    "default": "# Write Python code here\noutput = inputs",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {"type": "object", "properties": {}}
```

- [ ] **Step 3: Register nodes in builtin __init__.py**

Create `src/decision_system/workflow_engine/nodes/builtin/__init__.py`:

```python
"""Built-in node types shipped with the workflow engine."""

from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
    ManualTriggerNode, InputTextNode,
)
from decision_system.workflow_engine.nodes.builtin.flow_nodes import (
    FilterNode, MergeNode, CodeNode,
)

__all__ = [
    "ManualTriggerNode", "InputTextNode",
    "FilterNode", "MergeNode", "CodeNode",
]
```

- [ ] **Step 4: Write tests for trigger and flow nodes**

Add to `tests/test_workflow_engine/test_nodes.py`:

```python
from decision_system.workflow_engine.models import ExecutionContext


class TestManualTriggerNode:
    @pytest.mark.asyncio
    async def test_trigger_passes_inputs(self):
        node = ManualTriggerNode(id="n1", type="decision_system.trigger_manual")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"question": "test"}, ctx)
        assert result["triggered"] is True
        assert result["question"] == "test"


class TestInputTextNode:
    @pytest.mark.asyncio
    async def test_returns_configured_text(self):
        node = InputTextNode(
            id="n1", type="decision_system.input_text",
            config={"text": "What is our risk?"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["text"] == "What is our risk?"
        assert result["question"] == "What is our risk?"

    @pytest.mark.asyncio
    async def test_empty_text(self):
        node = InputTextNode(id="n1", type="decision_system.input_text")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["text"] == ""


class TestCodeNode:
    @pytest.mark.asyncio
    async def test_basic_code_execution(self):
        node = CodeNode(
            id="n1", type="decision_system.code",
            config={"source": "output = {'result': inputs['value'] * 2}"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"value": 21}, ctx)
        assert result["result"] == 42

    @pytest.mark.asyncio
    async def test_empty_code_passthrough(self):
        node = CodeNode(id="n1", type="decision_system.code")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"key": "val"}, ctx)
        assert result == {"key": "val"}

    @pytest.mark.asyncio
    async def test_code_syntax_error(self):
        node = CodeNode(
            id="n1", type="decision_system.code",
            config={"source": "this is not valid python"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        with pytest.raises(Exception):
            await node.execute({}, ctx)


class TestFilterNode:
    @pytest.mark.asyncio
    async def test_equals_pass(self):
        node = FilterNode(
            id="n1", type="decision_system.filter",
            config={"field": "status", "operator": "equals", "value": "active"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"status": "active"}, ctx)
        assert result["passed"] is True

    @pytest.mark.asyncio
    async def test_equals_fail(self):
        node = FilterNode(
            id="n1", type="decision_system.filter",
            config={"field": "status", "operator": "equals", "value": "inactive"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"status": "active"}, ctx)
        assert result["passed"] is False


class TestMergeNode:
    @pytest.mark.asyncio
    async def test_merge_strategy(self):
        node = MergeNode(
            id="n1", type="decision_system.merge",
            config={"strategy": "merge"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"a": 1, "b": 2}, ctx)
        assert result["a"] == 1
        assert result["b"] == 2
```

- [ ] **Step 5: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/builtin/ tests/test_workflow_engine/test_nodes.py
git commit -m "feat(workflow): add built-in trigger and flow control nodes"
```

---

### Task 9: Decision Nodes (Wrapping Existing Capabilities)

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/builtin/decision_nodes.py`
- Update: `src/decision_system/workflow_engine/nodes/builtin/__init__.py`
- Update: `tests/test_workflow_engine/test_nodes.py`

These nodes wrap the existing decision system capabilities. Each node calls
into the existing module functions, passing config from the node's config dict.

- [ ] **Step 1: Write the decision nodes**

Create `src/decision_system/workflow_engine/nodes/builtin/decision_nodes.py`:

```python
"""Built-in decision intelligence node types.

Each node wraps an existing decision-system capability. All use the
fake provider by default and require no API keys for execution.
"""

from __future__ import annotations

from pathlib import Path

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class RetrieveNode(WorkflowNode):
    """Retrieves evidence chunks from the local Chroma vector store."""
    type: str = "decision_system.retrieve"
    label: str = "Retrieve Evidence"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        question = inputs.get("question") or inputs.get("text") or ""
        if not question:
            return {"chunks": [], "count": 0}

        top_k = self.config.get("top_k", 5)

        try:
            from decision_system.rag.retriever import retrieve_evidence
            from decision_system.rag.vector_store import get_vector_store

            store = get_vector_store()
            collection_name = self.config.get("collection", "decision_docs")
            results = retrieve_evidence(
                question=question,
                collection_name=collection_name,
                top_k=top_k,
                vector_store=store,
            )
            chunks = []
            for chunk in results:
                chunks.append({
                    "evidence_id": chunk.evidence_id,
                    "source": chunk.source,
                    "text": chunk.text,
                    "score": chunk.score,
                })
            return {"chunks": chunks, "count": len(chunks)}
        except Exception as exc:
            return {"chunks": [], "count": 0, "error": str(exc)}

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "top_k": {"type": "integer", "default": 5, "title": "Top K"},
                "collection": {
                    "type": "string", "default": "decision_docs",
                    "title": "Collection Name",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "text": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class TechAnalystNode(WorkflowNode):
    """Runs technical analysis on retrieved evidence."""
    type: str = "decision_system.technical_analyst"
    label: str = "Technical Analyst"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.agents.technical_analyst import run_technical_analysis

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        provider = self.config.get("provider", ctx.provider)

        memo = run_technical_analysis(question=question, chunks=chunks, provider=provider)
        return {
            "memo": memo.model_dump() if hasattr(memo, "model_dump") else memo,
            "analysis": str(memo),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string", "default": "fake",
                    "enum": ["fake", "nvidia_nim", "ollama"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "memo": {"type": "object"},
                "analysis": {"type": "string"},
            },
        }


class RiskAnalystNode(WorkflowNode):
    """Runs risk analysis on retrieved evidence."""
    type: str = "decision_system.risk_analyst"
    label: str = "Risk Analyst"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.agents.risk_analyst import run_risk_analysis

        question = inputs.get("question") or ""
        chunks = inputs.get("chunks") or []
        provider = self.config.get("provider", ctx.provider)

        memo = run_risk_analysis(question=question, chunks=chunks, provider=provider)
        return {
            "memo": memo.model_dump() if hasattr(memo, "model_dump") else memo,
            "analysis": str(memo),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string", "default": "fake",
                    "enum": ["fake", "nvidia_nim", "ollama"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "memo": {"type": "object"},
                "analysis": {"type": "string"},
            },
        }


class ExtractClaimsNode(WorkflowNode):
    """Extracts claims from analyst memos into the claim ledger."""
    type: str = "decision_system.extract_claims"
    label: str = "Extract Claims"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ledger.claim_ledger import ClaimLedger

        tech_memo = inputs.get("technical_memo") or inputs.get("memo", {})
        risk_memo = inputs.get("risk_memo") or inputs.get("memo", {})

        ledger = ClaimLedger()
        if isinstance(tech_memo, dict):
            ledger.add_claims_from_memo(tech_memo)
        if isinstance(risk_memo, dict):
            ledger.add_claims_from_memo(risk_memo)

        claims = ledger.get_all_claims()
        return {
            "claims": [c.model_dump() if hasattr(c, "model_dump") else c for c in claims],
            "count": len(claims),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "technical_memo": {"type": "object"},
                "risk_memo": {"type": "object"},
                "memo": {"type": "object"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class VerifyClaimsNode(WorkflowNode):
    """Verifies extracted claims against retrieved evidence."""
    type: str = "decision_system.verify_claims"
    label: str = "Verify Claims"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ledger.verifier import verify_claims

        claims = inputs.get("claims") or []
        raw_claims = [c if isinstance(c, dict) else {} for c in claims]
        chunks = inputs.get("chunks") or []

        verified = verify_claims(claims=raw_claims, chunks=chunks)
        return {
            "verified_claims": [
                v.model_dump() if hasattr(v, "model_dump") else v for v in verified
            ],
            "count": len(verified),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "claims": {"type": "array"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "verified_claims": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class WriteReportNode(WorkflowNode):
    """Writes a decision report from verified claims."""
    type: str = "decision_system.write_report"
    label: str = "Write Report"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.reports.renderer import render_decision_report

        question = inputs.get("question") or ""
        claims = inputs.get("verified_claims") or inputs.get("claims") or []
        raw_claims = [c if isinstance(c, dict) else {} for c in claims]
        chunks = inputs.get("chunks") or []

        report_lines = render_decision_report(
            question=question,
            claims=[type("obj", (object,), c)() for c in raw_claims],  # simple compat
            chunks=chunks,
        )
        report = "\n".join(report_lines)

        return {
            "report": report,
            "format": self.config.get("format", "markdown"),
            "length": len(report),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string", "default": "markdown",
                    "enum": ["markdown", "json"],
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "claims": {"type": "array"},
                "verified_claims": {"type": "array"},
                "chunks": {"type": "array"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "report": {"type": "string"},
                "format": {"type": "string"},
                "length": {"type": "integer"},
            },
        }
```

- [ ] **Step 2: Update __init__.py**

Edit `src/decision_system/workflow_engine/nodes/builtin/__init__.py`:

```python
"""Built-in node types shipped with the workflow engine."""

from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
    ManualTriggerNode, InputTextNode,
)
from decision_system.workflow_engine.nodes.builtin.flow_nodes import (
    FilterNode, MergeNode, CodeNode,
)
from decision_system.workflow_engine.nodes.builtin.decision_nodes import (
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
)

__all__ = [
    "ManualTriggerNode", "InputTextNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
]
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/builtin/decision_nodes.py
git commit -m "feat(workflow): add decision intelligence node types"
```

---

### Task 10: Data Nodes (Graph, Profile, Ontology, Insights, War Room)

**Files:**
- Create: `src/decision_system/workflow_engine/nodes/builtin/data_nodes.py`
- Update: `src/decision_system/workflow_engine/nodes/builtin/__init__.py`
- Update: `tests/test_workflow_engine/test_nodes.py`

- [ ] **Step 1: Write the data nodes**

Create `src/decision_system/workflow_engine/nodes/builtin/data_nodes.py`:

```python
"""Built-in data analysis node types.

Each node wraps an existing data/analysis capability.
"""

from __future__ import annotations

from pathlib import Path

from decision_system.workflow_engine.models import (
    WorkflowNode, ExecutionContext,
)


class ExtractGraphNode(WorkflowNode):
    """Extracts entities and relationships from documents into a knowledge graph."""
    type: str = "decision_system.extract_graph"
    label: str = "Extract Graph"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.graphing.extractor import extract_knowledge_graph

        chunks = inputs.get("chunks") or []
        graph = extract_knowledge_graph(chunks)

        kg_dict = graph.model_dump() if hasattr(graph, "model_dump") else {}
        return {
            "graph": kg_dict,
            "entity_count": len(kg_dict.get("entities", [])),
            "relationship_count": len(kg_dict.get("relationships", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"chunks": {"type": "array"}},
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "graph": {"type": "object"},
                "entity_count": {"type": "integer"},
                "relationship_count": {"type": "integer"},
            },
        }


class ProfileDataNode(WorkflowNode):
    """Profiles local CSV data files."""
    type: str = "decision_system.profile_data"
    label: str = "Profile Data"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.data_catalog.profiler import profile_dataset
        from decision_system.data_catalog.loader import load_catalog_datasets

        catalog_path_str = self.config.get("catalog_path", "company_data")
        catalog_path = Path(catalog_path_str)

        datasets = []
        if catalog_path.exists():
            datasets = load_catalog_datasets(catalog_path)

        profiles = []
        for ds in datasets:
            profiles.append(profile_dataset(ds))

        return {
            "profiles": [p.model_dump() if hasattr(p, "model_dump") else p for p in profiles],
            "count": len(profiles),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "catalog_path": {
                    "type": "string", "default": "company_data",
                    "title": "Catalog Path",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "profiles": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class MapOntologyNode(WorkflowNode):
    """Maps data profiles to ontology concepts."""
    type: str = "decision_system.map_ontology"
    label: str = "Map Ontology"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.ontology.mapper import map_profiles_to_ontology

        profiles = inputs.get("profiles") or []
        ontology = map_profiles_to_ontology(profiles)
        onto_dict = ontology.model_dump() if hasattr(ontology, "model_dump") else {}
        return {
            "ontology": onto_dict,
            "concept_count": len(onto_dict.get("mappings", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {"type": "object", "properties": {}}

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {"profiles": {"type": "array"}},
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "ontology": {"type": "object"},
                "concept_count": {"type": "integer"},
            },
        }


class DetectPatternsNode(WorkflowNode):
    """Runs deterministic pattern and vulnerability detection."""
    type: str = "decision_system.detect_patterns"
    label: str = "Detect Patterns"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.insights.detectors import run_detectors
        from decision_system.insights.store import InsightStore

        store = InsightStore()
        profiles = inputs.get("profiles") or []
        graph_data = inputs.get("graph")

        csv_root = Path(self.config.get("catalog_path", "company_data"))
        run_detectors(store, profiles, csv_root)

        insights = store.get_all_insights()
        return {
            "insights": [i.model_dump() if hasattr(i, "model_dump") else i for i in insights],
            "count": len(insights),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "severity_threshold": {
                    "type": "string", "default": "low",
                    "enum": ["low", "medium", "high", "critical"],
                },
                "catalog_path": {
                    "type": "string", "default": "company_data",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "profiles": {"type": "array"},
                "graph": {"type": "object"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "insights": {"type": "array"},
                "count": {"type": "integer"},
            },
        }


class WarRoomNode(WorkflowNode):
    """Runs the war-cabinet multi-role analysis protocol."""
    type: str = "decision_system.war_room"
    label: str = "Run War Room"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        from decision_system.war_room.runner import run_war_room

        question = inputs.get("question") or inputs.get("text") or ""
        if not question:
            question = self.config.get("question", "")

        result = run_war_room(question=question)
        result_dict = result.model_dump() if hasattr(result, "model_dump") else {}
        return {
            "war_room_run": result_dict,
            "artifact_count": len(result_dict.get("artifacts", [])),
            "judge_interventions": len(result_dict.get("judge_findings", [])),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "title": "Question",
                    "description": "Business question for the war room",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "text": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "war_room_run": {"type": "object"},
                "artifact_count": {"type": "integer"},
                "judge_interventions": {"type": "integer"},
            },
        }
```

- [ ] **Step 2: Update builtin __init__.py**

Edit `src/decision_system/workflow_engine/nodes/builtin/__init__.py`:

```python
"""Built-in node types shipped with the workflow engine."""

from decision_system.workflow_engine.nodes.builtin.trigger_nodes import (
    ManualTriggerNode, InputTextNode,
)
from decision_system.workflow_engine.nodes.builtin.flow_nodes import (
    FilterNode, MergeNode, CodeNode,
)
from decision_system.workflow_engine.nodes.builtin.decision_nodes import (
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
)
from decision_system.workflow_engine.nodes.builtin.data_nodes import (
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
)

__all__ = [
    "ManualTriggerNode", "InputTextNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
    "ExtractGraphNode", "ProfileDataNode", "MapOntologyNode",
    "DetectPatternsNode", "WarRoomNode",
]
```

- [ ] **Step 3: Write test for data nodes**

Add to `tests/test_workflow_engine/test_nodes.py`:

```python
class TestExtractGraphNode:
    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        node = ExtractGraphNode(id="n1", type="decision_system.extract_graph")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({"chunks": []}, ctx)
        assert result["entity_count"] == 0


class TestProfileDataNode:
    @pytest.mark.asyncio
    async def test_nonexistent_catalog(self):
        node = ProfileDataNode(
            id="n1", type="decision_system.profile_data",
            config={"catalog_path": "/tmp/nonexistent_catalog_xyz"},
        )
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["count"] == 0


class TestWarRoomNode:
    @pytest.mark.asyncio
    async def test_empty_question(self):
        node = WarRoomNode(id="n1", type="decision_system.war_room")
        ctx = ExecutionContext(workflow_id="wf1", execution_id="e1")
        result = await node.execute({}, ctx)
        assert result["artifact_count"] >= 0
```

- [ ] **Step 4: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/builtin/data_nodes.py tests/test_workflow_engine/test_nodes.py
git commit -m "feat(workflow): add data analysis node types"
```

---

### Task 11: Auto-register Built-in Nodes

**Files:**
- Modify: `src/decision_system/workflow_engine/nodes/__init__.py`
- Update: `tests/test_workflow_engine/test_nodes.py`

- [ ] **Step 1: Update node package __init__.py**

Edit `src/decision_system/workflow_engine/nodes/__init__.py` to auto-register all built-in nodes into a default registry:

```python
"""Node definitions — base classes, registry, and built-in node types."""

from decision_system.workflow_engine.nodes.registry import NodeRegistry

# Built-in imports
from decision_system.workflow_engine.nodes.builtin import (
    ManualTriggerNode, InputTextNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
)

def create_default_registry() -> NodeRegistry:
    """Create a registry pre-populated with all built-in node types."""
    registry = NodeRegistry()
    for node_cls in _ALL_BUILTIN_NODES:
        registry.register(node_cls)
    return registry


_ALL_BUILTIN_NODES = [
    ManualTriggerNode, InputTextNode,
    FilterNode, MergeNode, CodeNode,
    RetrieveNode, TechAnalystNode, RiskAnalystNode,
    ExtractClaimsNode, VerifyClaimsNode, WriteReportNode,
    ExtractGraphNode, ProfileDataNode, MapOntologyNode,
    DetectPatternsNode, WarRoomNode,
]

__all__ = [
    "NodeRegistry", "create_default_registry",
    "ManualTriggerNode", "InputTextNode",
    "FilterNode", "MergeNode", "CodeNode",
    "RetrieveNode", "TechAnalystNode", "RiskAnalystNode",
    "ExtractClaimsNode", "VerifyClaimsNode", "WriteReportNode",
    "ExtractGraphNode", "ProfileDataNode", "MapOntologyNode",
    "DetectPatternsNode", "WarRoomNode",
]
```

- [ ] **Step 2: Write test for default registry**

Add to `tests/test_workflow_engine/test_nodes.py`:

```python
class TestDefaultRegistry:
    def test_create_default_registry_contains_all_builtins(self):
        from decision_system.workflow_engine.nodes import create_default_registry
        registry = create_default_registry()
        types = registry.list_types()
        type_names = {t.type for t in types}
        assert "decision_system.trigger_manual" in type_names
        assert "decision_system.retrieve" in type_names
        assert "decision_system.technical_analyst" in type_names
        assert "decision_system.risk_analyst" in type_names
        assert "decision_system.extract_claims" in type_names
        assert "decision_system.verify_claims" in type_names
        assert "decision_system.write_report" in type_names
        assert "decision_system.extract_graph" in type_names
        assert "decision_system.profile_data" in type_names
        assert "decision_system.map_ontology" in type_names
        assert "decision_system.detect_patterns" in type_names
        assert "decision_system.war_room" in type_names
        assert "decision_system.input_text" in type_names
        assert "decision_system.filter" in type_names
        assert "decision_system.merge" in type_names
        assert "decision_system.code" in type_names
        # Count should be 16
        assert len(type_names) == 16
```

- [ ] **Step 3: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_nodes.py -v
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/workflow_engine/nodes/
git commit -m "feat(workflow): auto-register all 16 built-in node types"
```

---

### Task 12: Workflow CLI Commands

**Files:**
- Create: `src/decision_system/workflow_engine/cli.py`
- Modify: `src/decision_system/cli.py` (add sub-app integration)
- Create: `tests/test_workflow_engine/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_cli.py`:

```python
"""Tests for workflow CLI commands."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner

import pytest

from decision_system.workflow_engine.cli import app as workflow_app


class TestWorkflowCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_workflow_path(self):
        """Create a simple valid workflow JSON file."""
        wf = {
            "name": "Test CLI Workflow",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual", "label": "Start"},
            ],
            "connections": [],
            "version": 1,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(wf, f)
            path = f.name
        yield Path(path)
        path.unlink(missing_ok=True)

    def test_validate_valid_workflow(self, runner, sample_workflow_path):
        result = runner.invoke(workflow_app, ["validate", str(sample_workflow_path)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_json(self, runner):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = f.name
        result = runner.invoke(workflow_app, ["validate", path])
        assert result.exit_code != 0
        Path(path).unlink(missing_ok=True)

    def test_list_nodes(self, runner):
        result = runner.invoke(workflow_app, ["list-nodes"])
        assert result.exit_code == 0
        assert "decision_system.trigger_manual" in result.stdout
        assert "decision_system.retrieve" in result.stdout

    def test_help(self, runner):
        result = runner.invoke(workflow_app, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout
        assert "list-nodes" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_cli.py -v
```

Expected: ImportError for `cli` module

- [ ] **Step 3: Write the CLI module**

Create `src/decision_system/workflow_engine/cli.py`:

```python
"""CLI commands for workflow management and execution."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.dag import DAGValidator, TopologicalSort
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.nodes import create_default_registry

console = Console()
app = typer.Typer(help="Create, validate, and run workflow definitions.")
_registry = create_default_registry()


def _load_workflow(path: Path) -> WorkflowDefinition:
    """Load a WorkflowDefinition from a JSON file."""
    data = json.loads(path.read_text())
    # If the file is the top-level definition format (not nested under a key)
    if "name" in data:
        nodes = [NodeConfig(**n) for n in data.get("nodes", [])]
        connections = [Connection(**c) for c in data.get("connections", [])]
        return WorkflowDefinition(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            nodes=nodes,
            connections=connections,
            version=data.get("version", 1),
        )
    raise ValueError("Invalid workflow definition: missing 'name' field")


@app.command()
def validate(
    workflow_path: Path = typer.Argument(
        ..., help="Path to workflow JSON file", exists=True,
    ),
) -> None:
    """Validate a workflow DAG definition."""
    try:
        wf = _load_workflow(workflow_path)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    errors = DAGValidator.validate(wf)
    if errors:
        console.print(f"[red]Workflow has {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(1)

    layers = TopologicalSort.sort(wf)
    console.print(f"[green]✓[/green] Workflow is valid: {len(wf.nodes)} nodes in {len(layers)} layers")


@app.command()
def list_nodes() -> None:
    """List all available node types."""
    types = _registry.list_types()
    table = Table(title=f"Available Nodes ({len(types)})")
    table.add_column("Type", style="cyan")
    table.add_column("Label", style="green")
    table.add_column("Description")

    for nt in types:
        desc = nt.description[:60] + "..." if len(nt.description) > 60 else nt.description
        table.add_row(nt.type, nt.label, desc)

    console.print(table)


@app.command()
def run(
    workflow_path: Path = typer.Argument(
        ..., help="Path to workflow JSON file", exists=True,
    ),
    global_input: list[str] = typer.Option(
        [], "--input", "-i",
        help="Global inputs as key=value pairs (can repeat)",
    ),
) -> None:
    """Execute a workflow definition."""
    try:
        wf = _load_workflow(workflow_path)
    except (json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    errors = DAGValidator.validate(wf)
    if errors:
        console.print(f"[red]Workflow has {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        raise typer.Exit(1)

    # Parse global inputs
    global_inputs: dict[str, str] = {}
    for pair in global_input:
        if "=" in pair:
            key, value = pair.split("=", 1)
            global_inputs[key] = value

    # Build engine (in-memory stores for CLI runs, no persistence)
    from decision_system.workflow_engine.stores.json_store import (
        JSONWorkflowStore, JSONExecutionStore,
    )
    import tempfile
    tmp_dir = Path(tempfile.mkdtemp())
    ws = JSONWorkflowStore(tmp_dir)
    es = JSONExecutionStore(tmp_dir)
    engine = DAGEngine(registry=_registry, workflow_store=ws, execution_store=es)

    # Print progress
    def on_event(event: ExecutionEvent) -> None:
        if event.event_type == "node_started":
            console.print(f"  [yellow]▶[/yellow] {event.node_id}...")
        elif event.event_type == "node_completed":
            console.print(f"  [green]✓[/green] {event.node_id}")
        elif event.event_type == "node_failed":
            console.print(f"  [red]✗[/red] {event.node_id}: {event.data.get('error', '')}")
        elif event.event_type == "workflow_completed":
            console.print(f"\n[green]Workflow completed: {event.data.get('status', '')}[/green]")
        elif event.event_type == "workflow_failed":
            console.print(f"\n[red]Workflow failed: {event.data.get('error', '')}[/red]")

    engine.on_event(on_event)

    import asyncio
    state = asyncio.run(engine.execute(wf, global_inputs=global_inputs))

    # Print summary
    if state.status == "completed":
        console.print(f"\n[bold green]✓ Execution {state.execution_id} completed[/bold green]")
    else:
        console.print(f"\n[bold red]✗ Execution {state.execution_id} failed: {state.error}[/bold red]")
        raise typer.Exit(1)
```

- [ ] **Step 4: Integrate into main CLI**

Add the sub-app to `src/decision_system/cli.py`. Insert after the `app` definition (around line 77):

```python
from decision_system.workflow_engine.cli import app as workflow_app
app.add_typer(workflow_app, name="workflow", help="Create, validate, and run workflows")
```

- [ ] **Step 5: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_cli.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Verify existing 700+ tests still pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest -q --timeout=60 2>&1 | tail -5
```

Expected: "700+ passed" (no regressions)

- [ ] **Step 7: Commit**

```bash
git add src/decision_system/workflow_engine/cli.py tests/test_workflow_engine/test_cli.py
git add src/decision_system/cli.py
git commit -m "feat(workflow): add CLI commands for workflow validate, run, list-nodes"
```

- [ ] **Step 8: Add tests for `workflow create` command**

Add to `tests/test_workflow_engine/test_cli.py`:

```python
    def test_create_workflow(self, runner):
        with tempfile.TemporaryDirectory() as td:
            output_path = Path(td) / "test_wf.json"
            result = runner.invoke(workflow_app, ["create", str(output_path)])
            assert result.exit_code == 0
            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert data["name"] == "untitled"
            assert len(data["nodes"]) == 1
            assert data["nodes"][0]["type"] == "decision_system.trigger_manual"

    def test_create_workflow_with_name(self, runner):
        with tempfile.TemporaryDirectory() as td:
            output_path = Path(td) / "named_wf.json"
            result = runner.invoke(workflow_app, [
                "create", str(output_path), "--name", "My Workflow",
            ])
            assert result.exit_code == 0
            data = json.loads(output_path.read_text())
            assert data["name"] == "My Workflow"
```

- [ ] **Step 9: Add tests for `workflow list` command**

Add to `tests/test_workflow_engine/test_cli.py`:

```python
    def test_workflow_list_empty(self, runner):
        """List with no store directory is handled gracefully."""
        result = runner.invoke(workflow_app, ["list"])
        assert result.exit_code == 0

    def test_workflow_list_with_saved(self, runner):
        """Save a workflow via API-equivalent, then list it."""
        from decision_system.workflow_engine.models import WorkflowDefinition
        from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore
        import tempfile
        from pathlib import Path

        tmp = Path(tempfile.mkdtemp())
        store = JSONWorkflowStore(tmp)
        wf = WorkflowDefinition(name="Listed Workflow")
        store.save(wf)

        result = runner.invoke(workflow_app, ["list", "--store-dir", str(tmp)])
        assert result.exit_code == 0
        assert "Listed Workflow" in result.stdout
```

- [ ] **Step 10: Add tests for `execution` commands**

Add to `tests/test_workflow_engine/test_cli.py`:

```python
    def test_execution_list(self, runner):
        result = runner.invoke(workflow_app, ["execution", "list"])
        assert result.exit_code == 0

    def test_execution_inspect_nonexistent(self, runner):
        result = runner.invoke(workflow_app, ["execution", "inspect", "nonexistent"])
        assert result.exit_code != 0
```

- [ ] **Step 11: Add `create`, `list`, and `execution` commands to CLI module**

Add these commands to `src/decision_system/workflow_engine/cli.py` (after the `run` command):

```python
@app.command()
def create(
    output_path: Path = typer.Argument(
        ..., help="Path to write the workflow template JSON",
    ),
    name: str = typer.Option("untitled", "--name", "-n", help="Workflow name"),
) -> None:
    """Generate a workflow template JSON file."""
    template = {
        "name": name,
        "description": "",
        "version": 1,
        "nodes": [
            {
                "id": "trigger_1",
                "type": "decision_system.trigger_manual",
                "label": "Manual Trigger",
                "config": {},
                "error_policy": "fail_workflow",
                "position_x": 100,
                "position_y": 100,
            },
            {
                "id": "node_1",
                "type": "decision_system.input_text",
                "label": "Input Text",
                "config": {"text": ""},
                "error_policy": "fail_workflow",
                "position_x": 300,
                "position_y": 100,
            },
        ],
        "connections": [
            {"source_node": "trigger_1", "source_output": "default",
             "target_node": "node_1", "target_input": "default"},
        ],
        "tags": [],
    }
    output_path.write_text(json.dumps(template, indent=2))
    console.print(f"[green]✓[/green] Created workflow template at {output_path}")


@app.command(name="list")
def list_workflows(
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """List saved workflow definitions."""
    from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore

    if store_dir:
        ws = JSONWorkflowStore(store_dir)
    else:
        import tempfile
        ws = JSONWorkflowStore(Path(tempfile.mkdtemp()))

    workflows = ws.list()
    if not workflows:
        console.print("No saved workflows found.")
        return

    table = Table(title=f"Saved Workflows ({len(workflows)})")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Nodes")
    table.add_column("Connections")

    for wf in workflows:
        table.add_row(
            wf.id[:8] + "...",
            wf.name,
            str(len(wf.nodes)),
            str(len(wf.connections)),
        )
    console.print(table)


# --- Execution sub-app ---

exec_app = typer.Typer(help="Inspect workflow executions.")


@exec_app.command(name="list")
def list_executions(
    workflow_id: str | None = typer.Option(
        None, "--workflow-id", "-w", help="Filter by workflow ID",
    ),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """List workflow executions."""
    from decision_system.workflow_engine.stores.json_store import JSONExecutionStore

    if store_dir:
        es = JSONExecutionStore(store_dir)
    else:
        import tempfile
        es = JSONExecutionStore(Path(tempfile.mkdtemp()))

    states = es.list(workflow_id=workflow_id)
    if not states:
        console.print("No executions found.")
        return

    table = Table(title=f"Executions ({len(states)})")
    table.add_column("Execution ID", style="cyan")
    table.add_column("Workflow ID")
    table.add_column("Status", style="green")
    table.add_column("Error")

    for s in states:
        eid = s.execution_id[:8] + "..."
        wid = s.workflow_id[:8] + "..."
        table.add_row(eid, wid, s.status, s.error or "")
    console.print(table)


@exec_app.command(name="inspect")
def inspect_execution(
    execution_id: str = typer.Argument(..., help="Execution ID to inspect"),
    store_dir: Path | None = typer.Option(
        None, "--store-dir", "-s",
        help="Store directory (default: temporary)",
    ),
) -> None:
    """Show detailed execution information."""
    from decision_system.workflow_engine.stores.json_store import JSONExecutionStore

    if store_dir:
        es = JSONExecutionStore(store_dir)
    else:
        import tempfile
        es = JSONExecutionStore(Path(tempfile.mkdtemp()))

    state = es.load(execution_id)
    if state is None:
        console.print(f"[red]Execution '{execution_id}' not found[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Execution:[/bold] {state.execution_id}")
    console.print(f"[bold]Workflow:[/bold] {state.workflow_id}")
    console.print(f"[bold]Status:[/bold] {state.status}")
    console.print(f"[bold]Error:[/bold] {state.error or 'None'}")

    if state.node_states:
        table = Table(title="Node States")
        table.add_column("Node ID")
        table.add_column("Status")
        table.add_column("Error")
        for ns in state.node_states.values():
            table.add_row(ns.node_id, ns.status, ns.error or "")
        console.print(table)


# Register the execution sub-app
app.add_typer(exec_app, name="execution", help="Inspect workflow executions.")
```

- [ ] **Step 12: Run tests to verify everything passes**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_cli.py -v
```

Expected: All tests PASS

- [ ] **Step 13: Verify existing 700+ tests still pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest -q --timeout=60 2>&1 | tail -5
```

Expected: "700+ passed"

- [ ] **Step 14: Commit**

```bash
git add src/decision_system/workflow_engine/cli.py tests/test_workflow_engine/test_cli.py
git commit -m "feat(workflow): add workflow create, list, and execution inspect CLI commands"
```

---

### Task 13: API Routes

**Files:**
- Create: `src/decision_system/workflow_engine/api.py`
- Modify: `src/decision_system/api/app.py` (register router)
- Create: `tests/test_workflow_engine/test_api.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workflow_engine/test_api.py`:

```python
"""Tests for workflow API routes."""

import pytest
from fastapi.testclient import TestClient

from decision_system.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWorkflowAPI:
    def test_list_node_types(self, client):
        response = client.get("/workflows/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        types = {t["type"] for t in data["node_types"]}
        assert "decision_system.trigger_manual" in types
        assert "decision_system.retrieve" in types

    def test_create_and_get_workflow(self, client):
        payload = {
            "name": "API Test Workflow",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
            ],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        assert create_resp.status_code == 200
        wf_id = create_resp.json()["id"]

        get_resp = client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "API Test Workflow"

    def test_list_workflows_empty(self, client):
        response = client.get("/workflows")
        assert response.status_code == 200
        assert "workflows" in response.json()

    def test_delete_workflow(self, client):
        payload = {
            "name": "Delete Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/workflows/{wf_id}")
        assert delete_resp.status_code == 200

        get_resp = client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 404

    def test_execute_workflow(self, client):
        payload = {
            "name": "Execute Test",
            "nodes": [{"id": "n1", "type": "decision_system.input_text"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        execute_resp = client.post(f"/workflows/{wf_id}/execute", json={"inputs": {"text": "hello"}})
        assert execute_resp.status_code == 200
        data = execute_resp.json()
        assert "execution_id" in data
        assert data["status"] == "completed"

    def test_get_execution_state(self, client):
        payload = {
            "name": "Exec State Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        exec_resp = client.post(f"/workflows/{wf_id}/execute")
        exec_id = exec_resp.json()["execution_id"]

        state_resp = client.get(f"/executions/{exec_id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["execution_id"] == exec_id

    def test_execute_nonexistent_workflow(self, client):
        response = client.post("/workflows/nonexistent/execute")
        assert response.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_api.py -v
```

Expected: ImportError for `api` module or 404 for routes

- [ ] **Step 3: Write the API module**

Create `src/decision_system/workflow_engine/api.py`:

```python
"""FastAPI router for workflow management and execution."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ExecutionState,
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


class ExecuteWorkflowResponse(BaseModel):
    execution_id: str
    status: str
    workflow_id: str


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
```

- [ ] **Step 4: Register the router in app.py**

Edit `src/decision_system/api/app.py` to add the workflow router.

Add the import at the top (around line 30):
```python
from decision_system.api import routes_workspaces
from decision_system.api import routes_enterprise
from decision_system.api import routes_observability
# ADD:
from decision_system.workflow_engine.api import router as routes_workflow
```

Add the include_router call (around line 72, after observability):
```python
    api.include_router(routes_observability.router)
    # ADD:
    api.include_router(routes_workflow)
```

- [ ] **Step 5: Run tests**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_api.py -v
```

Expected: All tests PASS

- [ ] **Step 6: Verify existing 700+ tests still pass**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest -q --timeout=120 2>&1 | tail -5
```

Expected: "700+ passed"

- [ ] **Step 7: Commit**

```bash
git add src/decision_system/workflow_engine/api.py tests/test_workflow_engine/test_api.py
git add src/decision_system/api/app.py
git commit -m "feat(workflow): add API routes for workflow CRUD and execution"
```

---

### Task 14: Integration Smoke Test (End-to-End)

**Files:**
- Create: `tests/test_workflow_engine/test_integration.py`

- [ ] **Step 1: Write the integration test**

Create `tests/test_workflow_engine/test_integration.py`:

```python
"""End-to-end integration tests for the workflow engine."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner

import pytest

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection, ExecutionContext,
)
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)


class TestEndToEnd:
    """Full integration: build workflow definition → execute → verify results."""

    @pytest.fixture
    def engine(self):
        registry = create_default_registry()
        tmp_dir = Path(tempfile.mkdtemp())
        ws = JSONWorkflowStore(tmp_dir)
        es = JSONExecutionStore(tmp_dir)
        return DAGEngine(registry=registry, workflow_store=ws, execution_store=es)

    def test_simple_text_input_workflow(self, engine):
        """A workflow with just one InputText node should return the configured text."""
        import asyncio

        wf = WorkflowDefinition(
            name="Simple Text",
            nodes=[
                NodeConfig(
                    id="input1",
                    type="decision_system.input_text",
                    config={"text": "What is our biggest risk?"},
                ),
            ],
            connections=[],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states["input1"].status == "completed"
        outputs = state.node_states["input1"].outputs or {}
        assert "What is our biggest risk?" in outputs.get("text", "")

    def test_two_node_chain(self, engine):
        """Input text → Filter: should pass through the text."""
        import asyncio

        wf = WorkflowDefinition(
            name="Chain Test",
            nodes=[
                NodeConfig(
                    id="input1",
                    type="decision_system.input_text",
                    config={"text": "active data"},
                ),
                NodeConfig(
                    id="filter1",
                    type="decision_system.filter",
                    config={"field": "text", "operator": "exists"},
                ),
            ],
            connections=[
                Connection(source_node="input1", target_node="filter1"),
            ],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states["filter1"].status == "completed"
        outputs = state.node_states["filter1"].outputs or {}
        assert outputs.get("passed") is True

    def test_code_node_transforms_data(self, engine):
        """Code node should transform inputs according to the inline script."""
        import asyncio

        wf = WorkflowDefinition(
            name="Code Transform",
            nodes=[
                NodeConfig(
                    id="code1",
                    type="decision_system.code",
                    config={"source": "output = {'doubled': inputs['value'] * 2, 'original': inputs['value']}"},
                ),
            ],
            connections=[],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 21}))
        assert state.status == "completed"
        outputs = state.node_states["code1"].outputs or {}
        assert outputs.get("doubled") == 42

    def test_workflow_is_persisted_after_execution(self, engine):
        """The execution should be saved to the store."""
        import asyncio

        wf = WorkflowDefinition(
            name="Persist Check",
            nodes=[
                NodeConfig(
                    id="t1",
                    type="decision_system.trigger_manual",
                ),
            ],
        )
        state = asyncio.run(engine.execute(wf))
        loaded = engine.execution_store.load(state.execution_id)
        assert loaded is not None
        assert loaded.status == "completed"

    def test_cli_list_nodes(self):
        """The CLI should list all 16 node types."""
        from decision_system.workflow_engine.cli import app as workflow_app

        runner = CliRunner()
        result = runner.invoke(workflow_app, ["list-nodes"])
        assert result.exit_code == 0
        assert "decision_system.trigger_manual" in result.stdout
        assert "16" in result.stdout  # Total count
```

- [ ] **Step 2: Run the integration test**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest tests/test_workflow_engine/test_integration.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Run the full test suite**

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System
python -m pytest -q 2>&1 | tail -10
```

Expected: All tests PASS (no regressions)

- [ ] **Step 4: Commit**

```bash
git add tests/test_workflow_engine/test_integration.py
git commit -m "feat(workflow): add end-to-end integration smoke tests"
```

---

## Completion Verification

After all tasks are complete, run:

```bash
cd /home/kali/Desktop/Agentic-Ai-Decision-System

# 1. All workflow engine tests
python -m pytest tests/test_workflow_engine/ -v

# 2. All existing tests (no regressions)
python -m pytest -q --timeout=120

# 3. CLI smoke test
python -m decision_system workflow list-nodes

# 4. API smoke test (start server, curl)
python -m decision_system serve-api &
sleep 2
curl -s http://127.0.0.1:8000/workflows/nodes | python -m json.tool | head -20
kill %1 2>/dev/null

# 5. Workflow definition + execute
echo '{"name":"smoke","nodes":[{"id":"n1","type":"decision_system.input_text","config":{"text":"Hello"}}],"connections":[]}' > /tmp/smoke_wf.json
python -m decision_system workflow validate /tmp/smoke_wf.json
python -m decision_system workflow run /tmp/smoke_wf.json
rm /tmp/smoke_wf.json
```
