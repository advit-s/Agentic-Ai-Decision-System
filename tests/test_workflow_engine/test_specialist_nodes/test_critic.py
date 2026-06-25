"""Tests for CriticNode — deterministic rule checks and LLM paths."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.nodes.specialist.critic import (
    CriticNode,
    _check_confidence,
    _check_contradictions,
    _check_fallacies,
    _check_unsupported,
    _normalize_claims_list,
)
from decision_system.workflow_engine.providers.store import (
    ProviderConfig,
    ProviderStore,
)


def _store_with_provider() -> ProviderStore:
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
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(provider_store: ProviderStore | None = None) -> ExecutionContext:
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if provider_store is not None:
        ctx._provider_store = provider_store
    return ctx


ISSUES_RESPONSE = {
    "id": "cmpl-1",
    "object": "chat.completion",
    "choices": [
        {
            "index": 0,
            "message": {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "issues": [
                            {
                                "type": "contradiction",
                                "severity": "high",
                                "location": "Claim 1 vs Claim 2",
                                "description": "Claims contradict each other",
                                "suggestion": "Reconcile the claims",
                            },
                        ],
                        "summary": "Found 1 contradiction",
                        "confidence_adjustment": -0.3,
                    }
                ),
            },
            "finish_reason": "stop",
        }
    ],
}


class TestCriticNode:
    """CriticNode — AI-powered review and quality checking."""

    pytestmark = pytest.mark.asyncio

    async def test_fallback_empty_input(self):
        """Empty input → returns passed=True with no issues."""
        node = CriticNode(id="c1", config={})
        ctx = _ctx(_fake_store())
        result = await node.execute({"target_data": {}}, ctx)
        assert result["passed"] is True
        assert result["issues"] == []
        assert "Nothing to review" in result["summary"]

    async def test_fallback_unsupported_claims(self):
        """Claims without evidence → flagged as unsupported."""
        node = CriticNode(id="c2", config={"criteria": ["unsupported_claims"]})
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "claims_list",
                "target_data": {"claims": [{"statement": "Test claim with no evidence"}]},
            },
            ctx,
        )
        assert not result["passed"]
        assert any(i["type"] == "unsupported" for i in result["issues"])

    async def test_fallback_contradictions(self):
        """Contradictory claims → flagged."""
        node = CriticNode(id="c3", config={"criteria": ["contradictions"]})
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "claims_list",
                "target_data": {
                    "claims": [
                        {"statement": "Revenue increased last quarter"},
                        {"statement": "Revenue decreased last quarter"},
                    ]
                },
            },
            ctx,
        )
        assert any(i["type"] == "contradiction" for i in result["issues"])

    async def test_fallback_logical_fallacies(self):
        """Fallacy trigger phrases → flagged."""
        node = CriticNode(
            id="c4", config={"criteria": ["logical_fallacies"], "strictness": "strict"}
        )
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "claims_list",
                "target_data": {
                    "claims": [
                        {"statement": "Everyone knows this project will succeed."},
                    ]
                },
            },
            ctx,
        )
        assert any(i["type"] == "logical_fallacy" for i in result["issues"])

    async def test_fallback_confidence_misalignment(self):
        """High confidence with thin evidence → flagged."""
        node = CriticNode(id="c5", config={"criteria": ["confidence_calibration"]})
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "claims_list",
                "target_data": {
                    "claims": [
                        {
                            "statement": "Very confident claim",
                            "confidence": 0.95,
                            "evidence": [],
                        },
                    ]
                },
            },
            ctx,
        )
        assert any(i["type"] == "misconfidence" for i in result["issues"])

    async def test_clean_claims_pass(self):
        """Supported, non-contradictory claims → passed=True."""
        node = CriticNode(
            id="c6",
            config={
                "criteria": ["contradictions", "unsupported_claims"],
            },
        )
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "claims_list",
                "target_data": {
                    "claims": [
                        {"statement": "Revenue increased", "evidence": ["doc1"]},
                        {"statement": "Costs remained stable", "evidence": ["doc2"]},
                    ]
                },
            },
            ctx,
        )
        assert result["passed"] is True

    async def test_with_provider_calls_llm(self, httpx_mock: HTTPXMock):
        """Provider → uses LLM for review."""
        os.environ["TEST_AI_KEY"] = "sk-test"
        try:
            httpx_mock.add_response(
                url="https://test.api/v1/chat/completions",
                method="POST",
                json=ISSUES_RESPONSE,
            )
            node = CriticNode(id="c7", config={"provider": "test-provider"})
            ctx = _ctx(_store_with_provider())
            result = await node.execute(
                {
                    "target_type": "claims_list",
                    "target_data": {"claims": [{"statement": "Test"}]},
                },
                ctx,
            )
            assert "issues" in result
            assert result["confidence_adjustment"] < 0

            # Verify the request included a system prompt
            request = httpx_mock.get_request()
            assert request is not None
            body = json.loads(request.content)
            assert any("Critic" in m.get("content", "") for m in body["messages"])
        finally:
            os.environ.pop("TEST_AI_KEY", None)

    async def test_findings_list_input(self):
        """Findings list format is handled correctly."""
        node = CriticNode(id="c8", config={"criteria": ["unsupported_claims"]})
        ctx = _ctx(_fake_store())
        result = await node.execute(
            {
                "target_type": "findings_list",
                "target_data": {"findings": [{"statement": "Finding with no evidence"}]},
            },
            ctx,
        )
        assert not result["passed"]

    async def test_output_schema_matches_contract(self):
        """Output conforms to output_schema properties."""
        node = CriticNode(id="c9", config={})
        schema = node.get_output_schema()
        assert "passed" in schema["properties"]
        assert "issues" in schema["properties"]
        assert "summary" in schema["properties"]
        assert "confidence_adjustment" in schema["properties"]
        assert "fallback_reason" in schema["properties"]


# ── Unit tests for helper functions ──────────────────────────────────


class TestCriticHelpers:
    def test_check_contradictions_finds_conflict(self):
        claims = [
            {"statement": "Revenue increased last quarter"},
            {"statement": "Revenue decreased last quarter"},
        ]
        issues = _check_contradictions(claims)
        assert len(issues) > 0
        assert issues[0]["type"] == "contradiction"

    def test_check_contradictions_no_false_positive(self):
        claims = [
            {"statement": "Revenue increased last quarter"},
            {"statement": "Costs remained stable"},
        ]
        issues = _check_contradictions(claims)
        assert len(issues) == 0

    def test_check_unsupported_no_evidence(self):
        claims = [{"statement": "Test claim"}]
        issues = _check_unsupported(claims)
        assert len(issues) == 1

    def test_check_unsupported_with_evidence(self):
        claims = [{"statement": "Supported claim", "evidence": ["doc1.md"]}]
        issues = _check_unsupported(claims)
        assert len(issues) == 0

    def test_check_fallacies_detects_phrases(self):
        text = "Everyone knows this is true. Clearly the best approach."
        issues = _check_fallacies(text)
        assert len(issues) >= 2

    def test_check_fallacies_clean_text(self):
        text = "Revenue grew 15% based on Q4 financial statements."
        issues = _check_fallacies(text)
        assert len(issues) == 0

    def test_check_confidence_misaligned(self):
        claims = [{"statement": "High confidence", "confidence": 0.95, "evidence": []}]
        issues = _check_confidence(claims)
        assert len(issues) == 1

    def test_check_confidence_ok(self):
        claims = [{"statement": "Low confidence", "confidence": 0.5, "evidence": ["doc1"]}]
        issues = _check_confidence(claims)
        assert len(issues) == 0

    def test_normalize_claims_list_direct(self):
        result = _normalize_claims_list([{"statement": "test"}])
        assert len(result) == 1

    def test_normalize_claims_list_from_dict(self):
        result = _normalize_claims_list({"claims": [{"statement": "test"}]})
        assert len(result) == 1

    def test_normalize_claims_list_findings(self):
        result = _normalize_claims_list({"findings": [{"statement": "test"}]})
        assert len(result) == 1

    def test_normalize_claims_list_empty(self):
        result = _normalize_claims_list({})
        assert len(result) == 0
