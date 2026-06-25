"""Tests for the v2 workspace-scoped graph store and models."""

from decision_system.graphing.models import (
    WorkspaceEdge,
    WorkspaceMetric,
    WorkspaceNode,
    WorkspaceRisk,
)
from decision_system.graphing.store import (
    delete_edge,
    delete_node,
    delete_workspace,
    get_edge,
    get_metric,
    get_node,
    get_risk,
    get_workspace_meta,
    list_edges,
    list_graph_for_workspace,
    list_metrics,
    list_nodes,
    list_risks,
    search_nodes,
    upsert_edge,
    upsert_metric,
    upsert_node,
    upsert_risk,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_WS = "test-workspace"


def _node(**kwargs) -> WorkspaceNode:
    defaults = dict(
        node_id="node-test-1",
        workspace_id=TEST_WS,
        node_type="company",
        name="Test Corp",
        normalized_name="test corp",
    )
    defaults.update(kwargs)
    return WorkspaceNode(**defaults)


def _edge(**kwargs) -> WorkspaceEdge:
    defaults = dict(
        edge_id="edge-test-1",
        workspace_id=TEST_WS,
        source_node_id="node-a",
        target_node_id="node-b",
        edge_type="depends_on",
        label="depends on",
    )
    defaults.update(kwargs)
    return WorkspaceEdge(**defaults)


def _risk(**kwargs) -> WorkspaceRisk:
    defaults = dict(
        risk_id="risk-test-1",
        workspace_id=TEST_WS,
        title="Test Risk",
        description="A test risk for testing",
        severity="high",
    )
    defaults.update(kwargs)
    return WorkspaceRisk(**defaults)


def _metric(**kwargs) -> WorkspaceMetric:
    defaults = dict(
        metric_id="metric-test-1",
        workspace_id=TEST_WS,
        name="Revenue",
        value="1000000",
        unit="USD",
    )
    defaults.update(kwargs)
    return WorkspaceMetric(**defaults)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_workspace_node_model():
    node = _node()
    assert node.node_id == "node-test-1"
    assert node.workspace_id == TEST_WS
    assert node.node_type == "company"
    assert node.status == "extracted"
    assert node.confidence == "medium"

    payload = node.model_dump(mode="json")
    assert payload["node_id"] == "node-test-1"
    assert payload["workspace_id"] == TEST_WS
    assert payload["node_type"] == "company"


def test_workspace_edge_model():
    edge = _edge()
    assert edge.edge_id == "edge-test-1"
    assert edge.source_node_id == "node-a"
    assert edge.target_node_id == "node-b"
    assert edge.edge_type == "depends_on"

    payload = edge.model_dump(mode="json")
    assert payload["edge_id"] == "edge-test-1"
    assert payload["edge_type"] == "depends_on"


def test_workspace_risk_model():
    risk = _risk()
    assert risk.risk_id == "risk-test-1"
    assert risk.severity == "high"
    assert risk.category == "unknown"
    assert risk.status == "extracted"


def test_workspace_metric_model():
    metric = _metric()
    assert metric.metric_id == "metric-test-1"
    assert metric.name == "Revenue"
    assert metric.value == "1000000"
    assert metric.unit == "USD"


# ---------------------------------------------------------------------------
# Node CRUD
# ---------------------------------------------------------------------------


def test_upsert_and_get_node(tmp_path):
    node = _node(node_id="node-crud-1")
    upsert_node(node, data_root=tmp_path)

    loaded = get_node("node-crud-1", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert loaded.node_id == "node-crud-1"
    assert loaded.name == "Test Corp"
    assert loaded.workspace_id == TEST_WS


def test_get_nonexistent_node(tmp_path):
    loaded = get_node("nope", TEST_WS, data_root=tmp_path)
    assert loaded is None


def test_list_nodes(tmp_path):
    upsert_node(_node(node_id="n1", name="Alpha"), data_root=tmp_path)
    upsert_node(_node(node_id="n2", name="Beta", node_type="person"), data_root=tmp_path)

    all_nodes = list_nodes(TEST_WS, data_root=tmp_path)
    assert len(all_nodes) == 2

    filtered = list_nodes(TEST_WS, node_type="person", data_root=tmp_path)
    assert len(filtered) == 1
    assert filtered[0].name == "Beta"


def test_search_nodes(tmp_path):
    upsert_node(_node(node_id="n1", name="Acme Corp"), data_root=tmp_path)
    upsert_node(_node(node_id="n2", name="Globex"), data_root=tmp_path)

    results = search_nodes("acme", TEST_WS, data_root=tmp_path)
    assert len(results) == 1
    assert results[0].name == "Acme Corp"

    results = search_nodes("xyz", TEST_WS, data_root=tmp_path)
    assert len(results) == 0


def test_delete_node(tmp_path):
    upsert_node(_node(node_id="n1"), data_root=tmp_path)
    upsert_node(_node(node_id="n2"), data_root=tmp_path)

    assert delete_node("n1", TEST_WS, data_root=tmp_path) is True
    assert len(list_nodes(TEST_WS, data_root=tmp_path)) == 1

    assert delete_node("n1", TEST_WS, data_root=tmp_path) is False


def test_delete_node_removes_edges(tmp_path):
    upsert_node(_node(node_id="n-a"), data_root=tmp_path)
    upsert_node(_node(node_id="n-b"), data_root=tmp_path)
    upsert_edge(
        _edge(edge_id="e1", source_node_id="n-a", target_node_id="n-b"),
        data_root=tmp_path,
    )

    delete_node("n-a", TEST_WS, data_root=tmp_path)
    assert len(list_edges(TEST_WS, data_root=tmp_path)) == 0


def test_upsert_node_updates_existing(tmp_path):
    node = _node(node_id="n1", name="Original")
    upsert_node(node, data_root=tmp_path)

    updated = _node(node_id="n1", name="Updated")
    upsert_node(updated, data_root=tmp_path)

    nodes = list_nodes(TEST_WS, data_root=tmp_path)
    assert len(nodes) == 1
    assert nodes[0].name == "Updated"


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------


def test_upsert_and_get_edge(tmp_path):
    edge = _edge(edge_id="edge-crud-1")
    upsert_edge(edge, data_root=tmp_path)

    loaded = get_edge("edge-crud-1", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert loaded.edge_id == "edge-crud-1"
    assert loaded.edge_type == "depends_on"


def test_list_edges_filtered(tmp_path):
    upsert_edge(_edge(edge_id="e1", edge_type="depends_on"), data_root=tmp_path)
    upsert_edge(_edge(edge_id="e2", edge_type="affects"), data_root=tmp_path)

    all_edges = list_edges(TEST_WS, data_root=tmp_path)
    assert len(all_edges) == 2

    filtered = list_edges(TEST_WS, edge_type="affects", data_root=tmp_path)
    assert len(filtered) == 1


def test_delete_edge(tmp_path):
    upsert_edge(_edge(edge_id="e1"), data_root=tmp_path)
    upsert_edge(_edge(edge_id="e2"), data_root=tmp_path)

    assert delete_edge("e1", TEST_WS, data_root=tmp_path) is True
    assert len(list_edges(TEST_WS, data_root=tmp_path)) == 1

    assert delete_edge("e1", TEST_WS, data_root=tmp_path) is False


# ---------------------------------------------------------------------------
# Workspace graph
# ---------------------------------------------------------------------------


def test_list_graph_for_workspace(tmp_path):
    upsert_node(_node(node_id="n1"), data_root=tmp_path)
    upsert_node(_node(node_id="n2"), data_root=tmp_path)
    upsert_edge(
        _edge(edge_id="e1", source_node_id="n1", target_node_id="n2"),
        data_root=tmp_path,
    )

    graph = list_graph_for_workspace(TEST_WS, data_root=tmp_path)
    assert graph.workspace_id == TEST_WS
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1


# ---------------------------------------------------------------------------
# Risk CRUD
# ---------------------------------------------------------------------------


def test_upsert_and_get_risk(tmp_path):
    risk = _risk(risk_id="risk-crud-1")
    upsert_risk(risk, data_root=tmp_path)

    loaded = get_risk("risk-crud-1", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert loaded.risk_id == "risk-crud-1"
    assert loaded.severity == "high"


def test_list_risks_filtered(tmp_path):
    upsert_risk(_risk(risk_id="r1", severity="high", category="financial"), data_root=tmp_path)
    upsert_risk(_risk(risk_id="r2", severity="low", category="operational"), data_root=tmp_path)
    upsert_risk(_risk(risk_id="r3", severity="high", category="security"), data_root=tmp_path)

    high_risks = list_risks(TEST_WS, severity="high", data_root=tmp_path)
    assert len(high_risks) == 2

    financial_risks = list_risks(TEST_WS, category="financial", data_root=tmp_path)
    assert len(financial_risks) == 1


# ---------------------------------------------------------------------------
# Metric CRUD
# ---------------------------------------------------------------------------


def test_upsert_and_get_metric(tmp_path):
    metric = _metric(metric_id="metric-crud-1")
    upsert_metric(metric, data_root=tmp_path)

    loaded = get_metric("metric-crud-1", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert loaded.metric_id == "metric-crud-1"
    assert loaded.value == "1000000"


def test_list_metrics(tmp_path):
    upsert_metric(_metric(metric_id="m1"), data_root=tmp_path)
    upsert_metric(_metric(metric_id="m2"), data_root=tmp_path)

    metrics = list_metrics(TEST_WS, data_root=tmp_path)
    assert len(metrics) == 2


# ---------------------------------------------------------------------------
# Workspace isolation
# ---------------------------------------------------------------------------


def test_workspace_isolation(tmp_path):
    upsert_node(_node(node_id="n1", workspace_id="ws-a"), data_root=tmp_path)
    upsert_node(_node(node_id="n2", workspace_id="ws-b"), data_root=tmp_path)

    ws_a_nodes = list_nodes("ws-a", data_root=tmp_path)
    ws_b_nodes = list_nodes("ws-b", data_root=tmp_path)

    assert len(ws_a_nodes) == 1
    assert len(ws_b_nodes) == 1


# ---------------------------------------------------------------------------
# Workspace meta
# ---------------------------------------------------------------------------


def test_workspace_meta(tmp_path):
    upsert_node(_node(node_id="n1"), data_root=tmp_path)
    upsert_edge(_edge(edge_id="e1"), data_root=tmp_path)

    meta = get_workspace_meta(TEST_WS, data_root=tmp_path)
    assert meta["workspace_id"] == TEST_WS
    assert meta["node_count"] == 1
    assert meta["edge_count"] == 1


# ---------------------------------------------------------------------------
# Delete workspace
# ---------------------------------------------------------------------------


def test_delete_workspace(tmp_path):
    upsert_node(_node(node_id="n1"), data_root=tmp_path)
    delete_workspace(TEST_WS, data_root=tmp_path)

    assert len(list_nodes(TEST_WS, data_root=tmp_path)) == 0


# ---------------------------------------------------------------------------
# Persistence across reloads
# ---------------------------------------------------------------------------


def test_persistence_survives_reload(tmp_path, monkeypatch):
    upsert_node(_node(node_id="persist-1"), data_root=tmp_path)

    # Simulate reload by reading from the same path
    nodes = list_nodes(TEST_WS, data_root=tmp_path)
    assert len(nodes) == 1
    assert nodes[0].node_id == "persist-1"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_workspace(tmp_path):
    graph = list_graph_for_workspace("empty-ws", data_root=tmp_path)
    assert graph.workspace_id == "empty-ws"
    assert len(graph.nodes) == 0
    assert len(graph.edges) == 0


def test_risk_with_recommended_actions(tmp_path):
    risk = _risk(
        risk_id="risk-actions",
        recommended_actions=["Update firewall", "Patch servers"],
    )
    upsert_risk(risk, data_root=tmp_path)

    loaded = get_risk("risk-actions", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert len(loaded.recommended_actions) == 2
    assert "Update firewall" in loaded.recommended_actions


def test_metric_with_entity_refs(tmp_path):
    metric = _metric(
        metric_id="metric-refs",
        entity_refs=["entity-billing", "entity-payments"],
        period="Q1 2026",
    )
    upsert_metric(metric, data_root=tmp_path)

    loaded = get_metric("metric-refs", TEST_WS, data_root=tmp_path)
    assert loaded is not None
    assert len(loaded.entity_refs) == 2
    assert loaded.period == "Q1 2026"
