"""Graph extraction and retrieval API endpoints (v2).

All endpoints are workspace-scoped and return evidence-linked data.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException

from decision_system.graphing.audit import (
    graph_extraction_completed,
    graph_extraction_failed,
    graph_extraction_started,
    risk_extraction_completed as audit_risk_extraction_completed,
    metric_extraction_completed as audit_metric_extraction_completed,
)
from decision_system.graphing.extractor_v2 import extract_intelligence
from decision_system.graphing.models import NodeType
from decision_system.graphing.store import (
    DEFAULT_DATA_ROOT,
    get_edge,
    get_node,
    get_workspace_meta,
    list_edges,
    list_graph_for_workspace,
    list_metrics,
    list_nodes,
    list_risks,
    upsert_edge,
    upsert_metric,
    upsert_node,
    upsert_risk,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/graph", tags=["graph"])

# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field


class TextSource(BaseModel):
    """A single text input with evidence references."""

    text: str
    evidence_id: str = ""
    source_id: str = ""
    chunk_id: str = ""


class ExtractionRequest(BaseModel):
    """Request body for graph extraction."""

    texts: list[TextSource] = Field(default_factory=list)
    mode: str = "deterministic"
    include_ai: bool = False
    provider_id: str | None = None


class ExtractionResponse(BaseModel):
    """Response body for graph extraction."""

    workspace_id: str
    nodes_extracted: int = 0
    edges_extracted: int = 0
    risks_extracted: int = 0
    metrics_extracted: int = 0
    warnings: list[str] = Field(default_factory=list)


class GraphSummary(BaseModel):
    """Summary statistics for a workspace graph."""

    workspace_id: str
    node_count: int = 0
    edge_count: int = 0
    risk_count: int = 0
    metric_count: int = 0


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/extract", response_model=ExtractionResponse)
def extract_graph(
    workspace_id: str,
    request: ExtractionRequest,
) -> ExtractionResponse:
    """Extract entities, relationships, risks, and metrics from provided texts."""
    start_time = time.monotonic()
    graph_extraction_started(workspace_id)
    try:
        if not request.texts:
            return ExtractionResponse(
                workspace_id=workspace_id,
                warnings=["No texts provided for extraction"],
            )

        text_tuples = [
            (t.text, t.evidence_id, t.source_id, t.chunk_id)
            for t in request.texts
            if t.text.strip()
        ]

        if not text_tuples:
            return ExtractionResponse(
                workspace_id=workspace_id,
                warnings=["All provided texts were empty"],
            )

        result = extract_intelligence(text_tuples, workspace_id)

        for node in result.to_node_list():
            upsert_node(node, data_root=DEFAULT_DATA_ROOT)
        for edge in result.to_edge_list():
            upsert_edge(edge, data_root=DEFAULT_DATA_ROOT)
        for risk in result.to_risk_list():
            upsert_risk(risk, data_root=DEFAULT_DATA_ROOT)
        for metric in result.to_metric_list():
            upsert_metric(metric, data_root=DEFAULT_DATA_ROOT)

        duration_ms = (time.monotonic() - start_time) * 1000.0
        graph_extraction_completed(
            workspace_id=workspace_id,
            duration_ms=duration_ms,
            entities_count=len(result.nodes),
            edges_count=len(result.edges),
            risks_count=len(result.risks),
            metrics_count=len(result.metrics),
        )
        if result.risks:
            audit_risk_extraction_completed(workspace_id, risks_count=len(result.risks))
        if result.metrics:
            audit_metric_extraction_completed(workspace_id, metrics_count=len(result.metrics))

        return ExtractionResponse(
            workspace_id=workspace_id,
            nodes_extracted=len(result.nodes),
            edges_extracted=len(result.edges),
            risks_extracted=len(result.risks),
            metrics_extracted=len(result.metrics),
            warnings=result.warnings,
        )
    except Exception as exc:
        duration_ms = (time.monotonic() - start_time) * 1000.0
        graph_extraction_failed(workspace_id, str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=dict)
def get_graph(workspace_id: str) -> dict[str, Any]:
    """Get the full graph for a workspace."""
    graph = list_graph_for_workspace(workspace_id, data_root=DEFAULT_DATA_ROOT)
    return {
        "workspace_id": graph.workspace_id,
        "nodes": [n.model_dump(mode="json") for n in graph.nodes],
        "edges": [e.model_dump(mode="json") for e in graph.edges],
    }


@router.get("/nodes", response_model=list[dict])
def list_graph_nodes(
    workspace_id: str,
    node_type: str | None = None,
) -> list[dict]:
    """List graph nodes for a workspace, optionally filtered by type."""
    ntype: NodeType | None = None
    if node_type:
        ntype = node_type  # type: ignore[assignment]
    nodes = list_nodes(workspace_id, node_type=ntype, data_root=DEFAULT_DATA_ROOT)
    return [n.model_dump(mode="json") for n in nodes]


@router.get("/edges", response_model=list[dict])
def list_graph_edges(
    workspace_id: str,
    edge_type: str | None = None,
) -> list[dict]:
    """List graph edges for a workspace, optionally filtered by type."""
    edges = list_edges(workspace_id, edge_type=edge_type, data_root=DEFAULT_DATA_ROOT)
    return [e.model_dump(mode="json") for e in edges]


@router.get("/risks", response_model=list[dict])
def list_graph_risks(
    workspace_id: str,
    severity: str | None = None,
    category: str | None = None,
) -> list[dict]:
    """List risks for a workspace, optionally filtered."""
    risks = list_risks(workspace_id, severity=severity, category=category, data_root=DEFAULT_DATA_ROOT)
    return [r.model_dump(mode="json") for r in risks]


@router.get("/metrics", response_model=list[dict])
def list_graph_metrics(workspace_id: str) -> list[dict]:
    """List metrics for a workspace."""
    metrics = list_metrics(workspace_id, data_root=DEFAULT_DATA_ROOT)
    return [m.model_dump(mode="json") for m in metrics]


@router.get("/summary", response_model=GraphSummary)
def graph_summary(workspace_id: str) -> GraphSummary:
    """Get summary statistics for a workspace graph."""
    meta = get_workspace_meta(workspace_id, data_root=DEFAULT_DATA_ROOT)
    return GraphSummary(
        workspace_id=workspace_id,
        node_count=meta.get("node_count", 0),
        edge_count=meta.get("edge_count", 0),
        risk_count=meta.get("risk_count", 0),
        metric_count=meta.get("metric_count", 0),
    )


@router.get("/nodes/{node_id}", response_model=dict | None)
def get_graph_node(workspace_id: str, node_id: str) -> dict | None:
    """Get a single graph node by ID."""
    node = get_node(node_id, workspace_id, data_root=DEFAULT_DATA_ROOT)
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return node.model_dump(mode="json")


@router.get("/edges/{edge_id}", response_model=dict | None)
def get_graph_edge(workspace_id: str, edge_id: str) -> dict | None:
    """Get a single graph edge by ID."""
    edge = get_edge(edge_id, workspace_id, data_root=DEFAULT_DATA_ROOT)
    if edge is None:
        raise HTTPException(status_code=404, detail=f"Edge not found: {edge_id}")
    return edge.model_dump(mode="json")
