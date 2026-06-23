"""Structured output parser for AI synthesis results.

Handles valid JSON, JSON inside markdown fences, plain text fallback,
missing fields, and invalid claim objects — without crashing or creating
trusted claims from unparseable output.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field


class DraftClaim(BaseModel):
    """A single claim extracted from AI synthesis output."""

    claim_text: str = ""
    claim_type: str = "unknown"
    confidence: float = 0.0
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParsedSynthesis(BaseModel):
    """Result of parsing AI synthesis output."""

    success: bool = False
    summary_text: str = ""
    draft_claims: list[DraftClaim] = Field(default_factory=list)
    raw_text: str = ""
    warnings: list[str] = Field(default_factory=list)
    parse_mode: str = "plain_text"


def parse_synthesis_output(raw_text: str) -> ParsedSynthesis:
    """Parse AI synthesis output into a structured result.

    Attempts, in order:
    1. Parse as valid JSON (top-level array or object)
    2. Extract JSON from markdown code fences
    3. Return as plain text with a warning

    Never crashes. Never creates trusted claims from unparseable output.
    """
    result = ParsedSynthesis(raw_text=raw_text)

    if not raw_text or not raw_text.strip():
        result.warnings.append("Empty response from provider")
        return result

    # Try 1: Direct JSON parse
    parsed = _try_parse_json(raw_text)
    if parsed is not None:
        return _process_parsed_json(result, parsed, "json")

    # Try 2: JSON inside markdown fences
    fenced = _extract_json_from_fence(raw_text)
    if fenced is not None:
        return _process_parsed_json(result, fenced, "markdown_fence")

    # Try 3: JSON inside code fences (no language specified)
    code_fenced = _extract_code_fence(raw_text)
    if code_fenced is not None:
        return _process_parsed_json(result, code_fenced, "code_fence")

    # Fallback: plain text
    result.summary_text = raw_text.strip()
    result.warnings.append("Output is not structured JSON — treated as plain text")
    return result


def _try_parse_json(text: str) -> Any | None:
    """Try to parse text as JSON."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _extract_json_from_fence(text: str) -> Any | None:
    """Extract JSON from ```json ... ``` fences."""
    match = re.search(
        r"```(?:json)\s*\n?(.*?)\n?```",
        text,
        re.DOTALL,
    )
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _extract_code_fence(text: str) -> Any | None:
    """Extract JSON from ``` ... ``` fences (no language specified)."""
    match = re.search(
        r"```\s*\n?(.*?)\n?```",
        text,
        re.DOTALL,
    )
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


def _process_parsed_json(
    result: ParsedSynthesis,
    parsed: Any,
    mode: str,
) -> ParsedSynthesis:
    """Process successfully parsed JSON into a ParsedSynthesis."""
    result.parse_mode = mode
    result.success = True

    if isinstance(parsed, list):
        # Array of claim objects
        for item in parsed:
            if isinstance(item, dict):
                try:
                    claim = DraftClaim.model_validate(item)
                    result.draft_claims.append(claim)
                except Exception:
                    result.warnings.append(f"Skipped invalid claim object: {item}")
        if not result.draft_claims:
            result.summary_text = str(parsed)
            result.warnings.append("JSON array did not contain valid claim objects")
    elif isinstance(parsed, dict):
        # Object — may contain summary, claims, or both
        if "claims" in parsed and isinstance(parsed["claims"], list):
            for item in parsed["claims"]:
                if isinstance(item, dict):
                    try:
                        claim = DraftClaim.model_validate(item)
                        result.draft_claims.append(claim)
                    except Exception:
                        result.warnings.append(f"Skipped invalid claim: {item}")

        if "summary" in parsed and isinstance(parsed["summary"], str):
            result.summary_text = parsed["summary"]
        elif "summary_text" in parsed and isinstance(parsed["summary_text"], str):
            result.summary_text = parsed["summary_text"]
        elif "text" in parsed and isinstance(parsed["text"], str):
            result.summary_text = parsed["text"]
        else:
            # Use the whole object as text representation
            result.summary_text = json.dumps(parsed, indent=2)
    else:
        result.summary_text = str(parsed)
        result.warnings.append(f"Unexpected JSON type: {type(parsed).__name__}")

    return result
