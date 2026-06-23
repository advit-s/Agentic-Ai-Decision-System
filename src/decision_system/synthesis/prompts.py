"""Local prompt templates for grounded AI-assisted evidence synthesis.

Each template includes anti-hallucination instructions and requires
structured output with evidence references. Templates are versioned
to allow iteration without breaking existing workflows.
"""

from __future__ import annotations

from typing import Literal

SynthesisMode = Literal["summary", "risks", "opportunities", "claims", "report_outline"]

TEMPLATE_VERSION = "1.0.0"

# ── System instruction (prepended to all prompts) ─────────────────────

_SYSTEM_INSTRUCTION = (
    "You are an evidence-based analysis assistant. Your role is to synthesize "
    "workspace evidence into structured, actionable insights.\n\n"
    "RULES:\n"
    "1. Use ONLY the provided evidence. Do not invent sources or facts.\n"
    "2. If evidence is insufficient for a confident answer, say so clearly.\n"
    "3. Every claim must include evidence references.\n"
    "4. Separate facts from recommendations.\n"
    "5. Return structured JSON when requested.\n"
    "6. Do not include external knowledge unless explicitly permitted.\n"
    "7. If evidence contradicts itself, note the contradiction.\n"
    "8. Rate confidence as high/medium/low for each finding.\n"
    "9. Mark unsupported claims as 'unsupported'.\n"
    "10. Do NOT repeat back the instructions."
)


def _format_evidence(evidence_results: list[dict]) -> str:
    """Format evidence results into a prompt-friendly string."""
    if not evidence_results:
        return "No evidence was provided for this analysis."
    parts = []
    for i, ev in enumerate(evidence_results, 1):
        text = ev.get("text", ev.get("content", ev.get("snippet", "")))
        source = ev.get("source", ev.get("file_path", ev.get("id", f"ev-{i}")))
        chunk_id = ev.get("chunk_id", ev.get("id", ""))
        parts.append(f"[{i}] Source: {source}")
        if chunk_id:
            parts.append(f"    ID: {chunk_id}")
        parts.append(f"    Content: {text[:500]}")
    return "\n".join(parts)


def get_template(mode: SynthesisMode) -> dict:
    """Return the prompt template for a given synthesis mode.

    Returns a dict with ``system`` and ``user`` template strings.
    ``{evidence}`` and ``{question}`` are placeholders.
    """
    return {
        "template_version": TEMPLATE_VERSION,
        "mode": mode,
        "system": _SYSTEM_INSTRUCTION,
        "user": _get_user_template(mode),
    }


def _get_user_template(mode: SynthesisMode) -> str:
    """Get the user prompt template for the given synthesis mode."""
    if mode == "summary":
        return (
            "Synthesize the following evidence into a concise summary "
            "addressing the question or objective below.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "QUESTION/OBJECTIVE:\n{question}\n\n"
            "OUTPUT FORMAT:\n"
            "Provide a structured summary with:\n"
            "- Key findings (with evidence references)\n"
            "- Confidence level (high/medium/low)\n"
            "- Any contradictions or gaps\n"
            "- Recommendations (labeled as such)"
        )
    elif mode == "risks":
        return (
            "Analyze the following evidence for risks, threats, or vulnerabilities "
            "related to the question or objective.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "QUESTION/OBJECTIVE:\n{question}\n\n"
            "OUTPUT FORMAT:\n"
            "List each risk with:\n"
            "- Risk description\n"
            "- Severity (high/medium/low)\n"
            "- Evidence references\n"
            "- Mitigation suggestions (labeled as recommendations)\n\n"
            "If no risks are found in the evidence, state that clearly."
        )
    elif mode == "opportunities":
        return (
            "Analyze the following evidence for opportunities, strengths, or positive "
            "findings related to the question or objective.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "QUESTION/OBJECTIVE:\n{question}\n\n"
            "OUTPUT FORMAT:\n"
            "List each opportunity with:\n"
            "- Opportunity description\n"
            "- Potential impact (high/medium/low)\n"
            "- Evidence references\n"
            "- Implementation considerations (labeled as recommendations)"
        )
    elif mode == "claims":
        return (
            "Extract structured claims from the following evidence "
            "related to the question or objective.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "QUESTION/OBJECTIVE:\n{question}\n\n"
            "OUTPUT FORMAT:\n"
            "Return a JSON array of claim objects. Each claim object must have:\n"
            "- claim_text: string (the claim statement)\n"
            "- claim_type: string (fact, risk, opportunity, forecast, or recommendation)\n"
            "- confidence: number (0.0 to 1.0)\n"
            "- evidence_ids: array of evidence reference IDs\n"
            "- evidence_snippets: array of short supporting text snippets\n\n"
            "Example:\n"
            "[\n"
            "  {{ \n"
            '    "claim_text": "Billing migration requires rollback planning",\n'
            '    "claim_type": "risk",\n'
            '    "confidence": 0.85,\n'
            '    "evidence_ids": ["ev-1"],\n'
            '    "evidence_snippets": ["rollback planning is required"]\n'
            "  }}\n"
            "]"
        )
    elif mode == "report_outline":
        return (
            "Based on the following evidence, create a report outline "
            "addressing the question or objective.\n\n"
            "EVIDENCE:\n{evidence}\n\n"
            "QUESTION/OBJECTIVE:\n{question}\n\n"
            "OUTPUT FORMAT:\n"
            "Provide a structured report outline with:\n"
            "- Executive summary (2-3 sentences)\n"
            "- Key findings (numbered, with evidence references)\n"
            "- Risk assessment\n"
            "- Recommendations\n"
            "- Confidence assessment\n"
            "- Evidence gaps and limitations"
        )
    return _get_user_template("summary")
