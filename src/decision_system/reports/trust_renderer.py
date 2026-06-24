"""Trust report renderer v2 — verification-aware Markdown reports.

Produces trust reports that clearly separate supported, contradicted,
unsupported, uncertain, and needs-review claims. Reports are honest
about limitations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from decision_system.models import (
    Claim,
    ContradictionRecord,
    DecisionReport,
    EvidenceTableEntry,
    ReportClaimEntry,
    VerificationResult,
    VerificationSummary,
)
from decision_system.graphing.models import (
    WorkspaceEdge,
    WorkspaceMetric,
    WorkspaceNode,
    WorkspaceRisk,
)


def render_trust_report(
    question: str,
    run_id: str,
    claims: list[Claim],
    verification_summary: VerificationSummary | None = None,
    verification_results: list[VerificationResult] | None = None,
    contradictions: list[ContradictionRecord] | None = None,
    workspace_id: str | None = None,
    graph_nodes: list[WorkspaceNode] | None = None,
    graph_edges: list[WorkspaceEdge] | None = None,
    graph_risks: list[WorkspaceRisk] | None = None,
    graph_metrics: list[WorkspaceMetric] | None = None,
) -> DecisionReport:
    """Render a trust-aware decision report with full verification sections.

    Args:
        question: Original decision question.
        run_id: Workflow run identifier.
        claims: All claim records (verified or not).
        verification_summary: Optional pre-computed verification summary.
        verification_results: Optional list of verification results.
        contradictions: Optional list of contradiction records.

    Returns:
        A DecisionReport with verification sections, evidence table,
        and clear separation of supported/contradicted/unsupported claims.
    """
    # Classify claims by status
    supported_claims = _classify_claims(claims, statuses=["supported", "verified"])
    contradicted_claims = _classify_claims(claims, statuses=["contradicted"])
    unsupported_claims = _classify_claims(claims, statuses=["unsupported"])
    uncertain_claims = _classify_claims(claims, statuses=["uncertain"])
    needs_review_claims = _classify_claims(claims, statuses=["needs_review"])

    # Verification summary
    if verification_summary is None:
        total = len(claims)
        supported = sum(1 for c in claims if c.status in ("supported", "verified"))
        contradicted = sum(1 for c in claims if c.status == "contradicted")
        unsupported = sum(1 for c in claims if c.status == "unsupported")
        uncertain = sum(1 for c in claims if c.status == "uncertain")
        needs_review = sum(1 for c in claims if c.status == "needs_review")
        confidences = {"high": 1.0, "medium": 0.5, "low": 0.0}
        avg_conf = sum(confidences.get(c.confidence, 0.0) for c in claims) / max(total, 1) if total > 0 else 0
        with_evidence = sum(1 for c in claims if c.evidence_ids or c.evidence_snippets)
        coverage = round(with_evidence / max(total, 1), 2) if total > 0 else 0

        verification_summary = VerificationSummary(
            total_claims=total,
            supported_claims=supported,
            contradicted_claims=contradicted,
            unsupported_claims=unsupported,
            uncertain_claims=uncertain,
            needs_review_claims=needs_review,
            average_confidence=round(avg_conf, 2),
            evidence_coverage_score=coverage,
        )

    # Build evidence table
    evidence_table = _build_evidence_table(claims)

    # Build risk list
    risks = [c.claim_text for c in claims if c.claim_type == "risk"]

    # Determine recommendation
    recommendation = _build_recommendation(verification_summary)

    # Determine confidence level
    confidence_level = _build_confidence_level(verification_summary)

    # Human review items
    human_review_required = _build_human_review_items(
        verification_summary, contradicted_claims, needs_review_claims
    )

    # Build report entries
    report_supported = [_claim_to_entry(c) for c in supported_claims]
    report_contradicted = [_claim_to_entry(c) for c in contradicted_claims]
    report_unsupported = [_claim_to_entry(c) for c in unsupported_claims]
    report_uncertain = [_claim_to_entry(c) for c in uncertain_claims]
    report_needs_review = [_claim_to_entry(c) for c in needs_review_claims]

    # Contradiction records for report
    contradiction_records = contradictions or []
    if not contradiction_records:
        # Derive from claims with contradicting evidence
        for c in claims:
            if c.contradicting_evidence_ids:
                contradiction_records.append(ContradictionRecord(
                    contradiction_id=f"derived-{c.claim_id}",
                    claim_id=c.claim_id,
                    source_id_a=c.evidence_ids[0] if c.evidence_ids else "",
                    chunk_id_a="",
                    source_id_b=c.contradicting_evidence_ids[0] if c.contradicting_evidence_ids else "",
                    chunk_id_b="",
                    type="claim_contradicted",
                    description=f"Claim '{c.claim_text[:80]}' has contradicting evidence.",
                    severity="high",
                ))

    markdown = _render_trust_markdown(
        question=question,
        recommendation=recommendation,
        verification_summary=verification_summary,
        supported=report_supported,
        contradicted=report_contradicted,
        unsupported=report_unsupported,
        uncertain=report_uncertain,
        needs_review=report_needs_review,
        evidence_table=evidence_table,
        contradictions=contradiction_records,
        risks=risks,
        confidence_level=confidence_level,
        human_review_required=human_review_required,
        workspace_id=workspace_id,
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
        graph_risks=graph_risks,
        graph_metrics=graph_metrics,
    )

    return DecisionReport(
        run_id=run_id,
        question=question,
        recommendation=recommendation,
        options=[
            "Proceed with a staged plan if verification is acceptable.",
            "Delay the decision until contradicted or unsupported claims are reviewed.",
            "Request additional evidence from a human owner.",
        ],
        evidence_citations=sorted({
            eid for c in claims for eid in c.evidence_ids
        }),
        risks=risks,
        contradictions=[c for c in claims if c.status == "contradicted"],
        unsupported_assumptions=[c for c in claims if c.status == "unsupported"],
        confidence_level=confidence_level,
        human_review_required=human_review_required,
        markdown=markdown,
        verification_summary=verification_summary,
        supported_claims=report_supported,
        contradicted_claims=report_contradicted,
        unsupported_claims=report_unsupported,
        uncertain_claims=report_uncertain,
        needs_review_claims=report_needs_review,
        evidence_table=evidence_table,
        contradiction_records=contradiction_records,
    )


def _classify_claims(
    claims: list[Claim], statuses: list[str]
) -> list[Claim]:
    """Filter claims by status."""
    return [c for c in claims if c.status in statuses]


def _claim_to_entry(claim: Claim) -> ReportClaimEntry:
    """Convert a Claim to a ReportClaimEntry."""
    return ReportClaimEntry(
        claim_id=claim.claim_id,
        claim_text=claim.claim_text,
        status=claim.status,  # type: ignore
        confidence=claim.confidence,  # type: ignore
        evidence_quality=getattr(claim, "evidence_quality", None),
        verification_method=getattr(claim, "verification_method", None),
        verification_reason=claim.verification_notes,
        evidence_ids=claim.evidence_ids,
        evidence_snippets=claim.evidence_snippets,
        contradicting_evidence_ids=claim.contradicting_evidence_ids,
        review_required=claim.review_required,
        graph_node_refs=getattr(claim, "graph_node_refs", []),
        graph_edge_refs=getattr(claim, "graph_edge_refs", []),
        risk_refs=getattr(claim, "risk_refs", []),
        metric_refs=getattr(claim, "metric_refs", []),
    )


def _build_evidence_table(claims: list[Claim]) -> list[EvidenceTableEntry]:
    """Build evidence table from claims."""
    evidence_map: dict[str, EvidenceTableEntry] = {}
    for claim in claims:
        for i, eid in enumerate(claim.evidence_ids):
            if eid not in evidence_map:
                snippet = (
                    claim.evidence_snippets[i]
                    if i < len(claim.evidence_snippets)
                    else ""
                )
                evidence_map[eid] = EvidenceTableEntry(
                    evidence_id=eid,
                    source_name="",
                    snippet=snippet[:200],
                )
            entry = evidence_map[eid]
            if claim.claim_id not in entry.supports_claim_ids:
                entry.supports_claim_ids.append(claim.claim_id)

        for cid in claim.contradicting_evidence_ids:
            if cid not in evidence_map:
                evidence_map[cid] = EvidenceTableEntry(
                    evidence_id=cid,
                    source_name="",
                    snippet="",
                )
            entry = evidence_map[cid]
            if claim.claim_id not in entry.contradicts_claim_ids:
                entry.contradicts_claim_ids.append(claim.claim_id)

    return list(evidence_map.values())


def _build_recommendation(summary: VerificationSummary) -> str:
    """Build recommendation based on verification summary."""
    if summary.contradicted_claims > 0:
        return (
            "Do not proceed on this evidence alone. "
            f"{summary.contradicted_claims} claim(s) are contradicted and must be resolved."
        )
    if summary.needs_review_claims > 0:
        return (
            "Proceed cautiously. "
            f"{summary.needs_review_claims} claim(s) need human review before action."
        )
    if summary.unsupported_claims > 0 or summary.uncertain_claims > 0:
        return (
            "Proceed with caution. "
            f"{summary.unsupported_claims} unsupported and {summary.uncertain_claims} uncertain "
            "claim(s) should be reviewed."
        )
    if summary.supported_claims > 0:
        return (
            "Proceed using the verified evidence, with normal human oversight."
        )
    return "Insufficient evidence to make a recommendation."


def _build_confidence_level(summary: VerificationSummary) -> str:
    """Determine report confidence level."""
    if summary.contradicted_claims > 0 and summary.supported_claims == 0:
        return "low"
    if summary.supported_claims > summary.unsupported_claims + summary.uncertain_claims + summary.contradicted_claims:
        return "high"
    if summary.supported_claims > 0:
        return "medium"
    return "low"


def _build_human_review_items(
    summary: VerificationSummary,
    contradicted: list[Claim],
    needs_review: list[Claim],
) -> list[str]:
    """Build human review items list."""
    items: list[str] = []
    if summary.contradicted_claims > 0:
        items.append(
            f"Resolve {summary.contradicted_claims} contradicted claim(s) before acting."
        )
    if summary.needs_review_claims > 0:
        items.append(
            f"Review {summary.needs_review_claims} claim(s) flagged as needing human review."
        )
    if summary.unsupported_claims > 0:
        items.append(
            f"Add supporting evidence for {summary.unsupported_claims} unsupported claim(s)."
        )
    if summary.uncertain_claims > 0:
        items.append(
            f"Clarify {summary.uncertain_claims} uncertain claim(s) with stronger evidence."
        )
    return items


def _render_trust_markdown(
    question: str,
    recommendation: str,
    verification_summary: VerificationSummary,
    supported: list[ReportClaimEntry],
    contradicted: list[ReportClaimEntry],
    unsupported: list[ReportClaimEntry],
    uncertain: list[ReportClaimEntry],
    needs_review: list[ReportClaimEntry],
    evidence_table: list[EvidenceTableEntry],
    contradictions: list[ContradictionRecord],
    risks: list[str],
    confidence_level: str,
    human_review_required: list[str],
    workspace_id: str | None = None,
    graph_nodes: list[WorkspaceNode] | None = None,
    graph_edges: list[WorkspaceEdge] | None = None,
    graph_risks: list[WorkspaceRisk] | None = None,
    graph_metrics: list[WorkspaceMetric] | None = None,
) -> str:
    """Build the trust report Markdown body."""
    sections: list[str] = [
        "# Trust Report",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Confidence Level:** {confidence_level.upper()}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        recommendation,
        "",
        "---",
        "",
        "## Verification Summary",
        "",
        f"- **Total Claims:** {verification_summary.total_claims}",
        f"- **Supported:** {verification_summary.supported_claims}",
        f"- **Contradicted:** {verification_summary.contradicted_claims}",
        f"- **Unsupported:** {verification_summary.unsupported_claims}",
        f"- **Uncertain:** {verification_summary.uncertain_claims}",
        f"- **Needs Review:** {verification_summary.needs_review_claims}",
        f"- **Average Confidence:** {verification_summary.average_confidence}",
        f"- **Evidence Coverage Score:** {verification_summary.evidence_coverage_score}",
        "",
    ]

    # Supported Claims
    sections.append("## Supported Claims")
    sections.append("")
    if supported:
        for entry in supported:
            qual = f" [{entry.evidence_quality.upper()}]" if entry.evidence_quality else ""
            sections.append(f"- **{entry.claim_text}**{qual}")
            sections.append(f"  - Confidence: {entry.confidence}")
            if entry.verification_reason:
                sections.append(f"  - Reason: {entry.verification_reason}")
            if entry.evidence_ids:
                sections.append(f"  - Evidence: {', '.join(entry.evidence_ids[:3])}")
            sections.append("")
    else:
        sections.append("- No supported claims.")
        sections.append("")

    # Contradicted Claims
    sections.append("## Contradicted Claims")
    sections.append("")
    if contradicted:
        for entry in contradicted:
            sections.append(f"- ⚠️ **{entry.claim_text}**")
            sections.append(f"  - Confidence: {entry.confidence}")
            if entry.verification_reason:
                sections.append(f"  - Reason: {entry.verification_reason}")
            if entry.contradicting_evidence_ids:
                sections.append(f"  - Contradicting Evidence: {', '.join(entry.contradicting_evidence_ids[:3])}")
            sections.append("")
    else:
        sections.append("- No contradicted claims found.")
        sections.append("")

    # Unsupported Claims
    sections.append("## Unsupported Claims")
    sections.append("")
    if unsupported:
        for entry in unsupported:
            sections.append(f"- ❓ **{entry.claim_text}**")
            sections.append(f"  - Reason: {entry.verification_reason or 'No evidence found.'}")
            sections.append("")
    else:
        sections.append("- No unsupported claims.")
        sections.append("")

    # Uncertain Claims
    sections.append("## Uncertain Claims")
    sections.append("")
    if uncertain:
        for entry in uncertain:
            sections.append(f"- ⁉️ **{entry.claim_text}**")
            sections.append(f"  - Reason: {entry.verification_reason or 'Weak or unclear evidence.'}")
            sections.append("")
    else:
        sections.append("- No uncertain claims.")
        sections.append("")

    # Claims Needing Review
    sections.append("## Claims Needing Review")
    sections.append("")
    if needs_review:
        for entry in needs_review:
            sections.append(f"- 🔴 **{entry.claim_text}**")
            sections.append(f"  - Reason: {entry.verification_reason or 'Requires human review.'}")
            sections.append("")
    else:
        sections.append("- No claims need review.")
        sections.append("")

    # Evidence Table
    sections.append("## Evidence Table")
    sections.append("")
    if evidence_table:
        sections.append("| Evidence ID | Snippet | Supports | Contradicts |")
        sections.append("|-------------|---------|----------|-------------|")
        for entry in evidence_table:
            snippet = entry.snippet[:80].replace("|", "\\|") if entry.snippet else "*empty*"
            supports = ", ".join(entry.supports_claim_ids[:2]) or "-"
            contradicts = ", ".join(entry.contradicts_claim_ids[:2]) or "-"
            sections.append(f"| {entry.evidence_id[:24]} | {snippet} | {supports} | {contradicts} |")
        sections.append("")
        if any(len(e.supports_claim_ids) > 2 or len(e.contradicts_claim_ids) > 2 for e in evidence_table):
            sections.append("*Only first 2 claim IDs shown per cell.*")
            sections.append("")
    else:
        sections.append("- No evidence references found.")
        sections.append("")

    # Contradictions
    sections.append("## Contradictions")
    sections.append("")
    if contradictions:
        for c in contradictions:
            sections.append(f"- **{c.type}** ({c.severity}): {c.description}")
            sections.append(f"  - Source A: {c.source_id_a}")
            sections.append(f"  - Source B: {c.source_id_b}")
            sections.append("")
    else:
        sections.append("- No contradictions detected.")
        sections.append("")

    # Risks
    sections.append("## Risks")
    sections.append("")
    if risks:
        for risk in risks:
            sections.append(f"- ⚠️ {risk}")
        sections.append("")
    else:
        sections.append("- No risk claims identified.")
        sections.append("")

    # Review Status
    sections.append("## Review Status")
    sections.append("")
    sections.append(f"- **Confidence Level:** {confidence_level}")
    if human_review_required:
        sections.append("- **Human Review Required:**")
        for item in human_review_required:
            sections.append(f"  - {item}")
    else:
        sections.append("- **Human Review:** Not required.")
    sections.append("")

    # Warnings and Limitations
    sections.append("## Warnings and Limitations")
    sections.append("")
    sections.append("- This report is generated by a deterministic local verifier, not a perfect truth engine.")
    sections.append("- Claim verification checks whether local workspace evidence appears to support, contradict, or fail to support claims.")
    sections.append("- Evidence quality labels are based on reference count and source diversity, not semantic accuracy.")
    sections.append("- Contradiction detection uses pattern matching and may miss nuanced contradictions.")
    sections.append("- The verifier does not claim to prove or disprove factual truth.")
    if verification_summary.contradicted_claims > 0 or verification_summary.unsupported_claims > 0:
        sections.append("- **Do not base decisions solely on this report without human review of contradictory or missing evidence.**")
    sections.append("")

    # ------------------------------------------------------------------
    # Graph sections (if graph data provided)
    # ------------------------------------------------------------------
    if graph_nodes:
        sections.extend(_render_entity_summary_section(graph_nodes))
    if graph_edges:
        sections.extend(_render_relationship_section(graph_edges, graph_nodes or []))
    if graph_risks:
        sections.extend(_render_risk_section(graph_risks))
    if graph_metrics:
        sections.extend(_render_metric_section(graph_metrics))
    if any([graph_nodes, graph_edges, graph_risks, graph_metrics]):
        sections.append("---")
        sections.append("")


    # Recommended Next Actions
    sections.append("## Recommended Next Actions")
    sections.append("")
    if verification_summary.contradicted_claims > 0:
        sections.append("1. Resolve contradicted claims by reviewing the original evidence sources.")
        sections.append("2. Gather additional evidence to clarify uncertainties.")
        sections.append("3. Escalate contradicted findings to a human decision-maker.")
    elif verification_summary.unsupported_claims > 0:
        sections.append("1. Add supporting evidence for unsupported claims before acting.")
        sections.append("2. Review uncertain claims with additional data sources.")
        sections.append("3. Proceed with caution on supported claims only.")
    else:
        sections.append("1. Review supported claims and their evidence sources.")
        sections.append("2. Consider the report confidence level in your decision.")
        sections.append("3. Proceed with normal human oversight.")

    sections.append("")
    sections.append("---")
    sections.append("")
    sections.append(f"## Decision Question")
    sections.append(f"")
    sections.append(question)
    sections.append("")

    return "\n".join(sections)
# ---------------------------------------------------------------------------
# Graph section renderers
# ---------------------------------------------------------------------------


def _render_entity_summary_section(nodes):
    """Render Entity Summary section from workspace graph nodes."""
    lines = ["## Entity Summary", ""]

    # Count by type
    type_counts = {}
    for n in nodes:
        t = str(n.node_type)
        type_counts[t] = type_counts.get(t, 0) + 1

    lines.append(f"**Total entities:** {len(nodes)}")
    lines.append("")
    if type_counts:
        lines.append("**Entities by type:**")
        for t, c in sorted(type_counts.items()):
            lines.append(f"- **{t}** ({c})")
        lines.append("")

    # List top entities by confidence
    conf_order = {"high": 3, "medium": 2, "low": 1}
    sorted_nodes = sorted(nodes, key=lambda n: conf_order.get(n.confidence, 0), reverse=True)
    display_nodes = sorted_nodes[:15]
    if display_nodes:
        lines.append("**Key entities:**")
        for n in display_nodes:
            status_marker = ""
            if n.status == "verified":
                status_marker = " ✅"
            elif n.status == "contradicted":
                status_marker = " ⚠️"
            desc = f" — {n.description[:60]}" if n.description else ""
            lines.append(f"- **{n.name}** ({n.node_type}) [{n.confidence}]{status_marker}{desc}")
        lines.append("")
        if len(nodes) > 15:
            lines.append(f"*{len(nodes) - 15} more entities not shown.*")
            lines.append("")

    lines.append("*Entities are extracted by deterministic pattern matching and may contain errors.*")
    lines.append("")
    return lines


def _render_relationship_section(edges, nodes):
    """Render Key Relationships section from workspace graph edges."""
    lines = ["## Key Relationships", ""]

    # Build node name lookup
    node_names = {}
    for n in nodes:
        node_names[n.node_id] = n.name

    lines.append(f"**Total relationships:** {len(edges)}")
    lines.append("")

    # Group by edge type
    type_counts = {}
    for e in edges:
        t = str(e.edge_type)
        type_counts[t] = type_counts.get(t, 0) + 1

    if type_counts:
        lines.append("**Relationship types:**")
        for t, c in sorted(type_counts.items()):
            lines.append(f"- **{t}** ({c})")
        lines.append("")

    # List edges
    display_edges = edges[:20]
    if display_edges:
        lines.append("**Relationships:**")
        for e in display_edges:
            src = node_names.get(e.source_node_id, e.source_node_id[:16])
            tgt = node_names.get(e.target_node_id, e.target_node_id[:16])
            label = f" ({e.label})" if e.label else ""
            lines.append(f"- **{src}** → **{tgt}** [{e.edge_type}]{label} ({e.confidence})")
        lines.append("")
        if len(edges) > 20:
            lines.append(f"*{len(edges) - 20} more relationships not shown.*")
            lines.append("")

    lines.append("*Relationships are extracted by deterministic pattern matching and may contain errors.*")
    lines.append("")
    return lines


def _render_risk_section(risks):
    """Render Extracted Risks section from workspace graph risks."""
    lines = ["## Extracted Risks", ""]

    lines.append(f"**Total risks:** {len(risks)}")
    lines.append("")

    # Severity breakdown
    severity_counts = {}
    for r in risks:
        s = str(r.severity)
        severity_counts[s] = severity_counts.get(s, 0) + 1

    if severity_counts:
        lines.append("**Risks by severity:**")
        for s in ("critical", "high", "medium", "low"):
            if s in severity_counts:
                lines.append(f"- **{s}** ({severity_counts[s]})")
        lines.append("")

    # Category breakdown
    category_counts = {}
    for r in risks:
        cat = str(r.category)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    if category_counts:
        lines.append("**Risks by category:**")
        for cat, c in sorted(category_counts.items()):
            lines.append(f"- **{cat}** ({c})")
        lines.append("")

    # Sort by severity (critical first) and list top risks
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_risks = sorted(risks, key=lambda r: severity_order.get(r.severity, 99))
    display_risks = sorted_risks[:10]

    if display_risks:
        lines.append("**Risk details:**")
        for r in display_risks:
            markers = {"critical": "🔴", "high": "⚠️", "medium": "⚡", "low": "ℹ️"}
            marker = markers.get(r.severity, "ℹ️")
            desc = f" — {r.description[:100]}" if r.description else ""
            lines.append(f"- {marker} **{r.title}** [{r.severity}/{r.category}] ({r.confidence}){desc}")
            if r.recommended_actions:
                for action in r.recommended_actions[:2]:
                    lines.append(f"  - *Recommended:* {action}")
        lines.append("")
        if len(risks) > 10:
            lines.append(f"*{len(risks) - 10} more risks not shown.*")
            lines.append("")

    lines.append("*Risks are flagged by keyword pattern matching and may include false positives.*")
    lines.append("")
    return lines


def _render_metric_section(metrics):
    """Render Key Metrics section from workspace graph metrics."""
    lines = ["## Key Metrics", ""]

    lines.append(f"**Total metrics extracted:** {len(metrics)}")
    lines.append("")

    if metrics:
        lines.append("| Name | Value | Unit | Period | Entity | Confidence |")
        lines.append("|------|-------|------|--------|--------|------------|")
        for m in metrics[:20]:
            name = (m.name[:40] if m.name else "*unnamed*")
            value = (m.value[:20] if m.value else "-")
            unit = m.unit or "-"
            period = m.period or "-"
            entity = ", ".join(m.entity_refs[:2]) if m.entity_refs else "-"
            lines.append(f"| {name} | {value} | {unit} | {period} | {entity} | {m.confidence} |")
        lines.append("")
        if len(metrics) > 20:
            lines.append(f"*{len(metrics) - 20} more metrics not shown.*")
            lines.append("")

    lines.append("*Metrics are extracted from text as found and may be out of context.*")
    lines.append("")
    return lines
