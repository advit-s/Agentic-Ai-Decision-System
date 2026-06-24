"""Tests for the graph extraction API routes."""

from fastapi.testclient import TestClient

from decision_system.api.app import create_app


client = TestClient(create_app())

TEST_WS = "test-graph-api-ws"


def test_extract_graph_no_texts():
    resp = client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={"texts": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert data["nodes_extracted"] == 0


def test_extract_graph_with_text():
    resp = client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Acme Corporation provides Cloud Services. Revenue: $5M.",
                    "evidence_id": "ev-1",
                    "source_id": "src-1",
                    "chunk_id": "ch-1",
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert data["nodes_extracted"] > 0


def test_get_empty_graph():
    ws = "test-empty-graph"
    resp = client.get(f"/workspaces/{ws}/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws
    assert len(data["nodes"]) == 0
    assert len(data["edges"]) == 0


def test_get_graph_after_extraction():
    # First extract
    client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Billing System depends on Auth Service.",
                    "evidence_id": "ev-2",
                    "source_id": "src-1",
                    "chunk_id": "ch-2",
                }
            ]
        },
    )
    # Then retrieve
    resp = client.get(f"/workspaces/{TEST_WS}/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


def test_list_nodes():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/nodes")
    assert resp.status_code == 200
    nodes = resp.json()
    assert isinstance(nodes, list)


def test_list_edges():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/edges")
    assert resp.status_code == 200
    edges = resp.json()
    assert isinstance(edges, list)


def test_graph_summary():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert data["node_count"] > 0


def test_get_nonexistent_node():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/nodes/nonexistent")
    assert resp.status_code == 404


def test_list_risks():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/risks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_list_metrics():
    resp = client.get(f"/workspaces/{TEST_WS}/graph/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_risk_extraction():
    resp = client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Security breach detected in the system.",
                    "evidence_id": "ev-3",
                    "source_id": "src-2",
                    "chunk_id": "ch-3",
                }
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["risks_extracted"] > 0


def test_empty_text_handling():
    resp = client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={
            "texts": [
                {"text": "", "evidence_id": "", "source_id": "", "chunk_id": ""}
            ]
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data


def test_health_still_works():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.26.0-dev"
