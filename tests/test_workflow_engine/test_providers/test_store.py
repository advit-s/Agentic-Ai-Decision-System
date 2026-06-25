"""Tests for ProviderConfig model and ProviderStore."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from decision_system.workflow_engine.providers.store import (
    DuplicateProviderError,
    ProviderConfig,
    ProviderNotFoundError,
    ProviderStore,
)


class TestProviderConfig:
    """ProviderConfig model validation."""

    def test_valid_config(self):
        cfg = ProviderConfig(
            name="test-provider",
            api_base="https://api.example.com/v1",
            api_key_env="TEST_API_KEY",
            default_model="gpt-4o",
        )
        assert cfg.name == "test-provider"
        assert cfg.api_base == "https://api.example.com/v1"
        assert cfg.api_key_env == "TEST_API_KEY"
        assert cfg.default_model == "gpt-4o"

    def test_minimal_config(self):
        """api_key_env can be None for local providers."""
        cfg = ProviderConfig(
            name="local",
            api_base="http://localhost:11434/v1",
            api_key_env=None,
            default_model="llama3",
        )
        assert cfg.api_key_env is None

    def test_default_serialization_roundtrip(self):
        cfg = ProviderConfig(
            name="test",
            api_base="https://test.com/v1",
            api_key_env="KEY",
            default_model="m1",
        )
        data = cfg.model_dump(mode="json")
        restored = ProviderConfig(**data)
        assert restored == cfg

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            ProviderConfig(
                name="",
                api_base="https://x.com/v1",
                default_model="m1",
            )

    def test_invalid_url_rejected(self):
        with pytest.raises(ValueError):
            ProviderConfig(
                name="test",
                api_base="not-a-url",
                api_key_env="K",
                default_model="m1",
            )


class TestProviderStore:
    """ProviderStore CRUD and persistence."""

    def _make_store(self) -> tuple[ProviderStore, Path]:
        tmp = Path(tempfile.mkdtemp())
        prov_file = tmp / ".decision_system" / "providers.json"
        store = ProviderStore(prov_file)
        return store, prov_file

    # ── Loading / Defaults ────────────────────────────────────────────

    def test_load_creates_default_when_missing(self):
        """No file exists → auto-creates with opencode as default."""
        store, prov_file = self._make_store()

        providers = store.load()

        assert len(providers) == 1
        assert providers[0].name == "opencode"
        assert providers[0].api_base == "https://opencode.ai/zen/v1"
        assert providers[0].api_key_env == "OPENCODE_API_KEY"
        assert providers[0].default_model == "claude-sonnet-4-20250514"

    def test_load_auto_creates_file(self):
        """load() actually writes the default file to disk."""
        store, prov_file = self._make_store()
        store.load()
        assert prov_file.exists()

    def test_load_auto_created_content(self):
        """Verify the default file has correct JSON structure."""
        store, prov_file = self._make_store()
        store.load()
        data = json.loads(prov_file.read_text())
        assert "providers" in data
        assert len(data["providers"]) == 1
        assert data["providers"][0]["name"] == "opencode"

    def test_load_returns_existing_providers(self):
        """Existing valid file is loaded correctly."""
        store, prov_file = self._make_store()
        prov_file.parent.mkdir(parents=True, exist_ok=True)
        prov_file.write_text(
            json.dumps(
                {
                    "providers": [
                        {
                            "name": "my-provider",
                            "api_base": "https://my.api/v1",
                            "api_key_env": "MY_KEY",
                            "default_model": "my-model",
                        },
                    ],
                }
            )
        )

        providers = store.load()
        assert len(providers) == 1
        assert providers[0].name == "my-provider"
        assert providers[0].api_base == "https://my.api/v1"

    def test_load_empty_providers_list(self):
        """Empty providers list is valid."""
        store, prov_file = self._make_store()
        prov_file.parent.mkdir(parents=True, exist_ok=True)
        prov_file.write_text(json.dumps({"providers": []}))
        assert store.load() == []

    def test_load_returns_empty_on_corrupt_file(self):
        """Corrupt JSON returns empty list, doesn't crash."""
        store, prov_file = self._make_store()
        prov_file.parent.mkdir(parents=True, exist_ok=True)
        prov_file.write_text("not json")
        assert store.load() == []

    # ── get_default ──────────────────────────────────────────────────

    def test_get_default_returns_first(self):
        """First provider in list is the default."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(name="first", api_base="https://a.com/v1", default_model="m1"),
                ProviderConfig(name="second", api_base="https://b.com/v1", default_model="m2"),
            ]
        )
        default = store.get_default()
        assert default is not None
        assert default.name == "first"

    def test_get_default_returns_none_when_empty(self):
        """Empty list → None."""
        store, prov_file = self._make_store()
        store.save([])
        assert store.get_default() is None

    # ── get ───────────────────────────────────────────────────────────

    def test_get_by_name(self):
        """Finds provider by name."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(name="alpha", api_base="https://a.com/v1", default_model="m1"),
            ]
        )
        found = store.get("alpha")
        assert found is not None
        assert found.name == "alpha"

    def test_get_nonexistent(self):
        """Returns None for missing name."""
        store, prov_file = self._make_store()
        assert store.get("does-not-exist") is None

    def test_get_from_empty_store(self):
        """Returns None when store is empty."""
        store, prov_file = self._make_store()
        store.save([])
        assert store.get("anything") is None

    # ── save ──────────────────────────────────────────────────────────

    def test_save_persists(self):
        """Save then load returns same data."""
        store, prov_file = self._make_store()
        providers = [
            ProviderConfig(name="p1", api_base="https://p1.com/v1", default_model="m1"),
            ProviderConfig(name="p2", api_base="https://p2.com/v1", default_model="m2"),
        ]
        store.save(providers)

        loaded = store.load()
        assert len(loaded) == 2
        assert loaded[0].name == "p1"
        assert loaded[1].name == "p2"

    def test_save_overwrites(self):
        """Save replaces the entire list."""
        store, prov_file = self._make_store()
        store.save([ProviderConfig(name="old", api_base="https://o.com/v1", default_model="m1")])
        store.save([ProviderConfig(name="new", api_base="https://n.com/v1", default_model="m2")])
        loaded = store.load()
        assert len(loaded) == 1
        assert loaded[0].name == "new"

    # ── add ────────────────────────────────────────────────────────────

    def test_add_provider(self):
        """Add appends to list."""
        store, prov_file = self._make_store()
        store.add(ProviderConfig(name="new-one", api_base="https://n.com/v1", default_model="m1"))
        assert len(store.load()) == 2  # default + new

    def test_add_duplicate_name_raises(self):
        """Duplicate name raises DuplicateProviderError."""
        store, prov_file = self._make_store()
        store.add(ProviderConfig(name="dup", api_base="https://a.com/v1", default_model="m1"))
        with pytest.raises(DuplicateProviderError):
            store.add(ProviderConfig(name="dup", api_base="https://b.com/v1", default_model="m2"))

    # ── remove ────────────────────────────────────────────────────────

    def test_remove_provider(self):
        """Remove by name."""
        store, prov_file = self._make_store()
        store.add(ProviderConfig(name="remove-me", api_base="https://r.com/v1", default_model="m1"))
        store.remove("remove-me")
        assert store.get("remove-me") is None

    def test_remove_nonexistent_raises(self):
        """Removing a nonexistent provider raises."""
        store, prov_file = self._make_store()
        with pytest.raises(ProviderNotFoundError):
            store.remove("no-such-provider")

    def test_remove_default_then_new_default(self):
        """Removing the first provider promotes next element as default."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(name="first", api_base="https://a.com/v1", default_model="m1"),
                ProviderConfig(name="second", api_base="https://b.com/v1", default_model="m2"),
            ]
        )
        store.remove("first")
        assert store.get_default() is not None
        assert store.get_default().name == "second"

    # ── set_default ───────────────────────────────────────────────────

    def test_set_default_reorders(self):
        """set_default moves named provider to first position."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(name="alpha", api_base="https://a.com/v1", default_model="m1"),
                ProviderConfig(name="beta", api_base="https://b.com/v1", default_model="m2"),
                ProviderConfig(name="gamma", api_base="https://c.com/v1", default_model="m3"),
            ]
        )
        store.set_default("beta")
        providers = store.load()
        assert providers[0].name == "beta"

    def test_set_default_nonexistent_raises(self):
        """Setting a nonexistent provider as default raises."""
        store, prov_file = self._make_store()
        with pytest.raises(ProviderNotFoundError):
            store.set_default("ghost")

    def test_set_default_already_first(self):
        """Setting the first provider as default is a no-op."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(name="first", api_base="https://a.com/v1", default_model="m1"),
                ProviderConfig(name="second", api_base="https://b.com/v1", default_model="m2"),
            ]
        )
        store.set_default("first")
        assert store.get_default().name == "first"

    # ── Check ─────────────────────────────────────────────────────────

    def test_check_returns_key_status(self):
        """check() returns list with api_key_configured booleans."""
        store, prov_file = self._make_store()
        store.save(
            [
                ProviderConfig(
                    name="with-key",
                    api_base="https://a.com/v1",
                    api_key_env="EXISTING_VAR",
                    default_model="m1",
                ),
                ProviderConfig(
                    name="no-key",
                    api_base="https://b.com/v1",
                    api_key_env="MISSING_VAR",
                    default_model="m2",
                ),
            ]
        )
        # Temporarily set a known env var
        os.environ["EXISTING_VAR"] = "sk-test"
        try:
            results = store.check()
            assert len(results) == 2
            # Find by name
            wk = next(r for r in results if r["name"] == "with-key")
            nk = next(r for r in results if r["name"] == "no-key")
            assert wk["api_key_configured"] is True
            assert nk["api_key_configured"] is False
        finally:
            os.environ.pop("EXISTING_VAR", None)

    def test_check_empty_store(self):
        """check() on empty store returns empty list."""
        store, prov_file = self._make_store()
        store.save([])
        assert store.check() == []


class TestProviderStoreFileCreation:
    """Edge cases around file and directory creation."""

    def test_parent_created_automatically(self):
        """If .decision_system/ doesn't exist, save creates it."""
        tmp = Path(tempfile.mkdtemp())
        prov_file = tmp / "nested" / "path" / "providers.json"
        assert not prov_file.parent.exists()
        store = ProviderStore(prov_file)
        store.save([ProviderConfig(name="test", api_base="https://t.com/v1", default_model="m1")])
        assert prov_file.exists()
        assert prov_file.parent.exists()
