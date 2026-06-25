"""Execution event models for streaming workflow progress."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ExecutionEvent(BaseModel):
    """A single event emitted during workflow execution."""

    execution_id: str
    event_type: Literal[
        "node_started",
        "node_completed",
        "node_failed",
        "workflow_completed",
        "workflow_failed",
        "workflow_paused",
        "workflow_resumed",
        "workflow_rejected",
        "workflow_started",
        "log",
    ]
    node_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
