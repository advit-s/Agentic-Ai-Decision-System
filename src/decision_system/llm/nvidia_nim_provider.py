"""NVIDIA NIM hosted provider via the OpenAI-compatible API."""

import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from decision_system.config import Settings
from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk


T = TypeVar("T", bound=BaseModel)


class ClaimsEnvelope(BaseModel):
    """Structured claim extraction payload returned by NVIDIA NIM."""

    claims: list[Claim]


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
            user_prompt=_technical_prompt(question, evidence),
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
            user_prompt=_risk_prompt(question, evidence, technical_memo),
        )

    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]:
        """Convert structured memos into claim-ledger records using NIM."""
        envelope = self._complete_json(
            schema_name="ClaimsEnvelope",
            schema_model=ClaimsEnvelope,
            user_prompt=_claim_prompt(run_id, memos),
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
                "content": _system_prompt(schema_name, schema_model),
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
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"NVIDIA NIM returned malformed JSON for {schema_name}.") from exc

        try:
            return schema_model.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"NVIDIA NIM returned invalid {schema_name} JSON.") from exc


def _system_prompt(schema_name: str, schema_model: type[BaseModel]) -> str:
    return "\n".join(
        [
            "You are a bounded decision-system model.",
            "Return only valid JSON. Do not include Markdown, prose, or code fences.",
            "Use only the evidence IDs provided by the user.",
            f"The JSON must validate as {schema_name}.",
            "Schema:",
            json.dumps(schema_model.model_json_schema(), indent=2),
        ]
    )


def _technical_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    return json.dumps(
        {
            "task": "Write a technical analyst memo as JSON.",
            "agent_name": "technical_analyst",
            "question": question,
            "evidence": [chunk.model_dump(mode="json") for chunk in evidence],
        },
        indent=2,
    )


def _risk_prompt(
    question: str,
    evidence: list[EvidenceChunk],
    technical_memo: AgentMemo,
) -> str:
    return json.dumps(
        {
            "task": "Write a risk analyst memo as JSON.",
            "agent_name": "risk_analyst",
            "question": question,
            "technical_memo": technical_memo.model_dump(mode="json"),
            "evidence": [chunk.model_dump(mode="json") for chunk in evidence],
        },
        indent=2,
    )


def _claim_prompt(run_id: str, memos: list[AgentMemo]) -> str:
    return json.dumps(
        {
            "task": "Extract material claims as JSON.",
            "run_id": run_id,
            "instructions": [
                "Return an object with a claims array.",
                "Each claim must use the provided run_id.",
                "Use pending status because verification happens later.",
                "Use evidence_ids from cited_evidence_ids only.",
            ],
            "memos": [memo.model_dump(mode="json") for memo in memos],
        },
        indent=2,
    )


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
