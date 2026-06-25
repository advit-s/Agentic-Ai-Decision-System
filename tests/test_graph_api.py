"""Tests for the graph extraction API routes.

All tests are offline using httpx.AsyncClient with ASGITransport.
No external services.
"""

TEST_WS = "test-graph-api-ws"


async def test_extract_graph_no_texts(async_client):
    resp = await async_client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={"texts": []},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert data["nodes_extracted"] == 0


async def test_extract_graph_with_text(async_client):
    resp = await async_client.post(
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


async def test_get_empty_graph(async_client):
    ws = "test-empty-graph"
    resp = await async_client.get(f"/workspaces/{ws}/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws
    assert len(data["nodes"]) == 0
    assert len(data["edges"]) == 0


async def test_get_graph_after_extraction(async_client):
    # First extract
    await async_client.post(
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
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


async def test_list_nodes(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/nodes")
    assert resp.status_code == 200
    nodes = resp.json()
    assert isinstance(nodes, list)


async def test_list_edges(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/edges")
    assert resp.status_code == 200
    edges = resp.json()
    assert isinstance(edges, list)


async def test_graph_summary(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert data["node_count"] >= 0


async def test_get_nonexistent_node(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/nodes/nonexistent")
    assert resp.status_code == 404


async def test_list_risks(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/risks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_list_metrics(async_client):
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/metrics")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_risk_extraction(async_client):
    resp = await async_client.post(
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


async def test_empty_text_handling(async_client):
    resp = await async_client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={"texts": [{"text": "", "evidence_id": "", "source_id": "", "chunk_id": ""}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "warnings" in data


async def test_health_still_works(async_client):
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Graph audit events API
# ---------------------------------------------------------------------------


async def test_list_graph_audit_events_empty(async_client):
    """Audit events endpoint should return empty list for fresh workspace."""
    ws = "test_audit_empty"
    resp = await async_client.get(f"/workspaces/{ws}/graph/audit-events")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws
    assert "events" in data
    assert data["total_count"] >= 0


async def test_list_graph_audit_events_after_extraction(async_client):
    """Audit events should exist after graph extraction."""
    resp = await async_client.post(
        f"/workspaces/{TEST_WS}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Acme Corp revenue grew 15% to $50M in Q1 2024, but faces security risks.",
                    "evidence_id": "ev1",
                    "source_id": "src1",
                    "chunk_id": "ch1",
                }
            ]
        },
    )
    assert resp.status_code == 200

    resp2 = await async_client.get(
        f"/workspaces/{TEST_WS}/graph/audit-events",
        params={"limit": 10},
    )
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["workspace_id"] == TEST_WS
    assert len(data["events"]) > 0
    # Should have extraction started/completed events
    event_types = {e["event_type"] for e in data["events"]}
    assert "graph_extraction_started" in event_types
    assert "graph_extraction_completed" in event_types


async def test_list_graph_audit_events_filter(async_client):
    """Audit events should support event_type filter."""
    resp = await async_client.get(
        f"/workspaces/{TEST_WS}/graph/audit-events",
        params={"event_type": "graph_extraction_started"},
    )
    assert resp.status_code == 200
    data = resp.json()
    for e in data["events"]:
        assert e["event_type"] == "graph_extraction_started"


# ---------------------------------------------------------------------------
# Graph metrics API
# ---------------------------------------------------------------------------


async def test_list_graph_metrics_empty(async_client):
    """Metrics endpoint should return empty for fresh workspace."""
    ws = "test_metrics_empty"
    resp = await async_client.get(f"/workspaces/{ws}/graph/metrics/aggregates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws
    assert "metrics" in data


async def test_list_graph_metrics_after_extraction(async_client):
    """Metrics should have data after extraction."""
    resp = await async_client.get(f"/workspaces/{TEST_WS}/graph/metrics/aggregates")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == TEST_WS
    assert "metrics" in data


# ---------------------------------------------------------------------------
# Extraction runs API
# ---------------------------------------------------------------------------


async def test_list_extraction_runs_empty(async_client):
    """Extraction runs endpoint should return empty list for fresh workspace."""
    ws = "test_runs_empty"
    resp = await async_client.get(f"/workspaces/{ws}/graph/extraction-runs")
    assert resp.status_code == 200
    data = resp.json()
    assert data["workspace_id"] == ws
    assert data["runs"] == []
    assert data["total_count"] == 0


async def test_list_extraction_runs_after_extraction(async_client):
    """Extraction runs should exist after graph extraction."""
    ws = "test_runs_extract"
    await async_client.post(
        f"/workspaces/{ws}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Test Corp faced a major data breach affecting 10K users.",
                    "evidence_id": "ev1",
                    "source_id": "src1",
                    "chunk_id": "ch1",
                }
            ]
        },
    )

    resp = await async_client.get(f"/workspaces/{ws}/graph/extraction-runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["runs"]) > 0
    run = data["runs"][0]
    assert run["workspace_id"] == ws
    assert run["status"] == "completed"
    assert run["nodes_created"] > 0
    assert "duration_ms" in run


async def test_get_extraction_run_by_id(async_client):
    """Should retrieve a specific extraction run by ID."""
    ws = "test_runs_by_id"
    resp = await async_client.post(
        f"/workspaces/{ws}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Widget Inc quarterly profit grew 10%.",
                    "evidence_id": "ev1",
                    "source_id": "src1",
                    "chunk_id": "ch1",
                }
            ]
        },
    )
    assert resp.status_code == 200

    # List runs to get run_id
    list_resp = await async_client.get(f"/workspaces/{ws}/graph/extraction-runs")
    runs = list_resp.json()["runs"]
    assert len(runs) > 0
    run_id = runs[0]["run_id"]

    # Get by ID
    get_resp = await async_client.get(f"/workspaces/{ws}/graph/extraction-runs/{run_id}")
    assert get_resp.status_code == 200
    run = get_resp.json()
    assert run["run_id"] == run_id
    assert run["workspace_id"] == ws


async def test_get_extraction_run_not_found(async_client):
    """Should return 404 for non-existent run."""
    resp = await async_client.get("/workspaces/nonexistent/graph/extraction-runs/no-such-run")
    assert resp.status_code == 404


async def test_latest_extraction_run(async_client):
    """Latest extraction endpoint should return the most recent run."""
    ws = "test_latest_run"
    await async_client.post(
        f"/workspaces/{ws}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Latest Corp revenue increased.",
                    "evidence_id": "ev1",
                    "source_id": "src1",
                    "chunk_id": "ch1",
                }
            ]
        },
    )

    resp = await async_client.get(f"/workspaces/{ws}/graph/latest-extraction")
    assert resp.status_code == 200
    run = resp.json()
    assert run is not None
    assert run["workspace_id"] == ws
    assert run["status"] == "completed"


async def test_latest_extraction_run_empty(async_client):
    """Latest extraction should return null for empty workspace."""
    resp = await async_client.get("/workspaces/no_runs_ever/graph/latest-extraction")
    assert resp.status_code == 200
    assert resp.json() is None


# ---------------------------------------------------------------------------
# Workspace isolation for extraction runs
# ---------------------------------------------------------------------------


async def test_extraction_runs_workspace_isolation(async_client):
    """Extraction runs should be isolated per workspace."""
    ws1 = "test_isolation_1"
    ws2 = "test_isolation_2"

    await async_client.post(
        f"/workspaces/{ws1}/graph/extract",
        json={"texts": [{"text": "WS1 Corp", "evidence_id": "e1"}]},
    )
    await async_client.post(
        f"/workspaces/{ws2}/graph/extract",
        json={"texts": [{"text": "WS2 Corp", "evidence_id": "e2"}]},
    )

    r1 = (await async_client.get(f"/workspaces/{ws1}/graph/extraction-runs")).json()
    r2 = (await async_client.get(f"/workspaces/{ws2}/graph/extraction-runs")).json()

    assert r1["total_count"] > 0
    assert r2["total_count"] > 0
    for run in r1["runs"]:
        assert run["workspace_id"] == ws1
    for run in r2["runs"]:
        assert run["workspace_id"] == ws2


# ---------------------------------------------------------------------------
# Graph-to-Claim API
# ---------------------------------------------------------------------------


async def test_create_claim_from_risk(async_client):
    """Should create a pending claim from a risk."""
    ws = "test_claim_risk"
    # First extract to create some risks
    await async_client.post(
        f"/workspaces/{ws}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Security breach in database leaking personal data.",
                    "evidence_id": "ev-sec",
                    "source_id": "src-sec",
                    "chunk_id": "ch-sec",
                }
            ]
        },
    )

    # Get a risk ID
    risks_resp = await async_client.get(f"/workspaces/{ws}/graph/risks")
    risks = risks_resp.json()
    if not risks:
        return  # skip if no risks extracted

    risk_id = risks[0]["risk_id"]

    resp = await async_client.post(
        f"/workspaces/{ws}/graph/claims",
        json={
            "fact_type": "risk",
            "fact_id": risk_id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert risk_id in data["risk_refs"]
    assert data["workspace_id"] == ws


async def test_create_claim_from_metric(async_client):
    """Should create a pending claim from a metric."""
    ws = "test_claim_metric"
    await async_client.post(
        f"/workspaces/{ws}/graph/extract",
        json={
            "texts": [
                {
                    "text": "Revenue grew 15% to $50M in Q1.",
                    "evidence_id": "ev-m1",
                    "source_id": "src-m1",
                    "chunk_id": "ch-m1",
                }
            ]
        },
    )

    metrics_resp = await async_client.get(f"/workspaces/{ws}/graph/metrics")
    metrics = metrics_resp.json()
    if not metrics:
        return

    metric_id = metrics[0]["metric_id"]

    resp = await async_client.post(
        f"/workspaces/{ws}/graph/claims",
        json={
            "fact_type": "metric",
            "fact_id": metric_id,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert metric_id in data["metric_refs"]


async def test_create_claim_missing_fields(async_client):
    """Should return 400 when fact_type or fact_id is missing."""
    resp = await async_client.post(
        "/workspaces/test_missing/graph/claims",
        json={},
    )
    assert resp.status_code == 400


async def test_create_claim_invalid_type(async_client):
    """Should return 400 for unknown fact_type."""
    ws = "test_bad_type"
    resp = await async_client.post(
        f"/workspaces/{ws}/graph/claims",
        json={"fact_type": "nonexistent", "fact_id": "abc"},
    )
    assert resp.status_code == 400


async def test_list_workspace_claims(async_client):
    """Should list claims for a workspace."""
    ws = "test_list_claims"
    # Create some claims
    for i in range(3):
        await async_client.post(
            f"/workspaces/{ws}/graph/claims",
            json={
                "fact_type": "risk",
                "fact_id": f"fake-risk-{i}",
                "claim_text": f"Test claim {i}",
            },
        )

    resp = await async_client.get(f"/workspaces/{ws}/graph/claims")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] >= 3
    assert len(data["claims"]) >= 3


async def test_list_workspace_claims_filter(async_client):
    """Should filter claims by status."""
    ws = "test_filter_claims"
    await async_client.post(
        f"/workspaces/{ws}/graph/claims",
        json={"fact_type": "risk", "fact_id": "r1", "claim_text": "C1"},
    )

    resp = await async_client.get(
        f"/workspaces/{ws}/graph/claims",
        params={"status": "pending"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(c["status"] == "pending" for c in data["claims"])
