# Phase 1: Workflow Node Engine + DAG Runtime Design

## Overview

Transform the Agentic AI Decision System from a CLI/backend prototype into an n8n-level
visual workflow automation platform. This spec covers **Phase 1 only**: the core node
abstraction, DAG execution engine, node registry, built-in node types (wrapping existing
capabilities), stores, CLI commands, and API endpoints.

Phase 1 adds the `decision_system.workflow_engine` package. Everything existing (50 CLI
commands, LangGraph workflow, FastAPI API, web UI, 700+ tests) continues to work
unchanged.

## Core Data Models

### WorkflowNode (Abstract Base Class)

```python
class WorkflowNode(ABC):
    """Base class for all node types in the system."""

    type: str                    # e.g. "decision_system.retrieve"
    label: str                   # User-visible name, e.g. "Retrieve Evidence"
    config: dict                 # Node-specific configuration
    inputs: list[Connection]     # Upstream connections feeding this node
    outputs: list[Connection]    # Where this node's outputs go

    @abstractmethod
    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        """Execute the node's logic. Returns output dict."""

    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> dict:
        """JSON Schema for config. Enables auto-generated config panels in Phase 2."""

    @classmethod
    @abstractmethod
    def get_input_schema(cls) -> dict:
        """JSON Schema for expected inputs (named ports)."""

    @classmethod
    @abstractmethod
    def get_output_schema(cls) -> dict:
        """JSON Schema for produced outputs (named ports)."""
```

### WorkflowDefinition

```python
class WorkflowDefinition(BaseModel):
    version: int = 1
    id: str                                    # UUID
    name: str                                  # "Quarterly Risk Review"
    description: str = ""
    nodes: list[NodeConfig]                    # Type reference + config
    connections: list[Connection]              # DAG edges
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime

class Connection(BaseModel):
    source_node: str                           # node_id
    source_output: str = "default"             # named output port
    target_node: str                           # node_id
    target_input: str = "default"              # named input port
```

### ExecutionState

```python
class ExecutionState(BaseModel):
    execution_id: str
    workflow_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    node_states: dict[str, NodeExecutionState]
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None

class NodeExecutionState(BaseModel):
    node_id: str
    status: Literal["pending", "running", "completed", "failed", "skipped"]
    inputs: dict | None
    outputs: dict | None
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
```

### ExecutionEvent (Streaming)

```python
class ExecutionEvent(BaseModel):
    execution_id: str
    event_type: Literal[
        "node_started", "node_completed", "node_failed",
        "workflow_completed", "workflow_failed", "log"
    ]
    node_id: str | None
    data: dict
    timestamp: datetime
```

### Error Handling

```python
class ErrorPolicy(str, Enum):
    FAIL_WORKFLOW = "fail_workflow"   # Stop everything (default)
    FAIL_NODE = "fail_node"           # Mark node failed, continue DAG
    RETRY = "retry"                   # Retry N times with backoff
    SKIP = "skip"                     # Skip and continue

class RetryConfig(BaseModel):
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60       # seconds
    backoff_multiplier: float = 2.0
    retryable_errors: list[str] = ["Timeout", "RateLimit"]
```

## Execution Engine

### DAGEngine

The DAGEngine is the main runtime. Execution flow:

1. **Validate** — Check for cycles, missing connections, schema compatibility
2. **Topo-sort** — Produce ordered layers (independent nodes in same layer)
3. **Execute layers** — For each layer: `asyncio.gather(*nodes)` for concurrent execution
4. **Per-node** — Resolve type from NodeRegistry → collect upstream outputs → create ExecutionContext → call `node.execute()`
5. **Stream events** — Emit ExecutionEvent per state change
6. **Error handling** — Apply per-node ErrorPolicy on failure
7. **Finalize** — Set final status, persist, return

### Node Registry

```python
class NodeRegistry:
    """Thread-safe registry of all known node types."""

    def register(self, node_cls: type[WorkflowNode]) -> None: ...
    def get(self, node_type: str) -> type[WorkflowNode]: ...
    def list_types(self) -> list[NodeTypeInfo]: ...
    def discover_entry_points(self) -> list[type[WorkflowNode]]: ...
```

Node types are registered via:
- Explicit `registry.register()` calls
- Python entry points (`decision_system.nodes` group) for future plugin discovery
- Built-in nodes auto-register on package import

### Stores

```python
class WorkflowStore(ABC):
    async def save(self, workflow: WorkflowDefinition) -> None: ...
    async def load(self, workflow_id: str) -> WorkflowDefinition: ...
    async def list(self) -> list[WorkflowDefinition]: ...
    async def delete(self, workflow_id: str) -> None: ...

class ExecutionStore(ABC):
    async def save(self, state: ExecutionState) -> None: ...
    async def load(self, execution_id: str) -> ExecutionState: ...
    async def list(self, workflow_id: str) -> list[ExecutionState]: ...
```

Initial implementation: `JSONWorkflowStore` and `JSONExecutionStore` writing to
`.decision_system/workflows/` and `.decision_system/executions/`.

## Built-in Node Types

Each node wraps an existing capability. All use the fake provider by default.

