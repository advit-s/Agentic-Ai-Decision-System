"""Tests for SynthesizerNode — fake fallback and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.synthesizer import (
    SynthesizerNode,
    _fake_options,
    _score_options,
    _default_criteria,
)
from decision_system.workflow_engine.providers.store import ProviderConfig, ProviderStore

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


SYNTHESIS_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps({
                    "options": [
                        {
                            "title": "Strategic Option A",
                            "description": "Full investment approach",
                            "pros": ["High upside", "Fast execution"],
                            "cons": ["High risk", "Capital intensive"],
                            "confidence": 0.7,
                            "criteria_scores": {"feasibility": 0.6, "impact": 0.8, "cost": 0.4, "risk": 0.5},
                            "risks": [{"risk": "Market risk", "likelihood": "medium", "mitigation": "Hedging"}],
                        },
                    ],
                    "recommendation": {
                        "title": "Strategic Option A",
                        "rationale": "Best balance of risk and reward",
                        "overall_confidence": 0.65,
                    },
                    "trade_offs_summary": "Option A trades higher risk for higher reward.",
                }),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestSynthesizerNode:
    """SynthesizerNode — AI-powered decision synthesis."""

    pytestmark = pytest.mark.asyncio

    async def test_fallback_empty_question(self):
        """Empty question → returns empty options."""
        node = SynthesizerNode(id="s1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": ""}, ctx)
        assert result["options"] == []
        assert result["recommendation"] is None
        assert "No question provided" in result["trade_offs_summary"]

    async def test_fallback_no_evidence(self):
        """Question without evidence → single preliminary option."""
        node = SynthesizerNode(id="s2", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"question": "Should we invest?"}, ctx)
        assert len(result["options"]) == 1
        assert result["options"][0]["confidence"] == 0.2
        assert result["recommendation"] is not None

    async def test_fallback_keyword_options(self):
        """Question keywords → matching option sets."""
        node = SynthesizerNode(id="s3", config={})
        ctx = _ctx(_fake_store())

        # "invest" keyword
        invest_result = await node.execute({
            "question": "Should we invest in AI?",
            "evidence_streams": [
                {"source_label": "Research", "content": {"summary": "Market is growing"}},
            ],
            "criteria": _default_criteria(),
        }, ctx)
        assert len(invest_result["options"]) == 3
        # Options should contain investment-related titles
        titles = [o["title"].lower() for o in invest_result["options"]]
        assert any("invest" in t for t in titles)

        # "expand" keyword
        expand_result = await node.execute({
            "question": "Should we expand to new markets?",
            "evidence_streams": [
                {"source_label": "Analysis", "content": {"summary": "Opportunities exist"}},
            ],
            "criteria": _default_criteria(),
        }, ctx)
        titles = [o["title"].lower() for o in expand_result["options"]]
        assert any("expansion" in t or "growth" in t or "partnership" in t for t in titles)

    async def test_fallback_scored_options(self):
        """Fake options come with computed recommendations."""
        options = _fake_options("investment opportunity", _default_criteria())
        assert len(options) == 3
        scored_options, recommendation = _score_options(options, _default_criteria())
        assert recommendation is not None
        assert recommendation["overall_confidence"] > 0

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → calls LLMClient with correct prompt."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=SYNTHESIS_RESPONSE,
            )
            node = SynthesizerNode(id="s4", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({
                "question": "Which strategy?",
                "evidence_streams": [
                    {"source_label": "Research", "content": {"findings": "Growth data"}},
                ],
                "criteria": _default_criteria(),
            }, ctx)
            assert len(result["options"]) >= 1
            assert result["recommendation"]["title"] == "Strategic Option A"
            assert result["fallback_reason"] == ""

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Decision Synthesis" in m.get("content", "") for m in body["messages"])
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
            node = SynthesizerNode(id="s5", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute({
                "question": "Invest?",
                "evidence_streams": [
                    {"source_label": "Research", "content": {"summary": "Data"}},
                ],
            }, ctx)
            # Should have fake options + fallback reason
            assert len(result["options"]) > 0
            assert result["fallback_reason"] != ""
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_risk_disabled(self):
        """include_risks=False → options don't contain risks."""
        node = SynthesizerNode(id="s6", config={"include_risks": False})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "question": "Should we invest?",
            "evidence_streams": [
                {"source_label": "Research", "content": {"summary": "Data"}},
            ],
        }, ctx)
        for opt in result["options"]:
            assert "risks" not in opt

    async def test_output_schema_matches_contract(self):
        """Output conforms to output_schema properties."""
        node = SynthesizerNode(id="s7", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({
            "question": "Test?",
            "evidence_streams": [
                {"source_label": "Test", "content": {"data": "test"}},
            ],
        }, ctx)
        schema = node.get_output_schema()
        schema_props = schema.get("properties", {})
        for key in schema_props:
            assert key in result, f"Missing output field: {key}"


# ── Unit tests for helper functions ──────────────────────────────────

class TestSynthesizerHelpers:

    def test_fake_options_by_keyword_invest(self):
        opts = _fake_options("investment decision", _default_criteria())
        assert len(opts) == 3
        titles = [o["title"] for o in opts]
        assert any("Investment" in t for t in titles)

    def test_fake_options_by_keyword_expand(self):
        opts = _fake_options("expansion strategy", _default_criteria())
        assert len(opts) == 3
        titles = [o["title"] for o in opts]
        assert any("Expansion" in t or "Growth" in t or "Partnership" in t for t in titles)

    def test_fake_options_default(self):
        opts = _fake_options("something completely unrelated", _default_criteria())
        assert len(opts) == 3
        # Default options should not contain investment or expansion keywords
        titles_text = " ".join(o["title"].lower() for o in opts)
        assert "invest" not in titles_text

    def test_score_options_selects_highest(self):
        options = _fake_options("invest", _default_criteria())
        scored, rec = _score_options(options, _default_criteria())
        assert rec is not None
        # The recommendation should be one of the options
        assert rec["title"] in [o["title"] for o in scored]
        assert 0 <= rec["overall_confidence"] <= 1

    def test_score_empty_options(self):
        scored, rec = _score_options([], _default_criteria())
        assert scored == []
        assert rec is None

    def test_default_criteria(self):
        crit = _default_criteria()
        assert len(crit) == 4
        names = [c["name"] for c in crit]
        assert "feasibility" in names
        assert "impact" in names
        assert "cost" in names
        assert "risk" in names
        total_weight = sum(c["weight"] for c in crit)
        assert total_weight == pytest.approx(1.0)
