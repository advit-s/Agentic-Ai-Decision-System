"""Provider runtime abstraction — unified interface for all provider types.

Every provider (fake, Ollama, OpenAI-compatible, etc.) implements this
interface, allowing the synthesis service and workflow nodes to call any
provider uniformly.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

from decision_system.providers.models import ProviderConfig, ProviderType

# ── Data types ────────────────────────────────────────────────────────


@dataclass
class ChatMessage:
    """A single message in a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class ChatRequest:
    """Input to a provider chat/generate call."""

    model: str
    messages: list[ChatMessage]
    temperature: float = 0.0
    max_tokens: int | None = None
    response_format: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChatResponse:
    """Output from a provider chat/generate call."""

    provider_id: str
    provider_type: ProviderType
    model: str
    text: str
    usage: dict[str, int] | None = None
    latency_ms: float = 0.0
    raw: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)


# ── Abstract base ─────────────────────────────────────────────────────


class BaseProvider(ABC):
    """Abstract base for all AI providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    def provider_id(self) -> str:
        return self.config.provider_id

    @property
    def provider_type(self) -> ProviderType:
        return self.config.provider_type

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return list of available model names."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and functional."""
        ...

    @abstractmethod
    def chat(self, request: ChatRequest) -> ChatResponse:
        """Send a chat request and return the response."""
        ...

    def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> ChatResponse:
        """Convenience method for single-prompt generation."""
        return self.chat(
            ChatRequest(
                model=model,
                messages=[ChatMessage(role="user", content=prompt)],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
            )
        )


# ── Provider runtime ──────────────────────────────────────────────────


class ProviderRuntime:
    """Runtime that selects and invokes the right provider implementation.

    Usage::

        runtime = ProviderRuntime.get_instance()
        provider = runtime.get_provider("prov-ollama-1")
        response = provider.chat(chat_request)
    """

    _instances: dict[str, BaseProvider] = {}

    @classmethod
    def get_instance(cls) -> ProviderRuntime:
        return cls()

    def get_provider(self, provider_id: str) -> BaseProvider | None:
        """Get a provider instance by ID, caching it for reuse."""
        if provider_id in self._instances:
            return self._instances[provider_id]

        from decision_system.providers.store import get_provider as get_config

        config = get_config(provider_id)
        if config is None:
            return None

        provider = self._build_provider(config)
        self._instances[provider_id] = provider
        return provider

    def get_provider_by_config(self, config: ProviderConfig) -> BaseProvider:
        """Get or create a provider instance from a config object."""
        if config.provider_id in self._instances:
            return self._instances[config.provider_id]

        provider = self._build_provider(config)
        self._instances[config.provider_id] = provider
        return provider

    def _build_provider(self, config: ProviderConfig) -> BaseProvider:
        """Factory method to create the right provider implementation."""
        if config.provider_type == "fake":
            from decision_system.providers.fake import FakeProvider

            return FakeProvider(config)
        elif config.provider_type == "ollama":
            from decision_system.providers.ollama import OllamaProvider

            return OllamaProvider(config)
        elif config.provider_type == "openai_compatible":
            from decision_system.providers.openai_compat import OpenAICompatibleProvider

            return OpenAICompatibleProvider(config)
        elif config.provider_type == "openai":
            from decision_system.providers.openai_compat import OpenAICompatibleProvider

            return OpenAICompatibleProvider(config)
        elif config.provider_type == "anthropic":
            from decision_system.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider(config)
        else:
            raise ValueError(f"Unknown provider type: {config.provider_type}")

    def clear_cache(self) -> None:
        """Clear all cached provider instances."""
        self._instances.clear()


def execute_with_timing(provider: BaseProvider, request: ChatRequest) -> ChatResponse:
    """Execute a chat request with timing and basic error handling."""
    from decision_system.observability.metrics import MetricsCollector, MetricType
    from decision_system.security.audit import append_event

    try:
        append_event(
            "provider_call_started",
            f"Provider call to {provider.provider_id}",
            metadata={
                "provider_id": provider.provider_id,
                "provider_type": provider.provider_type,
                "model": request.model,
            },
        )
    except Exception:
        pass

    start = time.time()
    try:
        response = provider.chat(request)
        response.latency_ms = round((time.time() - start) * 1000, 1)

        try:
            collector = MetricsCollector()
            collector.record(
                "provider_latency_ms",
                response.latency_ms,
                MetricType.TIMER,
                {
                    "provider_id": provider.provider_id,
                    "provider_type": provider.provider_type,
                    "model": request.model,
                },
            )
            collector.record(
                "provider_calls_count",
                1,
                MetricType.COUNTER,
                {
                    "provider_id": provider.provider_id,
                },
            )
        except Exception:
            pass

        try:
            append_event(
                "provider_call_completed",
                f"Provider call to {provider.provider_id} completed",
                metadata={
                    "provider_id": provider.provider_id,
                    "latency_ms": response.latency_ms,
                    "model": request.model,
                },
            )
        except Exception:
            pass

        return response
    except Exception as e:
        elapsed = round((time.time() - start) * 1000, 1)

        try:
            collector = MetricsCollector()
            collector.record(
                "provider_error_count",
                1,
                MetricType.COUNTER,
                {
                    "provider_id": provider.provider_id,
                    "error_type": type(e).__name__,
                },
            )
        except Exception:
            pass

        try:
            append_event(
                "provider_call_failed",
                f"Provider call to {provider.provider_id} failed",
                metadata={
                    "provider_id": provider.provider_id,
                    "error": type(e).__name__,
                    "latency_ms": elapsed,
                },
            )
        except Exception:
            pass

        return ChatResponse(
            provider_id=provider.provider_id,
            provider_type=provider.provider_type,
            model=request.model,
            text="",
            latency_ms=elapsed,
            warnings=[f"Provider error: {type(e).__name__}: {e}"],
        )
