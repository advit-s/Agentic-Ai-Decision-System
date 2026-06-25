"""Shared structured-output helpers for optional LLM providers."""

from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from decision_system.models import AgentMemo, Claim, EvidenceChunk

T = TypeVar("T", bound=BaseModel)


class ClaimsEnvelope(BaseModel):
    """Structured claim extraction payload returned by model providers."""

    claims: list[Claim]


def system_prompt(schema_name: str, schema_model: type[BaseModel]) -> str:
    """Build the shared strict JSON system prompt."""
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


def technical_prompt(question: str, evidence: list[EvidenceChunk]) -> str:
    """Build the shared technical memo prompt payload."""
    return json.dumps(
        {
            "task": "Write a technical analyst memo as JSON.",
            "agent_name": "technical_analyst",
            "question": question,
            "evidence": [chunk.model_dump(mode="json") for chunk in evidence],
        },
        indent=2,
    )


def risk_prompt(
    question: str,
    evidence: list[EvidenceChunk],
    technical_memo: AgentMemo,
) -> str:
    """Build the shared risk memo prompt payload."""
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


def claim_prompt(run_id: str, memos: list[AgentMemo]) -> str:
    """Build the shared claim extraction prompt payload."""
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


def parse_json_response(
    provider_label: str,
    schema_name: str,
    schema_model: type[T],
    response_text: str,
) -> T:
    """Parse provider JSON and validate it into the requested Pydantic model."""
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{provider_label} returned malformed JSON for {schema_name}.") from exc

    try:
        return schema_model.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError(f"{provider_label} returned invalid {schema_name} JSON.") from exc
