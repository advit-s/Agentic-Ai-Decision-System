"""Execution event streaming — bridges DAGEngine events to WebSocket consumers.

Uses an in-memory dict of asyncio.Queue objects, one per execution ID.
The DAGEngine's on_event handler calls emit_event(), which puts the event
into the execution's queue. The WebSocket endpoint reads from the queue
via ExecutionEventStream.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from decision_system.workflow_engine.engine.events import ExecutionEvent

# In-memory event queues: execution_id -> asyncio.Queue
_execution_queues: dict[str, asyncio.Queue] = {}


def get_execution_queue(execution_id: str) -> asyncio.Queue:
    """Get or create an event queue for the given execution ID."""
    if execution_id not in _execution_queues:
        _execution_queues[execution_id] = asyncio.Queue()
    return _execution_queues[execution_id]


def emit_event(event: ExecutionEvent) -> None:
    """Emit an event into the execution's queue (non-blocking).

    Called by DAGEngine's on_event handler.
    """
    queue = _execution_queues.get(event.execution_id)
    if queue is not None:
        queue.put_nowait(event.model_dump(mode="json"))


def cleanup_queue(execution_id: str) -> None:
    """Remove an execution's queue after the stream ends."""
    _execution_queues.pop(execution_id, None)


class ExecutionEventStream:
    """Async iterator that yields events for a given execution.

    Stops yielding when a terminal event (workflow_completed,
    workflow_failed) is received.
    """

    def __init__(self, execution_id: str, timeout: float = 1.0) -> None:
        self.execution_id = execution_id
        self.queue = get_execution_queue(execution_id)
        self.timeout = timeout

    def __aiter__(self) -> AsyncIterator[dict]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
                    yield event
                    if event.get("event_type") in (
                        "workflow_completed",
                        "workflow_failed",
                    ):
                        return
                except asyncio.TimeoutError:
                    # No event yet — yield a heartbeat so WS doesn't timeout
                    yield {
                        "event_type": "heartbeat",
                        "execution_id": self.execution_id,
                        "data": {},
                    }
        finally:
            cleanup_queue(self.execution_id)
