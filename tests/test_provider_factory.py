from pathlib import Path

import pytest

from decision_system.config import Settings
from decision_system.llm.fake_provider import FakeProvider
from decision_system.llm.factory import get_provider
from decision_system.llm.nvidia_nim_provider import NvidiaNimProvider


def _settings(provider="fake", api_key="", model="deepseek-ai/deepseek-v4-flash"):
    return Settings(
        docs_dir=Path("company_docs"),
        store_dir=Path(".decision_system/chroma"),
        collection_name="decision_chunks",
        provider=provider,
        nvidia_api_key=api_key,
        nvidia_nim_model=model,
        nvidia_temperature=0,
        nvidia_top_p=0.95,
        nvidia_max_tokens=4096,
        nvidia_reasoning_enabled=False,
        nvidia_reasoning_effort="medium",
    )


def test_fake_provider_remains_default():
    provider = get_provider(settings=_settings())

    assert isinstance(provider, FakeProvider)


def test_nvidia_nim_provider_loads_when_env_vars_exist():
    provider = get_provider(settings=_settings("nvidia_nim", "key"))

    assert isinstance(provider, NvidiaNimProvider)


def test_missing_nvidia_api_key_gives_clear_error():
    with pytest.raises(ValueError, match="NVIDIA_API_KEY is required"):
        get_provider(settings=_settings("nvidia_nim", ""))


def test_unknown_provider_gives_clear_error():
    with pytest.raises(ValueError, match="Unknown DECISION_PROVIDER"):
        get_provider(settings=_settings("mystery"))
