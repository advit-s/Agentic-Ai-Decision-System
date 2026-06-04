"""Markdown decision report renderer.

The renderer consumes claim ledger state only. It must not upgrade raw agent
memo text into final truth without a verification status.
"""

from decision_system.models import Claim, DecisionReport


def render_decision_report(question: str, run_id: str, claims: list[Claim]) -> DecisionReport:
    """Render a conservative decision report from verified ledger claims.

    Args:
        question: Original decision question.
        run_id: Workflow run identifier.
        claims: Verified, unsupported, or contradicted claim ledger records.

    Returns:
        A `DecisionReport` containing structured fields and Markdown.

    v0.1 limitation:
        The recommendation is rule-based and intentionally conservative.
    """

    verified = [claim for claim in claims if claim.status == "verified"]
    unsupported = [claim for claim in claims if claim.status == "unsupported"]
    contradicted = [claim for claim in claims if claim.status == "contradicted"]
    evidence_citations = sorted(
        {
            evidence_id
            for claim in verified
            for evidence_id in claim.evidence_ids
        }
    )
    risks = [claim.claim_text for claim in claims if claim.claim_type == "risk"]

    # Final synthesis is intentionally ledger-driven. Raw provider prose is not
    # treated as fact unless it has become a verified claim.
    if verified and not contradicted:
        recommendation = "Proceed cautiously using the verified evidence, with human review before action."
    else:
        recommendation = "Do not proceed on this evidence alone; resolve missing or contradictory evidence first."

    options = [
        "Proceed with a staged plan if verified claims are acceptable.",
        "Delay the decision until unsupported or contradicted claims are reviewed.",
        "Request additional evidence from a human owner.",
    ]

    if not verified or contradicted:
        confidence_level = "low"
    elif unsupported:
        confidence_level = "medium"
    else:
        confidence_level = "high"

    human_review_required: list[str] = []
    if contradicted:
        human_review_required.append("Resolve contradicted claims before taking action.")
    if unsupported:
        human_review_required.append("Review unsupported assumptions before relying on the recommendation.")
    if not verified:
        human_review_required.append("Add supporting evidence before making this decision.")

    markdown = _render_markdown(
        question=question,
        recommendation=recommendation,
        options=options,
        evidence_citations=evidence_citations,
        risks=risks,
        contradicted=contradicted,
        unsupported=unsupported,
        confidence_level=confidence_level,
        human_review_required=human_review_required,
    )

    return DecisionReport(
        run_id=run_id,
        question=question,
        recommendation=recommendation,
        options=options,
        evidence_citations=evidence_citations,
        risks=risks,
        contradictions=contradicted,
        unsupported_assumptions=unsupported,
        confidence_level=confidence_level,
        human_review_required=human_review_required,
        markdown=markdown,
    )


def _render_markdown(
    question: str,
    recommendation: str,
    options: list[str],
    evidence_citations: list[str],
    risks: list[str],
    contradicted: list[Claim],
    unsupported: list[Claim],
    confidence_level: str,
    human_review_required: list[str],
) -> str:
    """Build the report Markdown body from structured report sections."""

    return "\n".join(
        [
            "# Decision Report",
            "",
            "## Recommendation",
            recommendation,
            "",
            "## Options",
            _bullets(options),
            "",
            "## Evidence Citations",
            _bullets(evidence_citations) if evidence_citations else "- No verified evidence citations.",
            "",
            "## Risks",
            _bullets(risks) if risks else "- No risk claims were identified.",
            "",
            "## Contradictions",
            _claim_bullets(contradicted) if contradicted else "- No contradictions found.",
            "",
            "## Unsupported Assumptions",
            _claim_bullets(unsupported) if unsupported else "- No unsupported assumptions found.",
            "",
            "## Confidence Level",
            confidence_level,
            "",
            "## Human Review Required",
            _bullets(human_review_required) if human_review_required else "- No human review required for v0.1 evidence state.",
            "",
            "## Decision Question",
            question,
        ]
    )


def _bullets(items: list[str]) -> str:
    """Render simple Markdown bullets."""

    return "\n".join(f"- {item}" for item in items)


def _claim_bullets(claims: list[Claim]) -> str:
    """Render claim bullets with IDs and verification notes."""

    return "\n".join(
        f"- {claim.claim_text} ({claim.claim_id}): {claim.verification_notes}"
        for claim in claims
    )
