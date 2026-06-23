"""Provider configuration models for local AI provider setup.

Supports fake/dev, Ollama, OpenAI-compatible local endpoints, and cloud
providers (OpenAI, Anthropic) with env-var-based API key references.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ProviderType = Literal["fake", "ollama", "openai_compatible", "openai", "anthropic"]
ProviderStatus = Literal["configured", "missing_config", "offline", "healthy", "error"]


class ProviderConfig(BaseModel):
    """Persistent configuration for a single AI provider.

    API keys are never stored directly in the config. Instead, the
    ``api_key_env`` field references an environment variable name
    (e.g. ``OPENAI_API_KEY``) that the runtime reads at call time.
    """

    provider_id: str = Field(default="", description="Unique provider identifier")
    name: str = Field(description="Human-readable provider name")
    provider_type: ProviderType = Field(description="Provider type/backend")
    base_url: str | None = Field(
        default=None,
        description="Base URL for the provider API endpoint",
    )
    api_key_env: str | None = Field(
        default=None,
        description="Environment variable name holding the API key",
    )
    api_key_configured: bool = Field(
        default=False,
        description="Whether an API key is present in the environment",
    )
    default_model: str | None = Field(
        default=None,
        description="Default model to use for this provider",
    )
    available_models: list[str] = Field(
        default_factory=list,
        description="List of known available models",
    )
    status: ProviderStatus = Field(
        default="configured",
        description="Current provider status",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata key-value pairs",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    def model_post_init(self, __context: Any) -> None:
        """Auto-generate provider_id if not set."""
        if not self.provider_id:
            self.provider_id = f"prov-{self.name.lower().replace(' ', '-')}-{int(self.created_at.timestamp())}"


class ProviderCreateRequest(BaseModel):
    """Request body for creating a new provider.

    Accepts both ``base_url`` (new) and ``api_base`` (legacy) field names.
    """

    name: str = Field(description="Human-readable provider name")
    provider_type: ProviderType = Field(description="Provider type/backend")
    base_url: str | None = Field(default=None)
    api_key_env: str | None = Field(default=None)
    default_model: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_api_base(cls, data: Any) -> Any:
        """Support legacy api_base field name."""
        if isinstance(data, dict):
            if "api_base" in data and data.get("base_url") is None:
                data["base_url"] = data.pop("api_base")
            elif "api_base" in data and "base_url" not in data:
                data["base_url"] = data.pop("api_base")
        return data


class ProviderUpdateRequest(BaseModel):
    """Request body for updating an existing provider."""

    name: str | None = Field(default=None)
    base_url: str | None = Field(default=None)
    api_key_env: str | None = Field(default=None)
    default_model: str | None = Field(default=None)
    available_models: list[str] | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)


class ProviderStatusResponse(BaseModel):
    """Response for provider health/status check."""

    provider_id: str
    name: str
    provider_type: ProviderType
    status: ProviderStatus
    message: str = ""
    model_count: int = 0


class ProviderTestResult(BaseModel):
    """Result of testing a provider connection."""

    success: bool
    message: str
    latency_ms: float | None = None
    model_count: int = 0
    models: list[str] = Field(default_factory=list)


class ProviderListResponse(BaseModel):
    """Response containing a list of configured providers."""

    providers: list[ProviderConfig]
    total: int = 0
