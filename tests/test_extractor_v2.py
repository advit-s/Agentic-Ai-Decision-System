"""Tests for the v2 deterministic entity/risk/metric extraction."""

import pytest

from decision_system.graphing.extractor_v2 import (
    extract_intelligence,
    _normalize_name,
    _make_id,
    _clean_phrase,
    _infer_entity_type,
    _infer_unit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WS = "test-ws"


def _text(text: str, evidence_id: str = "ev-1", source_id: str = "src-1", chunk_id: str = "ch-1"):
    return (text, evidence_id, source_id, chunk_id)


# ---------------------------------------------------------------------------
# Unit tests for helpers
# ---------------------------------------------------------------------------


def test_normalize_name():
    assert _normalize_name("  Acme Corp  ") == "acme corp"
    assert _normalize_name("Hello World") == "hello world"


def test_make_id():
    assert _make_id("node", "Acme Corp").startswith("node-")
    assert "-acme-corp" in _make_id("node", "Acme Corp")


def test_clean_phrase():
    assert _clean_phrase("  Hello World.  ") == "Hello World"
    assert _clean_phrase("The Vendor Inc.") == "Vendor Inc"
    assert _clean_phrase("a test") == "test"


def test_infer_entity_type():
    assert _infer_entity_type("Platform Team") == "team"
    assert _infer_entity_type("Acme Vendor") == "vendor"
    assert _infer_entity_type("Big Customer") == "customer"
    assert _infer_entity_type("Some Product") == "product"
    assert _infer_entity_type("Billing System") == "system"
    assert _infer_entity_type("CTO Office") == "person"
    assert _infer_entity_type("Unknown Thing") == "unknown"


def test_infer_unit():
    assert _infer_unit("100%") == "%"
    assert _infer_unit("$500") == "USD"
    assert _infer_unit("100K") == "thousands"
    assert _infer_unit("5M") == "millions"
    assert _infer_unit("42") == "count"


# ---------------------------------------------------------------------------
# Company extraction
# ---------------------------------------------------------------------------


def test_extract_company_with_suffix():
    result = extract_intelligence([_text("Acme Corporation provides services.")], WS)
    companies = [n for n in result.to_node_list() if n.node_type == "company"]
    assert any("Acme Corp" in n.name or "Corporation" in n.name for n in companies)


def test_extract_company_with_keyword():
    result = extract_intelligence([_text("DataSync Technologies is growing.")], WS)
    companies = [n for n in result.to_node_list() if n.node_type == "company"]
    assert any("DataSync Technologies" in n.name for n in companies)


# ---------------------------------------------------------------------------
# Vendor extraction
# ---------------------------------------------------------------------------


def test_extract_vendor():
    result = extract_intelligence([_text("Vendor named GlobexSupplies provides parts.")], WS)
    vendors = [n for n in result.to_node_list() if n.node_type == "vendor"]
    assert any("GlobexSupplies" in n.name for n in vendors)


# ---------------------------------------------------------------------------
# Product extraction
# ---------------------------------------------------------------------------


def test_extract_product():
    result = extract_intelligence([_text("Platform called CloudMesh is our main product.")], WS)
    products = [n for n in result.to_node_list() if n.node_type == "product"]
    assert any("CloudMesh" in n.name for n in products)


# ---------------------------------------------------------------------------
# Money extraction
# ---------------------------------------------------------------------------


def test_extract_money_amount():
    result = extract_intelligence([_text("The budget is $500,000 for Q3.")], WS)
    assert len(result.to_metric_list()) >= 1
    assert any("$500,000" in m.value for m in result.to_metric_list())


# ---------------------------------------------------------------------------
# Percentage extraction
# ---------------------------------------------------------------------------


def test_extract_percentage():
    result = extract_intelligence([_text("Growth rate is 23.5% this quarter.")], WS)
    assert any("23.5%" in m.value for m in result.to_metric_list())


def test_extract_percent_text():
    result = extract_intelligence([_text("Margin declined 5 percent.")], WS)
    assert any("5 percent" in m.value for m in result.to_metric_list())


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------


def test_extract_date_iso():
    result = extract_intelligence([_text("Migrated on 2026-06-23.")], WS)
    events = [n for n in result.to_node_list() if n.node_type == "event"]
    assert any("2026-06-23" in n.name for n in events)


def test_extract_date_named():
    result = extract_intelligence([_text("Completed by June 30, 2026.")], WS)
    events = [n for n in result.to_node_list() if n.node_type == "event"]
    assert any("June 30, 2026" in n.name or "Jun 30, 2026" in n.name for n in events)


# ---------------------------------------------------------------------------
# Email/domain extraction
# ---------------------------------------------------------------------------


def test_extract_email():
    result = extract_intelligence([_text("Contact admin@example.com for access.")], WS)
    assert any("admin@example.com" in n.name for n in result.to_node_list())


# ---------------------------------------------------------------------------
# Risk extraction
# ---------------------------------------------------------------------------


def test_extract_security_risk():
    result = extract_intelligence([_text("The security breach exposed customer data.")], WS)
    risks = result.to_risk_list()
    assert len(risks) >= 1
    assert any("security" in r.category or "Security" in r.title for r in risks)


def test_extract_compliance_risk():
    result = extract_intelligence([_text("GDPR compliance violation found in audit.")], WS)
    risks = result.to_risk_list()
    assert len(risks) >= 1
    assert any("compliance" in r.category for r in risks)


def test_extract_vendor_risk():
    result = extract_intelligence([_text("High vendor concentration risk identified.")], WS)
    risks = result.to_risk_list()
    assert len(risks) >= 1
    assert any("vendor" in r.category for r in risks)


# ---------------------------------------------------------------------------
# Metric extraction
# ---------------------------------------------------------------------------


def test_extract_revenue_metric():
    result = extract_intelligence([_text("Revenue: $10,000,000 for FY 2026.")], WS)
    metrics = result.to_metric_list()
    revenue_metrics = [m for m in metrics if "Revenue" in m.name]
    assert len(revenue_metrics) >= 1


def test_extract_customer_count():
    result = extract_intelligence([_text("Customer count is 5000.")], WS)
    metrics = result.to_metric_list()
    customer_metrics = [m for m in metrics if "Customer" in m.name]
    assert len(customer_metrics) >= 1


# ---------------------------------------------------------------------------
# Relationship extraction
# ---------------------------------------------------------------------------


def test_depends_on_relationship():
    result = extract_intelligence([_text("Billing System depends on Auth Service.")], WS)
    edges = result.to_edge_list()
    assert len(edges) >= 1
    assert any(e.edge_type == "depends_on" for e in edges)


def test_owns_relationship():
    result = extract_intelligence([_text("Auth Service is owned by Platform Team.")], WS)
    edges = result.to_edge_list()
    assert len(edges) >= 1
    assert any(e.edge_type == "owns" for e in edges)


def test_supplies_relationship():
    result = extract_intelligence([_text("Acme Corp provides Cloud Services.")], WS)
    edges = result.to_edge_list()
    assert len(edges) >= 1
    assert any(e.edge_type == "supplies" for e in edges)


def test_contradiction_relationship():
    result = extract_intelligence([_text("Migration needs rollback. CONTRADICTS: Migration is safe.")], WS)
    edges = result.to_edge_list()
    assert any(e.edge_type == "contradicts" for e in edges)


# ---------------------------------------------------------------------------
# Evidence references
# ---------------------------------------------------------------------------


def test_evidence_ids_preserved():
    result = extract_intelligence([_text("Acme Corp has $1M revenue.", "ev-42", "src-7", "ch-3")], WS)
    for node in result.to_node_list():
        assert "ev-42" in node.evidence_ids or len(node.evidence_ids) > 0
    for risk in result.to_risk_list():
        assert "ev-42" in risk.evidence_ids
    for metric in result.to_metric_list():
        assert "ev-42" in metric.evidence_ids


# ---------------------------------------------------------------------------
# Empty/safe handling
# ---------------------------------------------------------------------------


def test_empty_text():
    result = extract_intelligence([_text("")], WS)
    assert len(result.to_node_list()) == 0
    assert len(result.to_edge_list()) == 0
    assert len(result.to_risk_list()) == 0
    assert len(result.to_metric_list()) == 0


def test_no_extractable_content():
    result = extract_intelligence([_text("This is just some random text without patterns.")], WS)
    # Should not crash, may find some entities
    assert isinstance(result.to_node_list(), list)


# ---------------------------------------------------------------------------
# Workspace scoping
# ---------------------------------------------------------------------------


def test_workspace_scoping():
    result = extract_intelligence([_text("Acme Corp.")], "ws-custom")
    assert all(n.workspace_id == "ws-custom" for n in result.to_node_list())


# ---------------------------------------------------------------------------
# Multiple texts
# ---------------------------------------------------------------------------


def test_multiple_texts():
    texts = [
        _text("Acme Corp provides Cloud Services.", "ev-1", "src-1", "ch-1"),
        _text("Revenue: $5M.", "ev-2", "src-2", "ch-2"),
    ]
    result = extract_intelligence(texts, WS)
    assert len(result.to_node_list()) >= 2
    assert len(result.to_metric_list()) >= 1
