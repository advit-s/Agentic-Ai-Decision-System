"""Workflow graph nodes for v2 knowledge graph extraction and analysis.

Node types:
  - GraphExtractionNode: Extract entities, relationships, risks, metrics from text
  - RiskExtractionNode: Extract risks from evidence
  - MetricExtractionNode: Extract metrics from evidence
  - GraphSummaryNode: Summarize graph for reports
"""

from __future__ import annotations

import time

from decision_system.graphing.audit import (
    graph_extraction_completed,
    graph_extraction_started,
)
from decision_system.graphing.audit import (
    metric_extraction_completed as audit_metric_extraction_completed,
)
from decision_system.graphing.audit import (
    risk_extraction_completed as audit_risk_extraction_completed,
)
from decision_system.workflow_engine.models import (
    ExecutionContext,
    WorkflowNode,
)

# ---------------------------------------------------------------------------
# GraphExtractionNode v2
# ---------------------------------------------------------------------------


class GraphExtractionNodeV2(WorkflowNode):
    """Extracts entities, relationships, risks, and metrics from text evidence.

    Uses the v2 deterministic extractor and persists results to the workspace
    graph store. Input texts should include evidence references.

    Inputs:
        workspace_id (str): Target workspace.
        texts (list[dict]): List of {"text": str, "evidence_id": str,
                             "source_id": str, "chunk_id": str} dicts.

    Output:
        nodes_extracted (int): Number of entity nodes extracted.
        edges_extracted (int): Number of relationship edges extracted.
        risks_extracted (int): Number of risks extracted.
        metrics_extracted (int): Number of metrics extracted.
        warnings (list[str]): Extraction warnings.
    """

    type: str = "decision_system.graph_extraction_v2"
    label: str = "Graph Extraction v2"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "default")
        raw_texts = inputs.get("texts") or []

        if not raw_texts:
            from decision_system.graphing.store import record_extraction_run

            record_extraction_run(
                workspace_id=workspace_id,
                status="failed",
                errors=["No texts provided for extraction"],
            )
            return {
                "error": "No texts provided for extraction",
                "nodes_extracted": 0,
                "edges_extracted": 0,
                "risks_extracted": 0,
                "metrics_extracted": 0,
                "warnings": ["No texts provided"],
            }

        text_tuples = [
            (
                t.get("text", "") if isinstance(t, dict) else str(t),
                t.get("evidence_id", "") if isinstance(t, dict) else "",
                t.get("source_id", "") if isinstance(t, dict) else "",
                t.get("chunk_id", "") if isinstance(t, dict) else "",
            )
            for t in raw_texts
            if (isinstance(t, dict) and t.get("text", "").strip())
            or (isinstance(t, str) and t.strip())
        ]

        if not text_tuples:
            from decision_system.graphing.store import record_extraction_run

            record_extraction_run(
                workspace_id=workspace_id,
                status="failed",
                errors=["All provided texts were empty"],
            )
            return {
                "error": "All provided texts were empty",
                "warnings": ["No non-empty texts found"],
                "nodes_extracted": 0,
                "edges_extracted": 0,
                "risks_extracted": 0,
                "metrics_extracted": 0,
            }

        from decision_system.graphing.extractor_v2 import extract_intelligence
        from decision_system.graphing.store import (
            get_default_data_root,
            upsert_edge,
            upsert_metric,
            upsert_node,
            upsert_risk,
        )

        _start_time = time.monotonic()
        graph_extraction_started(workspace_id)

        result = extract_intelligence(text_tuples, workspace_id)

        for node in result.to_node_list():
            upsert_node(node, data_root=get_default_data_root())
        for edge in result.to_edge_list():
            upsert_edge(edge, data_root=get_default_data_root())
        for risk in result.to_risk_list():
            upsert_risk(risk, data_root=get_default_data_root())
        for metric in result.to_metric_list():
            upsert_metric(metric, data_root=get_default_data_root())

        _duration_ms = (time.monotonic() - _start_time) * 1000.0
        graph_extraction_completed(
            workspace_id=workspace_id,
            duration_ms=_duration_ms,
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
        from decision_system.graphing.store import record_extraction_run

        record_extraction_run(
            workspace_id=workspace_id,
            status="completed",
            mode="deterministic",
            nodes_created=len(result.nodes),
            edges_created=len(result.edges),
            risks_created=len(result.risks),
            metrics_created=len(result.metrics),
            warnings=result.warnings,
            duration_ms=_duration_ms,
        )

        return {
            "nodes_extracted": len(result.nodes),
            "edges_extracted": len(result.edges),
            "risks_extracted": len(result.risks),
            "metrics_extracted": len(result.metrics),
            "warnings": result.warnings,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                    "description": "Target workspace for extraction",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "texts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "evidence_id": {"type": "string"},
                            "source_id": {"type": "string"},
                            "chunk_id": {"type": "string"},
                        },
                    },
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "nodes_extracted": {"type": "integer"},
                "edges_extracted": {"type": "integer"},
                "risks_extracted": {"type": "integer"},
                "metrics_extracted": {"type": "integer"},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }


