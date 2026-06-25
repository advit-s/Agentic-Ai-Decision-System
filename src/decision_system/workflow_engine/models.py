"""Core models for the workflow engine."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr


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


class WorkflowVersion(BaseModel):
    """An immutable snapshot of a workflow definition at a point in time."""

    version_id: str
    workflow_id: str
    version_number: int
    definition: dict[str, Any]
    content_hash: str = ""
    change_summary: str = ""
    created_at: datetime | None = None
    created_by: str = "api"


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
    workspace_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NodeExecutionState(BaseModel):
    """Execution state for a single node."""

    node_id: str
    status: Literal["pending", "running", "completed", "failed", "skipped", "awaiting_review"] = (
        "pending"
    )
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
    workflow_version_id: str | None = None
    workspace_id: str | None = None
    status: Literal[
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
        "awaiting_review",
        "rejected",
    ] = "pending"
    node_states: dict[str, NodeExecutionState] = Field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    review_count: int = 0
    claim_count: int = 0
    node_count: int = 0
    completed_node_count: int = 0
    failed_node_count: int = 0
    duration_ms: float | None = None
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    # Review-gate pause/resume fields
    review_id: str | None = None
    paused_node_id: str | None = None
    pending_inputs: dict[str, Any] = Field(default_factory=dict)
    downstream_nodes_not_started: list[str] = Field(default_factory=list)
    review_instructions: str = ""
    review_created_at: datetime | None = None


class ExecutionContext(BaseModel):
    """Shared context passed to every node during execution."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    workflow_id: str
    execution_id: str
    schedule_id: str | None = None
    workspace_id: str | None = None
    provider: str = "fake"
    global_config: dict[str, Any] = Field(default_factory=dict)
    log: list[str] = Field(default_factory=list)

    _provider_store: Any = PrivateAttr(default=None)

    def resolve_provider(
        self,
        provider_name: str | None = None,
        model: str | None = None,
    ) -> tuple[Any, str] | None:
        """Resolve a provider config + model pair.

        Resolution order:
        1. Per-node override (provider_name + model)
        2. System default (first provider in the list)
        3. None → caller falls back to fake provider

        Returns ``(ProviderConfig, resolved_model)`` or ``None``.
        """
        store = self._provider_store
        if store is None:
            return None

        # 1. Try named provider override
        if provider_name:
            cfg = store.get(provider_name)
            if cfg is not None:
                return (cfg, model or cfg.default_model)

        # 2. Fall back to system default
        default = store.get_default()
        if default is not None:
            return (default, model or default.default_model)

        # 3. No providers configured at all
        return None


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

    model_config = ConfigDict(arbitrary_types_allowed=True)

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
