"""Tests for the NVIDIA NIM provider using the OpenAI-compatible API."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_system.config import Settings
from decision_system.llm.nvidia_nim_provider import NvidiaNimProvider
from decision_system.models import AgentMemo, EvidenceChunk


class FakeOpenAI:
    """Mock OpenAI client for testing."""

    def __init__(self, response_payload: str):
        self.payload = response_payload
        self.create_calls: list[dict] = []
        self.chat = self._Chat(self)

    class _Chat:
        def __init__(self, parent):
            self.parent = parent
            self.completions = self._Completions(parent)

        class _Completions:
            def __init__(self, parent):
                self.parent = parent

            def create(self, **kwargs):
                self.parent.create_calls.append(kwargs)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(content=self.parent.payload),
                        )
                    ]
                )


def _settings():
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider="nvidia_nim",
        nvidia_api_key="key",
        nvidia_nim_model="deepseek-ai/deepseek-v4-flash",
        nvidia_nim_base_url="https://integrate.api.nvidia.com/v1",
        nvidia_temperature=0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
        ollama_base_url="http://localhost:11434",
        ollama_model="",
        ollama_temperature=0,
        ollama_max_tokens=2048,
        ollama_timeout_seconds=60,
    )


def _evidence():
    return [
        EvidenceChunk(
            evidence_id="e1",
            document_id="d1",
            source_path="billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning.",
        )
    ]


def test_mocked_nim_response_parses_into_agent_memo():
    payload = json.dumps(
        {
            "agent_name": "technical_analyst",
            "question": "Should we migrate billing?",
            "summary": "Use staged rollout.",
            "claims": ["Billing migration requires rollback planning."],
            "risks": [],
            "options": ["Proceed cautiously"],
            "cited_evidence_ids": ["e1"],
        }
    )
    fake_client = FakeOpenAI(payload)
    provider = NvidiaNimProvider(_settings(), client=fake_client)

    memo = provider.technical_memo("Should we migrate billing?", _evidence())

    assert isinstance(memo, AgentMemo)
    assert memo.cited_evidence_ids == ["e1"]
    assert fake_client.create_calls


def test_mocked_nim_response_parses_into_claim():
    payload = json.dumps(
        {
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
        }
    )
    provider = NvidiaNimProvider(_settings(), client=FakeOpenAI(payload))

    claims = provider.extract_claims(
        "run-1",
        [
            AgentMemo(
                agent_name="technical_analyst",
                question="Should we migrate billing?",
                summary="Use staged rollout.",
                claims=["Billing migration requires rollback planning."],
                cited_evidence_ids=["e1"],
            )
        ],
    )

    assert claims[0].claim_id == "claim-0001"
    assert claims[0].run_id == "run-1"
    assert claims[0].evidence_ids == ["e1"]


def test_malformed_json_response_fails_safely():
    provider = NvidiaNimProvider(_settings(), client=FakeOpenAI("not-json"))

    with pytest.raises(ValueError, match="NVIDIA NIM returned malformed JSON"):
        provider.technical_memo("Should we migrate billing?", [])


def test_provider_passes_api_settings_to_openai(monkeypatch):
    captured_kwargs: dict[str, object] = {}

    class CapturingOpenAI:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self.chat = self._Chat(self)

        class _Chat:
            def __init__(self, parent):
                self.completions = self._Completions(parent)

            class _Completions:
                def __init__(self, parent):
                    self.parent = parent

                def create(self, **kwargs):
                    return SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content=json.dumps(
                                        {
                                            "agent_name": "technical_analyst",
                                            "question": "Should we migrate billing?",
                                            "summary": "Use staged rollout.",
                                            "claims": [],
                                            "risks": [],
                                            "options": [],
                                            "cited_evidence_ids": [],
                                        }
                                    )
                                )
                            )
                        ]
                    )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=CapturingOpenAI))
    settings = _settings()
    provider = NvidiaNimProvider(settings)
    provider._openai = None

    provider.technical_memo("Should we migrate billing?", [])

    assert captured_kwargs["api_key"] == "key"
    assert captured_kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_provider_uses_nvidia_nim_base_url_from_settings(monkeypatch):
    """Verify that base_url is configurable."""

    class FakeOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.chat = self._Chat(self)

        class _Chat:
            def __init__(self, parent):
                self.completions = self._Completions(parent)

            class _Completions:
                def __init__(self, parent):
                    self.parent = parent

                def create(self, **kwargs):
                    return SimpleNamespace(
                        choices=[
                            SimpleNamespace(
                                message=SimpleNamespace(
                                    content=json.dumps(
                                        {
                                            "agent_name": "technical_analyst",
                                            "question": "Should we migrate billing?",
                                            "summary": "Use staged rollout.",
                                            "claims": [],
                                            "risks": [],
                                            "options": [],
                                            "cited_evidence_ids": [],
                                        }
                                    )
                                )
                            )
                        ]
                    )

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    settings = _settings()
    provider = NvidiaNimProvider(settings)
    assert provider.settings.nvidia_nim_base_url == "https://integrate.api.nvidia.com/v1"