# ---------------------------------------------------------------------------
# RiskExtractionNode
# ---------------------------------------------------------------------------


class RiskExtractionNode(WorkflowNode):
    """Extract risks from workspace evidence.

    Uses the v2 deterministic risk pattern matcher. Results are persisted
    to the workspace graph store.

    Inputs:
        workspace_id (str): Target workspace.
        texts (list[dict]): List of text inputs with evidence references.

    Output:
        risks_extracted (int): Number of risks extracted.
        risks (list[dict]): Extracted risk details.
    """

    type: str = "decision_system.risk_extraction"
    label: str = "Extract Risks"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "default")
        raw_texts = inputs.get("texts") or []

        if not raw_texts:
            return {
                "risks_extracted": 0,
                "risks": [],
                "warnings": ["No texts provided"],
            }

        text_tuples = [
            (
                t.get("text", "") if isinstance(t, dict) else str(t),
                t.get("evidence_id", "") if isinstance(t, dict) else "",
                t.get("source_id", "") if isinstance(t, dict) else "",
                t.get("chunk_id", "") if isinstance(t, dict) else "",
            )
            for t in raw_texts
            if (isinstance(t, dict) and t.get("text", "").strip())
            or (isinstance(t, str) and t.strip())
        ]

        if not text_tuples:
            return {
                "risks_extracted": 0,
                "risks": [],
                "warnings": ["No non-empty texts found"],
            }

        from decision_system.graphing.extractor_v2 import extract_intelligence
        from decision_system.graphing.store import get_default_data_root, upsert_risk

        result = extract_intelligence(text_tuples, workspace_id)

        for risk in result.to_risk_list():
            upsert_risk(risk, data_root=get_default_data_root())

        audit_risk_extraction_completed(workspace_id, risks_count=len(result.risks))

        return {
            "risks_extracted": len(result.risks),
            "risks": [r.model_dump(mode="json") for r in result.to_risk_list()],
            "warnings": result.warnings,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                },
                "severity_threshold": {
                    "type": "string",
                    "default": "low",
                    "enum": ["low", "medium", "high", "critical"],
                    "title": "Minimum Severity",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "texts": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "risks_extracted": {"type": "integer"},
                "risks": {"type": "array"},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }


# ---------------------------------------------------------------------------
# MetricExtractionNode
# ---------------------------------------------------------------------------


class MetricExtractionNode(WorkflowNode):
    """Extract metrics from workspace evidence.

    Uses the v2 deterministic metric pattern matcher. Results are persisted
    to the workspace graph store.

    Inputs:
        workspace_id (str): Target workspace.
        texts (list[dict]): List of text inputs with evidence references.

    Output:
        metrics_extracted (int): Number of metrics extracted.
        metrics (list[dict]): Extracted metric details.
    """

    type: str = "decision_system.metric_extraction"
    label: str = "Extract Metrics"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "default")
        raw_texts = inputs.get("texts") or []

        if not raw_texts:
            return {
                "metrics_extracted": 0,
                "metrics": [],
                "warnings": ["No texts provided"],
            }

        text_tuples = [
            (
                t.get("text", "") if isinstance(t, dict) else str(t),
                t.get("evidence_id", "") if isinstance(t, dict) else "",
                t.get("source_id", "") if isinstance(t, dict) else "",
                t.get("chunk_id", "") if isinstance(t, dict) else "",
            )
            for t in raw_texts
            if (isinstance(t, dict) and t.get("text", "").strip())
            or (isinstance(t, str) and t.strip())
        ]

        if not text_tuples:
            return {
                "metrics_extracted": 0,
                "metrics": [],
                "warnings": ["No non-empty texts found"],
            }

        from decision_system.graphing.extractor_v2 import extract_intelligence
        from decision_system.graphing.store import get_default_data_root, upsert_metric

        result = extract_intelligence(text_tuples, workspace_id)

        for metric in result.to_metric_list():
            upsert_metric(metric, data_root=get_default_data_root())

        audit_metric_extraction_completed(workspace_id, metrics_count=len(result.metrics))

        return {
            "metrics_extracted": len(result.metrics),
            "metrics": [m.model_dump(mode="json") for m in result.to_metric_list()],
            "warnings": result.warnings,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "texts": {
                    "type": "array",
                    "items": {"type": "object"},
                },
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "metrics_extracted": {"type": "integer"},
                "metrics": {"type": "array"},
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
        }


