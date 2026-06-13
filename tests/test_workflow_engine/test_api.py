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
