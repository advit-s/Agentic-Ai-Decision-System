"""AI-assisted evidence synthesis service.

Takes workspace evidence and a question/objective, uses a configured
provider to synthesize, and returns structured output with draft claims.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from decision_system.providers import (
    ChatMessage,
    ChatRequest,
    ProviderConfig,
    ProviderRuntime,
)
from decision_system.security.audit import append_event
from decision_system.synthesis.parser import (
    DraftClaim,
    parse_synthesis_output,
)
from decision_system.synthesis.prompts import (
    SynthesisMode,
    _format_evidence,
    get_template,
)

SYNTHESIS_MODES: list[SynthesisMode] = [
    "summary",
    "risks",
    "opportunities",
    "claims",
    "report_outline",
]


class SynthesisResult:
    """Result of an evidence synthesis operation."""

    def __init__(
        self,
        synthesis_id: str,
        workspace_id: str,
        provider_id: str,
        model: str,
        summary_text: str,
        draft_claims: list[DraftClaim],
        used_evidence_ids: list[str],
        warnings: list[str],
        parse_warnings: list[str],
        created_at: datetime | None = None,
    ) -> None:
        self.synthesis_id = synthesis_id
        self.workspace_id = workspace_id
        self.provider_id = provider_id
        self.model = model
        self.summary_text = summary_text
        self.draft_claims = draft_claims
        self.used_evidence_ids = used_evidence_ids
        self.warnings = warnings
        self.parse_warnings = parse_warnings
        self.created_at = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "synthesis_id": self.synthesis_id,
            "workspace_id": self.workspace_id,
            "provider_id": self.provider_id,
            "model": self.model,
            "summary_text": self.summary_text,
            "draft_claims": [c.model_dump() for c in self.draft_claims],
            "used_evidence_ids": self.used_evidence_ids,
            "warnings": self.warnings,
            "parse_warnings": self.parse_warnings,
            "created_at": self.created_at.isoformat(),
        }


def run_synthesis(
    workspace_id: str,
    question: str,
    evidence_results: list[dict] | None = None,
    provider_id: str | None = None,
    model: str | None = None,
    synthesis_mode: SynthesisMode = "summary",
    provider_config: ProviderConfig | None = None,
) -> SynthesisResult:
    """Run AI-assisted evidence synthesis.

    Args:
        workspace_id: The workspace to synthesize evidence for.
        question: The question or objective for synthesis.
        evidence_results: Optional list of evidence items. If None,
            synthesis will note that no evidence was provided.
        provider_id: Optional provider ID to use. If None, uses default provider.
        model: Optional model name. If None, uses provider's default model.
        synthesis_mode: The synthesis mode (summary, risks, etc.).
        provider_config: Optional pre-loaded provider config.

    Returns:
        SynthesisResult with summary text, draft claims, and metadata.
    """
    synthesis_id = f"syn-{uuid4().hex[:12]}"
    used_evidence_ids = _extract_evidence_ids(evidence_results or [])

    # Get provider
    runtime = ProviderRuntime()
    provider = None
    provider_warnings: list[str] = []

    if provider_config:
        provider = runtime.get_provider_by_config(provider_config)
    elif provider_id:
        provider = runtime.get_provider(provider_id)
        if provider is None:
            provider_warnings.append(f"Provider '{provider_id}' not found")

    if provider is None:
        try:
            append_event(
                "synthesis_created",
                f"Synthesis {synthesis_id} — no provider",
                metadata={
                    "synthesis_id": synthesis_id,
                    "workspace_id": workspace_id,
                    "mode": synthesis_mode,
                },
            )
        except Exception:
            pass
        # No provider available — return empty result with warning
        return SynthesisResult(
            synthesis_id=synthesis_id,
            workspace_id=workspace_id,
            provider_id=provider_id or "",
            model=model or "",
            summary_text="",
            draft_claims=[],
            used_evidence_ids=used_evidence_ids,
            warnings=provider_warnings or ["No provider configured — AI synthesis unavailable"],
            parse_warnings=[],
        )

    # Build prompt
    template = get_template(synthesis_mode)
    evidence_text = _format_evidence(evidence_results or [])
    user_prompt = template["user"].format(
        evidence=evidence_text,
        question=question,
    )

    # Call provider
    resolved_model = model or provider.config.default_model or "default"
    request = ChatRequest(
        model=resolved_model,
        messages=[
            ChatMessage(role="system", content=template["system"]),
            ChatMessage(role="user", content=user_prompt),
        ],
        temperature=0.0,
        metadata={"synthesis_mode": synthesis_mode},
    )

    from decision_system.providers.runtime import execute_with_timing

    response = execute_with_timing(provider, request)

    # Parse output
    parsed = parse_synthesis_output(response.text)

    try:
        append_event(
            "synthesis_claims_created",
            f"Synthesis {synthesis_id} — {len(parsed.draft_claims)} claims",
            metadata={
                "synthesis_id": synthesis_id,
                "workspace_id": workspace_id,
                "provider_id": provider.provider_id,
                "draft_claim_count": len(parsed.draft_claims),
                "mode": synthesis_mode,
            },
        )
    except Exception:
        pass

    # If mode was "claims" but parsing returned no claims, warn
    if synthesis_mode == "claims" and not parsed.draft_claims:
        parsed.warnings.append("Provider did not return structured claims in 'claims' mode")

    return SynthesisResult(
        synthesis_id=synthesis_id,
        workspace_id=workspace_id,
        provider_id=provider.provider_id,
        model=resolved_model,
        summary_text=parsed.summary_text,
        draft_claims=parsed.draft_claims,
        used_evidence_ids=used_evidence_ids,
        warnings=[w for w in (response.warnings or []) if w],
        parse_warnings=parsed.warnings,
    )


def _extract_evidence_ids(evidence_results: list[dict]) -> list[str]:
    """Extract evidence/chunk IDs from results."""
    ids: list[str] = []
    for ev in evidence_results:
        eid = ev.get("id") or ev.get("chunk_id") or ev.get("evidence_id")
        if eid:
            ids.append(str(eid))
    return ids