# ---------------------------------------------------------------------------
# GraphSummaryNode
# ---------------------------------------------------------------------------


class GraphSummaryNode(WorkflowNode):
    """Generate a structured summary of the workspace knowledge graph.

    Reads from the workspace graph store and produces human-readable and
    structured summaries including entity counts, top risks, key metrics,
    and graph limitations.

    Inputs:
        workspace_id (str): Target workspace.

    Output:
        entity_count (int): Number of entities in the graph.
        edge_count (int): Number of relationships.
        risk_count (int): Number of detected risks.
        metric_count (int): Number of extracted metrics.
        entities_by_type (dict): Node type breakdown.
        risks_by_severity (dict): Risk severity breakdown.
        metrics_by_name (list): Key metric names and values.
        summary_text (str): Human-readable Markdown summary.
        limitations (list[str]): Known graph limitations.
    """

    type: str = "decision_system.graph_summary"
    label: str = "Graph Summary"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "default")

        from decision_system.graphing.store import (
            get_default_data_root,
            get_workspace_meta,
            list_edges,
            list_metrics,
            list_nodes,
            list_risks,
        )

        get_workspace_meta(workspace_id, data_root=get_default_data_root())
        nodes = list_nodes(workspace_id, data_root=get_default_data_root())
        edges = list_edges(workspace_id, data_root=get_default_data_root())
        risks = list_risks(workspace_id, data_root=get_default_data_root())
        metrics = list_metrics(workspace_id, data_root=get_default_data_root())

        # Entity type breakdown
        entities_by_type: dict[str, int] = {}
        for n in nodes:
            t = str(n.node_type)
            entities_by_type[t] = entities_by_type.get(t, 0) + 1

        # Risk severity breakdown
        risks_by_severity: dict[str, int] = {}
        for r in risks:
            s = str(r.severity)
            risks_by_severity[s] = risks_by_severity.get(s, 0) + 1

        # Top risks by severity
        top_risks = sorted(
            risks,
            key=lambda r: ["low", "medium", "high", "critical"].index(
                r.severity if r.severity in ("low", "medium", "high", "critical") else "medium"
            ),
            reverse=True,
        )[:5]

        # Key metrics
        metrics_by_name = [{"name": m.name, "value": m.value, "unit": m.unit} for m in metrics[:10]]

        # Build summary text
        limitations = [
            "Graph facts are extracted by deterministic pattern matching, not verified by a human.",
            "Entity types are inferred from keywords and may be incorrect.",
            "Risk detection flags keyword patterns and may produce false positives.",
            "Metrics are extracted as found in text and may be out of context.",
            "This graph is a best-effort extraction, not a complete company intelligence model.",
        ]

        summary_parts = [
            "### Knowledge Graph Summary",
            "",
            f"- **Entities:** {len(nodes)}",
            f"- **Relationships:** {len(edges)}",
            f"- **Risks:** {len(risks)}",
            f"- **Metrics:** {len(metrics)}",
            "",
        ]
        if entities_by_type:
            summary_parts.append("**Entities by type:**")
            for t, c in sorted(entities_by_type.items()):
                summary_parts.append(f"- {t}: {c}")
            summary_parts.append("")
        if top_risks:
            summary_parts.append("**Top risks:**")
            for r in top_risks:
                summary_parts.append(f"- [{r.severity.upper()}] {r.title}")
            summary_parts.append("")
        if metrics_by_name:
            summary_parts.append("**Key metrics:**")
            for m in metrics_by_name:
                summary_parts.append(f"- {m['name']}: {m['value']} {m['unit']}")
            summary_parts.append("")

        return {
            "entity_count": len(nodes),
            "edge_count": len(edges),
            "risk_count": len(risks),
            "metric_count": len(metrics),
            "entities_by_type": entities_by_type,
            "risks_by_severity": risks_by_severity,
            "top_risks": [r.model_dump(mode="json") for r in top_risks],
            "metrics_by_name": metrics_by_name,
            "summary_text": "\n".join(summary_parts),
            "limitations": limitations,
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "string",
                    "title": "Workspace ID",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "entity_count": {"type": "integer"},
                "edge_count": {"type": "integer"},
                "risk_count": {"type": "integer"},
                "metric_count": {"type": "integer"},
                "entities_by_type": {"type": "object"},
                "risks_by_severity": {"type": "object"},
                "top_risks": {"type": "array"},
                "metrics_by_name": {"type": "array"},
                "summary_text": {"type": "string"},
                "limitations": {"type": "array", "items": {"type": "string"}},
            },
        }
