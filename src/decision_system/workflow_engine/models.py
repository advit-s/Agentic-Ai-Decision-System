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


class RetryConfig(BaseModel):
    """Retry configuration for node execution."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retryable_errors: list[str] = Field(default_factory=lambda: ["Timeout", "RateLimit"])


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
