"""Tests for workflow API routes using async httpx client."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from decision_system.api.app import set_scheduler_enabled, create_app


@pytest.fixture
async def client(tmp_path):
    """Create an async test client with isolated temp storage."""
    import os
    # Use isolated temp dir for durable storage
    os.environ['DECISION_SYSTEM_DATA_DIR'] = str(tmp_path)
    set_scheduler_enabled(False)
    # Clear any cached store instances by re-importing
    import importlib
    import decision_system.workflow_engine.api as wf_api
    importlib.reload(wf_api)
    from decision_system.api.app import create_app as fresh_create
    app = fresh_create()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


class TestWorkflowAPI:
    async def test_list_node_types(self, client):
        response = await client.get("/workflows/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        types = {t["type"] for t in data["node_types"]}
        assert "decision_system.trigger_manual" in types
        assert "decision_system.retrieve" in types

    async def test_create_and_get_workflow(self, client):
        payload = {
            "name": "API Test Workflow",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
            ],
            "connections": [],
        }
        create_resp = await client.post("/workflows", json=payload)
        assert create_resp.status_code == 200
        wf_id = create_resp.json()["id"]

        get_resp = await client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "API Test Workflow"

    async def test_list_workflows_empty(self, client):
        response = await client.get("/workflows")
        assert response.status_code == 200
        assert "workflows" in response.json()

    async def test_delete_workflow(self, client):
        payload = {
            "name": "Delete Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = await client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        delete_resp = await client.delete(f"/workflows/{wf_id}")
        assert delete_resp.status_code == 200

        get_resp = await client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 404

    async def test_execute_workflow(self, client):
        payload = {
            "name": "Execute Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = await client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        execute_resp = await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        assert execute_resp.status_code == 200
        data = execute_resp.json()
        assert "execution_id" in data
        assert data["status"] == "completed"

    async def test_get_execution_state(self, client):
        payload = {
            "name": "Exec State Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = await client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        exec_resp = await client.post(f"/workflows/{wf_id}/execute")
        exec_id = exec_resp.json()["execution_id"]

        state_resp = await client.get(f"/executions/{exec_id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["execution_id"] == exec_id

    async def test_execute_nonexistent_workflow(self, client):
        response = await client.post("/workflows/nonexistent/execute")
        assert response.status_code == 404

    # --- Execution History Tests ---

    async def test_execution_history_list_empty(self, client):
        resp = await client.get("/executions/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "executions" in data

    async def test_execution_history_after_execution(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "History Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})

        hist_resp = await client.get("/executions/history")
        assert hist_resp.status_code == 200
        data = hist_resp.json()
        assert len(data["executions"]) >= 1
        wf_ids = [e["workflow_id"] for e in data["executions"]]
        assert wf_id in wf_ids

    async def test_execution_history_filter_by_workflow(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Filter Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})

        resp = await client.get(f"/executions/history?workflow_id={wf_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["executions"]) >= 1
        for e in data["executions"]:
            assert e["workflow_id"] == wf_id

    async def test_delete_execution_history(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Del History WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        exec_resp = await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        exec_id = exec_resp.json()["execution_id"]

        del_resp = await client.delete(f"/executions/history/{exec_id}")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "deleted"

        get_resp = await client.get(f"/executions/{exec_id}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_execution_history(self, client):
        resp = await client.delete("/executions/history/nonexistent")
        assert resp.status_code == 404

    async def test_execution_detail(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Detail Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        exec_resp = await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        exec_id = exec_resp.json()["execution_id"]

        detail_resp = await client.get(f"/executions/{exec_id}/detail")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert "execution_state" in data
        assert "workflow_definition" in data
        assert "node_states" in data
        assert "event_timeline" in data
        assert "review_requests" in data
        assert "metrics_summary" in data

    async def test_execution_detail_nonexistent(self, client):
        resp = await client.get("/executions/nonexistent/detail")
        assert resp.status_code == 404

    async def test_execution_resume_placeholder(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Resume Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        exec_resp = await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        exec_id = exec_resp.json()["execution_id"]

        resume_resp = await client.post(f"/executions/{exec_id}/resume", json={"action": "resume"})
        assert resume_resp.status_code == 409, f"Expected 409 (not paused), got {resume_resp.status_code}"

    async def test_execution_resume_nonexistent(self, client):
        resume_resp = await client.post("/executions/nonexistent/resume", json={"action": "resume"})
        assert resume_resp.status_code == 404


class TestWorkflowVersioning:
    async def test_create_workflow_creates_version(self, client):
        resp = await client.post("/workflows", json={
            "name": "Version Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        ver_resp = await client.get(f"/workflows/{wf_id}/versions")
        assert ver_resp.status_code == 200
        versions = ver_resp.json()["versions"]
        assert len(versions) >= 1
        assert versions[0]["version_number"] == 1

    async def test_update_workflow_creates_new_version(self, client):
        resp = await client.post("/workflows", json={
            "name": "Update Version WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        await client.put(f"/workflows/{wf_id}", json={
            "name": "Update Version WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.trigger_manual"},
            ],
        })

        ver_resp = await client.get(f"/workflows/{wf_id}/versions")
        assert ver_resp.status_code == 200
        versions = ver_resp.json()["versions"]
        assert len(versions) >= 2

    async def test_list_versions_nonexistent_workflow(self, client):
        resp = await client.get("/workflows/nonexistent/versions")
        assert resp.status_code == 404

    async def test_get_version_by_id(self, client):
        resp = await client.post("/workflows", json={
            "name": "Get Version WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        ver_resp = await client.get(f"/workflows/{wf_id}/versions")
        version_id = ver_resp.json()["versions"][0]["version_id"]

        get_resp = await client.get(f"/workflows/{wf_id}/versions/{version_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["version_id"] == version_id

    async def test_get_version_by_number(self, client):
        resp = await client.post("/workflows", json={
            "name": "Get Version Num WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        get_resp = await client.get(f"/workflows/{wf_id}/versions/1")
        assert get_resp.status_code == 200
        assert get_resp.json()["version_number"] == 1

    async def test_get_nonexistent_version(self, client):
        resp = await client.post("/workflows", json={
            "name": "No Version WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        get_resp = await client.get(f"/workflows/{wf_id}/versions/999")
        assert get_resp.status_code == 404

    async def test_execution_linked_to_version(self, client):
        resp = await client.post("/workflows", json={
            "name": "Exec Version Link WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        assert exec_resp.status_code == 200
        data = exec_resp.json()
        assert "workflow_version_id" in data
        assert data["workflow_version_id"] is not None

    async def test_version_has_content_hash(self, client):
        resp = await client.post("/workflows", json={
            "name": "Hash Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        ver_resp = await client.get(f"/workflows/{wf_id}/versions")
        version = ver_resp.json()["versions"][0]
        assert "content_hash" in version
        assert len(version["content_hash"]) > 0


class TestScheduleAPI:
    async def _create_schedule(self, client, trigger_type="cron", trigger_config=None):
        wf_resp = await client.post("/workflows", json={
            "name": "Scheduled WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        resp = await client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": trigger_type,
            "trigger_config": trigger_config or {},
        })
        assert resp.status_code == 200
        return resp.json()["id"], wf_id

    async def test_list_schedules_empty(self, client):
        response = await client.get("/schedules")
        assert response.status_code == 200
        data = response.json()
        assert "schedules" in data
        assert len(data["schedules"]) == 0

    async def test_create_schedule(self, client):
        sch_id, wf_id = await self._create_schedule(client)
        assert sch_id.startswith("sch-")
        resp = await client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_id"] == wf_id
        assert data["trigger_type"] == "cron"

    async def test_get_schedule(self, client):
        sch_id, _ = await self._create_schedule(client)
        resp = await client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sch_id

    async def test_get_nonexistent_schedule(self, client):
        resp = await client.get("/schedules/nonexistent")
        assert resp.status_code == 404

    async def test_list_schedules_filtered(self, client):
        sch_id, wf_id = await self._create_schedule(client)
        resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schedules"]) == 1
        resp = await client.get("/schedules?workflow_id=nonexistent")
        assert resp.status_code == 200
        assert len(resp.json()["schedules"]) == 0

    async def test_update_schedule(self, client):
        sch_id, _ = await self._create_schedule(client)
        resp = await client.put(f"/schedules/{sch_id}", json={
            "enabled": False,
            "trigger_config": {"expression": "0 12 * * *"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["trigger_config"]["expression"] == "0 12 * * *"

    async def test_update_nonexistent_schedule(self, client):
        resp = await client.put("/schedules/nonexistent", json={"enabled": False})
        assert resp.status_code == 404

    async def test_toggle_schedule(self, client):
        sch_id, _ = await self._create_schedule(client)
        resp = await client.post(f"/schedules/{sch_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is not True
        resp = await client.post(f"/schedules/{sch_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

    async def test_delete_schedule(self, client):
        sch_id, _ = await self._create_schedule(client)
        resp = await client.delete(f"/schedules/{sch_id}")
        assert resp.status_code == 200
        resp = await client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_schedule(self, client):
        resp = await client.delete("/schedules/nonexistent")
        assert resp.status_code == 404

    async def test_create_schedule_bad_trigger_type(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Bad Trigger WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        resp = await client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": "invalid_trigger",
        })
        assert resp.status_code == 400

    async def test_create_schedule_nonexistent_workflow(self, client):
        resp = await client.post("/schedules", json={
            "workflow_id": "nonexistent",
            "trigger_type": "cron",
        })
        assert resp.status_code == 404

    async def test_webhook_receiver_triggers_execution(self, client):
        wf_resp = await client.post("/workflows", json={
            "name": "Webhook WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_webhook"}],
        })
        wf_id = wf_resp.json()["id"]
        await client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": "webhook",
            "trigger_config": {"webhook_path": "my-webhook"},
        })
        resp = await client.post("/webhook/my-webhook", json={"event": "push"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggered"] == 1
        assert len(data["executions"]) == 1
        assert data["executions"][0]["status"] == "completed"

    async def test_webhook_no_match(self, client):
        resp = await client.post("/webhook/unknown-path", json={})
        assert resp.status_code == 404


class TestAutoSchedule:
    async def test_create_workflow_auto_schedules_cron(self, client):
        resp = await client.post("/workflows", json={
            "name": "Auto Cron WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_cron", "config": {"expression": "0 9 * * 1"}}],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "cron"
        assert data["schedules"][0]["trigger_config"]["expression"] == "0 9 * * 1"

    async def test_create_workflow_auto_schedules_webhook(self, client):
        resp = await client.post("/workflows", json={
            "name": "Auto Webhook WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_webhook", "config": {"webhook_path": "test-hook"}}],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "webhook"

    async def test_create_workflow_auto_schedules_file_watch(self, client):
        resp = await client.post("/workflows", json={
            "name": "Auto FileWatch WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_file_watch", "config": {"directory": "/tmp", "pattern": "*.csv"}}],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "file_watch"

    async def test_non_trigger_nodes_do_not_create_schedules(self, client):
        resp = await client.post("/workflows", json={
            "name": "No Trigger WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        assert len(sched_resp.json()["schedules"]) == 0

    async def test_update_workflow_creates_new_schedule(self, client):
        resp = await client.post("/workflows", json={
            "name": "Update Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]
        resp = await client.put(f"/workflows/{wf_id}", json={
            "name": "Update Test WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.trigger_cron", "config": {"expression": "*/5 * * * *"}},
            ],
            "connections": [],
        })
        assert resp.status_code == 200
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        assert len(sched_resp.json()["schedules"]) == 1

    async def test_update_workflow_removes_orphan_schedule(self, client):
        resp = await client.post("/workflows", json={
            "name": "Remove Trigger WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_cron", "config": {"expression": "0 9 * * 1"}}],
        })
        wf_id = resp.json()["id"]
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 1
        resp = await client.put(f"/workflows/{wf_id}", json={
            "name": "Remove Trigger WF",
            "nodes": [{"id": "n2", "type": "decision_system.trigger_manual"}],
            "connections": [],
        })
        assert resp.status_code == 200
        sched_resp = await client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 0


class TestProviderAPI:
    @classmethod
    def setup_class(cls):
        from decision_system.workflow_engine.api import _provider_store
        providers = _provider_store.load()
        defaults = {"opencode"}
        for p in list(providers):
            if p.name not in defaults:
                providers.remove(p)
        _provider_store.save(providers)

    @classmethod
    def teardown_class(cls):
        from decision_system.workflow_engine.api import _provider_store
        from decision_system.workflow_engine.providers.store import DEFAULT_PROVIDERS
        _provider_store.save(list(DEFAULT_PROVIDERS))

    async def _provider_names(self, client):
        return [p["name"] for p in (await client.get("/providers")).json()["providers"]]

    async def test_list_providers(self, client):
        resp = await client.get("/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) >= 1
        names = [p["name"] for p in data["providers"]]
        assert "opencode" in names

    async def test_list_providers_has_key_status(self, client):
        resp = await client.get("/providers")
        assert resp.status_code == 200
        for p in resp.json()["providers"]:
            assert "api_key_configured" in p
            assert isinstance(p["api_key_configured"], bool)

    async def test_create_provider(self, client):
        name = "test-create-provider"
        await client.delete(f"/providers/{name}")
        resp = await client.post("/providers", json={
            "name": name, "api_base": "https://test.api/v1",
            "api_key_env": "TEST_KEY", "default_model": "test-model",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == name
        assert name in await self._provider_names(client)
        await client.delete(f"/providers/{name}")

    async def test_create_duplicate_provider(self, client):
        name = "test-dupe-provider"
        await client.delete(f"/providers/{name}")
        await client.post("/providers", json={
            "name": name, "api_base": "https://first.api/v1", "default_model": "m1",
        })
        resp = await client.post("/providers", json={
            "name": name, "api_base": "https://second.api/v1", "default_model": "m1",
        })
        assert resp.status_code == 409
        await client.delete(f"/providers/{name}")

    async def test_create_provider_invalid_api_base(self, client):
        resp = await client.post("/providers", json={
            "name": "bad-provider", "api_base": "not-a-url", "default_model": "m1",
        })
        assert resp.status_code == 422

    async def test_get_provider(self, client):
        resp = await client.get("/providers/opencode")
        assert resp.status_code == 200
        assert resp.json()["name"] == "opencode"

    async def test_get_nonexistent_provider(self, client):
        resp = await client.get("/providers/does-not-exist")
        assert resp.status_code == 404

    async def test_update_provider(self, client):
        resp = await client.put("/providers/opencode", json={
            "default_model": "claude-sonnet-4-20250514", "api_key_env": "CUSTOM_KEY",
        })
        assert resp.status_code == 200
        await client.put("/providers/opencode", json={
            "default_model": "claude-sonnet-4-20250514", "api_key_env": "OPENCODE_API_KEY",
        })

    async def test_update_nonexistent_provider(self, client):
        resp = await client.put("/providers/does-not-exist", json={"default_model": "m1"})
        assert resp.status_code == 404

    async def test_delete_provider(self, client):
        name = "test-delete-provider"
        await client.delete(f"/providers/{name}")
        await client.post("/providers", json={
            "name": name, "api_base": "https://delete.me/v1", "default_model": "m1",
        })
        resp = await client.delete(f"/providers/{name}")
        assert resp.status_code == 200
        get_resp = await client.get(f"/providers/{name}")
        assert get_resp.status_code == 404

    async def test_delete_nonexistent_provider(self, client):
        resp = await client.delete("/providers/does-not-exist")
        assert resp.status_code == 404

    async def test_check_provider_returns_result(self, client):
        resp = await client.post("/providers/opencode/check")
        assert resp.status_code == 200
        assert resp.json()["provider"] == "opencode"

    async def test_check_nonexistent_provider(self, client):
        resp = await client.post("/providers/does-not-exist/check")
        assert resp.status_code == 404

    async def test_set_default_provider(self, client):
        name = "test-default-provider"
        await client.delete(f"/providers/{name}")
        await client.post("/providers", json={
            "name": name, "api_base": "https://test-default.api/v1", "default_model": "m2",
        })
        resp = await client.post("/providers/system/default", json={"name": name})
        assert resp.status_code == 200
        list_resp = await client.get("/providers")
        assert list_resp.json()["providers"][0]["name"] == name
        await client.post("/providers/system/default", json={"name": "opencode"})
        await client.delete(f"/providers/{name}")

    async def test_set_default_missing_name(self, client):
        resp = await client.post("/providers/system/default", json={})
        assert resp.status_code == 400

    async def test_set_default_nonexistent(self, client):
        resp = await client.post("/providers/system/default", json={"name": "no-such-provider"})
        assert resp.status_code == 404


class TestReviewGatePauseResume:
    """Tests for true review-gate pause/resume functionality."""

    async def test_review_gate_pauses_execution(self, client):
        """Workflow with review gate pauses and shows awaiting_review status."""
        resp = await client.post("/workflows", json={
            "name": "Review Pause WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        # Execute with data that triggers review
        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}, "instructions": "Review this data"}},
        )
        assert exec_resp.status_code == 200
        data = exec_resp.json()

        # Execution should be paused
        assert data["status"] == "awaiting_review"

        # Verify execution state shows review data
        exec_id = data["execution_id"]
        state_resp = await client.get(f"/executions/{exec_id}")
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert state_data["status"] == "awaiting_review"
        assert state_data["review_id"] is not None
        assert state_data["paused_node_id"] == "n2"

    async def test_downstream_node_does_not_run_before_approval(self, client):
        """Downstream nodes should not execute while awaiting review."""
        resp = await client.post("/workflows", json={
            "name": "Downstream Blocked WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]

        # Verify n3 (downstream) has not run
        state_resp = await client.get(f"/executions/{exec_id}")
        state = state_resp.json()
        assert state["status"] == "awaiting_review"
        node_states = state.get("node_states", {})
        assert node_states.get("n3", {}).get("status") in ("pending", None)

    async def test_review_appears_in_reviews_list(self, client):
        """Review should appear in the /reviews endpoint."""
        resp = await client.post("/workflows", json={
            "name": "Review List WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
            ],
            "connections": [{"source_node": "n1", "target_node": "n2"}],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]

        # Reviews should include a pending entry
        reviews_resp = await client.get("/reviews?status=pending_review")
        assert reviews_resp.status_code == 200
        reviews = reviews_resp.json()["reviews"]
        matching = [r for r in reviews if r.get("execution_id") == exec_id]
        assert len(matching) >= 1
        assert matching[0]["status"] == "pending_review"

    async def test_approval_resumes_workflow(self, client):
        """Approving a review should resume and complete the workflow."""
        resp = await client.post("/workflows", json={
            "name": "Approve Resume WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]
        review_id = exec_resp.json().get("review_id")

        # Resolve the review: approve
        resolve_resp = await client.post(
            f"/reviews/{review_id}/resolve",
            json={
                "action": "approve",
                "notes": "Looks good",
                "reviewed_by": "test-user",
            },
        )
        assert resolve_resp.status_code == 200

        # Resume the execution
        print(f"DEBUG: Resuming execution {exec_id}")
        resume_resp = await client.post(
            f"/executions/{exec_id}/resume",
            json={"action": "resume"},
        )
        print(f"DEBUG: Resume status={resume_resp.status_code}")
        assert resume_resp.status_code == 200
        resume_data = resume_resp.json()
        print(f"DEBUG: Resume response status={resume_data.get('status')}")

        # Execution should now be completed
        state_resp = await client.get(f"/executions/{exec_id}")
        state = state_resp.json()
        print(f"DEBUG: State after resume status={state.get('status')}")
        if state.get('error'):
            print(f"DEBUG: Error={state.get('error')}")
        assert state["status"] == "completed"

        # Downstream node should have run
        node_states = state.get("node_states", {})
        assert node_states.get("n3", {}).get("status") == "completed"

    async def test_rejection_prevents_downstream_execution(self, client):
        """Rejecting a review should end execution without running downstream."""
        resp = await client.post("/workflows", json={
            "name": "Reject Block WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]
        review_id = exec_resp.json().get("review_id")

        # Reject the review
        resolve_resp = await client.post(
            f"/reviews/{review_id}/resolve",
            json={
                "action": "reject",
                "notes": "Not acceptable",
                "reviewed_by": "test-user",
            },
        )
        assert resolve_resp.status_code == 200

        # Resume with reject action
        resume_resp = await client.post(
            f"/executions/{exec_id}/resume",
            json={"action": "reject"},
        )
        assert resume_resp.status_code == 200

        # Execution should be rejected
        state_resp = await client.get(f"/executions/{exec_id}")
        state = state_resp.json()
        assert state["status"] == "rejected"

        # Downstream node should not have run
        node_states = state.get("node_states", {})
        assert node_states.get("n3", {}).get("status") != "completed"

    async def test_changes_requested_does_not_continue(self, client):
        """Changes requested should keep execution waiting."""
        resp = await client.post("/workflows", json={
            "name": "Changes Requested WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]
        review_id = exec_resp.json().get("review_id")

        # Request changes
        resolve_resp = await client.post(
            f"/reviews/{review_id}/resolve",
            json={
                "action": "request_changes",
                "notes": "Please update",
                "reviewed_by": "test-user",
            },
        )
        assert resolve_resp.status_code == 200

        # Execution should still be awaiting_review
        state_resp = await client.get(f"/executions/{exec_id}")
        state = state_resp.json()
        assert state["status"] == "awaiting_review"

    async def test_execution_history_records_pause_resume(self, client):
        """Execution history should reflect pause and resume events."""
        resp = await client.post("/workflows", json={
            "name": "History Pause WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.review_gate"},
                {"id": "n3", "type": "decision_system.input_text"},
            ],
            "connections": [
                {"source_node": "n1", "target_node": "n2"},
                {"source_node": "n2", "target_node": "n3"},
            ],
        })
        wf_id = resp.json()["id"]

        exec_resp = await client.post(
            f"/workflows/{wf_id}/execute",
            json={"inputs": {"data": {"value": 42}}},
        )
        exec_id = exec_resp.json()["execution_id"]
        review_id = exec_resp.json().get("review_id")

        # Paused status should be in history
        hist_resp = await client.get(f"/executions/history?workflow_id={wf_id}")
        entries = [e for e in hist_resp.json()["executions"] if e["execution_id"] == exec_id]
        assert len(entries) >= 1
        assert entries[0]["status"] == "awaiting_review"
