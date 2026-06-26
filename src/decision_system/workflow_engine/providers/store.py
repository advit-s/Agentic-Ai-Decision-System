"""Provider configuration store — persists provider definitions as JSON."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, field_validator


class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider instance.

    Each provider is an OpenAI-compatible API endpoint.
    The first provider in the list is the system default.
    """

    name: str
    api_base: str
    api_key_env: str | None = None
    default_model: str

    @field_validator("name")
    @classmethod
    def name_must_be_non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Provider name must not be empty")
        return v.strip()

    @field_validator("api_base")
    @classmethod
    def api_base_must_be_valid(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"api_base must start with http:// or https://, got: {v}")
        return v.rstrip("/")


class DuplicateProviderError(ValueError):
    """Raised when adding a provider with a name that already exists."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Provider '{name}' already exists")
        self.provider_name = name


class ProviderNotFoundError(ValueError):
    """Raised when referencing a provider name that does not exist."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Provider '{name}' not found")
        self.provider_name = name


DEFAULT_PROVIDERS = [
    ProviderConfig(
        name="opencode",
        api_base="https://opencode.ai/zen/v1",
        api_key_env="OPENCODE_API_KEY",
        default_model="claude-sonnet-4-20250514",
    ),
]


class ProviderStore:
    """JSON file-backed store for LLM provider configurations.

    Each provider is stored as an entry in a JSON file with a
    ``{"providers": [...]}`` structure. The file is auto-created
    with a default opencode entry when it doesn't exist.

    Usage::

        store = ProviderStore()
        all_providers = store.load()
        default = store.get_default()
        provider = store.get("opencode")
        store.add(new_provider)
        store.remove("bad-provider")
        store.set_default("openai")
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path else self._default_path()

    @staticmethod
    def _default_path() -> Path:
        from decision_system._data_root import get_data_root

        return get_data_root() / "workflow_providers.json"

    # ── Public API ────────────────────────────────────────────────────

    def load(self) -> list[ProviderConfig]:
        """Load all providers from the JSON file.

        If the file doesn't exist, creates it with default providers
        and returns those. Returns an empty list on corrupt data.
        """
        if not self._path.exists():
            self.save(DEFAULT_PROVIDERS)
            return list(DEFAULT_PROVIDERS)

        data = self._read_json()
        if data is None:
            return []

        raw_list: list[dict[str, Any]] = data.get("providers", [])
        providers: list[ProviderConfig] = []
        for item in raw_list:
            try:
                providers.append(ProviderConfig(**item))
            except (ValueError, TypeError):
                continue  # skip corrupt entries
        return providers

    def save(self, providers: list[ProviderConfig]) -> None:
        """Overwrite the provider list in the JSON file."""
        self._ensure_dir()
        self._write_json({"providers": [p.model_dump(mode="json") for p in providers]})

    def get_default(self) -> ProviderConfig | None:
        """Return the first provider in the list, or None if empty."""
        providers = self.load()
        return providers[0] if providers else None

    def get(self, name: str) -> ProviderConfig | None:
        """Look up a provider by name. Returns None if not found."""
        for p in self.load():
            if p.name == name:
                return p
        return None

    def add(self, provider: ProviderConfig) -> None:
        """Append a new provider. Raises DuplicateProviderError on duplicate name."""
        providers = self.load()
        if any(p.name == provider.name for p in providers):
            raise DuplicateProviderError(provider.name)
        providers.append(provider)
        self.save(providers)

    def remove(self, name: str) -> None:
        """Remove a provider by name. Raises ProviderNotFoundError if missing."""
        providers = self.load()
        before = len(providers)
        providers = [p for p in providers if p.name != name]
        if len(providers) == before:
            raise ProviderNotFoundError(name)
        self.save(providers)

    def set_default(self, name: str) -> None:
        """Move a provider to the first position (system default).

        Raises ProviderNotFoundError if the name doesn't exist.
        """
        providers = self.load()
        idx = next((i for i, p in enumerate(providers) if p.name == name), None)
        if idx is None:
            raise ProviderNotFoundError(name)
        if idx == 0:
            return  # already first
        provider = providers.pop(idx)
        providers.insert(0, provider)
        self.save(providers)

    def check(self) -> list[dict[str, Any]]:
        """Return provider list with ``api_key_configured`` booleans.

        Each entry is::

            {"name": "...", "api_base": "...",
             "api_key_configured": true, "default_model": "..."}
        """
        result: list[dict[str, Any]] = []
        for p in self.load():
            key_set = False
            if p.api_key_env:
                key_set = os.environ.get(p.api_key_env) is not None
            result.append(
                {
                    "name": p.name,
                    "api_base": p.api_base,
                    "api_key_configured": key_set,
                    "default_model": p.default_model,
                }
            )
        return result

    # ── Internal Helpers ──────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            data = json.loads(self._path.read_text())
            if isinstance(data, dict):
                return data
            return None
        except (json.JSONDecodeError, OSError):
            return None

    def _write_json(self, data: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))
