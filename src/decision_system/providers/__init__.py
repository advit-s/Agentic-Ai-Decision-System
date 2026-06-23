"""Provider configuration and runtime management.

Supports local (Ollama, OpenAI-compatible, fake/dev) and cloud
(OpenAI, Anthropic) AI providers with a unified interface.
"""

from decision_system.providers.models import (
    ProviderConfig,
    ProviderCreateRequest,
    ProviderUpdateRequest,
    ProviderStatusResponse,
    ProviderTestResult,
    ProviderListResponse,
    ProviderType,
    ProviderStatus,
)

from decision_system.providers.store import (
    list_providers,
    get_provider,
    get_provider_by_name,
    get_providers_by_type,
    create_provider,
    update_provider,
    delete_provider,
    provider_exists,
)

from decision_system.providers.runtime import (
    BaseProvider,
    ProviderRuntime,
    ChatRequest,
    ChatMessage,
    ChatResponse,
    execute_with_timing,
)

from decision_system.providers.fake import (
    FakeProvider,
    FAKE_MODELS,
)

__all__ = [
    "ProviderConfig",
    "ProviderCreateRequest",
    "ProviderUpdateRequest",
    "ProviderStatusResponse",
    "ProviderTestResult",
    "ProviderListResponse",
    "ProviderType",
    "ProviderStatus",
    "list_providers",
    "get_provider",
    "get_provider_by_name",
    "get_providers_by_type",
    "create_provider",
    "update_provider",
    "delete_provider",
    "provider_exists",
    "BaseProvider",
    "ProviderRuntime",
    "ChatRequest",
    "ChatMessage",
    "ChatResponse",
    "execute_with_timing",
    "FakeProvider",
    "FAKE_MODELS",
]
