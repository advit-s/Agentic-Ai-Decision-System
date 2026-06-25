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
        assert "Available Nodes (37)" in result.stdout
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


class TestScheduleCLI:
    """Tests for schedule CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def saved_schedule_id(self):
        """Create a workflow + schedule in a temp dir, return (schedule_id, store_dir)."""
        from decision_system.workflow_engine.models import WorkflowDefinition
        from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore
        from decision_system.workflow_engine.scheduler import ScheduleDefinition, ScheduleStore, TriggerType
        from uuid import uuid4

        store_dir = Path(tempfile.mkdtemp())

        # Save a workflow
        ws = JSONWorkflowStore(store_dir)
        wf = WorkflowDefinition(name="Scheduled WF")
        ws.save(wf)

        # Save a schedule
        ss = ScheduleStore(store_dir)
        schedule = ScheduleDefinition(
            id=f"sch-{uuid4().hex[:12]}",
            workflow_id=wf.id,
            trigger_type=TriggerType.CRON,
            trigger_config={"expression": "0 9 * * 1"},
        )
        ss.save(schedule)

        yield schedule.id, str(store_dir)

    def test_schedule_list_empty(self, runner):
        result = runner.invoke(workflow_app, ["schedule", "list"])
        assert result.exit_code == 0

    def test_schedule_list_with_schedules(self, runner, saved_schedule_id):
        sch_id, store_dir = saved_schedule_id
        result = runner.invoke(workflow_app, ["schedule", "list", "--store-dir", store_dir])
        assert result.exit_code == 0
        assert sch_id[:12] in result.stdout.replace("...", "")

    def test_schedule_list_filtered(self, runner, saved_schedule_id):
        sch_id, store_dir = saved_schedule_id
        result = runner.invoke(workflow_app, [
            "schedule", "list", "--store-dir", store_dir,
            "--workflow-id", "nonexistent",
        ])
        assert result.exit_code == 0
        assert "No schedules found" in result.stdout

    def test_schedule_create(self, runner):
        from decision_system.workflow_engine.models import WorkflowDefinition
        from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore

        store_dir = Path(tempfile.mkdtemp())
        ws = JSONWorkflowStore(store_dir)
        wf = WorkflowDefinition(name="CLI Sched WF")
        ws.save(wf)

        result = runner.invoke(workflow_app, [
            "schedule", "create", wf.id,
            "--store-dir", str(store_dir),
            "--trigger-type", "cron",
            "--config", '{"expression": "0 12 * * *"}',
        ])
        assert result.exit_code == 0
        assert "Created schedule" in result.stdout
        assert "cron" in result.stdout

    def test_schedule_create_nonexistent_workflow(self, runner):
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(workflow_app, [
                "schedule", "create", "nonexistent",
                "--store-dir", td,
            ])
            assert result.exit_code != 0
            assert "not found" in result.stdout

    def test_schedule_delete(self, runner, saved_schedule_id):
        sch_id, store_dir = saved_schedule_id
        result = runner.invoke(workflow_app, [
            "schedule", "delete", sch_id,
            "--store-dir", store_dir,
        ])
        assert result.exit_code == 0
        assert "Deleted" in result.stdout

    def test_schedule_delete_nonexistent(self, runner):
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(workflow_app, [
                "schedule", "delete", "nonexistent",
                "--store-dir", td,
            ])
            assert result.exit_code != 0

    def test_schedule_toggle(self, runner, saved_schedule_id):
        sch_id, store_dir = saved_schedule_id
        result = runner.invoke(workflow_app, [
            "schedule", "toggle", sch_id,
            "--store-dir", store_dir,
        ])
        assert result.exit_code == 0
        assert "disabled" in result.stdout

        # Toggle back
        result = runner.invoke(workflow_app, [
            "schedule", "toggle", sch_id,
            "--store-dir", store_dir,
        ])
        assert result.exit_code == 0
        assert "enabled" in result.stdout

    def test_schedule_toggle_nonexistent(self, runner):
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(workflow_app, [
                "schedule", "toggle", "nonexistent",
                "--store-dir", td,
            ])
            assert result.exit_code != 0
