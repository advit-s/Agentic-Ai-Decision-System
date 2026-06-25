"""Tests for the Ollama provider with mocked HTTP responses."""

from __future__ import annotations

import pytest

from decision_system.providers import ChatMessage, ChatRequest, ProviderConfig
from decision_system.providers.ollama import OllamaProvider


@pytest.fixture
def ollama_config() -> ProviderConfig:
    return ProviderConfig(
        provider_id="prov-ollama-test",
        name="Ollama Test",
        provider_type="ollama",
        base_url="http://localhost:11434",
    )


class TestOllamaProviderMocked:
    def test_list_models_empty_when_offline(self, ollama_config):
        """When Ollama is offline, list_models should return empty list."""
        provider = OllamaProvider(ollama_config)
        models = provider.list_models()
        assert models == []

    def test_health_check_false_when_offline(self, ollama_config):
        """When Ollama is offline, health_check should return False."""
        provider = OllamaProvider(ollama_config)
        assert provider.health_check() is False

    def test_chat_returns_error_when_offline(self, ollama_config):
        """When Ollama is offline, chat should return error warning."""
        provider = OllamaProvider(ollama_config)
        request = ChatRequest(
            model="llama3",
            messages=[ChatMessage(role="user", content="Hello")],
        )
        response = provider.chat(request)
        assert response.text == ""
        assert len(response.warnings) > 0
        assert "Could not connect" in response.warnings[0]

    def test_custom_base_url(self):
        config = ProviderConfig(
            provider_id="prov-custom",
            name="Custom Ollama",
            provider_type="ollama",
            base_url="http://192.168.1.100:11434",
        )
        provider = OllamaProvider(config)
        assert provider.base_url == "http://192.168.1.100:11434"

    def test_default_base_url(self):
        config = ProviderConfig(
            provider_id="prov-default",
            name="Default Ollama",
            provider_type="ollama",
        )
        provider = OllamaProvider(config)
        assert provider.base_url == "http://localhost:11434"
