"""Tests for workflow CLI commands."""

import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner

import pytest

from decision_system.workflow_engine.cli import app as workflow_app


class TestWorkflowCLI:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def sample_workflow_path(self):
        """Create a simple valid workflow JSON file."""
        wf = {
            "name": "Test CLI Workflow",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual", "label": "Start"},
            ],
            "connections": [],
            "version": 1,
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(wf, f)
            path_str = f.name
        result = Path(path_str)
        yield result
        result.unlink(missing_ok=True)

    def test_validate_valid_workflow(self, runner, sample_workflow_path):
        result = runner.invoke(workflow_app, ["validate", str(sample_workflow_path)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_validate_invalid_json(self, runner):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json")
            path = f.name
        result = runner.invoke(workflow_app, ["validate", path])
        assert result.exit_code != 0
        Path(path).unlink(missing_ok=True)

    def test_list_nodes(self, runner):
        result = runner.invoke(workflow_app, ["list-nodes"])
        assert result.exit_code == 0
        assert "Available Nodes (16)" in result.stdout
        assert "Manual Trigger" in result.stdout

    def test_help(self, runner):
        result = runner.invoke(workflow_app, ["--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout
        assert "list-nodes" in result.stdout

    def test_create_workflow(self, runner):
        with tempfile.TemporaryDirectory() as td:
            output_path = Path(td) / "test_wf.json"
            result = runner.invoke(workflow_app, ["create", str(output_path)])
            assert result.exit_code == 0
            assert output_path.exists()
            data = json.loads(output_path.read_text())
            assert data["name"] == "untitled"
            assert len(data["nodes"]) == 2
            assert data["nodes"][0]["type"] == "decision_system.trigger_manual"

    def test_create_workflow_with_name(self, runner):
        with tempfile.TemporaryDirectory() as td:
            output_path = Path(td) / "named_wf.json"
            result = runner.invoke(workflow_app, [
                "create", str(output_path), "--name", "My Workflow",
            ])
            assert result.exit_code == 0
            data = json.loads(output_path.read_text())
            assert data["name"] == "My Workflow"

    def test_workflow_list_empty(self, runner):
        """List with no store directory is handled gracefully."""
        result = runner.invoke(workflow_app, ["list"])
        assert result.exit_code == 0

    def test_workflow_list_with_saved(self, runner):
        """Save a workflow via API-equivalent, then list it."""
        from decision_system.workflow_engine.models import WorkflowDefinition
        from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore

        tmp = Path(tempfile.mkdtemp())
        store = JSONWorkflowStore(tmp)
        wf = WorkflowDefinition(name="Listed Workflow")
        store.save(wf)

        result = runner.invoke(workflow_app, ["list", "--store-dir", str(tmp)])
        assert result.exit_code == 0
        assert "Listed Workflow" in result.stdout

    def test_execution_list(self, runner):
        result = runner.invoke(workflow_app, ["execution", "list"])
        assert result.exit_code == 0

    def test_execution_inspect_nonexistent(self, runner):
        result = runner.invoke(workflow_app, ["execution", "inspect", "nonexistent"])
        assert result.exit_code != 0
