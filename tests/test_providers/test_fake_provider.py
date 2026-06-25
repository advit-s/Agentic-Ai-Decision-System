"""Tests for the fake/dev provider runtime."""

from __future__ import annotations

import pytest

from decision_system.providers import (
    ChatMessage,
    ChatRequest,
    FakeProvider,
    ProviderConfig,
    ProviderCreateRequest,
    ProviderRuntime,
    execute_with_timing,
)


@pytest.fixture
def fake_config() -> ProviderConfig:
    return ProviderConfig(
        provider_id="prov-fake-test",
        name="Fake Test",
        provider_type="fake",
    )


class TestFakeProvider:
    def test_list_models(self, fake_config):
        provider = FakeProvider(fake_config)
        models = provider.list_models()
        assert len(models) == 2
        assert "fake-model-1" in models
        assert "fake-model-2" in models

    def test_health_check(self, fake_config):
        provider = FakeProvider(fake_config)
        assert provider.health_check() is True

    def test_default_chat(self, fake_config):
        provider = FakeProvider(fake_config)
        request = ChatRequest(
            model="fake-model-1",
            messages=[ChatMessage(role="user", content="What is the analysis?")],
        )
        response = provider.chat(request)
        assert response.provider_id == "prov-fake-test"
        assert response.provider_type == "fake"
        assert response.model == "fake-model-1"
        assert len(response.text) > 0
        assert response.usage is not None
        assert response.usage["total_tokens"] == 150

    def test_summary_chat(self, fake_config):
        provider = FakeProvider(fake_config)
        request = ChatRequest(
            model="fake-model-1",
            messages=[ChatMessage(role="user", content="Please summarize the findings")],
        )
        response = provider.chat(request)
        assert "## Summary" in response.text

    def test_claims_chat(self, fake_config):
        provider = FakeProvider(fake_config)
        request = ChatRequest(
            model="fake-model-1",
            messages=[ChatMessage(role="user", content="Extract claims from evidence")],
        )
        response = provider.chat(request)
        assert "claim_text" in response.text
        assert "Billing migration" in response.text

    def test_generate_convenience(self, fake_config):
        provider = FakeProvider(fake_config)
        response = provider.generate(model="fake-model-1", prompt="Summarize the data")
        assert response.text is not None

    def test_deterministic_output(self, fake_config):
        """Fake provider output should be deterministic for same input."""
        provider = FakeProvider(fake_config)
        req = ChatRequest(
            model="fake-model-1",
            messages=[ChatMessage(role="user", content="Summarize the key points")],
        )
        resp1 = provider.chat(req)
        resp2 = provider.chat(req)
        assert resp1.text == resp2.text


class TestExecuteWithTiming:
    def test_timing_included(self, fake_config):
        provider = FakeProvider(fake_config)
        request = ChatRequest(
            model="fake-model-1",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        response = execute_with_timing(provider, request)
        assert response.latency_ms >= 0
        assert response.text is not None


class TestProviderRuntimeWithFake:
    def test_runtime_get_fake_provider(self):
        # Create a fake provider config and register it with runtime
        import os
        import tempfile

        tmp = tempfile.mkdtemp()
        old_data_dir = os.environ.get("DECISION_SYSTEM_DATA_DIR")
        os.environ["DECISION_SYSTEM_DATA_DIR"] = tmp
        try:
            from decision_system.providers.store import create_provider

            req = ProviderCreateRequest(name="Runtime Fake", provider_type="fake")
            config = create_provider(req)
            runtime = ProviderRuntime()
            provider = runtime.get_provider(config.provider_id)
            assert provider is not None
            assert provider.provider_type == "fake"
            assert provider.health_check() is True
        finally:
            import shutil

            shutil.rmtree(tmp, ignore_errors=True)
            if old_data_dir is not None:
                os.environ["DECISION_SYSTEM_DATA_DIR"] = old_data_dir
            else:
                os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)
