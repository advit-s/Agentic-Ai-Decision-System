"""Tests for DataAnalystNode — fake fallback and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.data_analyst import (
    DataAnalystNode,
    _fake_analysis,
    _summarize_analysis,
)
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

pytestmark = pytest.mark.asyncio


def _store_with_provider() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([
        ProviderConfig(
            name="test-provider",
            api_base="https://test.api/v1",
            api_key_env="TEST_AI_KEY",
            default_model="test-model",
        ),
    ])
    return store


def _fake_store() -> ProviderStore:
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


SAMPLE_DATA = [
    {"id": 1, "name": "Alice", "revenue": 150000, "region": "North"},
    {"id": 2, "name": "Bob", "revenue": 250000, "region": "South"},
    {"id": 3, "name": "Charlie", "revenue": 95000, "region": "East"},
    {"id": 4, "name": "Diana", "revenue": 320000, "region": "West"},
    {"id": 5, "name": "Eve", "revenue": 180000, "region": "North"},
]

ANALYSIS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "analysis": {
                        "row_count": 5,
                        "columns": ["id", "name", "revenue", "region"],
                        "key_insights": ["Revenue ranges from $95K to $320K"],
                    },
                    "summary": "Analyzed 5 records. Revenue ranges widely.",
                    "charts": {"revenue_distribution": {"labels": ["Alice", "Bob", "Charlie", "Diana", "Eve"], "values": [150000, 250000, 95000, 320000, 180000]}},
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestDataAnalystNode:
    """DataAnalystNode — AI-powered structured data analysis."""

    async def test_fallback_empty_data(self):
        """Empty data returns empty analysis."""
        node = DataAnalystNode(id="d1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": []}, ctx)
        assert result["analysis"] == {}
        assert "No data provided" in result["summary"]

    async def test_fallback_dict_data(self):
        """Single dict data wrapped in list and analyzed."""
        node = DataAnalystNode(id="d2", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": {"test": "value"}}, ctx)
        assert "analysis" in result
        assert result["summary"]

    async def test_fallback_profile_analysis(self):
        """analysis_type=profile returns profile mock."""
        node = DataAnalystNode(id="d3", config={"analysis_type": "profile"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        analysis = result["analysis"]
        assert "row_count" in analysis
        assert "column_count" in analysis
        assert "numeric_columns" in analysis

    async def test_fallback_trend_analysis(self):
        """analysis_type=trend returns trend mock."""
        node = DataAnalystNode(id="d4", config={"analysis_type": "trend"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        analysis = result["analysis"]
        assert "overall_direction" in analysis
        assert "trends" in analysis

    async def test_fallback_anomaly_analysis(self):
        """analysis_type=anomaly returns anomaly mock."""
        node = DataAnalystNode(id="d5", config={"analysis_type": "anomaly"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        analysis = result["analysis"]
        assert "total_outliers" in analysis
        assert "outliers" in analysis

    async def test_fallback_correlation_analysis(self):
        """analysis_type=correlation returns correlation mock."""
        node = DataAnalystNode(id="d6", config={"analysis_type": "correlation"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        analysis = result["analysis"]
        assert "pairs" in analysis
        assert "notable_insights" in analysis

    async def test_fallback_summary_analysis(self):
        """analysis_type=summary returns summary mock."""
        node = DataAnalystNode(id="d7", config={"analysis_type": "summary"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        analysis = result["analysis"]
        assert "profile_summary" in analysis
        assert "key_findings" in analysis
        assert "recommendation" in analysis

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider configured calls LLMClient with correct prompt."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=ANALYSIS_RESPONSE,
            )
            node = DataAnalystNode(id="d8", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"data": SAMPLE_DATA}, ctx)
            assert result["analysis"]["row_count"] == 5
            assert "summary" in result
            assert result["fallback_reason"] == ""

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Data Analyst" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_with_provider_fallback_on_error(self, httpx_mock: HTTPXMock):
        """Provider error falls back to fake with fallback_reason."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                status_code=429,
            )
            node = DataAnalystNode(id="d9", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"data": SAMPLE_DATA}, ctx)
            assert result["analysis"] != {}
            assert result["fallback_reason"] != ""
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_output_schema_matches_contract(self):
        """Output conforms to output_schema properties."""
        node = DataAnalystNode(id="d10", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA}, ctx)
        schema = node.get_output_schema()
        schema_props = schema.get("properties", {})
        for key in schema_props:
            assert key in result, f"Missing output field: {key}"

    async def test_analysis_type_override_from_input(self):
        """Input analysis_type overrides config default."""
        node = DataAnalystNode(id="d11", config={"analysis_type": "profile"})
        ctx = _ctx(_fake_store())
        result = await node.execute({"data": SAMPLE_DATA, "analysis_type": "trend"}, ctx)
        assert "overall_direction" in result["analysis"]


# ── Unit tests for helper functions ─────────────────────────────────

class TestDataAnalystHelpers:

    def test_fake_analysis_profile(self):
        result = _fake_analysis(SAMPLE_DATA, "profile")
        assert "row_count" in result
        assert "numeric_columns" in result

    def test_fake_analysis_trend(self):
        result = _fake_analysis(SAMPLE_DATA, "trend")
        assert "overall_direction" in result
        assert "trends" in result

    def test_fake_analysis_anomaly(self):
        result = _fake_analysis(SAMPLE_DATA, "anomaly")
        assert "outliers" in result

    def test_fake_analysis_correlation(self):
        result = _fake_analysis(SAMPLE_DATA, "correlation")
        assert "pairs" in result

    def test_fake_analysis_default(self):
        result = _fake_analysis(SAMPLE_DATA, "summary")
        assert "key_findings" in result

    def test_fake_analysis_unknown_type(self):
        result = _fake_analysis(SAMPLE_DATA, "unknown_type")
        assert "key_findings" in result  # should fall back to summary

    def test_summarize_profile(self):
        result = _fake_analysis(SAMPLE_DATA, "profile")
        summary = _summarize_analysis(result, "profile")
        assert "rows" in summary
        assert "columns" in summary

    def test_summarize_trend(self):
        result = _fake_analysis(SAMPLE_DATA, "trend")
        summary = _summarize_analysis(result, "trend")
        assert "upward" in summary.lower() or "downward" in summary.lower()

    def test_summarize_anomaly(self):
        result = _fake_analysis(SAMPLE_DATA, "anomaly")
        summary = _summarize_analysis(result, "anomaly")
        assert "outlier" in summary.lower()

    def test_summarize_correlation(self):
        result = _fake_analysis(SAMPLE_DATA, "correlation")
        summary = _summarize_analysis(result, "correlation")
        assert "correlation" in summary.lower()
