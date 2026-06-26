"""Graph extraction and retrieval API endpoints (v2).

All endpoints are workspace-scoped and return evidence-linked data.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from decision_system.graphing.audit import (
    graph_extraction_completed,
    graph_extraction_failed,
    graph_extraction_started,
)
from decision_system.graphing.audit import (
    metric_extraction_completed as audit_metric_extraction_completed,
)
from decision_system.graphing.audit import (
    risk_extraction_completed as audit_risk_extraction_completed,
)
from decision_system.graphing.extractor_v2 import extract_intelligence
from decision_system.graphing.models import NodeType
from decision_system.graphing.store import (
    get_default_data_root,
    get_edge,
    get_node,
    get_workspace_meta,
    list_edges,
    list_graph_for_workspace,
    list_metrics,
    list_nodes,
    list_risks,
    record_extraction_run,
    upsert_edge,
    upsert_metric,
    upsert_node,
    upsert_risk,
)
from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import (
    require_workspace_permission,
)

router = APIRouter(prefix="/workspaces/{workspace_id}/graph", tags=["graph"])

# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


from pydantic import BaseModel, Field

from decision_system.observability.store import list_metric_names, load_metric_points


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
    user: LocalUser = Depends(require_workspace_permission(Permission.GRAPH_EXTRACT)),
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
            upsert_node(node, data_root=get_default_data_root())
        for edge in result.to_edge_list():
            upsert_edge(edge, data_root=get_default_data_root())
        for risk in result.to_risk_list():
            upsert_risk(risk, data_root=get_default_data_root())
        for metric in result.to_metric_list():
            upsert_metric(metric, data_root=get_default_data_root())

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

        # Record extraction run
        record_extraction_run(
            workspace_id=workspace_id,
            status="completed",
            mode=request.mode,
            include_ai=request.include_ai,
            source_ids=[t.source_id for t in request.texts if t.source_id],
            chunks_processed=len(request.texts),
            nodes_created=len(result.nodes),
            edges_created=len(result.edges),
            risks_created=len(result.risks),
            metrics_created=len(result.metrics),
            warnings=result.warnings,
            duration_ms=duration_ms,
        )

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
        # Record failed extraction run
        record_extraction_run(
            workspace_id=workspace_id,
            status="failed",
            mode=request.mode,
            include_ai=request.include_ai,
            source_ids=[t.source_id for t in request.texts if t.source_id],
            chunks_processed=len(request.texts),
            errors=[str(exc)],
            duration_ms=duration_ms,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("", response_model=dict)
def get_graph(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict[str, Any]:
    """Get the full graph for a workspace."""
    graph = list_graph_for_workspace(workspace_id, data_root=get_default_data_root())
    return {
        "workspace_id": graph.workspace_id,
        "nodes": [n.model_dump(mode="json") for n in graph.nodes],
        "edges": [e.model_dump(mode="json") for e in graph.edges],
    }


@router.get("/nodes", response_model=list[dict])
def list_graph_nodes(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    node_type: str | None = None,
) -> list[dict]:
    """List graph nodes for a workspace, optionally filtered by type."""
    ntype: NodeType | None = None
    if node_type:
        ntype = node_type  # type: ignore[assignment]
    nodes = list_nodes(workspace_id, node_type=ntype, data_root=get_default_data_root())
    return [n.model_dump(mode="json") for n in nodes]


@router.get("/edges", response_model=list[dict])
def list_graph_edges(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    edge_type: str | None = None,
) -> list[dict]:
    """List graph edges for a workspace, optionally filtered by type."""
    edges = list_edges(workspace_id, edge_type=edge_type, data_root=get_default_data_root())
    return [e.model_dump(mode="json") for e in edges]


@router.get("/risks", response_model=list[dict])
def list_graph_risks(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    severity: str | None = None,
    category: str | None = None,
) -> list[dict]:
    """List risks for a workspace, optionally filtered."""
    risks = list_risks(
        workspace_id,
        severity=severity,
        category=category,
        data_root=get_default_data_root(),
    )
    return [r.model_dump(mode="json") for r in risks]


@router.get("/metrics", response_model=list[dict])
def list_graph_metrics(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> list[dict]:
    """List metrics for a workspace."""
    metrics = list_metrics(workspace_id, data_root=get_default_data_root())
    return [m.model_dump(mode="json") for m in metrics]


@router.get("/summary", response_model=GraphSummary)
def graph_summary(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> GraphSummary:
    """Get summary statistics for a workspace graph."""
    meta = get_workspace_meta(workspace_id, data_root=get_default_data_root())
    return GraphSummary(
        workspace_id=workspace_id,
        node_count=meta.get("node_count", 0),
        edge_count=meta.get("edge_count", 0),
        risk_count=meta.get("risk_count", 0),
        metric_count=meta.get("metric_count", 0),
    )


@router.get("/nodes/{node_id}", response_model=dict | None)
def get_graph_node(
    workspace_id: str,
    node_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict | None:
    """Get a single graph node by ID."""
    node = get_node(node_id, workspace_id, data_root=get_default_data_root())
    if node is None:
        raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")
    return node.model_dump(mode="json")


@router.get("/edges/{edge_id}", response_model=dict | None)
def get_graph_edge(
    workspace_id: str,
    edge_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict | None:
    """Get a single graph edge by ID."""
    edge = get_edge(edge_id, workspace_id, data_root=get_default_data_root())
    if edge is None:
        raise HTTPException(status_code=404, detail=f"Edge not found: {edge_id}")
    return edge.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Audit / Metrics / Extraction Run response models
# ---------------------------------------------------------------------------

_GRAPH_EVENT_NAMES = frozenset(
    {
        "graph_extraction_started",
        "graph_extraction_completed",
        "graph_extraction_failed",
        "risk_extraction_completed",
        "metric_extraction_completed",
        "graph_fact_created",
    }
)

_GRAPH_METRIC_NAMES = frozenset(
    {
        "graph_extraction_duration_ms",
        "entities_extracted_count",
        "edges_extracted_count",
        "risks_extracted_count",
        "metrics_extracted_count",
        "graph_extraction_failure_count",
    }
)


@router.get("/audit-events")
def list_graph_audit_events(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    event_type: str | None = Query(None, description="Filter by event type"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    """List graph audit events for a workspace, filtering by workspace_id label."""
    all_events: list[dict] = []
    metric_names = list_metric_names()
    for name in metric_names:
        if name not in _GRAPH_EVENT_NAMES:
            continue
        if event_type and name != event_type:
            continue
        points = load_metric_points(name)
        for p in points:
            labels = p.labels or {}
            if labels.get("workspace_id") != workspace_id:
                continue
            all_events.append(
                {
                    "event_type": name,
                    "timestamp": p.timestamp.isoformat(),
                    "value": p.value,
                    "labels": labels,
                }
            )
    all_events.sort(key=lambda e: e["timestamp"], reverse=True)
    return {
        "workspace_id": workspace_id,
        "events": all_events[:limit],
        "total_count": len(all_events),
    }


@router.get("/metrics/aggregates")
def list_graph_metrics_aggregated(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict:
    """List aggregated graph observability metrics for a workspace."""
    result: dict = {
        "workspace_id": workspace_id,
        "metrics": {},
        "last_extraction_at": None,
    }
    metric_names = list_metric_names()
    for name in _GRAPH_METRIC_NAMES:
        if name not in metric_names:
            continue
        points = load_metric_points(name)
        ws_points = [p for p in points if (p.labels or {}).get("workspace_id") == workspace_id]
        if not ws_points:
            continue
        values = [p.value for p in ws_points]
        last_ts = max(p.timestamp for p in ws_points)
        result["metrics"][name] = {
            "count": len(values),
            "sum": sum(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "last_value": values[-1],
            "last_timestamp": last_ts.isoformat(),
        }
        if name == "graph_extraction_duration_ms":
            result["last_extraction_at"] = last_ts.isoformat()
    return result


@router.get("/extraction-runs")
def list_graph_extraction_runs(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    limit: int = Query(50, ge=1, le=500),
) -> dict:
    """List extraction run records for a workspace."""
    from decision_system.graphing.store import list_extraction_runs as _list_runs

    runs = _list_runs(workspace_id)
    run_dicts = [r.model_dump(mode="json") for r in runs[:limit]]
    return {
        "workspace_id": workspace_id,
        "runs": run_dicts,
        "total_count": len(runs),
    }


@router.get("/extraction-runs/{run_id}")
def get_graph_extraction_run(
    workspace_id: str,
    run_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict:
    """Get a single extraction run by ID."""
    from decision_system.graphing.store import get_extraction_run as _get_run

    run = _get_run(workspace_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Extraction run not found: {run_id}")
    return run.model_dump(mode="json")


@router.get("/latest-extraction")
def get_latest_extraction(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
) -> dict | None:
    """Get the most recent extraction run for a workspace."""
    from decision_system.graphing.store import get_latest_extraction_run as _get_latest

    run = _get_latest(workspace_id)
    if run is None:
        return None
    return run.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Graph-to-Claim
# ---------------------------------------------------------------------------


@router.post("/claims", status_code=201)
def create_claim_from_graph_fact(
    workspace_id: str,
    request: dict,
    user: LocalUser = Depends(require_workspace_permission(Permission.CLAIM_VERIFY)),
) -> dict:
    """Create a pending claim from a graph fact (risk, metric, or relationship).

    Request body:
    {
        "fact_type": "risk" | "metric" | "relationship",
        "fact_id": "the graph object ID",
        "claim_text": "Optional override text",
        "source_ids": ["src1"],
        "evidence_ids": ["ev1"]
    }
    """
    fact_type = request.get("fact_type", "")
    fact_id = request.get("fact_id", "")
    claim_text = request.get("claim_text", "")
    source_ids = request.get("source_ids", [])
    evidence_ids = request.get("evidence_ids", [])

    if not fact_type or not fact_id:
        raise HTTPException(status_code=400, detail="fact_type and fact_id are required")

    from uuid import uuid4

    # Build graph refs based on fact_type
    node_refs: list[str] = []
    edge_refs: list[str] = []
    risk_refs: list[str] = []
    metric_refs: list[str] = []

    if fact_type == "risk":
        risk_refs = [fact_id]
        # Also look up the risk to build claim text
        from decision_system.graphing.store import list_risks

        risks = list_risks(workspace_id)
        for r in risks:
            if r.risk_id == fact_id:
                if not claim_text:
                    claim_text = r.title or f"Risk: {r.description[:200]}"
                source_ids = source_ids or r.source_ids
                evidence_ids = evidence_ids or r.evidence_ids
                break
    elif fact_type == "metric":
        metric_refs = [fact_id]
        from decision_system.graphing.store import list_metrics

        metrics = list_metrics(workspace_id)
        for m in metrics:
            if m.metric_id == fact_id:
                if not claim_text:
                    claim_text = f"Metric: {m.name} = {m.value} {m.unit or ''}"
                source_ids = source_ids or m.source_ids
                evidence_ids = evidence_ids or m.evidence_ids
                break
    elif fact_type == "relationship":
        edge_refs = [fact_id]
        from decision_system.graphing.store import list_edges

        edges = list_edges(workspace_id)
        for e in edges:
            if e.edge_id == fact_id:
                if not claim_text:
                    claim_text = (
                        f"Relationship: {e.source_node_id} {e.edge_type} {e.target_node_id}"
                    )
                source_ids = source_ids or e.source_ids
                evidence_ids = evidence_ids or e.evidence_ids
                break
    elif fact_type == "entity":
        node_refs = [fact_id]
        from decision_system.graphing.store import list_nodes

        nodes = list_nodes(workspace_id)
        for n in nodes:
            if n.node_id == fact_id:
                if not claim_text:
                    claim_text = f"Entity: {n.name} ({n.node_type})"
                source_ids = source_ids or n.source_ids
                evidence_ids = evidence_ids or n.evidence_ids
                break
    else:
        raise HTTPException(status_code=400, detail=f"Unknown fact_type: {fact_type}")

    if not claim_text:
        claim_text = f"Claim from {fact_type} {fact_id[:20]}"

    from decision_system._data_root import get_data_root
    from decision_system.models import Claim as ClaimModel
    from decision_system.workflow_engine.stores.claim_store import JSONClaimStore

    claim_id = str(uuid4())
    claim = ClaimModel(
        claim_id=claim_id,
        run_id=str(uuid4()),
        workspace_id=workspace_id,
        source_agent="graph_extraction",
        claim_text=claim_text,
        claim_type="fact",
        status="pending",
        confidence="medium",
        evidence_ids=evidence_ids or [],
        source_ids=source_ids or [],
        graph_node_refs=node_refs or [],
        graph_edge_refs=edge_refs or [],
        risk_refs=risk_refs or [],
        metric_refs=metric_refs or [],
    )

    claim_store = JSONClaimStore(get_data_root())
    claim_store.save(claim)

    # Also save to graphing store for backward compat during migration
    from decision_system.graphing.store import save_workspace_claim

    save_workspace_claim(claim.model_dump(mode="json"))

    # Also emit audit event
    from decision_system.graphing.audit import graph_fact_created

    graph_fact_created(workspace_id, fact_type=fact_type, fact_id=fact_id)

    return claim.model_dump(mode="json")


@router.get("/claims")
def list_workspace_claims(
    workspace_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
    status: str | None = Query(None, description="Filter by status"),
) -> dict:
    """List claims created from graph facts for a workspace."""
    from decision_system._data_root import get_data_root
    from decision_system.workflow_engine.stores.claim_store import JSONClaimStore

    store = JSONClaimStore(get_data_root())
    claims = store.list(workspace_id=workspace_id)

    if status:
        claims = [c for c in claims if c.status == status]

    return {
        "workspace_id": workspace_id,
        "claims": [c.model_dump(mode="json") for c in claims],
        "total_count": len(claims),
    }
