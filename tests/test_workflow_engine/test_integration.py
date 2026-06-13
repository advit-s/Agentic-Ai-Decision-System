"""End-to-end integration tests for the workflow engine."""

import tempfile
from pathlib import Path
from typer.testing import CliRunner

import pytest

from decision_system.workflow_engine.models import (
    WorkflowDefinition, NodeConfig, Connection,
)
from decision_system.workflow_engine.engine.executor import DAGEngine
from decision_system.workflow_engine.nodes import create_default_registry
from decision_system.workflow_engine.stores.json_store import (
    JSONWorkflowStore, JSONExecutionStore,
)


class TestEndToEnd:
    """Full integration: build workflow definition -> execute -> verify results."""

    @pytest.fixture
    def engine(self):
        registry = create_default_registry()
        tmp_dir = Path(tempfile.mkdtemp())
        ws = JSONWorkflowStore(tmp_dir)
        es = JSONExecutionStore(tmp_dir)
        return DAGEngine(registry=registry, workflow_store=ws, execution_store=es)

    def test_simple_text_input_workflow(self, engine):
        """A workflow with just one InputText node should return the configured text."""
        import asyncio

        wf = WorkflowDefinition(
            name="Simple Text",
            nodes=[
                NodeConfig(
                    id="input1",
                    type="decision_system.input_text",
                    config={"text": "What is our biggest risk?"},
                ),
            ],
            connections=[],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states["input1"].status == "completed"
        outputs = state.node_states["input1"].outputs or {}
        assert "What is our biggest risk?" in outputs.get("text", "")

    def test_two_node_chain(self, engine):
        """Input text -> Filter: should pass through the text."""
        import asyncio

        wf = WorkflowDefinition(
            name="Chain Test",
            nodes=[
                NodeConfig(
                    id="input1",
                    type="decision_system.input_text",
                    config={"text": "active data"},
                ),
                NodeConfig(
                    id="filter1",
                    type="decision_system.filter",
                    config={"field": "text", "operator": "exists"},
                ),
            ],
            connections=[
                Connection(source_node="input1", target_node="filter1"),
            ],
        )
        state = asyncio.run(engine.execute(wf))
        assert state.status == "completed"
        assert state.node_states["filter1"].status == "completed"
        outputs = state.node_states["filter1"].outputs or {}
        assert outputs.get("passed") is True

    def test_code_node_transforms_data(self, engine):
        """Code node should transform inputs according to the inline script."""
        import asyncio

        wf = WorkflowDefinition(
            name="Code Transform",
            nodes=[
                NodeConfig(
                    id="code1",
                    type="decision_system.code",
                    config={"source": "output = {'doubled': inputs['value'] * 2, 'original': inputs['value']}"},
                ),
            ],
            connections=[],
        )
        state = asyncio.run(engine.execute(wf, global_inputs={"value": 21}))
        assert state.status == "completed"
        outputs = state.node_states["code1"].outputs or {}
        assert outputs.get("doubled") == 42

    def test_workflow_is_persisted_after_execution(self, engine):
        """The execution should be saved to the store."""
        import asyncio

        wf = WorkflowDefinition(
            name="Persist Check",
            nodes=[
                NodeConfig(
                    id="t1",
                    type="decision_system.trigger_manual",
                ),
            ],
        )
        state = asyncio.run(engine.execute(wf))
        loaded = engine.execution_store.load(state.execution_id)
        assert loaded is not None
        assert loaded.status == "completed"

    def test_cli_list_nodes(self):
        """The CLI should list all 19 node types."""
        from decision_system.workflow_engine.cli import app as workflow_app

        runner = CliRunner()
        result = runner.invoke(workflow_app, ["list-nodes"])
        assert result.exit_code == 0
        assert "Manual Trigger" in result.stdout
        assert "Run War Room" in result.stdout
        assert "Available Nodes (19)" in result.stdout
