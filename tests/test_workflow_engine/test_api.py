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