| Node Type | Wraps | Config |
|-----------|-------|--------|
| `decision_system.trigger_manual` | N/A (no-op trigger) | None |
| `decision_system.retrieve` | `rag/retriever.py` | collection name, top-k, score-threshold |
| `decision_system.technical_analyst` | `agents/technical_analyst.py` | provider, model |
| `decision_system.risk_analyst` | `agents/risk_analyst.py` | provider, model |
| `decision_system.extract_claims` | `ledger/claim_ledger.py` | supported types |
| `decision_system.verify_claims` | `ledger/verifier.py` | None |
| `decision_system.write_report` | `reports/report.py` | format (markdown, json) |
| `decision_system.extract_graph` | `graphing/extractor.py` | None |
| `decision_system.profile_data` | `data_catalog/profiler.py` | catalog path |
| `decision_system.map_ontology` | `ontology/mapper.py` | concepts list |
| `decision_system.detect_patterns` | `insights/detector.py` | severity threshold |
| `decision_system.run_war_room` | `war_room/run.py` | question, roles |
| `decision_system.input_text` | Input node | prompt text |
| `decision_system.filter` | Passthrough with condition | filter expression |
| `decision_system.code` | Executes Python snippet | source code |
| `decision_system.merge` | Merges multiple inputs | merge strategy |

## Integration Points

### CLI

```
decision-system workflow create my-workflow.json   # Create workflow from template
decision-system workflow validate my-workflow.json  # Validate DAG
decision-system workflow run my-workflow.json       # Execute workflow
decision-system workflow run my-workflow.json --watch  # Execute with live output
decision-system workflow list                        # List saved workflows
decision-system execution list                       # List executions
decision-system execution inspect <id>               # Show execution details
```

### API

```
POST   /workflows                 → Create workflow
GET    /workflows                 → List workflows
GET    /workflows/:id             → Get workflow
PUT    /workflows/:id             → Update workflow
DELETE /workflows/:id             → Delete workflow
POST   /workflows/:id/execute     → Execute workflow
GET    /executions/:id            → Get execution state
WS     /executions/:id/stream     → Live execution events (Phase 2)
GET    /workflows/nodes           → List available node types + their schemas
```

### Web UI

A new `/workflows` section is added to the web UI in Phase 2. Phase 1
delivers the API endpoints that Phase 2 will call.

## Backward Compatibility

All existing functionality is preserved:

- 50 CLI commands (`index`, `ask`, `extract-graph`, etc.) — unchanged
- LangGraph linear workflow — unchanged
- FastAPI v0.8 routes — unchanged
- Web UI v1.7 sections — unchanged
- 700+ tests — all pass without API keys

The `workflow_engine` package is purely additive. The existing `ask` command
continues to produce decision reports via the LangGraph workflow. The new
`workflow run` command adds DAG-based execution alongside it.

## Package Structure

```
src/decision_system/
  workflow_engine/
    __init__.py
    models.py                # WorkflowNode, WorkflowDefinition, ExecutionState, etc.
    nodes/
      __init__.py
      base.py                # WorkflowNode ABC
      registry.py            # NodeRegistry
      builtin/               # ~15 node types wrapping existing capabilities
        __init__.py
        trigger_nodes.py     # Manual trigger, input_text
        decision_nodes.py    # Retrieve, Tech/risk analyst, claims, report
        data_nodes.py        # Profile, graph, ontology, patterns, war room
        flow_nodes.py        # Filter, merge, code
    engine/
      __init__.py
      dag.py                 # DAGValidator, TopologicalSort
      executor.py            # DAGEngine — main execution loop
      events.py              # ExecutionEvent models
    stores/
      __init__.py
      base.py                # Store ABCs
      json_store.py          # JSON file implementations
    cli.py                   # workflow/execution CLI commands
    api.py                   # workflow API routes
    tests/
      test_models.py
      test_dag.py
      test_executor.py
      test_nodes.py
      test_stores.py
      test_cli.py
      test_api.py
```

## Testing

- Unit tests for each node type in isolation (mock existing services)
- Unit tests for DAG validation (cyclic graphs, missing connections)
- Unit tests for topo-sort (independent nodes, dependent chains, complex DAGs)
- Unit tests for error handling (retry, fail, skip)
- Integration tests for multi-node workflows using fake provider
- All tests pass with no API key required
- Existing 700+ tests remain passing

## Future Phases (Not in Scope)

| Phase | Focus | Depends On |
|-------|-------|------------|
| **Phase 2** | Visual drag-and-drop workflow builder (React Flow) | Phase 1 |
| **Phase 3** | Node SDK, plugin entry points, credential management, triggers | Phase 1 |
| **Phase 4** | Auth, RBAC, multi-tenant, execution history viewer, templates | Phase 1-3 |

## Key Design Decisions

1. **Named ports** — Nodes declare named input/output ports (not positional). Enables
   multiple typed output channels from one node (e.g. verified vs contradicted claims).
2. **JSON Schema config** — Each node declares its config schema via Pydantic. Phase 2's
   config panel auto-renders from schema — no manual UI code per node.
3. **Async execution** — LLM calls, file I/O, API calls are async. DAG engine fans out
   parallel branches via `asyncio.gather`.
4. **JSON persistence initially** — Matches existing `.decision_system/` pattern.
   SQLite can be swapped in for execution history in Phase 4.
5. **Additive, not replacement** — Existing LangGraph workflow stays. Node engine is
   alongside it. Migration is organic, not forced.
