"""Decision report exporter — Markdown, JSON, and optional HTML output.

Reads from the claim ledger state / war-room run store and produces
exportable report files.  No raw secrets are included in any export format.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from html import escape

from decision_system.models import Claim, DecisionReport, VerificationResult
from decision_system.path_util import ensure_safe_path
from decision_system.war_room.store import load_latest_run as load_latest_war_room

ExportFormat = Literal["markdown", "json", "html"]


def _html_escape_dict(obj: Any) -> Any:
    """Recursively HTML-escape string values in a JSON-like structure."""
    if isinstance(obj, str):
        return escape(obj)
    if isinstance(obj, dict):
        return {k: _html_escape_dict(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_html_escape_dict(v) for v in obj]
    return obj


def build_report_payload(
    question: str = "",
    recommendation: str = "",
    options: list[str] | None = None,
    risks: list[str] | None = None,
    assumptions: list[str] | None = None,
    claims: list[Claim] | None = None,
    verification_results: list[VerificationResult] | None = None,
    evidence_ids: list[str] | None = None,
    audit_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a structured report payload safe for export.

    All fields have safe defaults when not provided.  The payload never
    contains raw secret values, only references and structured metadata.
    """
    payload: dict[str, Any] = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "question": question or "(no question)",
        "recommendation": recommendation or "(no recommendation)",
        "options": options or [],
        "risks": risks or [],
        "assumptions": assumptions or [],
        "claims": [],
        "verification_results": [],
        "evidence_ids": evidence_ids or [],
        "unsupported_claims": [],
        "contradicted_claims": [],
        "audit_metadata": audit_metadata or {},
    }

    if claims:
        for c in claims:
            claim_data = {
                "claim_id": c.claim_id,
                "source_agent": c.source_agent,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "status": c.status,
                "confidence": c.confidence,
                "evidence_ids": c.evidence_ids,
                "contradicting_evidence_ids": c.contradicting_evidence_ids,
                "verification_notes": c.verification_notes,
            }
            payload["claims"].append(claim_data)
            if c.status == "unsupported":
                payload["unsupported_claims"].append(c.claim_id)
            elif c.status == "contradicted":
                payload["contradicted_claims"].append(c.claim_id)

    if verification_results:
        for vr in verification_results:
            payload["verification_results"].append({
                "claim_id": vr.claim_id,
                "status": vr.status,
                "evidence_ids": vr.evidence_ids,
                "contradicting_evidence_ids": vr.contradicting_evidence_ids,
                "confidence": vr.confidence,
                "verification_notes": vr.verification_notes,
            })

    return payload


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render the report payload as Markdown."""
    lines = [
        "# Decision Report",
        "",
        f"**Exported:** {payload['exported_at']}",
        "",
        "## Question",
        "",
        payload["question"],
        "",
        "## Recommendation",
        "",
        payload["recommendation"],
        "",
    ]

    if payload["assumptions"]:
        lines.extend(["## Assumptions", ""])
        for a in payload["assumptions"]:
            lines.append(f"- {a}")
        lines.append("")

    if payload["options"]:
        lines.extend(["## Options Considered", ""])
        for o in payload["options"]:
            lines.append(f"- {o}")
        lines.append("")

    if payload["risks"]:
        lines.extend(["## Risks", ""])
        for r in payload["risks"]:
            lines.append(f"- {r}")
        lines.append("")

    lines.extend(["## Claims Overview", ""])
    lines.append(f"- Total claims: {len(payload['claims'])}")
    lines.append(f"- Unsupported: {len(payload['unsupported_claims'])}")
    lines.append(f"- Contradicted: {len(payload['contradicted_claims'])}")
    lines.append("")

    if payload["claims"]:
        lines.extend(["## Claims Detail", ""])
        for c in payload["claims"]:
            status_icon = {
                "verified": "✓",
                "unsupported": "✗",
                "contradicted": "⚡",
                "pending": "?",
            }.get(c["status"], "?")
            lines.append(f"### {status_icon} {c['claim_text']}")
            lines.append(f"- **Status:** {c['status']}")
            lines.append(f"- **Confidence:** {c['confidence']}")
            lines.append(f"- **Source:** {c['source_agent']}")
            lines.append(f"- **Evidence IDs:** {', '.join(c['evidence_ids']) or 'none'}")
            if c["contradicting_evidence_ids"]:
                lines.append(f"- **Contradicting Evidence:** {', '.join(c['contradicting_evidence_ids'])}")
            if c["verification_notes"]:
                lines.append(f"- **Notes:** {c['verification_notes']}")
            lines.append("")

    if payload["evidence_ids"]:
        lines.extend(["## Evidence Sources", ""])
        for eid in payload["evidence_ids"]:
            lines.append(f"- `{eid}`")
        lines.append("")

    if payload["audit_metadata"]:
        lines.extend(["## Audit Metadata", ""])
        for key, value in payload["audit_metadata"].items():
            lines.append(f"- **{key}:** {value}")
        lines.append("")

    return "\n".join(lines)


def _render_json(payload: dict[str, Any], indent: int = 2) -> str:
    """Render the report payload as pretty-printed JSON."""
    return json.dumps(payload, indent=indent, default=str)


def _render_html(payload: dict[str, Any]) -> str:
    """Render the report payload as a simple self-contained HTML page."""
    safe = _html_escape_dict(payload)
    lines = ["<!DOCTYPE html>", "<html><head><meta charset='utf-8'>"]
    lines.append("<title>Decision Report</title>")
    lines.append("<style>")
    lines.append("body{font-family:sans-serif;max-width:960px;margin:2em auto;padding:0 1em;}")
    lines.append("h1{color:#1a1a2e;}h2{color:#16213e;border-bottom:1px solid #eee;}h3{margin:1em 0 .25em;}")
    lines.append(".status-verified{color:#2e7d32}.status-unsupported{color:#c62828}")
    lines.append(".status-contradicted{color:#e65100}")
    lines.append("ul{padding-left:1.5em}li{margin:.25em 0}")
    lines.append("</style></head><body>")
    lines.append(f"<h1>Decision Report</h1>")
    lines.append(f"<p><strong>Exported:</strong> {safe['exported_at']}</p>")
    lines.append(f"<h2>Question</h2><p>{safe['question']}</p>")
    lines.append(f"<h2>Recommendation</h2><p>{safe['recommendation']}</p>")

    if safe["assumptions"]:
        lines.append("<h2>Assumptions</h2><ul>")
        for a in safe["assumptions"]:
            lines.append(f"<li>{a}</li>")
        lines.append("</ul>")

    if safe["options"]:
        lines.append("<h2>Options Considered</h2><ul>")
        for o in safe["options"]:
            lines.append(f"<li>{o}</li>")
        lines.append("</ul>")

    if safe["risks"]:
        lines.append("<h2>Risks</h2><ul>")
        for r in safe["risks"]:
            lines.append(f"<li>{r}</li>")
        lines.append("</ul>")

    lines.append("<h2>Claims Overview</h2><ul>")
    lines.append(f"<li>Total: {len(safe['claims'])}</li>")
    lines.append(f"<li>Unsupported: {len(safe['unsupported_claims'])}</li>")
    lines.append(f"<li>Contradicted: {len(safe['contradicted_claims'])}</li>")
    lines.append("</ul>")

    if safe["claims"]:
        lines.append("<h2>Claims Detail</h2>")
        for c in safe["claims"]:
            cls = f"status-{c['status']}" if c["status"] in ("verified", "unsupported", "contradicted") else ""
            lines.append(f"<h3 class='{cls}'>{c['claim_text']}</h3>")
            lines.append("<ul>")
            lines.append(f"<li>Status: {c['status']}</li>")
            lines.append(f"<li>Confidence: {c['confidence']}</li>")
            lines.append(f"<li>Source: {c['source_agent']}</li>")
            lines.append(f"<li>Evidence IDs: {', '.join(c['evidence_ids']) or 'none'}</li>")
            if c.get("contradicting_evidence_ids"):
                lines.append(f"<li>Contradicting: {', '.join(c['contradicting_evidence_ids'])}</li>")
            if c.get("verification_notes"):
                lines.append(f"<li>Notes: {c['verification_notes']}</li>")
            lines.append("</ul>")

    if safe["evidence_ids"]:
        lines.append("<h2>Evidence Sources</h2><ul>")
        for eid in safe["evidence_ids"]:
            lines.append(f"<li><code>{escape(eid)}</code></li>")
        lines.append("</ul>")

    if safe["audit_metadata"]:
        lines.append("<h2>Audit Metadata</h2><ul>")
        for key, value in safe["audit_metadata"].items():
            lines.append(f"<li><strong>{escape(str(key))}:</strong> {escape(str(value))}</li>")
        lines.append("</ul>")

    lines.append("</body></html>")
    return "\n".join(lines)


def export_report(
    payload: dict[str, Any],
    fmt: ExportFormat = "markdown",
    output_path: str | Path | None = None,
) -> str:
    """Export a report payload in the requested format.

    If *output_path* is given, writes the result to that file and returns
    the file path as a string.  Otherwise returns the rendered text.
    """
    if fmt == "markdown":
        rendered = _render_markdown(payload)
    elif fmt == "json":
        rendered = _render_json(payload)
    elif fmt == "html":
        rendered = _render_html(payload)
    else:
        raise ValueError(f"Unknown export format: {fmt}")

    if output_path:
        path = Path(output_path)
        # Guard against unsafe write destinations
        try:
            path = ensure_safe_path(path)
        except ValueError as exc:
            raise ValueError(
                f"Cannot export report to unsafe path: {path}. "
                f"Writes must stay within the project root."
            ) from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return str(path.resolve())

    return rendered


def load_latest_report_payload() -> dict[str, Any] | None:
    """Build a report payload from the latest war-room run if available."""
    try:
        run = load_latest_war_room()
    except Exception:
        return None

    if run is None:
        return None

    claims_from_artifacts: list[Claim] = []
    evidence_ids: list[str] = []
    risks: list[str] = []
    options: list[str] = []
    assumptions: list[str] = []

    if run.workspace and run.workspace.artifacts:
        for art in run.workspace.artifacts:
            if art.title:
                assumptions.append(art.title)
            if hasattr(art, "confidence") and art.confidence:
                pass

    judge_summary = {}
    if run.judge_interventions:
        for ji in run.judge_interventions:
            reason = ji.reason or ""
            if "risk" in reason.lower():
                risks.append(reason)
            elif ji.severity in ("high", "critical"):
                risks.append(reason)

    audit_metadata = {
        "run_id": run.run_id,
        "war_room_version": "0.6",
        "artifact_count": len(run.workspace.artifacts) if run.workspace else 0,
        "judge_intervention_count": len(run.judge_interventions),
        "human_review_required": sum(
            1 for ji in run.judge_interventions if ji.requires_human_review
        ),
    }

    return build_report_payload(
        question=run.question or "",
        risks=risks,
        assumptions=assumptions,
        evidence_ids=evidence_ids,
        claims=claims_from_artifacts if claims_from_artifacts else None,
        audit_metadata=audit_metadata,
    )
