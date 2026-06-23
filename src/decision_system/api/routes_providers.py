"""Provider configuration API endpoints.

Supports CRUD for provider configurations, health checks, model listing,
and connection testing — all with environment-variable-based API keys.
"""

from __future__ import annotations

import os
import time

from fastapi import APIRouter, HTTPException

from decision_system.api.models import api_error
from decision_system.security.audit import append_event
from decision_system.providers import (
    ProviderConfig,
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ProviderStatusResponse,
    ProviderTestResult,
    ProviderListResponse,
    ProviderType,
    create_provider,
    get_provider,
    list_providers,
    update_provider,
    delete_provider,
    provider_exists,
    get_providers_by_type,
)


router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("", response_model=ProviderListResponse)
def list_all_providers():
    """List all configured providers."""
    providers = list_providers()
    return ProviderListResponse(providers=providers, total=len(providers))


@router.post("", response_model=ProviderConfig, status_code=201)
def create_new_provider(request: ProviderCreateRequest):
    """Create a new provider configuration."""
    try:
        config = create_provider(request)
        try:
            append_event("provider_created", f"Provider {config.name} created", metadata={
                "provider_id": config.provider_id,
                "provider_type": config.provider_type,
            })
        except Exception:
            pass
        return config
    except ValueError as e:
        if "already exists" in str(e):
            raise api_error(409, "provider_already_exists", str(e))
        raise api_error(400, "provider_create_failed", str(e))


@router.post("/default", response_model=ProviderConfig)
def set_default_provider(request: ProviderCreateRequest | None = None, provider_id: str | None = None):
    """Set a provider as the default (stored in the first provider slot)."""
    # We use a simple convention: the first provider in the list is the default
    # This endpoint ensures the provider exists and returns it
    if provider_id:
        config = get_provider(provider_id)
        if config is None:
            raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")
        return config
    if request:
        config = create_provider(request)
        return config
    raise api_error(400, "missing_provider", "Provide either provider_id or a new provider config")


@router.get("/default", response_model=ProviderConfig | None)
def get_default_provider():
    """Get the default provider (first in the list)."""
    providers = list_providers()
    if not providers:
        return None
    return providers[0]


@router.get("/{provider_id}", response_model=ProviderConfig)
def get_provider_by_id(provider_id: str):
    """Get a single provider configuration by ID."""
    config = get_provider(provider_id)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")
    return config


@router.put("/{provider_id}", response_model=ProviderConfig)
def update_provider_by_id(provider_id: str, request: ProviderUpdateRequest):
    """Update an existing provider configuration."""
    config = update_provider(provider_id, request)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")
    try:
        append_event("provider_updated", f"Provider {config.name} updated", metadata={
            "provider_id": provider_id,
        })
    except Exception:
        pass
    return config


@router.delete("/{provider_id}", status_code=204)
def delete_provider_by_id(provider_id: str):
    """Delete a provider configuration."""
    if not delete_provider(provider_id):
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")
    try:
        append_event("provider_deleted", f"Provider {provider_id} deleted", metadata={
            "provider_id": provider_id,
        })
    except Exception:
        pass
    return None


@router.get("/{provider_id}/status", response_model=ProviderStatusResponse)
def get_provider_status(provider_id: str):
    """Get the current status of a provider."""
    config = get_provider(provider_id)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")

    # Check if API key is configured
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return ProviderStatusResponse(
            provider_id=config.provider_id,
            name=config.name,
            provider_type=config.provider_type,
            status="missing_config",
            message=f"API key env var '{config.api_key_env}' is not set",
        )

    return ProviderStatusResponse(
        provider_id=config.provider_id,
        name=config.name,
        provider_type=config.provider_type,
        status=config.status,
        message="Provider is configured",
        model_count=len(config.available_models),
    )


@router.post("/{provider_id}/test", response_model=ProviderTestResult)
def test_provider_connection(provider_id: str):
    """Test the connection to a provider."""
    config = get_provider(provider_id)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")

    try:
        append_event("provider_tested", f"Provider {config.name} tested", metadata={
            "provider_id": provider_id,
        })
    except Exception:
        pass

    # For fake provider, always succeeds
    if config.provider_type == "fake":
        return ProviderTestResult(
            success=True,
            message="Fake provider is always available (no network required)",
            latency_ms=0.5,
        )

    # For other providers, check basic prerequisites
    if config.api_key_env and not os.environ.get(config.api_key_env):
        return ProviderTestResult(
            success=False,
            message=f"API key env var '{config.api_key_env}' is not set",
        )

    if not config.base_url:
        return ProviderTestResult(
            success=False,
            message="No base URL configured for this provider type",
        )

    # For local providers (Ollama, OpenAI-compatible), try a basic health check
    if config.provider_type in ("ollama", "openai_compatible"):
        try:
            import httpx
            start = time.time()
            # Simple GET to base URL
            with httpx.Client(timeout=5.0) as client:
                response = client.get(config.base_url.rstrip("/") + "/")
            latency = (time.time() - start) * 1000
            if response.status_code < 500:
                return ProviderTestResult(
                    success=True,
                    message=f"Provider responded with status {response.status_code}",
                    latency_ms=round(latency, 1),
                )
            return ProviderTestResult(
                success=False,
                message=f"Provider returned status {response.status_code}",
                latency_ms=round(latency, 1),
            )
        except Exception as e:
            return ProviderTestResult(
                success=False,
                message=f"Connection failed: {type(e).__name__}: {e}",
            )

    return ProviderTestResult(
        success=True,
        message="Provider configuration looks valid (full test requires runtime)",
    )


@router.get("/{provider_id}/models", response_model=dict)
def list_provider_models(provider_id: str):
    """List available models for a provider."""
    config = get_provider(provider_id)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{provider_id}' not found")

    return {
        "provider_id": config.provider_id,
        "provider_type": config.provider_type,
        "models": config.available_models,
        "default_model": config.default_model,
        "count": len(config.available_models),
    }


@router.get("/types/list", response_model=list[str])
def list_provider_types():
    """List all supported provider types."""
    return ["fake", "ollama", "openai_compatible", "openai", "anthropic"]



@router.post("/system/default")
def set_default_provider_system(body: dict[str, str]) -> dict[str, Any]:
    """Backward-compat alias: POST /providers/system/default -> POST /providers/default.

    Legacy endpoint used by older frontend clients and tests.
    """
    name = body.get("name", "")
    if not name:
        raise api_error(400, "missing_name", "'name' field is required")

    try:
        from decision_system.providers import get_provider_by_name
        config = get_provider_by_name(name)
    except Exception:
        config = None

    if config is None:
        # Try direct lookup by provider_id
        config = get_provider(name)

    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{name}' not found")

    return config.model_dump(mode="json")


@router.get("/by-name/{name}")
def get_provider_by_name_route(name: str) -> dict[str, Any]:
    """Look up a provider by its human-readable name."""
    from decision_system.providers import get_provider_by_name as _get_by_name
    config = _get_by_name(name)
    if config is None:
        raise api_error(404, "provider_not_found", f"Provider '{name}' not found")
    return config.model_dump(mode="json")
