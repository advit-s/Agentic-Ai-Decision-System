"""Tests for provider resolution in the execution engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from decision_system.workflow_engine.models import ExecutionContext
from decision_system.workflow_engine.providers.store import (
    ProviderConfig,
    ProviderStore,
)


@pytest.fixture
def store_with_providers() -> ProviderStore:
    """Provider store with multiple named providers."""
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save(
        [
            ProviderConfig(
                name="default-provider",
                api_base="https://default.api/v1",
                api_key_env="DEFAULT_KEY",
                default_model="default-model",
            ),
            ProviderConfig(
                name="secondary",
                api_base="https://second.api/v1",
                api_key_env="SECOND_KEY",
                default_model="second-model",
            ),
        ]
    )
    return store


@pytest.fixture
def empty_store() -> ProviderStore:
    """Empty provider store."""
    tmp = Path(tempfile.mkdtemp())
    store = ProviderStore(tmp / "providers.json")
    store.save([])
    return store


def _ctx(store: ProviderStore | None = None) -> ExecutionContext:
    """Helper: create an ExecutionContext with optional provider store."""
    ctx = ExecutionContext(workflow_id="wf-1", execution_id="exec-1")
    if store is not None:
        ctx._provider_store = store
    return ctx


# ── Tests ─────────────────────────────────────────────────────────────


class TestResolveProvider:
    """ExecutionContext.resolve_provider() resolution order."""

    def test_resolve_with_node_override(self, store_with_providers: ProviderStore):
        """Node specifies provider + model → returns that provider + model."""
        ctx = _ctx(store_with_providers)
        result = ctx.resolve_provider(provider_name="secondary", model="custom-model")
        assert result is not None
        provider_cfg, resolved_model = result
        assert provider_cfg.name == "secondary"
        assert resolved_model == "custom-model"

    def test_resolve_with_node_provider_only(self, store_with_providers: ProviderStore):
        """Node specifies provider, no model → provider + its default_model."""
        ctx = _ctx(store_with_providers)
        result = ctx.resolve_provider(provider_name="secondary")
        assert result is not None
        provider_cfg, resolved_model = result
        assert provider_cfg.name == "secondary"
        assert resolved_model == "second-model"

    def test_resolve_without_override(self, store_with_providers: ProviderStore):
        """No node override → returns system default (first provider)."""
        ctx = _ctx(store_with_providers)
        result = ctx.resolve_provider()
        assert result is not None
        provider_cfg, resolved_model = result
        assert provider_cfg.name == "default-provider"
        assert resolved_model == "default-model"

    def test_resolve_fallback_to_fake(self, empty_store: ProviderStore):
        """No providers configured → returns None (caller uses fake)."""
        ctx = _ctx(empty_store)
        assert ctx.resolve_provider() is None

    def test_resolve_invalid_provider_falls_to_default(self, store_with_providers: ProviderStore):
        """Nonexistent provider name → falls to system default."""
        ctx = _ctx(store_with_providers)
        result = ctx.resolve_provider(provider_name="does-not-exist")
        assert result is not None
        provider_cfg, _ = result
        assert provider_cfg.name == "default-provider"

    def test_resolve_invalid_provider_with_empty_store(self, empty_store: ProviderStore):
        """Nonexistent provider + empty store → None."""
        ctx = _ctx(empty_store)
        result = ctx.resolve_provider(provider_name="anything")
        assert result is None

    def test_resolve_no_store_configured(self):
        """No provider_store attached → returns None."""
        ctx = _ctx(None)
        assert ctx.resolve_provider() is None

    def test_resolve_empty_provider_name_uses_default(self, store_with_providers: ProviderStore):
        """Empty string provider name → default."""
        ctx = _ctx(store_with_providers)
        result = ctx.resolve_provider(provider_name="")
        assert result is not None
        provider_cfg, _ = result
        assert provider_cfg.name == "default-provider"
