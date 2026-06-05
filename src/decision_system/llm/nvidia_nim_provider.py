"""NVIDIA NIM hosted provider via the OpenAI-compatible API."""

from typing import Any, TypeVar

from pydantic import BaseModel

from decision_system.config import Settings
from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk
from decision_system.llm.structured_io import (
    ClaimsEnvelope,
    claim_prompt,
    parse_json_response,
    risk_prompt,
    system_prompt,
    technical_prompt,
)

T = TypeVar("T", bound=BaseModel)


class NvidiaNimProvider:
    """Hosted provider backed by NVIDIA NIM's OpenAI-compatible API."""

    def __init__(self, settings: Settings, client: Any | None = None):
        if not settings.nvidia_api_key:
            raise ValueError("NVIDIA_API_KEY is required when DECISION_PROVIDER=nvidia_nim.")
        if not settings.nvidia_nim_model:
            raise ValueError("NVIDIA_NIM_MODEL is required when DECISION_PROVIDER=nvidia_nim.")

        self.settings = settings
        self._openai: Any | None = client

    def _api(self) -> Any:
        if self._openai is None:
            from openai import OpenAI

            self._openai = OpenAI(
                api_key=self.settings.nvidia_api_key,
                base_url=self.settings.nvidia_nim_base_url,
            )
        return self._openai

    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo:
        """Create a structured technical memo from NIM output."""
        return self._complete_json(
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
        """Create a structured risk memo from NIM output."""
        return self._complete_json(
            schema_name="AgentMemo",
            schema_model=AgentMemo,
            user_prompt=risk_prompt(question, evidence, technical_memo),
        )

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        """Convert structured memos into claim-ledger records using NIM."""
        envelope = self._complete_json(
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
        raise NotImplementedError("NvidiaNimProvider report writing is handled by the local renderer.")

    def _complete_json(
        self,
        schema_name: str,
        schema_model: type[T],
        user_prompt: str,
    ) -> T:
        messages = [
            {
                "role": "system",
                "content": system_prompt(schema_name, schema_model),
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ]
        response = self._api().chat.completions.create(
            model=self.settings.nvidia_nim_model,
            messages=messages,
            temperature=self.settings.nvidia_temperature,
            top_p=self.settings.nvidia_top_p,
            max_tokens=self.settings.nvidia_max_tokens,
        )
        content = _string_content(response.choices[0].message.content)
        return parse_json_response("NVIDIA NIM", schema_name, schema_model, content)


def _string_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    return str(content)
