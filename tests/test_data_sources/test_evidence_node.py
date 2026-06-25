"""Tests for EvidenceSearchNode."""

import pytest

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes import create_default_registry


def _ctx(
    execution_id: str = "test-exec",
    workflow_id: str = "test-wf",
    workspace_id: str = "test-ws",
):
    return ExecutionContext(
        execution_id=execution_id,
        workflow_id=workflow_id,
        workspace_id=workspace_id,
    )


@pytest.mark.asyncio
async def test_evidence_node_registered():
    registry = create_default_registry()
    assert "decision_system.evidence_search" in registry


@pytest.mark.asyncio
async def test_evidence_node_missing_workspace():
    registry = create_default_registry()
    node = registry.instantiate(
        "decision_system.evidence_search",
        id="test-node-1",
    )
    ctx = _ctx()
    result = await node.execute({"query": "test"}, ctx)
    assert result["result_count"] == 0
    assert "workspace_id is required" in result.get("error", "")


@pytest.mark.asyncio
async def test_evidence_node_missing_query():
    registry = create_default_registry()
    node = registry.instantiate(
        "decision_system.evidence_search",
        id="test-node-2",
    )
    ctx = _ctx()
    result = await node.execute({"workspace_id": "ws1"}, ctx)
    assert result["result_count"] == 0
    assert "query is required" in result.get("error", "")


@pytest.mark.asyncio
async def test_evidence_node_keyword_fallback():
    """Keyword fallback works even without vector index."""
    registry = create_default_registry()
    node = registry.instantiate(
        "decision_system.evidence_search",
        id="test-node-3",
    )
    ctx = _ctx(workspace_id="ws-empty")

    result = await node.execute(
        {
            "workspace_id": "ws-empty",
            "query": "test query",
            "limit": 5,
        },
        ctx,
    )
    assert "evidence_results" in result
    assert result["retrieval_mode"] in ("vector", "keyword", "none")


@pytest.mark.asyncio
async def test_evidence_node_config_overrides():
    """Config-based defaults should work when inputs are empty."""
    registry = create_default_registry()
    node = registry.instantiate(
        "decision_system.evidence_search",
        id="test-node-4",
        config={"workspace_id": "ws-cfg", "query": "default query"},
    )
    ctx = _ctx(workspace_id="ws-cfg")
    result = await node.execute({}, ctx)
    assert "evidence_results" in result
