"""End-to-end integration tests for the Phase 4 scheduling system.

Exercises the full pipeline: API CRUD, auto-scheduling on workflow save,
webhook receiver, CLI commands, and scheduler lifecycle.
"""

import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from decision_system.workflow_engine.cli import app as workflow_cli
from decision_system.workflow_engine.models import WorkflowDefinition
from decision_system.workflow_engine.stores.json_store import JSONWorkflowStore


@pytest.fixture()
def async_client():
    """Create an async HTTP client for API tests."""
    import httpx
    from httpx import ASGITransport

    from decision_system.api.app import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return client


class TestScheduleIntegration:
    """Full pipeline integration tests for scheduling."""

    # ── API Integration ─────────────────────────────────────────────────

    async def test_api_full_lifecycle(self, async_client):
        """API: create workflow -> auto-schedule -> list -> toggle -> delete."""
        # Create a workflow with a cron trigger node
        wf_resp = await async_client.post(
            "/workflows",
            json={
                "name": "Integration WF",
                "nodes": [
                    {
                        "id": "trigger1",
                        "type": "decision_system.trigger_cron",
                        "config": {"expression": "0 9 * * 1"},
                    }
                ],
            },
        )
        assert wf_resp.status_code == 200
        wf_id = wf_resp.json()["id"]

        # Verify auto-schedule
        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        schedules = sched_resp.json()["schedules"]
        assert len(schedules) == 1
        s = schedules[0]
        assert s["trigger_type"] == "cron"
        assert s["trigger_config"]["expression"] == "0 9 * * 1"
        assert s["enabled"] is True

        # Toggle schedule
        toggle_resp = await async_client.post(f"/schedules/{s['id']}/toggle")
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled"] is False

        # Toggle back
        toggle_resp = await async_client.post(f"/schedules/{s['id']}/toggle")
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled"] is True

        # Update schedule config
        update_resp = await async_client.put(
            f"/schedules/{s['id']}",
            json={
                "trigger_config": {"expression": "0 12 * * *", "_node_id": "trigger1"},
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["trigger_config"]["expression"] == "0 12 * * *"

        # Delete schedule
        del_resp = await async_client.delete(f"/schedules/{s['id']}")
        assert del_resp.status_code == 200

        get_resp = await async_client.get(f"/schedules/{s['id']}")
        assert get_resp.status_code == 404

    async def test_auto_schedule_updates_on_workflow_change(self, async_client):
        """API: updating a workflow syncs schedules (create + remove)."""
        # Create a workflow with a manual trigger (no auto-schedule)
        wf_resp = await async_client.post(
            "/workflows",
            json={
                "name": "Auto Sync WF",
                "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            },
        )
        assert wf_resp.status_code == 200
        wf_id = wf_resp.json()["id"]

        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 0

        # Update: add a cron trigger node
        wf_resp = await async_client.put(
            f"/workflows/{wf_id}",
            json={
                "name": "Auto Sync WF",
                "nodes": [
                    {"id": "n1", "type": "decision_system.trigger_manual"},
                    {
                        "id": "cron1",
                        "type": "decision_system.trigger_cron",
                        "config": {"expression": "*/5 * * * *"},
                    },
                ],
                "connections": [],
            },
        )
        assert wf_resp.status_code == 200

        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 1

        # Update: remove the cron trigger
        wf_resp = await async_client.put(
            f"/workflows/{wf_id}",
            json={
                "name": "Auto Sync WF",
                "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
                "connections": [],
            },
        )
        assert wf_resp.status_code == 200

        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 0

    async def test_webhook_end_to_end(self, async_client):
        """API: webhook receiver triggers workflow execution."""
        # Create workflow with webhook trigger node
        wf_resp = await async_client.post(
            "/workflows",
            json={
                "name": "Webhook E2E WF",
                "nodes": [
                    {
                        "id": "wh1",
                        "type": "decision_system.trigger_webhook",
                        "config": {"webhook_path": "e2e-test-hook"},
                    }
                ],
            },
        )
        assert wf_resp.status_code == 200
        wf_id = wf_resp.json()["id"]

        # Verify schedule was auto-created
        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 1

        # Fire webhook
        wh_resp = await async_client.post("/webhook/e2e-test-hook", json={"event": "test"})
        assert wh_resp.status_code == 200
        data = wh_resp.json()
        assert data["triggered"] == 1
        assert data["executions"][0]["status"] == "completed"
        assert data["executions"][0]["workflow_id"] == wf_id

    async def test_webhook_no_match_returns_404(self, async_client):
        """API: webhook with no matching schedule returns 404."""
        resp = await async_client.post("/webhook/nonexistent-hook", json={})
        assert resp.status_code == 404

    async def test_multiple_trigger_types_in_one_workflow(self, async_client):
        """API: workflow with multiple trigger nodes creates multiple schedules."""
        wf_resp = await async_client.post(
            "/workflows",
            json={
                "name": "Multi Trigger WF",
                "nodes": [
                    {
                        "id": "c1",
                        "type": "decision_system.trigger_cron",
                        "config": {"expression": "0 9 * * 1"},
                    },
                    {
                        "id": "w1",
                        "type": "decision_system.trigger_webhook",
                        "config": {"webhook_path": "multi-hook"},
                    },
                    {
                        "id": "f1",
                        "type": "decision_system.trigger_file_watch",
                        "config": {"directory": "/tmp", "pattern": "*.csv"},
                    },
                ],
            },
        )
        assert wf_resp.status_code == 200
        wf_id = wf_resp.json()["id"]

        sched_resp = await async_client.get(f"/schedules?workflow_id={wf_id}")
        schedules = sched_resp.json()["schedules"]
        assert len(schedules) == 3

        types = {s["trigger_type"] for s in schedules}
        assert types == {"cron", "webhook", "file_watch"}

    # ── CLI Integration ─────────────────────────────────────────────────

    def test_cli_create_and_list(self):
        """CLI: create schedule, list it, delete it."""
        runner = CliRunner()
        store_dir = Path(tempfile.mkdtemp())

        # Create a workflow via store directly
        ws = JSONWorkflowStore(store_dir)
        wf = WorkflowDefinition(name="CLI E2E WF")
        ws.save(wf)

        # Create schedule via CLI
        create_result = runner.invoke(
            workflow_cli,
            [
                "schedule",
                "create",
                wf.id,
                "--store-dir",
                str(store_dir),
                "--trigger-type",
                "cron",
                "--config",
                '{"expression": "0 9 * * 1"}',
            ],
        )
        assert create_result.exit_code == 0
        assert "Created schedule" in create_result.stdout

        # Extract schedule ID from create output
        sch_id = None
        for line in create_result.stdout.split("\n"):
            if "Created schedule" in line:
                parts = line.strip().split(" ")
                for i, part in enumerate(parts):
                    if part.startswith("sch-"):
                        sch_id = part
                        break

        # List schedules
        result = runner.invoke(
            workflow_cli,
            [
                "schedule",
                "list",
                "--store-dir",
                str(store_dir),
            ],
        )
        assert result.exit_code == 0
        assert "cron" in result.stdout

        # Toggle schedule by ID
        assert sch_id is not None, f"Could not find schedule ID in: {create_result.stdout}"
        result = runner.invoke(
            workflow_cli,
            [
                "schedule",
                "toggle",
                sch_id,
                "--store-dir",
                str(store_dir),
            ],
        )
        assert result.exit_code == 0
        assert "disabled" in result.stdout

    def test_cli_create_invalid_trigger_type(self):
        """CLI: invalid trigger type prints error."""
        runner = CliRunner()
        with tempfile.TemporaryDirectory() as td:
            result = runner.invoke(
                workflow_cli,
                [
                    "schedule",
                    "create",
                    "wf-1",
                    "--store-dir",
                    td,
                    "--trigger-type",
                    "invalid",
                ],
            )
            assert result.exit_code != 0
            assert "Invalid trigger type" in result.stdout

    # ── Scheduler Service Integration ───────────────────────────────────
    # Tests with the actual scheduler service would need a running event
    # loop and time-dependent assertions. We verify the service can be
    # instantiated and its core methods work without side effects.

    def test_scheduler_service_can_start_and_stop(self):
        """SchedulerService: start() and stop() are idempotent and non-blocking."""
        import asyncio
        import tempfile

        from decision_system.workflow_engine.engine.executor import DAGEngine
        from decision_system.workflow_engine.nodes import create_default_registry
        from decision_system.workflow_engine.scheduler import (
            SchedulerService,
            ScheduleStore,
        )
        from decision_system.workflow_engine.stores.json_store import (
            JSONExecutionStore,
            JSONWorkflowStore,
        )

        tmp = Path(tempfile.mkdtemp())
        registry = create_default_registry()
        ws = JSONWorkflowStore(tmp)
        es = JSONExecutionStore(tmp)
        engine = DAGEngine(registry=registry, workflow_store=ws, execution_store=es)
        store = ScheduleStore(tmp)
        scheduler = SchedulerService(
            schedule_store=store,
            dag_engine=engine,
            poll_interval=600.0,
        )

        assert scheduler.is_running is False

        # Start
        asyncio.run(scheduler.start())
        assert scheduler.is_running is True

        # Double start is a no-op
        asyncio.run(scheduler.start())
        assert scheduler.is_running is True

        # Stop
        asyncio.run(scheduler.stop())
        assert scheduler.is_running is False

        # Double stop is a no-op
        asyncio.run(scheduler.stop())
        assert scheduler.is_running is False
