"""Tests for the Ollama provider using mocked HTTP and client calls."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from decision_system.config import Settings
from decision_system.llm.factory import get_provider
from decision_system.llm.ollama_provider import ClaimsEnvelope, OllamaProvider, _parse_response
from decision_system.models import AgentMemo, Claim, EvidenceChunk


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture()
def settings():
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider="ollama",
        nvidia_api_key="",
        nvidia_nim_model="deepseek-ai/deepseek-v4-flash",
        nvidia_temperature=0.0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
        nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama3.1:8b",
        ollama_temperature=0.0,
        ollama_max_tokens=2048,
        ollama_timeout_seconds=60,
    )


@pytest.fixture()
def evidence():
    return [
        EvidenceChunk(
            evidence_id="e1",
            document_id="d1",
            source_path="billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning.",
            score=0.95,
        )
    ]


# ------------------------------------------------------------------
# Agent memo payload helpers
# ------------------------------------------------------------------

def _memo_payload(**overrides):
    base = {
        "agent_name": "technical_analyst",
        "question": "Should we migrate billing?",
        "summary": "Use staged rollout.",
        "claims": ["Billing migration requires rollback planning."],
        "risks": [],
        "options": ["Proceed cautiously"],
        "cited_evidence_ids": ["e1"],
    }
    base.update(overrides)
    return json.dumps(base)


def _claims_payload():
    return json.dumps({
        "claims": [
            {
                "claim_id": "claim-0001",
                "run_id": "run-1",
                "source_agent": "technical_analyst",
                "claim_text": "Billing migration requires rollback planning.",
                "claim_type": "technical",
                "status": "pending",
                "evidence_ids": ["e1"],
                "contradicting_evidence_ids": [],
                "confidence": "low",
                "verification_notes": "",
            }
        ]
    })


# ------------------------------------------------------------------
# _parse_response helper tests
# ------------------------------------------------------------------

class TestParseResponse:
    def test_valid_json(self):
        payload = '{"agent_name": "t", "question": "Q?", "summary": "s", "claims": [], "risks": [], "options": [], "cited_evidence_ids": []}'
        result = _parse_response("AgentMemo", AgentMemo, payload)
        assert isinstance(result, AgentMemo)

    def test_malformed_json_raises(self):
        with pytest.raises(ValueError, match="malformed JSON"):
            _parse_response("AgentMemo", AgentMemo, "not-json")

    def test_invalid_schema_raises(self):
        with pytest.raises(ValueError, match="invalid"):
            _parse_response("AgentMemo", AgentMemo, '{"bad": true}')


# ------------------------------------------------------------------
# Missing model config
# ------------------------------------------------------------------

class TestMissingModel:
    def test_missing_model_raises(self):
        settings = Settings(
            docs_dir=Path("company_docs"),
            store_dir=Path(".decision_system/chroma"),
            collection_name="decision_chunks",
            provider="ollama",
            nvidia_api_key="",
            nvidia_nim_model="deepseek-ai/deepseek-v4-flash",
            nvidia_temperature=0.0,
            nvidia_top_p=0.95,
            nvidia_max_tokens=4096,
            nvidia_reasoning_enabled=False,
            nvidia_reasoning_effort="medium",
            nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
            ollama_base_url="http://localhost:11434",
            ollama_model="",
            ollama_temperature=0.0,
            ollama_max_tokens=2048,
            ollama_timeout_seconds=60,
        )
        with pytest.raises(ValueError, match="OLLAMA_MODEL is required"):
            OllamaProvider(settings)

    def test_invalid_base_url_raises(self, settings):
        broken = replace(settings, ollama_base_url="localhost:11434")

        with pytest.raises(ValueError, match="OLLAMA_BASE_URL"):
            OllamaProvider(broken)


# ------------------------------------------------------------------
# Mocked client tests
# ------------------------------------------------------------------

class TestMockedClient:
    """Use an injected client to avoid any HTTP calls."""

    def _make_provider(self, settings, response_map):
        """Create an OllamaProvider with a mocked client."""
        client = _MockOllamaClient(response_map)
        return OllamaProvider(settings, client=client)

    def test_technical_memo_with_client(self, settings, evidence):
        provider = self._make_provider(settings, {"AgentMemo": _memo_payload()})
        memo = provider.technical_memo("Should we migrate billing?", evidence)
        assert isinstance(memo, AgentMemo)
        assert memo.agent_name == "technical_analyst"
        assert len(memo.claims) == 1
        assert memo.cited_evidence_ids == ["e1"]

    def test_risk_memo_with_client(self, settings, evidence):
        tech = AgentMemo(
            agent_name="technical_analyst",
            question="Should we migrate billing?",
            summary="s",
            claims=[],
            risks=[],
            options=[],
            cited_evidence_ids=[],
        )
        provider = self._make_provider(settings, {"AgentMemo": _memo_payload(agent_name="risk_analyst")})
        risk = provider.risk_memo("Should we migrate billing?", evidence, tech)
        assert isinstance(risk, AgentMemo)
        assert risk.agent_name == "risk_analyst"

    def test_extract_claims_with_client(self, settings):
        provider = self._make_provider(settings, {"ClaimsEnvelope": _claims_payload()})
        tech = AgentMemo(
            agent_name="technical_analyst",
            question="Q?", summary="s", claims=[], risks=[], options=[], cited_evidence_ids=[],
        )
        claims = provider.extract_claims("run-1", [tech])
        assert len(claims) == 1
        assert claims[0].claim_id == "claim-0001"
        assert claims[0].run_id == "run-1"

    def test_write_report_raises(self, settings):
        provider = self._make_provider(settings, {})
        with pytest.raises(NotImplementedError, match="local renderer"):
            provider.write_report("Q?", [], [])

    def test_malformed_client_json_raises(self, settings):
        client = _MockOllamaClient({"AgentMemo": "not-json"})
        provider = OllamaProvider(settings, client=client)
        with pytest.raises(ValueError, match="malformed JSON"):
            provider.technical_memo("Q?", [])

    def test_invalid_client_schema_raises(self, settings):
        client = _MockOllamaClient({"AgentMemo": '{"bad": true}'})
        provider = OllamaProvider(settings, client=client)
        with pytest.raises(ValueError, match="invalid"):
            provider.technical_memo("Q?", [])


class _MockOllamaClient:
    """Minimal Ollama client mock for testing."""

    def __init__(self, response_map: dict[str, str]):
        self._response_map = dict(response_map)
        self.calls: list[dict] = []

    def chat(self, payload: dict) -> str:
        self.calls.append(payload)
        content = ""
        if payload.get("messages"):
            content = " ".join(m.get("content", "") for m in payload["messages"])
        for key in ["ClaimsEnvelope", "AgentMemo"]:
            if key in content and key in self._response_map:
                return self._response_map[key]
        return self._response_map.get("default", '{"agent_name":"technical_analyst","question":"Q?","summary":"s","claims":[],"risks":[],"options":[],"cited_evidence_ids":[]}')


# ------------------------------------------------------------------
# Connection error test (no mock - tests the error path)
# ------------------------------------------------------------------

class TestConnectionError:
    def test_urlerror_message(self, settings):
        """Verify that URL errors produce a clear message mentioning Ollama."""
        import urllib.error

        provider = OllamaProvider(settings, client=None)
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with pytest.raises(ConnectionError, match="Cannot reach Ollama"):
                provider.technical_memo("Q?", [])

    def test_malformed_http_response_json_raises_contextual_error(self, settings):
        provider = OllamaProvider(settings, client=None)

        with patch("urllib.request.urlopen", return_value=_FakeHTTPResponse(b"not-json")):
            with pytest.raises(ValueError, match="malformed HTTP response JSON"):
                provider.technical_memo("Q?", [])


class _FakeHTTPResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._payload


# ------------------------------------------------------------------
# Provider factory tests (supplementing existing test_provider_factory.py)
# ------------------------------------------------------------------

def _ollama_settings(model: str = "llama3.1:8b", provider: str = "ollama"):
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider=provider,
        nvidia_api_key="",
        nvidia_nim_model="deepseek-ai/deepseek-v4-flash",
        nvidia_temperature=0.0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
        nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
        ollama_base_url="http://localhost:11434",
        ollama_model=model,
        ollama_temperature=0.0,
        ollama_max_tokens=2048,
        ollama_timeout_seconds=60,
    )


class TestFactoryWithOllama:
    def test_factory_returns_ollama(self):
        settings = _ollama_settings(model="llama3.1:8b")
        provider = get_provider("ollama", settings=settings)
        assert isinstance(provider, OllamaProvider)

    def test_ollama_factory_missing_model(self):
        settings = _ollama_settings(model="")
        with pytest.raises(ValueError, match="OLLAMA_MODEL is required"):
            get_provider("ollama", settings=settings)

    def test_unknown_provider_error_includes_ollama(self):
        with pytest.raises(ValueError, match="ollama"):
            get_provider("wizard", settings=_ollama_settings())
