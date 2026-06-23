"""Fake/dev provider — deterministic, offline, for development and testing.

Supports list_models, chat/generate, and structured claim synthesis.
No network access required.
"""

from __future__ import annotations

from decision_system.providers.runtime import (
    BaseProvider, ChatRequest, ChatResponse,
)


FAKE_MODELS = ["fake-model-1", "fake-model-2"]
FAKE_DEFAULT_MODEL = "fake-model-1"

# Deterministic responses for known prompts
FAKE_RESPONSES: dict[str, str] = {
    "default": (
        "Based on the provided evidence, the analysis indicates that the company's current "
        "billing infrastructure may require migration planning. Key findings suggest that "
        "there are potential risks in the current approach, and further investigation is recommended."
    ),
    "summary": (
        "## Summary\n\nThe workspace evidence covers billing infrastructure, customer "
        "migration patterns, and system dependencies. Key findings include:\n\n"
        "- Billing migration requires rollback planning\n"
        "- LegacyAuth is owned by the Platform Team\n"
        "- Multiple data sources show consistent patterns\n\n"
        "**Confidence:** Medium — evidence quality is moderate."
    ),
    "claims": (
        '[\n'
        '  {\n'
        '    "claim_text": "Billing migration requires rollback planning",\n'
        '    "claim_type": "risk",\n'
        '    "confidence": 0.85,\n'
        '    "evidence_ids": ["ev-1"]\n'
        '  },\n'
        '  {\n'
        '    "claim_text": "LegacyAuth is owned by the Platform Team",\n'
        '    "claim_type": "fact",\n'
        '    "confidence": 0.95,\n'
        '    "evidence_ids": ["ev-2"]\n'
        '  },\n'
        '  {\n'
        '    "claim_text": "Revenue growth is projected at 15% for next quarter",\n'
        '    "claim_type": "forecast",\n'
        '    "confidence": 0.60,\n'
        '    "evidence_ids": ["ev-3"]\n'
        '  }\n'
        ']'
    ),
}


class FakeProvider(BaseProvider):
    """Deterministic fake provider for development/testing. No network needed."""

    def list_models(self) -> list[str]:
        return list(FAKE_MODELS)

    def health_check(self) -> bool:
        return True

    def chat(self, request: ChatRequest) -> ChatResponse:
        # Determine response based on prompt content
        combined = " ".join(m.content for m in request.messages).lower()
        text = FAKE_RESPONSES.get("default")

        if "summary" in combined or "summarize" in combined:
            text = FAKE_RESPONSES["summary"]
        elif "claim" in combined or "extract" in combined:
            text = FAKE_RESPONSES["claims"]

        return ChatResponse(
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            model=request.model or FAKE_DEFAULT_MODEL,
            text=text,
            usage={"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            warnings=[],
        )
