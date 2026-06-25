"""Ollama provider for local model testing.

Uses Ollama's local HTTP API (POST /api/chat) with stdlib urllib to avoid
adding new dependencies. The provider validates strict JSON into Pydantic
models and raises clear errors for connection and parsing failures.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, TypeVar

from pydantic import BaseModel

from decision_system.config import Settings
from decision_system.llm.structured_io import (
    ClaimsEnvelope,
    claim_prompt,
    parse_json_response,
    risk_prompt,
    system_prompt,
    technical_prompt,
)
from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk

T = TypeVar("T", bound=BaseModel)


class OllamaProvider:
    """Local provider backed by Ollama's /api/chat endpoint."""

    def __init__(self, settings: Settings, client: Any | None = None):
        if not settings.ollama_model:
            raise ValueError(
                "OLLAMA_MODEL is required when DECISION_PROVIDER=ollama. "
                "Start Ollama and pull a model first, e.g.: "
                "ollama pull llama3.1:8b"
            )
        if not settings.ollama_base_url:
            raise ValueError("OLLAMA_BASE_URL is required when DECISION_PROVIDER=ollama.")
        if not settings.ollama_base_url.startswith(("http://", "https://")):
            raise ValueError("OLLAMA_BASE_URL must start with http:// or https://.")
        self.settings = settings
        self._client = client  # optional injected client for testing

    def _base_url(self) -> str:
        return self.settings.ollama_base_url.rstrip("/")

    def _chat(
        self,
        schema_name: str,
        schema_model: type[T],
        user_prompt: str,
    ) -> T:
        base = self._base_url()
        url = f"{base}/api/chat"
        structured_system_prompt = system_prompt(schema_name, schema_model)

        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": structured_system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": self.settings.ollama_temperature,
                "num_predict": self.settings.ollama_max_tokens,
            },
            "format": schema_model.model_json_schema(),
        }

        if self._client is not None:
            response_text = self._client.chat(payload)
            return _parse_response(schema_name, schema_model, response_text)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            timeout = self.settings.ollama_timeout_seconds
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                try:
                    body = json.loads(resp.read().decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise ValueError(
                        f"Ollama returned malformed HTTP response JSON for {schema_name}."
                    ) from exc
                response_text = body.get("message", {}).get("content", "")
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach Ollama at {base}. Start Ollama locally: ollama serve"
            ) from exc

        return _parse_response(schema_name, schema_model, response_text)

    # ------------------------------------------------------------------
    # Provider interface
    # ------------------------------------------------------------------

    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo:
        """Create a structured technical memo from Ollama output."""
        return self._chat(
            schema_name="AgentMemo",
            schema_model=AgentMemo,
            user_prompt=technical_prompt(question, evidence),
        )

    def risk_memo(
        self,
        question: str,
        evidence: list[EvidenceChunk],
        technical_memo: AgentMemo,
    ) -> AgentMemo:
        """Create a structured risk memo from Ollama output."""
        return self._chat(
            schema_name="AgentMemo",
            schema_model=AgentMemo,
            user_prompt=risk_prompt(question, evidence, technical_memo),
        )

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        """Convert structured memos into claim-ledger records using Ollama."""
        envelope = self._chat(
            schema_name="ClaimsEnvelope",
            schema_model=ClaimsEnvelope,
            user_prompt=claim_prompt(run_id, memos),
        )
        return envelope.claims

    def write_report(
        self,
        question: str,
        claims: list[Claim],
        evidence: list[EvidenceChunk],
    ) -> DecisionReport:
        """Provider-side reports are not used; local renderer owns reports."""
        raise NotImplementedError("OllamaProvider report writing is handled by the local renderer.")


def _parse_response(
    schema_name: str,
    schema_model: type[T],
    response_text: str,
) -> T:
    """Parse and validate a JSON response from Ollama."""
    return parse_json_response("Ollama", schema_name, schema_model, response_text)
