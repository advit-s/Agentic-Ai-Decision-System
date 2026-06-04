"""Provider factory for selecting offline or hosted LLM providers."""

from decision_system.config import Settings, load_settings
from decision_system.llm.fake_provider import FakeProvider
from decision_system.llm.provider import LLMProvider


def get_provider(
    provider_name: str | None = None,
    settings: Settings | None = None,
) -> LLMProvider:
    """Return the configured LLM provider.

    `fake` remains the default so tests and local runs stay offline unless the
    user explicitly selects a hosted provider.
    """

    resolved_settings = settings or load_settings()
    name = provider_name or resolved_settings.provider

    if name == "fake":
        return FakeProvider()
    if name == "nvidia_nim":
        from decision_system.llm.nvidia_nim_provider import NvidiaNimProvider

        return NvidiaNimProvider(resolved_settings)

    raise ValueError(
        f"Unknown DECISION_PROVIDER '{name}'. Expected one of: fake, nvidia_nim."
    )
