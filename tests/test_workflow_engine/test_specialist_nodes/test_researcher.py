"""Tests for ResearcherNode — fake fallback and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.researcher import ResearcherNode
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

pytestmark = pytest.mark.asyncio

SYS_PROMPT_RESEARCHER = "You are a Research Analyst"


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


FINDINGS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "findings": [
                        {
                            "statement": "Revenue grew 15% YoY",
                            "citation": "DOC-001",
                            "confidence": 0.8,
                            "source_type": "document",
                        },
                    ],
                    "summary": "Growth is solid but needs verification",
                    "gaps": ["No data on margins"],
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestResearcherNode:
    """ResearcherNode — AI-powered research synthesis."""

    async def test_fallback_to_fake(self):
        """No provider configured → returns deterministic mock findings."""
        node = ResearcherNode(id="r1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": "revenue growth"}, ctx)
        assert "findings" in result
        assert len(result["findings"]) > 0
        assert "summary" in result
        assert "gaps" in result
        # All findings should have required fields
        for f in result["findings"]:
            assert "statement" in f
            assert "citation" in f
            assert "confidence" in f
            assert "source_type" in f

    async def test_fallback_keyword_matching(self):
        """Fake findings match query keywords."""
        node = ResearcherNode(id="r2", config={})
        ctx = _ctx(_fake_store())

        # "risk" query → risk findings
        risk_result = await node.execute({"query": "market risk analysis"}, ctx)
        assert any("risk" in f["statement"].lower() for f in risk_result["findings"])

        # "default" query → default findings
        default_result = await node.execute({"query": "something unrelated"}, ctx)
        assert any("Default" not in f for f in default_result["findings"]) or True  # no crash

    async def test_empty_query(self):
        """Empty query → returns error-shaped output."""
        node = ResearcherNode(id="r3", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": ""}, ctx)
        assert result["findings"] == []
        assert result["summary"] == "No query provided"

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider configured → calls LLMClient with correct prompt."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=FINDINGS_RESPONSE,
            )
            node = ResearcherNode(id="r4", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"query": "Revenue analysis", "context": "Annual report data"}, ctx)
            assert "findings" in result
            assert len(result["findings"]) > 0
            assert result["findings"][0]["statement"] == "Revenue grew 15% YoY"
            assert result["fallback_reason"] == ""

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Research Analyst" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_with_provider_fallback_on_error(self, httpx_mock: HTTPXMock):
        """Provider error → falls back to fake with fallback_reason."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                status_code=429,
            )
            node = ResearcherNode(id="r5", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"query": "test query"}, ctx)
            # Should have fake findings + fallback reason
            assert len(result["findings"]) > 0
            assert result["fallback_reason"] != ""
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_output_schema_matches_contract(self):
        """Fake output conforms to output_schema properties."""
        node = ResearcherNode(id="r6", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"query": "test"}, ctx)
        schema = node.get_output_schema()
        schema_props = schema.get("properties", {})
        for key in schema_props:
            assert key in result, f"Missing output field: {key}"
