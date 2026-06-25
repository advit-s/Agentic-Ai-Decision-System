"""Tests for workflow engine core models."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.models import (
    Connection,
    ErrorPolicy,
    ExecutionContext,
    ExecutionState,
    NodeConfig,
    NodeExecutionState,
    NodeTypeInfo,
    RetryConfig,
    WorkflowDefinition,
    WorkflowNode,
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
            source_node="n1",
            source_output="verified",
            target_node="n2",
            target_input="claims",
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
            execution_id="e1",
            workflow_id="wf1",
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
                execution_id="e1",
                workflow_id="wf1",
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
