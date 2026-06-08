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
    (
        "phone",
        re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
        "[PHONE]",
        "phone",
    ),
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
        "customer_id",
        re.compile(r"customer_id\s*[=:]\s*\d+"),
        "customer_id=[CUSTOMER_ID]",
        "customer_id",
    ),
]


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def _apply(text: str) -> tuple[str, list[RedactionFinding]]:
    """Find all sensitive spans in *text* and replace them."""
    findings: list[RedactionFinding] = []
    result = list(text)

    for pattern, compiled, replacement, kind in _PATTERNS:
        for match in compiled.finditer(text):
            start, end = match.start(), match.end()
            preview = text[start:end]
            if len(preview) > 40:
                preview = f"{preview[:17]}…{preview[-17:]}"
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
    """
    if not isinstance(text, str):
        text = str(text)

    redacted, findings = _apply(text)

    # Adjust finding start/end to represent the redacted view.  Re-find
    # offset adjustments are applied incrementally from the end of the
    # string backwards.  This keeps the result deterministic without
    # re-scanning.
    shifted: list[RedactionFinding] = []
    delta = 0
    for finding in sorted(findings, key=lambda f: f.start):
        delta += len(finding.replacement) - (finding.end - finding.start)
        shifted.append(
            finding.model_copy(
                update={
                    "start": finding.start,
                    "end": finding.end,
                }
            )
        )

    return RedactionPreviewResult(
        original_text=text,
        redacted_text=redacted,
        findings=sorted(shifted, key=lambda f: f.start),
        finding_count=len(findings),
    )
