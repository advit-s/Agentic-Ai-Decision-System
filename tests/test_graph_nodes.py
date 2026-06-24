"""Tests for the v2 graph extraction workflow nodes.

Covers:
  - GraphExtractionNodeV2 (extract entities, relationships, risks, metrics)
  - RiskExtractionNode (extract risks only)
  - MetricExtractionNode (extract metrics only)
  - GraphSummaryNode (summarize workspace graph)
"""

from __future__ import annotations

import pytest

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.builtin.graph_nodes import (
    GraphExtractionNodeV2,
    GraphSummaryNode,
    MetricExtractionNode,
    RiskExtractionNode,
)
from decision_system.graphing.store import (
    DEFAULT_DATA_ROOT,
    delete_workspace,
    list_edges,
    list_metrics,
    list_nodes,
    list_risks,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_WS = "test-graph-nodes-ws"
TEST_WS2 = "test-graph-nodes-ws2"


def _ctx(workspace_id: str = TEST_WS) -> ExecutionContext:
    return ExecutionContext(
        workflow_id="test-wf",
        execution_id="test-exec-1",
        workspace_id=workspace_id,
    )


def _text_input(text: str, evidence_id: str = "ev-1", source_id: str = "src-1", chunk_id: str = "ch-1") -> dict:
    return {
        "text": text,
        "evidence_id": evidence_id,
        "source_id": source_id,
        "chunk_id": chunk_id,
    }


def _cleanup(workspace_id: str = TEST_WS) -> None:
    """Remove test workspace data."""
    try:
        delete_workspace(workspace_id, data_root=DEFAULT_DATA_ROOT)
    except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup():
    """Clean test workspaces before and after each test."""
    _cleanup(TEST_WS)
    _cleanup(TEST_WS2)
    yield
    _cleanup(TEST_WS)
    _cleanup(TEST_WS2)


# ---------------------------------------------------------------------------
# GraphExtractionNodeV2
# ---------------------------------------------------------------------------


class TestGraphExtractionNodeV2:
    """Tests for GraphExtractionNodeV2."""

    @pytest.mark.asyncio
    async def test_empty_texts(self):
        node = GraphExtractionNodeV2(id="gn1", config={"workspace_id": TEST_WS})
        result = await node.execute({"texts": []}, _ctx())
        assert result["nodes_extracted"] == 0
        assert result["edges_extracted"] == 0
        assert result["risks_extracted"] == 0
        assert result["metrics_extracted"] == 0
        assert "warnings" in result

    @pytest.mark.asyncio
    async def test_no_inputs(self):
        node = GraphExtractionNodeV2(id="gn2")
        result = await node.execute({}, _ctx())
        assert result["nodes_extracted"] == 0

    @pytest.mark.asyncio
    async def test_all_empty_texts(self):
        node = GraphExtractionNodeV2(id="gn3", config={"workspace_id": TEST_WS})
        texts = [
            {"text": "", "evidence_id": "", "source_id": "", "chunk_id": ""}
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["nodes_extracted"] == 0
        assert "All provided texts were empty" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_company_product_extraction(self):
        node = GraphExtractionNodeV2(id="gn4", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Acme Corporation provides CloudSync and DataVault."
                " Revenue: $5M. Employees: 120.",
                evidence_id="ev-company-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["nodes_extracted"] >= 2  # Acme + products
        assert result["edges_extracted"] >= 1
        assert result["metrics_extracted"] >= 2  # $5M, 120

        # Verify persistence
        nodes = list_nodes(TEST_WS, data_root=DEFAULT_DATA_ROOT)
        assert len(nodes) >= 2
        names = [n.name for n in nodes]
        assert "Acme Corporation" in names or "Acme" in names

    @pytest.mark.asyncio
    async def test_risk_extraction_integrated(self):
        node = GraphExtractionNodeV2(id="gn5", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Security vulnerability in payment gateway."
                " Risk of data breach. Compliance issue with GDPR.",
                evidence_id="ev-risk-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["risks_extracted"] >= 1
        assert result["nodes_extracted"] >= 1

    @pytest.mark.asyncio
    async def test_multiple_texts(self):
        node = GraphExtractionNodeV2(id="gn6", config={"workspace_id": TEST_WS})
        texts = [
            _text_input("Acme Corp provides cloud services. Revenue: $10M.", evidence_id="ev-1"),
            _text_input("Vendor: FastCloud Ltd. Annual spend: $500k. Risk of vendor lock-in.", evidence_id="ev-2"),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["nodes_extracted"] >= 2
        assert result["metrics_extracted"] >= 1

    @pytest.mark.asyncio
    async def test_workspace_isolation(self):
        """Different workspaces should not share data."""
        node1 = GraphExtractionNodeV2(id="gn7", config={"workspace_id": TEST_WS})
        node2 = GraphExtractionNodeV2(id="gn8", config={"workspace_id": TEST_WS2})

        text1 = [_text_input("Acme Corp provides CloudSync.", evidence_id="ev-1")]
        text2 = [_text_input("Beta Inc offers DataVault.", evidence_id="ev-2")]
        await node1.execute({"texts": text1}, _ctx(TEST_WS))
        await node2.execute({"texts": text2}, _ctx(TEST_WS2))

        nodes1 = list_nodes(TEST_WS, data_root=DEFAULT_DATA_ROOT)
        nodes2 = list_nodes(TEST_WS2, data_root=DEFAULT_DATA_ROOT)

        assert len(nodes1) > 0
        assert len(nodes2) > 0
        # Node IDs should differ across workspaces
        id_set1 = {n.node_id for n in nodes1}
        id_set2 = {n.node_id for n in nodes2}
        assert id_set1.isdisjoint(id_set2), "Node IDs should not overlap across workspaces"

    @pytest.mark.asyncio
    async def test_handles_plain_strings(self):
        node = GraphExtractionNodeV2(id="gn9", config={"workspace_id": TEST_WS})
        texts = ["Acme Corp revenue is $5M."]
        result = await node.execute({"texts": texts}, _ctx())
        # Should handle plain strings (not dicts) gracefully
        assert result["nodes_extracted"] >= 0
        assert isinstance(result["warnings"], list)

    @pytest.mark.asyncio
    async def test_schema_methods(self):
        node = GraphExtractionNodeV2(id="gn10")
        assert node.type == "decision_system.graph_extraction_v2"
        assert "workspace_id" in node.get_config_schema().get("properties", {})
        assert "texts" in node.get_input_schema().get("properties", {})
        assert "nodes_extracted" in node.get_output_schema().get("properties", {})


# ---------------------------------------------------------------------------
# RiskExtractionNode
# ---------------------------------------------------------------------------


class TestRiskExtractionNode:
    """Tests for RiskExtractionNode."""

    @pytest.mark.asyncio
    async def test_empty_texts(self):
        node = RiskExtractionNode(id="rn1", config={"workspace_id": TEST_WS})
        result = await node.execute({"texts": []}, _ctx())
        assert result["risks_extracted"] == 0
        assert result["risks"] == []

    @pytest.mark.asyncio
    async def test_extract_security_risk(self):
        node = RiskExtractionNode(id="rn2", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Security vulnerability: SQL injection in payment API. "
                "Risk of data breach is high. Vendor compliance issue.",
                evidence_id="ev-risk-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["risks_extracted"] >= 1
        assert len(result["risks"]) >= 1
        # Verify risk has required fields
        risk = result["risks"][0]
        assert "risk_id" in risk
        assert "title" in risk
        assert "severity" in risk

    @pytest.mark.asyncio
    async def test_extract_financial_risk(self):
        node = RiskExtractionNode(id="rn3", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Budget overrun of $2M. Revenue decline of 15%. "
                "Cash flow issues reported.",
                evidence_id="ev-fin-risk-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["risks_extracted"] >= 1

    @pytest.mark.asyncio
    async def test_workspace_scoped_persistence(self):
        node = RiskExtractionNode(id="rn4", config={"workspace_id": TEST_WS})
        texts = [
            _text_input("Security vulnerability in system.", evidence_id="ev-1"),
        ]
        await node.execute({"texts": texts}, _ctx())
        risks = list_risks(TEST_WS, data_root=DEFAULT_DATA_ROOT)
        assert len(risks) >= 1

    @pytest.mark.asyncio
    async def test_no_risk_text(self):
        node = RiskExtractionNode(id="rn5", config={"workspace_id": TEST_WS})
        texts = [
            _text_input("The sky is blue. Water is wet.", evidence_id="ev-1"),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        # Neutral text may still trigger some risk patterns
        assert result["risks_extracted"] >= 0
        assert isinstance(result["risks"], list)

    @pytest.mark.asyncio
    async def test_schema_methods(self):
        node = RiskExtractionNode(id="rn6")
        assert node.type == "decision_system.risk_extraction"
        assert "severity_threshold" in node.get_config_schema().get("properties", {})
        assert "texts" in node.get_input_schema().get("properties", {})


# ---------------------------------------------------------------------------
# MetricExtractionNode
# ---------------------------------------------------------------------------


class TestMetricExtractionNode:
    """Tests for MetricExtractionNode."""

    @pytest.mark.asyncio
    async def test_empty_texts(self):
        node = MetricExtractionNode(id="mn1", config={"workspace_id": TEST_WS})
        result = await node.execute({"texts": []}, _ctx())
        assert result["metrics_extracted"] == 0
        assert result["metrics"] == []

    @pytest.mark.asyncio
    async def test_extract_financial_metrics(self):
        node = MetricExtractionNode(id="mn2", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Revenue: $10M. Profit margin: 20%. Customers: 5000. "
                "Employee count: 120. Growth rate: 15%.",
                evidence_id="ev-metrics-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["metrics_extracted"] >= 4
        assert len(result["metrics"]) >= 4

        # Check metric structure
        metric = result["metrics"][0]
        assert "metric_id" in metric
        assert "name" in metric
        assert "value" in metric

    @pytest.mark.asyncio
    async def test_extract_percentage_metrics(self):
        node = MetricExtractionNode(id="mn3", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Churn rate: 5%. Customer satisfaction: 92%. "
                "Uptime: 99.9%.",
                evidence_id="ev-pct-1",
            ),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["metrics_extracted"] >= 2

    @pytest.mark.asyncio
    async def test_workspace_persistence(self):
        node = MetricExtractionNode(id="mn4", config={"workspace_id": TEST_WS})
        texts = [
            _text_input("Revenue: $5M. Profit: $1M.", evidence_id="ev-1"),
        ]
        await node.execute({"texts": texts}, _ctx())
        metrics = list_metrics(TEST_WS, data_root=DEFAULT_DATA_ROOT)
        assert len(metrics) >= 2

    @pytest.mark.asyncio
    async def test_no_metrics_text(self):
        node = MetricExtractionNode(id="mn5", config={"workspace_id": TEST_WS})
        texts = [
            _text_input("Acme provides cloud services.", evidence_id="ev-1"),
        ]
        result = await node.execute({"texts": texts}, _ctx())
        assert result["metrics_extracted"] == 0
        assert result["metrics"] == []

    @pytest.mark.asyncio
    async def test_schema_methods(self):
        node = MetricExtractionNode(id="mn6")
        assert node.type == "decision_system.metric_extraction"
        assert "workspace_id" in node.get_config_schema().get("properties", {})


# ---------------------------------------------------------------------------
# GraphSummaryNode
# ---------------------------------------------------------------------------


class TestGraphSummaryNode:
    """Tests for GraphSummaryNode."""

    @pytest.mark.asyncio
    async def test_empty_graph_summary(self):
        node = GraphSummaryNode(id="gsn1", config={"workspace_id": TEST_WS})
        result = await node.execute({"workspace_id": TEST_WS}, _ctx())
        assert result["entity_count"] == 0
        assert result["edge_count"] == 0
        assert result["risk_count"] == 0
        assert result["metric_count"] == 0
        assert "summary_text" in result
        assert "limitations" in result
        assert len(result["limitations"]) >= 3

    @pytest.mark.asyncio
    async def test_summary_after_extraction(self):
        """Summary should reflect data extracted by GraphExtractionNode."""
        extract_node = GraphExtractionNodeV2(id="gn-extract", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Acme Corp provides CloudSync. Revenue of $5,000,000 and 20% profit margin. Risk of vendor lock-in.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn2", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert result["entity_count"] >= 1
        assert result["metric_count"] >= 1
        assert result["risk_count"] >= 1
        assert "entities_by_type" in result
        assert "risks_by_severity" in result
        assert "summary_text" in result
        assert "Entities" in result["summary_text"]

    @pytest.mark.asyncio
    async def test_entities_by_type_breakdown(self):
        extract_node = GraphExtractionNodeV2(id="gn-extract2", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Acme Corp provides CloudSync by TechVendor Inc.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn3", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert isinstance(result["entities_by_type"], dict)
        assert len(result["entities_by_type"]) > 0

    @pytest.mark.asyncio
    async def test_risks_by_severity(self):
        extract_node = GraphExtractionNodeV2(id="gn-extract3", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Security vulnerability. Data breach risk. Compliance issue.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn4", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert isinstance(result["risks_by_severity"], dict)

    @pytest.mark.asyncio
    async def test_top_risks(self):
        extract_node = GraphExtractionNodeV2(id="gn-extract4", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Critical security vulnerability in payment system. "
                "High risk of data breach. Medium compliance issue.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn5", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert "top_risks" in result
        if result["top_risks"]:
            risk = result["top_risks"][0]
            assert "title" in risk or "risk_id" in risk

    @pytest.mark.asyncio
    async def test_key_metrics(self):
        extract_node = GraphExtractionNodeV2(id="gn-extract5", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Revenue: $10M. Profit: $2M. Customers: 5000.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn6", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert "metrics_by_name" in result
        if result["metrics_by_name"]:
            metric = result["metrics_by_name"][0]
            assert "name" in metric
            assert "value" in metric

    @pytest.mark.asyncio
    async def test_edge_count_after_extraction(self):
        extract_node = GraphExtractionNodeV2(id="gn-extract6", config={"workspace_id": TEST_WS})
        texts = [
            _text_input(
                "Acme Corp provides CloudSync by TechVendor Inc.",
                evidence_id="ev-1",
            ),
        ]
        await extract_node.execute({"texts": texts}, _ctx())

        summary_node = GraphSummaryNode(id="gsn7", config={"workspace_id": TEST_WS})
        result = await summary_node.execute({"workspace_id": TEST_WS}, _ctx())

        assert result["edge_count"] >= 1

    @pytest.mark.asyncio
    async def test_schema_methods(self):
        node = GraphSummaryNode(id="gsn8")
        assert node.type == "decision_system.graph_summary"
        assert "workspace_id" in node.get_config_schema().get("properties", {})
        assert "entity_count" in node.get_output_schema().get("properties", {})
        assert "summary_text" in node.get_output_schema().get("properties", {})
