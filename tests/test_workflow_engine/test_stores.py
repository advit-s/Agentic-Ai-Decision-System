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


class TestJSONVersionStore:
    """Tests for JSONVersionStore."""

    @pytest.fixture
    def store(self, tmp_path):
        from decision_system.workflow_engine.stores.version_store import JSONVersionStore
        return JSONVersionStore(tmp_path)

    def test_create_and_load_version(self, store):
        """Creating a version returns it and it can be loaded."""
        definition = {"name": "test", "nodes": []}
        v = store.create_version("wf-1", definition, change_summary="Initial")
        assert v.workflow_id == "wf-1"
        assert v.version_number == 1
        assert v.change_summary == "Initial"

        loaded = store.load_version("wf-1", 1)
        assert loaded is not None
        assert loaded.version_id == v.version_id
        assert loaded.definition == definition

    def test_auto_increment_version_number(self, store):
        """Creating multiple versions auto-increments the version number."""
        store.create_version("wf-2", {"v": 1})
        store.create_version("wf-2", {"v": 2})
        store.create_version("wf-2", {"v": 3})

        v3 = store.load_version("wf-2", 3)
        assert v3 is not None
        assert v3.version_number == 3
        assert v3.definition == {"v": 3}

    def test_list_versions_newest_first(self, store):
        """list_versions returns versions sorted newest first."""
        store.create_version("wf-3", {"v": 1})
        store.create_version("wf-3", {"v": 2})
        store.create_version("wf-3", {"v": 3})

        versions = store.list_versions("wf-3")
        assert len(versions) == 3
        assert versions[0].version_number == 3
        assert versions[1].version_number == 2
        assert versions[2].version_number == 1

    def test_load_nonexistent_version(self, store):
        """Loading a nonexistent version returns None."""
        v = store.load_version("nonexistent", 99)
        assert v is None

    def test_load_version_by_id(self, store):
        """Loading a version by its UUID works across workflows."""
        v1 = store.create_version("wf-a", {"data": "a"})
        v2 = store.create_version("wf-b", {"data": "b"})

        loaded = store.load_version_by_id(v1.version_id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-a"

        loaded = store.load_version_by_id(v2.version_id)
        assert loaded is not None
        assert loaded.workflow_id == "wf-b"

    def test_load_version_by_id_nonexistent(self, store):
        """Loading a nonexistent version UUID returns None."""
        loaded = store.load_version_by_id("nonexistent-id")
        assert loaded is None

    def test_get_latest_version_number(self, store):
        """get_latest_version_number returns the highest version number."""
        assert store.get_latest_version_number("wf-x") == 0
        store.create_version("wf-x", {"v": 1})
        assert store.get_latest_version_number("wf-x") == 1
        store.create_version("wf-x", {"v": 2})
        assert store.get_latest_version_number("wf-x") == 2

    def test_version_has_content_hash(self, store):
        """Each version has a content hash based on the definition."""
        v = store.create_version("wf-hash", {"name": "test"})
        assert v.content_hash
        assert len(v.content_hash) == 16
