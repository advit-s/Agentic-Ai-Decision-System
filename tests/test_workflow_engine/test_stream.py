"""Tests for the execution event stream / WebSocket module."""

from __future__ import annotations

import asyncio

import pytest

from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.stream import (
    ExecutionEventStream,
    cleanup_queue,
    emit_event,
    get_execution_queue,
)


@pytest.mark.asyncio
async def test_get_execution_queue_creates_queue() -> None:
    queue = get_execution_queue("test-exec-1")
    assert queue is not None


@pytest.mark.asyncio
async def test_emit_event_puts_into_queue() -> None:
    exec_id = "test-exec-2"
    queue = get_execution_queue(exec_id)
    event = ExecutionEvent(
        execution_id=exec_id,
        event_type="node_started",
        node_id="n1",
        data={},
    )
    emit_event(event)
    result = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert result["event_type"] == "node_started"
    assert result["node_id"] == "n1"
    cleanup_queue(exec_id)


@pytest.mark.asyncio
async def test_event_stream_yields_events() -> None:
    exec_id = "test-exec-3"
    stream = ExecutionEventStream(exec_id)

    # Emit a couple events
    emit_event(
        ExecutionEvent(
            execution_id=exec_id,
            event_type="node_started",
            node_id="n1",
            data={},
        )
    )
    emit_event(
        ExecutionEvent(
            execution_id=exec_id,
            event_type="node_completed",
            node_id="n1",
            data={"outputs": {}},
        )
    )
    emit_event(
        ExecutionEvent(
            execution_id=exec_id,
            event_type="workflow_completed",
            node_id=None,
            data={"status": "completed"},
        )
    )

    events = []
    async for event in stream:
        events.append(event)
        if event["event_type"] in ("workflow_completed", "workflow_failed"):
            break

    assert len(events) >= 2
    assert events[0]["event_type"] == "node_started"
    cleanup_queue(exec_id)


@pytest.mark.asyncio
async def test_cleanup_queue_removes_queue() -> None:
    exec_id = "test-exec-4"
    get_execution_queue(exec_id)
    assert exec_id in stream_module._execution_queues
    cleanup_queue(exec_id)
    assert exec_id not in stream_module._execution_queues


@pytest.mark.asyncio
async def test_stream_heartbeat_on_timeout() -> None:
    exec_id = "test-exec-5"
    stream = ExecutionEventStream(exec_id, timeout=0.1)

    events = []
    async for event in stream:
        events.append(event)
        if len(events) >= 2:
            break

    # First event should be a heartbeat (no events emitted)
    assert events[0]["event_type"] == "heartbeat"
    cleanup_queue(exec_id)


# Need to import the module-level dict for the cleanup test
from decision_system.workflow_engine import stream as stream_module
