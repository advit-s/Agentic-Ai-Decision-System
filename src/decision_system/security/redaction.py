"""Deterministic PII redaction previewer.

Scans arbitrary text for sensitive substrings and returns the redacted
version along with structured findings.  Original text is never mutated;
callers pass a string and receive a string back.

No external services are contacted.
"""

from __future__ import annotations

import re
from typing import Literal

from decision_system.security.models import (
    RedactionFinding,
    RedactionKind,
    RedactionPreviewResult,
)

# ---------------------------------------------------------------------------
# Pattern catalog
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[RedactionKind, re.Pattern, str, str]] = [
    (
        "email",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        "[EMAIL]",
        "email",
    ),
    # secret_token before phone: longer, more-specific patterns first so that
    # phone-digit fragments inside a secret token are skipped as overlapping.
    (
        "secret_token",
        re.compile(
            r"(?:sk-[A-Za-z0-9]{8,}|nvapi-[A-Za-z0-9\-_]{8,}|"
            r"(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA)[0-9A-Z]{16})"
        ),
        "[SECRET]",
        "secret_token",
    ),
    (
        "phone",
        re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
        "[PHONE]",
        "phone",
    ),
    (
        "customer_id",
        re.compile(r"customer_id\s*[=:]\s*\d+"),
        "customer_id=[CUSTOMER_ID]",
        "customer_id",
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mask_preview(text: str) -> str:
    """Return a safe masked preview of *text* never showing the full value.

    Examples:
        "sk-EXAMPLE-short-no-match" -> "sk-EX…atch"
        "a@b.com" -> "a…m"
        "1234567890" -> "1234…7890"
    """
    if len(text) <= 8:
        # Very short matches: show first 2 + last 2 if possible, else fully mask
        if len(text) <= 4:
            return "****"
        return f"{text[:2]}…{text[-2:]}"
    # Show first ~1/3 and last ~1/3
    head_len = max(4, len(text) // 3)
    tail_len = max(4, len(text) // 3)
    return f"{text[:head_len]}…{text[-tail_len:]}"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _is_overlapping(existing: list[RedactionFinding], start: int, end: int) -> bool:
    """Return True if a new span [start, end) overlaps any existing finding."""
    for f in existing:
        if start < f.end and end > f.start:
            return True
    return False


def _apply(text: str) -> tuple[str, list[RedactionFinding]]:
    """Find all sensitive spans in *text* and replace them.

    Overlapping findings are deduplicated: when a later pattern matches
    inside an already-found span, the inner match is skipped to avoid
    noisy / confusing output (e.g. a phone number inside a secret token).
    """
    findings: list[RedactionFinding] = []
    result = list(text)

    for pattern, compiled, replacement, kind in _PATTERNS:
        for match in compiled.finditer(text):
            start, end = match.start(), match.end()
            raw_preview = text[start:end]

            # Skip overlapping matches (inner fragments)
            if _is_overlapping(findings, start, end):
                continue

            preview = _mask_preview(raw_preview)
            findings.append(
                RedactionFinding(
                    text_type=kind,
                    start=start,
                    end=end,
                    matched_preview=preview,
                    replacement=replacement,
                    confidence=_confidence_for(kind),
                )
            )

    # Sort findings by start position, descending, so that replacing later
    # ranges does not shift earlier indices.
    findings.sort(key=lambda f: f.start, reverse=True)

    for finding in findings:
        result[finding.start : finding.end] = list(finding.replacement)

    return "".join(result), findings


def _confidence_for(kind: str) -> Literal["high", "medium", "low"]:
    mapping: dict[str, Literal["high", "medium", "low"]] = {
        "email": "high",
        "secret_token": "high",
        "customer_id": "high",
        "phone": "medium",
    }
    return mapping.get(kind, "medium")


def redact(text: str) -> RedactionPreviewResult:
    """Run deterministic redaction preview on *text* and return the result.

    Input *text* is not modified in place.
    The returned ``original_text`` is intentionally never the raw input when
    findings exist — it is always the redacted version so callers (including
    the API) never receive full raw secrets in the response.
    """
    if not isinstance(text, str):
        text = str(text)

    redacted, findings = _apply(text)

    # Do NOT expose original_text when findings exist — use redacted text
    # so the API response never leaks raw secrets.
    safe_original = text if not findings else redacted

    # Adjust finding start/end to represent the redacted view.  Re-find
    # offset adjustments are applied incrementally from the end of the
    # string backwards.  This keeps the result deterministic without
    # re-scanning.
    shifted: list[RedactionFinding] = []
    delta = 0
    for finding in sorted(findings, key=lambda f: f.start):
        prev_len = finding.end - finding.start
        delta += len(finding.replacement) - prev_len
        shifted.append(
            finding.model_copy(
                update={
                    "start": finding.start,
                    "end": finding.end,
                }
            )
        )

    return RedactionPreviewResult(
        original_text=safe_original,
        redacted_text=redacted,
        findings=sorted(shifted, key=lambda f: f.start),
        finding_count=len(findings),
    )


def redact_connector_token(text: str) -> str:
    """Redact connector token values from text (logs, errors, audit).

    Replaces common token patterns with [REDACTED].
    Returns the text with tokens safely masked.
    """
    token_patterns = [
        (r'(?i)(token|secret|api_key|password|auth)\s*[=:]\s*\S+', r'\1=[REDACTED]'),
        (r'(?i)(github_token|notion_api_key|google_drive_token)\s*[=:]\s*\S+', r'\1=[REDACTED]'),
        (r'(?i)(bearer\s+)\S+', r'\1[REDACTED]'),
        (r'(?i)(Authorization:\s*Bearer\s+)\S+', r'\1[REDACTED]'),
        (r'(?:ghp_|gho_|github_pat_|nvapi-)[A-Za-z0-9_\-]{10,}', '[REDACTED_TOKEN]'),
        (r'(?:sk-[A-Za-z0-9]{10,})', '[REDACTED_TOKEN]'),
        (r'(?:xox[bpsra]-)[A-Za-z0-9\-]{10,}', '[REDACTED_TOKEN]'),
    ]

    result = text
    for pattern, replacement in token_patterns:
        result = re.sub(pattern, replacement, result)
    return result


def safe_credential_status(env_var_name: str) -> dict:
    """Return a safe credential status dict without exposing the token value.

    Returns:
        dict with keys: configured (bool), token_present (bool),
        env_var_name (str), missing_message (str)
    """
    import os
    token_value = os.environ.get(env_var_name, "")
    token_present = bool(token_value)
    return {
        "configured": token_present,
        "token_present": token_present,
        "env_var_name": env_var_name,
        "missing_message": (
            f"Set the {env_var_name} environment variable to enable authenticated access."
            if not token_present else ""
        ),
    }
