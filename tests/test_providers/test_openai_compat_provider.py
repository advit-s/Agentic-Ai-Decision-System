"""Tests for the OpenAI-compatible provider with mocked HTTP responses."""

from __future__ import annotations

import pytest

from decision_system.providers import ProviderConfig, ChatRequest, ChatMessage
from decision_system.providers.openai_compat import OpenAICompatibleProvider


@pytest.fixture
def openai_config() -> ProviderConfig:
    return ProviderConfig(
        provider_id="prov-openai-test",
        name="OpenAI Compat Test",
        provider_type="openai_compatible",
        base_url="http://localhost:1234/v1",
    )


class TestOpenAICompatibleProviderMocked:
    def test_list_models_empty_when_offline(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        models = provider.list_models()
        assert models == []

    def test_health_check_false_when_offline(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        assert provider.health_check() is False

    def test_chat_returns_error_when_offline(self, openai_config):
        provider = OpenAICompatibleProvider(openai_config)
        request = ChatRequest(
            model="local-model",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        response = provider.chat(request)
        assert response.text == ""
        assert len(response.warnings) > 0
        assert "Could not connect" in response.warnings[0]

    def test_no_base_url(self):
        config = ProviderConfig(
            provider_id="prov-no-url",
            name="No URL",
            provider_type="openai_compatible",
        )
        provider = OpenAICompatibleProvider(config)
        assert provider.base_url == ""

    def test_api_key_from_env(self):
        import os
        os.environ["TEST_LOCAL_KEY"] = "sk-local-test-key"
        config = ProviderConfig(
            provider_id="prov-key-test",
            name="Key Test",
            provider_type="openai_compatible",
            base_url="http://localhost:8080",
            api_key_env="TEST_LOCAL_KEY",
        )
        provider = OpenAICompatibleProvider(config)
        assert provider.api_key == "sk-local-test-key"
        os.environ.pop("TEST_LOCAL_KEY", None)

    def test_api_key_optional_for_local(self):
        config = ProviderConfig(
            provider_id="prov-no-key",
            name="No Key",
            provider_type="openai_compatible",
            base_url="http://localhost:8080",
        )
        provider = OpenAICompatibleProvider(config)
        assert provider.api_key is None
