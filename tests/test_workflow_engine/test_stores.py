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
