import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from decision_system.config import Settings
from decision_system.llm.nvidia_nim_provider import NvidiaNimProvider
from decision_system.models import AgentMemo, EvidenceChunk


class FakeChatNVIDIA:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        return SimpleNamespace(content=self.payload, additional_kwargs={"reasoning": "mock reasoning"})


def _settings():
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider="nvidia_nim",
        nvidia_api_key="key",
        nvidia_nim_model="deepseek-ai/deepseek-v4-flash",
        nvidia_temperature=0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
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
    fake_client = FakeChatNVIDIA(payload)
    provider = NvidiaNimProvider(_settings(), client=fake_client)

    memo = provider.technical_memo("Should we migrate billing?", _evidence())

    assert isinstance(memo, AgentMemo)
    assert memo.cited_evidence_ids == ["e1"]
    assert fake_client.calls


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
    provider = NvidiaNimProvider(_settings(), client=FakeChatNVIDIA(payload))

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
    provider = NvidiaNimProvider(_settings(), client=FakeChatNVIDIA("not-json"))

    with pytest.raises(ValueError, match="NVIDIA NIM returned malformed JSON"):
        provider.technical_memo("Should we migrate billing?", [])


def test_provider_builds_chat_nvidia_with_configured_settings(monkeypatch):
    captured = {}

    class CapturingChatNVIDIA:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def invoke(self, messages):
            return SimpleNamespace(
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
                ),
                additional_kwargs={},
            )

    monkeypatch.setitem(
        sys.modules,
        "langchain_nvidia_ai_endpoints",
        SimpleNamespace(ChatNVIDIA=CapturingChatNVIDIA),
    )
    provider = NvidiaNimProvider(_settings())

    provider.technical_memo("Should we migrate billing?", [])

    assert captured["model"] == "deepseek-ai/deepseek-v4-flash"
    assert captured["api_key"] == "key"
    assert "base_url" not in captured
    assert captured["temperature"] == 0
    assert captured["top_p"] == 0.95
    assert captured["max_tokens"] == 4096
    assert "extra_body" not in captured


def test_provider_passes_reasoning_config_when_enabled(monkeypatch):
    captured = {}

    class CapturingChatNVIDIA:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def invoke(self, messages):
            return SimpleNamespace(
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
                ),
                additional_kwargs={},
            )

    monkeypatch.setitem(
        sys.modules,
        "langchain_nvidia_ai_endpoints",
        SimpleNamespace(ChatNVIDIA=CapturingChatNVIDIA),
    )
    base_settings = _settings()
    settings = Settings(
        docs_dir=base_settings.docs_dir,
        store_dir=base_settings.store_dir,
        collection_name=base_settings.collection_name,
        provider=base_settings.provider,
        nvidia_api_key=base_settings.nvidia_api_key,
        nvidia_nim_model=base_settings.nvidia_nim_model,
        nvidia_temperature=base_settings.nvidia_temperature,
        nvidia_top_p=base_settings.nvidia_top_p,
        nvidia_max_tokens=base_settings.nvidia_max_tokens,
        nvidia_reasoning_enabled=True,
        nvidia_reasoning_effort="medium",
    )
    provider = NvidiaNimProvider(settings)

    provider.technical_memo("Should we migrate billing?", [])

    assert captured["extra_body"] == {
        "chat_template_kwargs": {
            "thinking": True,
            "reasoning_effort": "medium",
        }
    }
