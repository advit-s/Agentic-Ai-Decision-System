"""Markdown decision report renderer.

The renderer consumes claim ledger state only. It must not upgrade raw agent
memo text into final truth without a verification status.
"""

from decision_system.context.models import DecisionContext
from decision_system.models import Claim, DecisionReport


def render_decision_report(
    question: str,
    run_id: str,
    claims: list[Claim],
    context: DecisionContext | None = None,
) -> DecisionReport:
    """Render a conservative decision report from verified ledger claims.

    Args:
        question: Original decision question.
        run_id: Workflow run identifier.
        claims: Verified, unsupported, or contradicted claim ledger records.
        context: Optional DecisionContext for insight-aware sections.

    Returns:
        A `DecisionReport` containing structured fields and Markdown.

    v0.1 limitation:
        The recommendation is rule-based and intentionally conservative.
    """

    verified = [claim for claim in claims if claim.status == "verified"]
    unsupported = [claim for claim in claims if claim.status == "unsupported"]
    contradicted = [claim for claim in claims if claim.status == "contradicted"]
    evidence_citations = sorted(
        {evidence_id for claim in verified for evidence_id in claim.evidence_ids}
    )
    risks = [claim.claim_text for claim in claims if claim.claim_type == "risk"]

    # Final synthesis is intentionally ledger-driven. Raw provider prose is not
    # treated as fact unless it has become a verified claim.
    if verified and not contradicted:
        recommendation = (
            "Proceed cautiously using the verified evidence, with human review before action."
        )
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
        human_review_required.append(
            "Review unsupported assumptions before relying on the recommendation."
        )
    if not verified:
        human_review_required.append("Add supporting evidence before making this decision.")

    # Add context-based human review items
    if context and context.human_review_items:
        human_review_required.extend(context.human_review_items)

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
        context=context,
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
    context: DecisionContext | None = None,
) -> str:
    """Build the report Markdown body from structured report sections."""

    sections = [
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
    ]

    # Optional insight-aware sections
    if context:
        if context.relevant_insights:
            sections.extend(_render_insights_section(context.relevant_insights))
        if context.relevant_ontology_concepts:
            sections.extend(_render_ontology_section(context.relevant_ontology_concepts))
        if context.graph_signals:
            sections.extend(_render_graph_section(context.graph_signals))
        if context.orchestration_summary:
            sections.extend(
                _render_orchestration_section(context.orchestration_summary, context.judge_summary)
            )

    sections.extend(
        [
            "## Confidence Level",
            confidence_level,
            "",
            "## Human Review Required",
            _bullets(human_review_required)
            if human_review_required
            else "- No human review required for v0.1 evidence state.",
            "",
            "## Decision Question",
            question,
        ]
    )

    return "\n".join(sections)


def _render_insights_section(insights: list) -> list[str]:
    """Render Business/Data Insights section."""
    lines = ["## Business/Data Insights", ""]
    for insight in insights:
        severity_marker = f"[{insight.severity.upper()}]"
        lines.extend(
            [
                f"### {insight.title} {severity_marker}",
                f"- **Category:** {insight.category}",
                f"- **Confidence:** {insight.confidence}",
                f"- **Evidence:** {insight.evidence_summary}",
                f"- **Recommended Action:** {insight.recommended_action}",
                f"- **Ontology Concepts:** {', '.join(insight.ontology_concepts) or '(none)'}",
                f"- **Source IDs:** {', '.join(insight.source_ids) or '(none)'}",
                "",
            ]
        )
    lines.append("*Insights are detected signals, not absolute truth. Verify before acting.*")
    lines.append("")
    return lines


def _render_ontology_section(concepts: list[dict]) -> list[str]:
    """Render Ontology Concepts Used section."""
    lines = ["## Ontology Concepts Used", ""]
    for c in concepts:
        required_mark = " *(required)*" if c.get("required") else ""
        lines.append(
            f"- **{c['concept_id']}** ({c.get('type', 'unknown')}): {c['name']}{required_mark}"
        )
    lines.append("")
    return lines


def _render_graph_section(signals: list[str]) -> list[str]:
    """Render Graph and Relationship Signals section."""
    lines = ["## Graph and Relationship Signals", ""]
    for signal in signals:
        lines.append(f"- {signal}")
    lines.append("")
    return lines


def _render_orchestration_section(orch_summary: dict, judge_summary: dict) -> list[str]:
    """Render Orchestration Summary section."""
    lines = ["## Orchestration Summary", ""]
    lines.append(f"- **Run ID:** {orch_summary.get('run_id', 'unknown')}")
    lines.append(f"- **Decision Type:** {orch_summary.get('decision_type', 'unknown')}")
    lines.append(f"- **Insight Count:** {orch_summary.get('insight_count', 0)}")
    by_sev = orch_summary.get("insights_by_severity", {})
    if by_sev:
        lines.append("- **Insights by Severity:**")
        for sev, count in sorted(by_sev.items()):
            lines.append(f"  - {sev}: {count}")
    lines.append("")

    if judge_summary:
        lines.append("### Judge Summary")
        lines.append(f"- **Confidence:** {judge_summary.get('confidence_level', 'unknown')}")
        key_findings = judge_summary.get("key_findings", [])
        if key_findings:
            lines.append("- **Key Findings:**")
            for f in key_findings:
                lines.append(f"  - {f}")
        human_review = judge_summary.get("human_review_required", [])
        if human_review:
            lines.append("- **Human Review Required:**")
            for r in human_review:
                lines.append(f"  - {r}")
        lines.append("")

    return lines


def _bullets(items: list[str]) -> str:
    """Render simple Markdown bullets."""

    return "\n".join(f"- {item}" for item in items)


def _claim_bullets(claims: list[Claim]) -> str:
    """Render claim bullets with IDs and verification notes."""

    return "\n".join(
        f"- {claim.claim_text} ({claim.claim_id}): {claim.verification_notes}" for claim in claims
    )
