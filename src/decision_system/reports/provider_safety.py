"""Provider safety status — checks current provider mode and warns if external.

The default provider is ``fake`` (offline).  When a real external provider
(NVIDIA NIM or Ollama) is configured, the safety status clearly warns that
data may be sent to an external service.

No network calls are made — all checks are local config inspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from decision_system.config import load_settings


@dataclass
class ProviderSafetyStatus:
    """Provider safety status for the current configuration."""

    configured_provider: str
    is_external: bool
    is_online: bool
    safety_level: str  # "safe" | "warning" | "external"
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "configured_provider": self.configured_provider,
            "is_external": self.is_external,
            "is_online": self.is_online,
            "safety_level": self.safety_level,
            "message": self.message,
            "details": self.details,
        }


def get_provider_safety_status() -> ProviderSafetyStatus:
    """Check the current provider configuration and return a safety status.

    The check reads from ``Settings`` (which loads from environment variables
    and ``.env``).  No external services are contacted.
    """
    settings = load_settings()
    provider = settings.provider.strip().lower()

    if provider == "fake":
        return ProviderSafetyStatus(
            configured_provider="fake",
            is_external=False,
            is_online=False,
            safety_level="safe",
            message="Fake/offline provider is active. No external services are contacted.",
            details={
                "default": True,
                "requires_api_key": False,
            },
        )

    if provider == "ollama":
        ollama_configured = bool(settings.ollama_model)
        return ProviderSafetyStatus(
            configured_provider="ollama",
            is_external=False,
            is_online=ollama_configured,
            safety_level="warning" if not ollama_configured else "external",
            message=(
                "Ollama is configured as a local provider. "
                "Data stays on your machine but uses a local LLM. "
                + (
                    "Ollama model is configured and ready."
                    if ollama_configured
                    else "Ollama model is NOT configured (missing OLLAMA_MODEL)."
                )
            ),
            details={
                "base_url": settings.ollama_base_url,
                "model_configured": ollama_configured,
                "model": settings.ollama_model or "(not set)",
            },
        )

    if provider == "nvidia_nim":
        nim_configured = bool(settings.nvidia_api_key) and bool(settings.nvidia_nim_model)
        return ProviderSafetyStatus(
            configured_provider="nvidia_nim",
            is_external=True,
            is_online=nim_configured,
            safety_level="warning" if not nim_configured else "external",
            message=(
                "NVIDIA NIM is configured as an external provider. "
                "Data may be sent to NVIDIA's hosted API."
                if nim_configured
                else "NVIDIA NIM is selected but NOT fully configured (missing API key or model). "
                "The fake provider will be used as fallback."
            ),
            details={
                "base_url": settings.nvidia_nim_base_url,
                "configured": nim_configured,
                "model": settings.nvidia_nim_model or "(not set)",
            },
        )

    # Unknown provider — treat as external with warning
    return ProviderSafetyStatus(
        configured_provider=provider,
        is_external=True,
        is_online=False,
        safety_level="warning",
        message=f"Unknown provider '{provider}'. Defaulting to fake/offline behavior.",
        details={},
    )


def safety_to_text(status: ProviderSafetyStatus) -> str:
    """Render a ProviderSafetyStatus as human-readable text."""
    level_icon = {
        "safe": "✓",
        "warning": "⚠",
        "external": "⟐",
    }.get(status.safety_level, "?")

    lines = [
        "# Provider Safety Status",
        "",
        f"{level_icon} Provider: {status.configured_provider}",
        f"  Safety level: {status.safety_level}",
        f"  External: {'Yes' if status.is_external else 'No'}",
        f"  Online: {'Yes' if status.is_online else 'No'}",
        "",
        status.message,
    ]

    if status.details:
        lines.append("")
        lines.append("Details:")
        for key, value in status.details.items():
            lines.append(f"  - {key}: {value}")

    return "\n".join(lines)
