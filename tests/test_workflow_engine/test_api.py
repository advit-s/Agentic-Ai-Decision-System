"""Tests for workflow API routes."""

import pytest
from fastapi.testclient import TestClient

from decision_system.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


class TestWorkflowAPI:
    def test_list_node_types(self, client):
        response = client.get("/workflows/nodes")
        assert response.status_code == 200
        data = response.json()
        assert "node_types" in data
        types = {t["type"] for t in data["node_types"]}
        assert "decision_system.trigger_manual" in types
        assert "decision_system.retrieve" in types

    def test_create_and_get_workflow(self, client):
        payload = {
            "name": "API Test Workflow",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
            ],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        assert create_resp.status_code == 200
        wf_id = create_resp.json()["id"]

        get_resp = client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "API Test Workflow"

    def test_list_workflows_empty(self, client):
        response = client.get("/workflows")
        assert response.status_code == 200
        assert "workflows" in response.json()

    def test_delete_workflow(self, client):
        payload = {
            "name": "Delete Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        delete_resp = client.delete(f"/workflows/{wf_id}")
        assert delete_resp.status_code == 200

        get_resp = client.get(f"/workflows/{wf_id}")
        assert get_resp.status_code == 404

    def test_execute_workflow(self, client):
        payload = {
            "name": "Execute Test",
            "nodes": [{"id": "n1", "type": "decision_system.input_text"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        execute_resp = client.post(f"/workflows/{wf_id}/execute", json={"inputs": {}})
        assert execute_resp.status_code == 200
        data = execute_resp.json()
        assert "execution_id" in data
        assert data["status"] == "completed"

    def test_get_execution_state(self, client):
        payload = {
            "name": "Exec State Test",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
            "connections": [],
        }
        create_resp = client.post("/workflows", json=payload)
        wf_id = create_resp.json()["id"]

        exec_resp = client.post(f"/workflows/{wf_id}/execute")
        exec_id = exec_resp.json()["execution_id"]

        state_resp = client.get(f"/executions/{exec_id}")
        assert state_resp.status_code == 200
        assert state_resp.json()["execution_id"] == exec_id

    def test_execute_nonexistent_workflow(self, client):
        response = client.post("/workflows/nonexistent/execute")
        assert response.status_code == 404


class TestScheduleAPI:
    """Tests for schedule CRUD and webhook API routes."""

    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_list_schedules_empty(self, client):
        """GET /schedules returns empty list initially."""
        response = client.get("/schedules")
        assert response.status_code == 200
        data = response.json()
        assert "schedules" in data
        assert len(data["schedules"]) == 0

    def _create_schedule(self, client, trigger_type="cron", trigger_config=None):
        """Helper: create a workflow + schedule, return (schedule_id, workflow_id)."""
        wf_resp = client.post("/workflows", json={
            "name": "Scheduled WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]
        resp = client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": trigger_type,
            "trigger_config": trigger_config or {},
        })
        assert resp.status_code == 200
        return resp.json()["id"], wf_id

    def test_create_schedule(self, client):
        """POST /schedules creates a new schedule."""
        sch_id, wf_id = self._create_schedule(client)
        assert sch_id.startswith("sch-")

        resp = client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["workflow_id"] == wf_id
        assert data["trigger_type"] == "cron"

    def test_get_schedule(self, client):
        """GET /schedules/{id} returns the schedule."""
        sch_id, _ = self._create_schedule(client)

        resp = client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sch_id

    def test_get_nonexistent_schedule(self, client):
        """GET /schedules/{id} returns 404 for missing schedule."""
        resp = client.get("/schedules/nonexistent")
        assert resp.status_code == 404

    def test_list_schedules_filtered(self, client):
        """GET /schedules?workflow_id=... filters results."""
        sch_id, wf_id = self._create_schedule(client)

        resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schedules"]) == 1

        resp = client.get("/schedules?workflow_id=nonexistent")
        assert resp.status_code == 200
        assert len(resp.json()["schedules"]) == 0

    def test_update_schedule(self, client):
        """PUT /schedules/{id} updates a schedule."""
        sch_id, _ = self._create_schedule(client)

        resp = client.put(f"/schedules/{sch_id}", json={
            "enabled": False,
            "trigger_config": {"expression": "0 12 * * *"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["enabled"] is False
        assert data["trigger_config"]["expression"] == "0 12 * * *"

    def test_update_nonexistent_schedule(self, client):
        """PUT /schedules/{id} returns 404 for missing schedule."""
        resp = client.put("/schedules/nonexistent", json={"enabled": False})
        assert resp.status_code == 404

    def test_toggle_schedule(self, client):
        """POST /schedules/{id}/toggle toggles enabled/disabled."""
        sch_id, _ = self._create_schedule(client)

        resp = client.post(f"/schedules/{sch_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is not True  # was True, now False

        resp = client.post(f"/schedules/{sch_id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True  # back to True

    def test_delete_schedule(self, client):
        """DELETE /schedules/{id} removes the schedule."""
        sch_id, _ = self._create_schedule(client)

        resp = client.delete(f"/schedules/{sch_id}")
        assert resp.status_code == 200

        resp = client.get(f"/schedules/{sch_id}")
        assert resp.status_code == 404

    def test_delete_nonexistent_schedule(self, client):
        """DELETE /schedules/{id} returns 404 for missing schedule."""
        resp = client.delete("/schedules/nonexistent")
        assert resp.status_code == 404

    def test_create_schedule_bad_trigger_type(self, client):
        """POST /schedules with invalid trigger_type returns 400."""
        wf_resp = client.post("/workflows", json={
            "name": "Bad Trigger WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = wf_resp.json()["id"]

        resp = client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": "invalid_trigger",
        })
        assert resp.status_code == 400

    def test_create_schedule_nonexistent_workflow(self, client):
        """POST /schedules with nonexistent workflow returns 404."""
        resp = client.post("/schedules", json={
            "workflow_id": "nonexistent",
            "trigger_type": "cron",
        })
        assert resp.status_code == 404

    def test_webhook_receiver_triggers_execution(self, client):
        """POST /webhook/{path} triggers the matching webhook schedule."""
        wf_resp = client.post("/workflows", json={
            "name": "Webhook WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_webhook"}],
        })
        wf_id = wf_resp.json()["id"]

        client.post("/schedules", json={
            "workflow_id": wf_id,
            "trigger_type": "webhook",
            "trigger_config": {"webhook_path": "my-webhook"},
        })

        resp = client.post("/webhook/my-webhook", json={"event": "push"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["triggered"] == 1
        assert len(data["executions"]) == 1
        assert data["executions"][0]["status"] == "completed"

    def test_webhook_no_match(self, client):
        """POST /webhook/{path} returns 404 when no webhook matches."""
        resp = client.post("/webhook/unknown-path", json={})
        assert resp.status_code == 404


class TestAutoSchedule:
    """Tests for auto-scheduling when workflows with trigger nodes are saved."""

    @pytest.fixture
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_create_workflow_auto_schedules_cron(self, client):
        """Creating a workflow with a cron trigger node auto-creates a schedule."""
        resp = client.post("/workflows", json={
            "name": "Auto Cron WF",
            "nodes": [{
                "id": "n1",
                "type": "decision_system.trigger_cron",
                "config": {"expression": "0 9 * * 1"},
            }],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        # Check a schedule was auto-created
        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "cron"
        assert data["schedules"][0]["trigger_config"]["expression"] == "0 9 * * 1"

    def test_create_workflow_auto_schedules_webhook(self, client):
        """Creating a workflow with a webhook trigger node auto-creates a schedule."""
        resp = client.post("/workflows", json={
            "name": "Auto Webhook WF",
            "nodes": [{
                "id": "n1",
                "type": "decision_system.trigger_webhook",
                "config": {"webhook_path": "test-hook"},
            }],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "webhook"

    def test_create_workflow_auto_schedules_file_watch(self, client):
        """Creating a workflow with a file_watch trigger node auto-creates a schedule."""
        resp = client.post("/workflows", json={
            "name": "Auto FileWatch WF",
            "nodes": [{
                "id": "n1",
                "type": "decision_system.trigger_file_watch",
                "config": {"directory": "/tmp", "pattern": "*.csv"},
            }],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        data = sched_resp.json()
        assert len(data["schedules"]) == 1
        assert data["schedules"][0]["trigger_type"] == "file_watch"

    def test_non_trigger_nodes_do_not_create_schedules(self, client):
        """Creating a workflow without trigger nodes does not create schedules."""
        resp = client.post("/workflows", json={
            "name": "No Trigger WF",
            "nodes": [{
                "id": "n1",
                "type": "decision_system.trigger_manual",
            }],
        })
        assert resp.status_code == 200
        wf_id = resp.json()["id"]

        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        assert len(sched_resp.json()["schedules"]) == 0

    def test_update_workflow_creates_new_schedule(self, client):
        """Adding a trigger node to an existing workflow creates a schedule."""
        resp = client.post("/workflows", json={
            "name": "Update Test WF",
            "nodes": [{"id": "n1", "type": "decision_system.trigger_manual"}],
        })
        wf_id = resp.json()["id"]

        # Update: add a cron trigger node
        resp = client.put(f"/workflows/{wf_id}", json={
            "name": "Update Test WF",
            "nodes": [
                {"id": "n1", "type": "decision_system.trigger_manual"},
                {"id": "n2", "type": "decision_system.trigger_cron", "config": {"expression": "*/5 * * * *"}},
            ],
            "connections": [],
        })
        assert resp.status_code == 200

        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert sched_resp.status_code == 200
        assert len(sched_resp.json()["schedules"]) == 1

    def test_update_workflow_removes_orphan_schedule(self, client):
        """Removing a trigger node from a workflow deletes its schedule."""
        resp = client.post("/workflows", json={
            "name": "Remove Trigger WF",
            "nodes": [{
                "id": "n1",
                "type": "decision_system.trigger_cron",
                "config": {"expression": "0 9 * * 1"},
            }],
        })
        wf_id = resp.json()["id"]

        # Verify schedule was created
        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 1

        # Update: remove the trigger node
        resp = client.put(f"/workflows/{wf_id}", json={
            "name": "Remove Trigger WF",
            "nodes": [{"id": "n2", "type": "decision_system.trigger_manual"}],
            "connections": [],
        })
        assert resp.status_code == 200

        # Schedule should be deleted
        sched_resp = client.get(f"/schedules?workflow_id={wf_id}")
        assert len(sched_resp.json()["schedules"]) == 0


class TestProviderAPI:
    """Tests for LLM provider CRUD API routes.

    Note: provider store persists to file, so state carries across test runs.
    Each test cleans up providers it creates. The class teardown resets the
    store to its default state.
    """

    @classmethod
    def setup_class(cls):
        """Clean up any test providers left from previous runs."""
        from decision_system.workflow_engine.api import _provider_store
        providers = _provider_store.load()
        # Remove any providers that aren't in the defaults
        defaults = {"opencode"}
        for p in list(providers):
            if p.name not in defaults:
                providers.remove(p)
        _provider_store.save(providers)

    @classmethod
    def teardown_class(cls):
        """Reset provider store to defaults after all tests run."""
        from decision_system.workflow_engine.api import _provider_store
        from decision_system.workflow_engine.providers.store import DEFAULT_PROVIDERS
        _provider_store.save(list(DEFAULT_PROVIDERS))

    def _provider_names(self, client):
        """Helper: get current provider names."""
        return [p["name"] for p in client.get("/providers").json()["providers"]]

    def test_list_providers(self, client):
        """GET /providers returns the provider list with key status."""
        resp = client.get("/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "providers" in data
        assert len(data["providers"]) >= 1
        names = [p["name"] for p in data["providers"]]
        assert "opencode" in names

    def test_list_providers_has_key_status(self, client):
        """Each provider entry includes api_key_configured boolean."""
        resp = client.get("/providers")
        assert resp.status_code == 200
        for p in resp.json()["providers"]:
            assert "api_key_configured" in p
            assert isinstance(p["api_key_configured"], bool)

    def test_create_provider(self, client):
        """POST /providers adds a new provider."""
        name = "test-create-provider"
        client.delete(f"/providers/{name}")  # clean up any leftover

        resp = client.post("/providers", json={
            "name": name,
            "api_base": "https://test.api/v1",
            "api_key_env": "TEST_KEY",
            "default_model": "test-model",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == name
        assert data["api_base"] == "https://test.api/v1"

        # Verify it appears in the list
        assert name in self._provider_names(client)
        client.delete(f"/providers/{name}")

    def test_create_duplicate_provider(self, client):
        """POST /providers with duplicate name returns 409."""
        name = "test-dupe-provider"
        client.delete(f"/providers/{name}")
        client.post("/providers", json={
            "name": name,
            "api_base": "https://first.api/v1",
            "default_model": "m1",
        })

        resp = client.post("/providers", json={
            "name": name,
            "api_base": "https://second.api/v1",
            "default_model": "m1",
        })
        assert resp.status_code == 409
        client.delete(f"/providers/{name}")

    def test_create_provider_invalid_api_base(self, client):
        """POST /providers with invalid api_base returns 422."""
        resp = client.post("/providers", json={
            "name": "bad-provider",
            "api_base": "not-a-url",
            "default_model": "m1",
        })
        assert resp.status_code == 422

    def test_get_provider(self, client):
        """GET /providers/{name} returns the provider config."""
        resp = client.get("/providers/opencode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "opencode"
        assert "api_base" in data

    def test_get_nonexistent_provider(self, client):
        """GET /providers/{name} with unknown name returns 404."""
        resp = client.get("/providers/does-not-exist")
        assert resp.status_code == 404

    def test_update_provider(self, client):
        """PUT /providers/{name} updates provider fields."""
        resp = client.put("/providers/opencode", json={
            "default_model": "claude-sonnet-4-20250514",
            "api_key_env": "CUSTOM_KEY",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_model"] == "claude-sonnet-4-20250514"
        assert data["api_key_env"] == "CUSTOM_KEY"

        # Restore to avoid affecting other tests
        client.put("/providers/opencode", json={
            "default_model": "claude-sonnet-4-20250514",
            "api_key_env": "OPENCODE_API_KEY",
        })

    def test_update_nonexistent_provider(self, client):
        """PUT /providers/{name} with unknown name returns 404."""
        resp = client.put("/providers/does-not-exist", json={
            "default_model": "m1",
        })
        assert resp.status_code == 404

    def test_delete_provider(self, client):
        """DELETE /providers/{name} removes a provider."""
        name = "test-delete-provider"
        client.delete(f"/providers/{name}")
        client.post("/providers", json={
            "name": name,
            "api_base": "https://delete.me/v1",
            "default_model": "m1",
        })

        resp = client.delete(f"/providers/{name}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify gone
        get_resp = client.get(f"/providers/{name}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_provider(self, client):
        """DELETE /providers/{name} with unknown name returns 404."""
        resp = client.delete("/providers/does-not-exist")
        assert resp.status_code == 404

    def test_check_provider_returns_result(self, client):
        """POST /providers/{name}/check returns connection test result."""
        resp = client.post("/providers/opencode/check")
        assert resp.status_code == 200
        data = resp.json()
        assert "provider" in data
        assert data["provider"] == "opencode"

    def test_check_nonexistent_provider(self, client):
        """POST /providers/{name}/check with unknown name returns 404."""
        resp = client.post("/providers/does-not-exist/check")
        assert resp.status_code == 404

    def test_set_default_provider(self, client):
        """POST /providers/system/default sets and reorders providers."""
        name = "test-default-provider"
        client.delete(f"/providers/{name}")
        client.post("/providers", json={
            "name": name,
            "api_base": "https://test-default.api/v1",
            "default_model": "m2",
        })

        resp = client.post("/providers/system/default", json={"name": name})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["default_provider"]["name"] == name

        # Verify it's now first in the list
        list_resp = client.get("/providers")
        assert list_resp.json()["providers"][0]["name"] == name

        # Restore opencode as default
        client.post("/providers/system/default", json={"name": "opencode"})
        client.delete(f"/providers/{name}")

    def test_set_default_missing_name(self, client):
        """POST /providers/system/default without name returns 400."""
        resp = client.post("/providers/system/default", json={})
        assert resp.status_code == 400

    def test_set_default_nonexistent(self, client):
        """POST /providers/system/default with unknown name returns 404."""
        resp = client.post("/providers/system/default", json={"name": "no-such-provider"})
        assert resp.status_code == 404
