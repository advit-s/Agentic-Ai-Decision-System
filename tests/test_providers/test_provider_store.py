"""Tests for the provider configuration store."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from decision_system.providers import (
    ProviderCreateRequest,
    ProviderUpdateRequest,
    create_provider,
    delete_provider,
    get_provider,
    get_provider_by_name,
    get_providers_by_type,
    list_providers,
    provider_exists,
    update_provider,
)


@pytest.fixture
def tmp_store(tmp_path: Path):
    """Set up a temporary provider store directory."""
    os.environ["DECISION_SYSTEM_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)


class TestProviderStore:
    def test_create_and_get(self, tmp_store):
        req = ProviderCreateRequest(
            name="Local Ollama",
            provider_type="ollama",
            base_url="http://localhost:11434",
        )
        config = create_provider(req)
        assert config.name == "Local Ollama"
        assert config.provider_type == "ollama"
        assert config.base_url == "http://localhost:11434"
        assert config.provider_id == "prov-local-ollama"

        fetched = get_provider(config.provider_id)
        assert fetched is not None
        assert fetched.name == "Local Ollama"
        assert fetched.provider_type == "ollama"

    def test_list_empty(self, tmp_store):
        providers = list_providers()
        assert providers == []

    def test_list_with_providers(self, tmp_store):
        create_provider(ProviderCreateRequest(name="Fake", provider_type="fake"))
        create_provider(ProviderCreateRequest(name="Ollama", provider_type="ollama"))
        providers = list_providers()
        assert len(providers) == 2

    def test_update_provider(self, tmp_store):
        req = ProviderCreateRequest(name="Test", provider_type="fake")
        config = create_provider(req)
        assert config.default_model is None

        update_req = ProviderUpdateRequest(default_model="gpt-4")
        updated = update_provider(config.provider_id, update_req)
        assert updated is not None
        assert updated.default_model == "gpt-4"

    def test_update_nonexistent(self, tmp_store):
        update_req = ProviderUpdateRequest(name="New Name")
        result = update_provider("nonexistent-id", update_req)
        assert result is None

    def test_delete_provider(self, tmp_store):
        req = ProviderCreateRequest(name="Delete Me", provider_type="fake")
        config = create_provider(req)
        assert provider_exists(config.provider_id)

        deleted = delete_provider(config.provider_id)
        assert deleted is True
        assert provider_exists(config.provider_id) is False

    def test_delete_nonexistent(self, tmp_store):
        assert delete_provider("nonexistent") is False

    def test_get_by_name(self, tmp_store):
        create_provider(ProviderCreateRequest(name="My Ollama", provider_type="ollama"))
        found = get_provider_by_name("My Ollama")
        assert found is not None
        assert found.provider_type == "ollama"

    def test_get_by_type(self, tmp_store):
        create_provider(ProviderCreateRequest(name="Fake 1", provider_type="fake"))
        create_provider(ProviderCreateRequest(name="Fake 2", provider_type="fake"))
        create_provider(ProviderCreateRequest(name="Ollama", provider_type="ollama"))
        fakes = get_providers_by_type("fake")
        assert len(fakes) == 2
        ollamas = get_providers_by_type("ollama")
        assert len(ollamas) == 1

    def test_api_key_not_stored(self, tmp_store):
        """Verify plaintext API keys are never stored in the config file."""
        os.environ["TEST_OPENAI_KEY"] = "sk-test123"
        req = ProviderCreateRequest(
            name="OpenAI",
            provider_type="openai",
            api_key_env="TEST_OPENAI_KEY",
        )
        config = create_provider(req)
        assert config.api_key_configured is True

        # Read raw JSON to confirm no API key value is stored
        import json

        store_dir = tmp_store / "providers"
        json_file = store_dir / f"{config.provider_id}.json"
        raw = json.loads(json_file.read_text(encoding="utf-8"))
        assert "api_key" not in raw
        assert raw.get("api_key_env") == "TEST_OPENAI_KEY"
        assert "api_key_configured" in raw
        os.environ.pop("TEST_OPENAI_KEY", None)
