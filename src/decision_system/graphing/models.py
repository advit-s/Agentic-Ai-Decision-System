"""Typed models for the local company knowledge graph.

v1 (legacy): Entity, Relationship, KnowledgeGraph — kept for backward compat.
v2 (current): WorkspaceNode, WorkspaceEdge, WorkspaceGraph — workspace-scoped,
              evidence-linked, with expanded types and status tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from decision_system.models import ConfidenceLevel

# ---------------------------------------------------------------------------
# v2 — Expanded node and edge type literals
# ---------------------------------------------------------------------------

NodeType = Literal[
    "company",
    "person",
    "team",
    "vendor",
    "customer",
    "product",
    "system",
    "document",
    "dataset",
    "metric",
    "risk",
    "event",
    "decision",
    "unknown",
]

EdgeType = Literal[
    "mentions",
    "owns",
    "depends_on",
    "supplies",
    "affects",
    "contradicts",
    "supports",
    "related_to",
    "has_metric",
    "has_risk",
    "occurred_on",
    "evidence_for",
]

NodeStatus = Literal[
    "extracted",
    "verified",
    "contradicted",
    "uncertain",
    "archived",
]

# ---------------------------------------------------------------------------
# v2 — WorkspaceNode
# ---------------------------------------------------------------------------


class WorkspaceNode(BaseModel):
    """A company object mentioned in workspace evidence (v2)."""

    node_id: str
    workspace_id: str
    node_type: NodeType = "unknown"
    name: str
    normalized_name: str = ""
    description: str | None = None
    confidence: ConfidenceLevel = "medium"
    status: NodeStatus = "extracted"
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# v2 — WorkspaceEdge
# ---------------------------------------------------------------------------


class WorkspaceEdge(BaseModel):
    """A directed relationship between two workspace nodes (v2)."""

    edge_id: str
    workspace_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = "related_to"
    label: str = ""
    confidence: ConfidenceLevel = "medium"
    status: NodeStatus = "extracted"
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# v2 — WorkspaceGraph (container)
# ---------------------------------------------------------------------------


class WorkspaceGraph(BaseModel):
    """Container for a workspace-scoped knowledge graph (v2)."""

    workspace_id: str
    nodes: list[WorkspaceNode] = Field(default_factory=list)
    edges: list[WorkspaceEdge] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # -- convenience helpers --------------------------------------------------

    def node_by_id(self, node_id: str) -> WorkspaceNode | None:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        return None

    def edges_for_node(self, node_id: str) -> list[WorkspaceEdge]:
        return [
            e for e in self.edges
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]

    def nodes_by_type(self, node_type: NodeType) -> list[WorkspaceNode]:
        return [n for n in self.nodes if n.node_type == node_type]


# ---------------------------------------------------------------------------
# v2 — Risk
# ---------------------------------------------------------------------------

RiskSeverity = Literal["low", "medium", "high", "critical"]
RiskCategory = Literal[
    "financial",
    "operational",
    "security",
    "compliance",
    "vendor",
    "technical",
    "strategic",
    "reputational",
    "unknown",
]


class WorkspaceRisk(BaseModel):
    """A detected risk linked to workspace evidence (v2)."""

    risk_id: str
    workspace_id: str
    title: str = ""
    description: str = ""
    severity: RiskSeverity = "medium"
    category: RiskCategory = "unknown"
    confidence: ConfidenceLevel = "medium"
    status: NodeStatus = "extracted"
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    related_entity_ids: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# v2 — Metric
# ---------------------------------------------------------------------------


class WorkspaceMetric(BaseModel):
    """An extracted metric linked to workspace evidence (v2)."""

    metric_id: str
    workspace_id: str
    name: str = ""
    value: str = ""
    unit: str = ""
    period: str | None = None
    entity_refs: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "medium"
    status: NodeStatus = "extracted"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# v1 — Legacy models (keep for backward compat with extractor/inspector)
# ---------------------------------------------------------------------------

EntityType = Literal[
    "project",
    "system",
    "team",
    "person",
    "vendor",
    "customer",
    "incident",
    "risk",
    "decision",
    "technology",
    "unknown",
]

RelationType = Literal[
    "depends_on",
    "owned_by",
    "caused",
    "affects",
    "blocks",
    "mitigates",
    "contradicts",
    "related_to",
]


class Entity(BaseModel):
    """Legacy v1 entity — kept for backward compatibility."""

    entity_id: str
    name: str
    entity_type: EntityType
    source_evidence_ids: list[str] = Field(default_factory=list)
    source_filenames: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel


class Relationship(BaseModel):
    """Legacy v1 relationship — kept for backward compatibility."""

    relationship_id: str
    source_entity_id: str
    relation_type: RelationType
    target_entity_id: str
    source_evidence_ids: list[str] = Field(default_factory=list)
    source_filenames: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel


class KnowledgeGraph(BaseModel):
    """Legacy v1 graph container — kept for backward compatibility."""

    entities: list[Entity] = Field(default_factory=list)
    relationships: list[Relationship] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# v2 — Extraction Run Record
# ---------------------------------------------------------------------------


class ExtractionRunRecord(BaseModel):
    """Record of a single graph extraction run."""

    run_id: str = Field(default_factory=lambda: __import__("uuid").uuid4().hex)
    workspace_id: str = ""
    started_at: str = ""
    completed_at: str = ""
    status: str = "running"
    mode: str = "deterministic"
    include_ai: bool = False
    source_ids: list[str] = Field(default_factory=list)
    chunks_processed: int = 0
    nodes_created: int = 0
    edges_created: int = 0
    risks_created: int = 0
    metrics_created: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_ms: float = 0.0
