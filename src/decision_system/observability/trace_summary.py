"""Trace summary generation and storage."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from .models import TraceSummary
from .store import load_traces, save_trace


def create_trace(
    workflow_type: str,
    question: str,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    node_count: int = 0,
    nodes_executed: Optional[list[str]] = None,
    node_durations: Optional[dict[str, float]] = None,
    total_tokens: int = 0,
    error_count: int = 0,
    errors: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
    root: Optional[str] = None,
) -> TraceSummary:
    duration = 0.0
    if completed_at and started_at:
        duration = (completed_at - started_at).total_seconds()
    trace = TraceSummary(
        workflow_type=workflow_type,
        question=question,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
        node_count=node_count,
        nodes_executed=nodes_executed or [],
        node_durations=node_durations or {},
        total_tokens=total_tokens,
        error_count=error_count,
        errors=errors or [],
        metadata=metadata or {},
    )
    save_trace(trace, root)
    return trace


def get_recent_traces(limit: int = 10, root: Optional[str] = None) -> list[TraceSummary]:
    return load_traces(root)[:limit]
