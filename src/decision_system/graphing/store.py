"""Local JSON persistence for the workspace-scoped knowledge graph (v2).

Supports CRUD operations for workspace nodes, edges, risks, and metrics.
Persistence uses JSON files under ``.decision_system/graph/workspaces/{ws_id}/``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_system.graphing.models import (
    NodeType,
    WorkspaceEdge,
    WorkspaceGraph,
    WorkspaceMetric,
    WorkspaceNode,
    WorkspaceRisk,
)

# ---------------------------------------------------------------------------
# Default data root
# ---------------------------------------------------------------------------

DEFAULT_DATA_ROOT = Path(".decision_system") / "graph"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _workspace_dir(data_root: Path, workspace_id: str) -> Path:
    return data_root / "workspaces" / workspace_id


def _nodes_path(data_root: Path, workspace_id: str) -> Path:
    return _workspace_dir(data_root, workspace_id) / "nodes.json"


def _edges_path(data_root: Path, workspace_id: str) -> Path:
    return _workspace_dir(data_root, workspace_id) / "edges.json"


def _risks_path(data_root: Path, workspace_id: str) -> Path:
    return _workspace_dir(data_root, workspace_id) / "risks.json"


def _metrics_path(data_root: Path, workspace_id: str) -> Path:
    return _workspace_dir(data_root, workspace_id) / "metrics.json"


def _meta_path(data_root: Path, workspace_id: str) -> Path:
    return _workspace_dir(data_root, workspace_id) / "meta.json"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# JSON read/write helpers
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    _ensure_dir(path)
    path.write_text(
        json.dumps(data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Node CRUD
# ---------------------------------------------------------------------------


def upsert_node(
    node: WorkspaceNode,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceNode:
    """Insert or update a workspace node. Dedup by node_id."""
    path = _nodes_path(data_root, node.workspace_id)
    nodes = _read_json(path)
    node.updated_at = datetime.now(timezone.utc)

    for i, existing in enumerate(nodes):
        if existing.get("node_id") == node.node_id:
            nodes[i] = node.model_dump(mode="json")
            _write_json(path, nodes)
            return node

    nodes.append(node.model_dump(mode="json"))
    _write_json(path, nodes)
    _update_meta(data_root, node.workspace_id)
    return node


def get_node(
    node_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceNode | None:
    """Get a single node by ID within a workspace."""
    for entry in _read_json(_nodes_path(data_root, workspace_id)):
        if entry.get("node_id") == node_id:
            return WorkspaceNode.model_validate(entry)
    return None


def list_nodes(
    workspace_id: str,
    node_type: NodeType | None = None,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[WorkspaceNode]:
    """List all nodes in a workspace, optionally filtered by type."""
    nodes = _read_json(_nodes_path(data_root, workspace_id))
    result = [WorkspaceNode.model_validate(n) for n in nodes]
    if node_type:
        result = [n for n in result if n.node_type == node_type]
    return result


def search_nodes(
    query: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[WorkspaceNode]:
    """Search nodes by name (case-insensitive substring match)."""
    q = query.lower()
    nodes = _read_json(_nodes_path(data_root, workspace_id))
    return [
        WorkspaceNode.model_validate(n)
        for n in nodes
        if q in n.get("name", "").lower()
        or q in n.get("normalized_name", "").lower()
        or q in (n.get("description") or "").lower()
    ]


def delete_node(
    node_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> bool:
    """Delete a node and its associated edges. Returns True if deleted."""
    path = _nodes_path(data_root, workspace_id)
    nodes = _read_json(path)
    new_nodes = [n for n in nodes if n.get("node_id") != node_id]
    if len(new_nodes) == len(nodes):
        return False
    _write_json(path, new_nodes)

    # Clean up associated edges
    edges_path = _edges_path(data_root, workspace_id)
    edges = _read_json(edges_path)
    edges = [
        e for e in edges
        if e.get("source_node_id") != node_id and e.get("target_node_id") != node_id
    ]
    _write_json(edges_path, edges)

    _update_meta(data_root, workspace_id)
    return True


# ---------------------------------------------------------------------------
# Edge CRUD
# ---------------------------------------------------------------------------


def upsert_edge(
    edge: WorkspaceEdge,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceEdge:
    """Insert or update an edge. Dedup by edge_id."""
    path = _edges_path(data_root, edge.workspace_id)
    edges = _read_json(path)
    edge.updated_at = datetime.now(timezone.utc)

    for i, existing in enumerate(edges):
        if existing.get("edge_id") == edge.edge_id:
            edges[i] = edge.model_dump(mode="json")
            _write_json(path, edges)
            return edge

    edges.append(edge.model_dump(mode="json"))
    _write_json(path, edges)
    _update_meta(data_root, edge.workspace_id)
    return edge


def get_edge(
    edge_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceEdge | None:
    for entry in _read_json(_edges_path(data_root, workspace_id)):
        if entry.get("edge_id") == edge_id:
            return WorkspaceEdge.model_validate(entry)
    return None


def list_edges(
    workspace_id: str,
    edge_type: str | None = None,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[WorkspaceEdge]:
    edges = _read_json(_edges_path(data_root, workspace_id))
    result = [WorkspaceEdge.model_validate(e) for e in edges]
    if edge_type:
        result = [e for e in result if e.edge_type == edge_type]
    return result


def delete_edge(
    edge_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> bool:
    path = _edges_path(data_root, workspace_id)
    edges = _read_json(path)
    new_edges = [e for e in edges if e.get("edge_id") != edge_id]
    if len(new_edges) == len(edges):
        return False
    _write_json(path, new_edges)
    _update_meta(data_root, workspace_id)
    return True


# ---------------------------------------------------------------------------
# Workspace graph retrieval
# ---------------------------------------------------------------------------


def list_graph_for_workspace(
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceGraph:
    """Load the full graph (nodes + edges) for a workspace."""
    return WorkspaceGraph(
        workspace_id=workspace_id,
        nodes=list_nodes(workspace_id, data_root=data_root),
        edges=list_edges(workspace_id, data_root=data_root),
    )


# ---------------------------------------------------------------------------
# Risk CRUD
# ---------------------------------------------------------------------------


def upsert_risk(
    risk: WorkspaceRisk,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceRisk:
    path = _risks_path(data_root, risk.workspace_id)
    risks = _read_json(path)
    risk.updated_at = datetime.now(timezone.utc)

    for i, existing in enumerate(risks):
        if existing.get("risk_id") == risk.risk_id:
            risks[i] = risk.model_dump(mode="json")
            _write_json(path, risks)
            return risk

    risks.append(risk.model_dump(mode="json"))
    _write_json(path, risks)
    return risk


def get_risk(
    risk_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceRisk | None:
    for entry in _read_json(_risks_path(data_root, workspace_id)):
        if entry.get("risk_id") == risk_id:
            return WorkspaceRisk.model_validate(entry)
    return None


def list_risks(
    workspace_id: str,
    severity: str | None = None,
    category: str | None = None,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[WorkspaceRisk]:
    risks = _read_json(_risks_path(data_root, workspace_id))
    result = [WorkspaceRisk.model_validate(r) for r in risks]
    if severity:
        result = [r for r in result if r.severity == severity]
    if category:
        result = [r for r in result if r.category == category]
    return result


# ---------------------------------------------------------------------------
# Metric CRUD
# ---------------------------------------------------------------------------


def upsert_metric(
    metric: WorkspaceMetric,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceMetric:
    path = _metrics_path(data_root, metric.workspace_id)
    metrics = _read_json(path)
    metric.updated_at = datetime.now(timezone.utc)

    for i, existing in enumerate(metrics):
        if existing.get("metric_id") == metric.metric_id:
            metrics[i] = metric.model_dump(mode="json")
            _write_json(path, metrics)
            return metric

    metrics.append(metric.model_dump(mode="json"))
    _write_json(path, metrics)
    return metric


def get_metric(
    metric_id: str,
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> WorkspaceMetric | None:
    for entry in _read_json(_metrics_path(data_root, workspace_id)):
        if entry.get("metric_id") == metric_id:
            return WorkspaceMetric.model_validate(entry)
    return None


def list_metrics(
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> list[WorkspaceMetric]:
    metrics = _read_json(_metrics_path(data_root, workspace_id))
    return [WorkspaceMetric.model_validate(m) for m in metrics]


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


def _update_meta(data_root: Path, workspace_id: str) -> None:
    """Update workspace metadata (counts, timestamp)."""
    meta = {
        "workspace_id": workspace_id,
        "node_count": len(_read_json(_nodes_path(data_root, workspace_id))),
        "edge_count": len(_read_json(_edges_path(data_root, workspace_id))),
        "risk_count": len(_read_json(_risks_path(data_root, workspace_id))),
        "metric_count": len(_read_json(_metrics_path(data_root, workspace_id))),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    path = _meta_path(data_root, workspace_id)
    _ensure_dir(path)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def get_workspace_meta(
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> dict[str, Any]:
    """Get workspace graph metadata (counts, timestamps)."""
    path = _meta_path(data_root, workspace_id)
    if not path.exists():
        _update_meta(data_root, workspace_id)
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Delete all data for a workspace
# ---------------------------------------------------------------------------


def delete_workspace(
    workspace_id: str,
    data_root: Path = DEFAULT_DATA_ROOT,
) -> None:
    """Delete all graph data for a workspace."""
    import shutil
    ws_dir = _workspace_dir(data_root, workspace_id)
    if ws_dir.exists():
        shutil.rmtree(ws_dir)


# ---------------------------------------------------------------------------
# Legacy v1 functions (keep for backward compat)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Legacy v1 functions (keep for backward compat with CLI commands)
# ---------------------------------------------------------------------------


DEFAULT_GRAPH_PATH = Path(".decision_system") / "graph" / "knowledge_graph.json"


def save_knowledge_graph(
    graph: "KnowledgeGraph",
    path: Path | str = DEFAULT_GRAPH_PATH,
) -> Path:
    """Write a legacy v1 knowledge graph JSON file and return its path."""
    from decision_system.graphing.models import KnowledgeGraph
    if not isinstance(graph, KnowledgeGraph):
        graph = KnowledgeGraph.model_validate(graph)
    graph_path = Path(path)
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(graph.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return graph_path


def load_knowledge_graph(path: Path | str = DEFAULT_GRAPH_PATH) -> "KnowledgeGraph":
    """Load a legacy v1 knowledge graph JSON file, or return an empty graph."""
    from decision_system.graphing.models import KnowledgeGraph
    graph_path = Path(path)
    if not graph_path.exists():
        return KnowledgeGraph()
    return KnowledgeGraph.model_validate_json(graph_path.read_text(encoding="utf-8"))
