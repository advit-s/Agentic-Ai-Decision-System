"""Local file-based provider configuration store.

Provider configs are persisted as individual JSON files under
``.decision_system/providers/``. Files named ``<provider_id>.json``.

No plaintext API keys are stored — the ``api_key_env`` field references
an environment variable name instead.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from decision_system.providers.models import (
    ProviderConfig,
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ProviderType,
)


def _get_store_dir() -> Path:
    """Return the provider store directory, creating it if needed."""
    base = Path(os.environ.get("DECISION_SYSTEM_DATA_DIR", ".decision_system"))
    store_dir = base / "providers"
    store_dir.mkdir(parents=True, exist_ok=True)
    return store_dir


def _provider_path(provider_id: str) -> Path:
    return _get_store_dir() / f"{provider_id}.json"


def _load_provider(path: Path) -> ProviderConfig | None:
    """Load a single provider from a JSON file."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProviderConfig.model_validate(data)
    except (json.JSONDecodeError, ValueError):
        return None


def _save_provider(config: ProviderConfig) -> None:
    """Persist a single provider config to a JSON file."""
    path = _provider_path(config.provider_id)
    path.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _check_api_key(config: ProviderConfig) -> bool:
    """Check whether the referenced API key env var is set."""
    if not config.api_key_env:
        return True  # No API key required (e.g., Ollama, fake)
    return bool(os.environ.get(config.api_key_env))


# ── Public API ────────────────────────────────────────────────────────


def list_providers() -> List[ProviderConfig]:
    """Return all configured providers."""
    store_dir = _get_store_dir()
    if not store_dir.exists():
        return []
    providers: list[ProviderConfig] = []
    for path in sorted(store_dir.iterdir()):
        if path.suffix == ".json":
            config = _load_provider(path)
            if config:
                config.api_key_configured = _check_api_key(config)
                providers.append(config)
    return providers


def get_provider(provider_id: str) -> ProviderConfig | None:
    """Get a single provider by ID."""
    path = _provider_path(provider_id)
    config = _load_provider(path)
    if config:
        config.api_key_configured = _check_api_key(config)
    return config


def get_provider_by_name(name: str) -> ProviderConfig | None:
    """Find a provider by its human-readable name."""
    for p in list_providers():
        if p.name == name:
            return p
    return None


def get_providers_by_type(provider_type: ProviderType) -> List[ProviderConfig]:
    """Return all providers of a given type."""
    return [p for p in list_providers() if p.provider_type == provider_type]


def create_provider(request: ProviderCreateRequest) -> ProviderConfig:
    """Create and persist a new provider config."""
    now = datetime.now(timezone.utc)
    config = ProviderConfig(
        name=request.name,
        provider_type=request.provider_type,
        base_url=request.base_url,
        api_key_env=request.api_key_env,
        default_model=request.default_model,
        metadata=request.metadata,
        created_at=now,
        updated_at=now,
        api_key_configured=_check_api_key(
            ProviderConfig(
                name=request.name,
                provider_type=request.provider_type,
                api_key_env=request.api_key_env,
            )
        ),
    )
    config.provider_id = f"prov-{request.name.lower().replace(' ', '-')}"
    # Enforce unique provider names
    existing = get_provider_by_name(request.name)
    if existing:
        raise ValueError(f"Provider with name '{request.name}' already exists")
    _save_provider(config)
    return config


def update_provider(
    provider_id: str,
    request: ProviderUpdateRequest,
) -> ProviderConfig | None:
    """Update an existing provider's config fields."""
    config = get_provider(provider_id)
    if config is None:
        return None

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(config, field, value)

    config.updated_at = datetime.now(timezone.utc)
    config.api_key_configured = _check_api_key(config)
    _save_provider(config)
    return config


def delete_provider(provider_id: str) -> bool:
    """Delete a provider by ID. Returns True if deleted, False if not found."""
    path = _provider_path(provider_id)
    if not path.exists():
        return False
    path.unlink()
    return True


def provider_exists(provider_id: str) -> bool:
    """Check if a provider exists."""
    return _provider_path(provider_id).exists()
