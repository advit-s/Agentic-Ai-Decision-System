"""Tests for AI node LLM integration.

Each AI node should:
1. Resolve provider via ctx.resolve_provider()
2. If provider found → call LLMClient
3. If no provider → fall back to existing fake/rule-based behavior
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.builtin.decision_nodes import (
    ExtractClaimsNode,
    RiskAnalystNode,
    TechAnalystNode,
    VerifyClaimsNode,
    WriteReportNode,
)
from decision_system.workflow_engine.providers.store import (
    ProviderConfig,
    ProviderStore,
)

pytestmark = pytest.mark.asyncio


# ── Fixtures ──────────────────────────────────────────────────────────

SYS_PROMPT_TECH = "You are a senior technical analyst"
SYS_PROMPT_RISK = "You are a risk analyst"
SYS_PROMPT_CLAIMS = "Extract factual claims"
SYS_PROMPT_VERIFY = "verify each claim"
SYS_PROMPT_REPORT = "Write a structured decision report"


def _store_with_provider() -> ProviderStore:
    """Provider store with one real provider."""
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save(
        [
            ProviderConfig(
                name="test-provider",
                api_base="https://test.api/v1",
                api_key_env="TEST_AI_KEY",
                default_model="test-model",
            ),
        ]
    )
    return store


def _fake_store() -> ProviderStore:
    """Empty provider store — no real provider."""
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


SIMPLE_JSON_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {"findings": [{"title": "Test finding", "severity": "high"}]}
                ),
            },
            "finish_reason": "stop",
        }
    ],
}

MARKDOWN_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": "# Test Report\n\nThis is a report.",
            },
            "finish_reason": "stop",
        }
    ],
}

CLAIMS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(["Claim 1", "Claim 2"]),
            },
            "finish_reason": "stop",
        }
    ],
}

VERIFY_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    [
                        {"claim": "Claim 1", "status": "supported"},
                        {"claim": "Claim 2", "status": "unsupported"},
                    ]
                ),
            },
            "finish_reason": "stop",
        }
    ],
}


# ── TechAnalystNode ──────────────────────────────────────────────────


class TestTechAnalystNode:
    """TechAnalystNode — LLM-powered technical analysis."""

    async def test_fallback_to_fake(self):
        """No provider configured → uses existing fake behavior."""
        node = TechAnalystNode(id="t1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "test"}, ctx)
        assert "analysis" in result
        assert result["analysis"]  # non-empty fake response

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider configured → calls LLMClient with correct prompt."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=SIMPLE_JSON_RESPONSE,
            )
            node = TechAnalystNode(id="t1", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute(
                {"question": "Analyze this", "chunks": [{"text": "data"}]}, ctx
            )
            assert "analysis" in result
            assert "Test finding" in result["analysis"]

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("analyst" in m.get("content", "").lower() for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)


# ── RiskAnalystNode ─────────────────────────────────────────────────


class TestRiskAnalystNode:
    """RiskAnalystNode — LLM-powered risk analysis."""

    async def test_fallback_to_fake(self):
        """No provider → fake behavior."""
        node = RiskAnalystNode(id="r1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "test"}, ctx)
        assert "analysis" in result

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → LLMClient."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=SIMPLE_JSON_RESPONSE,
            )
            node = RiskAnalystNode(id="r1", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"question": "Find risks"}, ctx)
            assert "analysis" in result
        finally:
            os.environ.pop("TEST_AI_KEY", None)


# ── ExtractClaimsNode ───────────────────────────────────────────────


class TestExtractClaimsNode:
    """ExtractClaimsNode — LLM-powered claim extraction."""

    async def test_fallback_to_fake(self):
        """No provider → existing claim ledger behavior."""
        node = ExtractClaimsNode(id="ec1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"memo": {"findings": [{"title": "test"}]}}, ctx)
        assert "claims" in result

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → LLMClient extracts claims."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=CLAIMS_RESPONSE,
            )
            node = ExtractClaimsNode(id="ec1", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"memo": "Some text with claims"}, ctx)
            assert "claims" in result
        finally:
            os.environ.pop("TEST_AI_KEY", None)


# ── VerifyClaimsNode ────────────────────────────────────────────────


class TestVerifyClaimsNode:
    """VerifyClaimsNode — LLM-powered claim verification."""

    async def test_fallback_to_fake(self):
        """No provider → existing verifier behavior."""
        node = VerifyClaimsNode(id="vc1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"claims": [{"text": "Claim 1"}]}, ctx)
        assert "verified_claims" in result

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → LLMClient verifies claims."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=VERIFY_RESPONSE,
            )
            node = VerifyClaimsNode(id="vc1", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute(
                {"claims": [{"text": "Claim 1"}], "chunks": [{"text": "Evidence"}]}, ctx
            )
            assert "verified_claims" in result
        finally:
            os.environ.pop("TEST_AI_KEY", None)


# ── WriteReportNode ─────────────────────────────────────────────────


class TestWriteReportNode:
    """WriteReportNode — LLM-powered report writing."""

    async def test_fallback_to_fake(self):
        """No provider → existing renderer behavior."""
        node = WriteReportNode(id="wr1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "test"}, ctx)
        assert "report" in result

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → LLMClient writes report."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=MARKDOWN_RESPONSE,
            )
            node = WriteReportNode(id="wr1", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({"question": "Summarize", "verified_claims": []}, ctx)
            assert "report" in result
            assert "# Test Report" in result["report"]
        finally:
            os.environ.pop("TEST_AI_KEY", None)
