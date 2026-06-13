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
        """n1 -> n2 (x3), n1 -> n3 (+1), n2/n3 -> n4.
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


# ─── Schedule-Aware Execution Tests ──────────────────────────────────────────

class TestScheduleAwareExecution:
    """DAGEngine passes schedule_id through to node ExecutionContext."""

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

    def test_execute_with_schedule_id(self, engine):
        """schedule_id appears in the node's ExecutionContext."""
        received_schedule_ids: list[str | None] = []

        class CaptureScheduleNode(WorkflowNode):
            type: str = "test.capture_schedule"
            label: str = "Capture"

            async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
                received_schedule_ids.append(ctx.schedule_id)
                return {"captured": True}

            @classmethod
            def get_config_schema(cls) -> dict:
                return {"type": "object", "properties": {}}
            @classmethod
            def get_input_schema(cls) -> dict:
                return {"type": "object", "properties": {}}
            @classmethod
            def get_output_schema(cls) -> dict:
                return {"type": "object", "properties": {"captured": {"type": "boolean"}}}

        engine.registry.register(CaptureScheduleNode)

        wf = WorkflowDefinition(
            name="schedule-test",
            nodes=[NodeConfig(id="n1", type="test.capture_schedule")],
        )
        asyncio.run(engine.execute(wf, schedule_id="sch-test-123"))
        assert received_schedule_ids == ["sch-test-123"]

    def test_execute_without_schedule_id(self, engine):
        """schedule_id is None for manual execution."""
        received_schedule_ids: list[str | None] = []

        class CaptureScheduleNode(WorkflowNode):
            type: str = "test.capture_schedule2"
            label: str = "Capture2"

            async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
                received_schedule_ids.append(ctx.schedule_id)
                return {"captured": True}

            @classmethod
            def get_config_schema(cls) -> dict:
                return {"type": "object", "properties": {}}
            @classmethod
            def get_input_schema(cls) -> dict:
                return {"type": "object", "properties": {}}
            @classmethod
            def get_output_schema(cls) -> dict:
                return {"type": "object", "properties": {"captured": {"type": "boolean"}}}

        engine.registry.register(CaptureScheduleNode)

        wf = WorkflowDefinition(
            name="manual-test",
            nodes=[NodeConfig(id="n1", type="test.capture_schedule2")],
        )
        asyncio.run(engine.execute(wf))
        assert received_schedule_ids == [None]
