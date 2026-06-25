"""Inspector and rendering helpers for the v1.2 security subsystem.

Follows the same pure-computation (inspect_) / presentation (render_)
pattern used by the insights, graph, data-catalog, and war-room subsystems.
"""

from __future__ import annotations

from typing import Any

from decision_system.security.models import (
    ApprovalRequest,
    AuditEvent,
    PolicyCheckResult,
    RedactionPreviewResult,
    SecretScanResult,
)

# ---------------------------------------------------------------------------
# Secret scan inspector
# ---------------------------------------------------------------------------


def inspect_secret_scan(result: SecretScanResult) -> dict[str, Any]:
    return {
        "scan_id": result.scan_id,
        "scanned_path": result.scanned_path,
        "files_scanned": result.files_scanned,
        "files_skipped": result.files_skipped,
        "finding_count": len(result.findings),
        "overall_status": result.overall_status,
        "by_severity": _count_by(result.findings, "severity"),
        "by_type": _count_by(result.findings, "secret_type"),
        "top_findings": [
            {
                "finding_id": f.finding_id,
                "source_path": f.source_path,
                "line_number": f.line_number,
                "secret_type": f.secret_type,
                "severity": f.severity,
                "matched_preview": f.matched_preview,
            }
            for f in result.findings[:20]
        ],
        "created_at": result.created_at,
    }


def render_secret_scan(summary: dict[str, Any]) -> str:
    lines: list[str] = ["# Secret Scan Inspection", ""]
    lines.append(f"Scanned path: {summary.get('scanned_path', '(unknown)')}")
    lines.append(f"Status: {summary.get('overall_status', 'unknown').upper()}")
    lines.append(f"Files scanned: {summary.get('files_scanned', 0)}")
    lines.append(f"Files skipped: {summary.get('files_skipped', 0)}")
    lines.append(f"Findings: {summary.get('finding_count', 0)}")
    lines.append("")
    by_sev = summary.get("by_severity", {})
    if by_sev:
        lines.append("By severity:")
        for sev in ("critical", "high", "medium", "low"):
            count = by_sev.get(sev, 0)
            if count:
                lines.append(f"- {sev}: {count}")
        lines.append("")
    by_type = summary.get("by_type", {})
    if by_type:
        lines.append("By type:")
        for t, c in sorted(by_type.items()):
            lines.append(f"- {t}: {c}")
        lines.append("")
    top = summary.get("top_findings", [])
    if top:
        lines.append("Top findings:")
        lines.append("")
        for f in top:
            lines.append(
                f"- [{f['severity'].upper()}] {f['secret_type']} in {f['source_path']}:{f['line_number']}"
            )
            lines.append(f"  Preview: {f['matched_preview']}")
        lines.append("")
    lines.append(f"Run at: {summary.get('created_at', 'unknown')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Redaction inspector
# ---------------------------------------------------------------------------


def inspect_redaction(result: RedactionPreviewResult) -> dict[str, Any]:
    return {
        "original_text": result.original_text,
        "redacted_text": result.redacted_text,
        "finding_count": result.finding_count,
        "by_type": _count_by(result.findings, "text_type"),
        "findings": [
            {
                "finding_id": f.finding_id,
                "text_type": f.text_type,
                "start": f.start,
                "end": f.end,
                "matched_preview": f.matched_preview,
                "replacement": f.replacement,
                "confidence": f.confidence,
            }
            for f in result.findings
        ],
    }


def render_redaction(summary: dict[str, Any]) -> str:
    lines: list[str] = ["# Redaction Preview", ""]
    lines.append("Original:")
    lines.append(f"> {summary['original_text']}")
    lines.append("")
    lines.append("Redacted:")
    lines.append(f"> {summary['redacted_text']}")
    lines.append("")
    lines.append(f"Findings: {summary['finding_count']}")
    by_type = summary.get("by_type", {})
    if by_type:
        lines.append("By type:")
        for t, c in sorted(by_type.items()):
            lines.append(f"- {t}: {c}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Audit log inspector
# ---------------------------------------------------------------------------


def inspect_audit_log(events: list[AuditEvent]) -> dict[str, Any]:
    return {
        "total_events": len(events),
        "by_type": _count_by(events, "event_type"),
        "latest_event": (
            {
                "event_id": events[-1].event_id,
                "event_type": events[-1].event_type,
                "actor": events[-1].actor,
                "message": events[-1].message,
                "created_at": events[-1].created_at,
            }
            if events
            else None
        ),
    }


def render_audit_log(summary: dict[str, Any]) -> str:
    lines: list[str] = ["# Audit Log", ""]
    lines.append(f"Total events: {summary.get('total_events', 0)}")
    by_type = summary.get("by_type", {})
    if by_type:
        lines.append("By type:")
        for t, c in sorted(by_type.items()):
            lines.append(f"- {t}: {c}")
        lines.append("")
    latest = summary.get("latest_event")
    if latest:
        lines.append(f"Latest event: [{latest['event_type']}] by {latest['actor']}")
        lines.append(f"  {latest['message']}")
        lines.append(f"  At: {latest['created_at']}")
    else:
        lines.append("(no latest event)")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Policy inspector
# ---------------------------------------------------------------------------


def inspect_policy(result: PolicyCheckResult) -> dict[str, Any]:
    return {
        "overall_status": result.overall_status,
        "passed_count": result.passed_count,
        "failure_count": result.failed_count,
        "warning_count": result.warning_count,
        "check_count": len(result.checks),
        "checks": [
            {
                "check_id": c.check_id,
                "name": c.name,
                "passed": c.passed,
                "severity": c.severity,
                "message": c.message,
                "recommendation": c.recommendation,
            }
            for c in result.checks
        ],
        "created_at": result.created_at,
    }


def render_policy(summary: dict[str, Any]) -> str:
    lines: list[str] = ["# Policy Check", ""]
    tag = summary.get("overall_status", "unknown").upper()
    status_display = {"ok": "PASS", "warn": "WARN", "fail": "FAIL"}.get(tag, tag)
    lines.append(f"Overall: {status_display}")
    lines.append(f"Passed: {summary.get('passed_count', 0)} / {summary.get('check_count', 0)}")
    if summary.get("failure_count"):
        lines.append(f"Failures: {summary.get('failure_count', 0)}")
    if summary.get("warning_count"):
        lines.append(f"Warnings: {summary.get('warning_count', 0)}")
    lines.append("")
    checks = summary.get("checks", [])
    if checks:
        lines.append("Checks:")
        lines.append("")
        for c in checks:
            status_icon = "PASS" if c["passed"] else "FAIL"
            sev_tag = f"[{c['severity'].upper()}]" if not c["passed"] else ""
            lines.append(f"- [{status_icon}] {c['name']} {sev_tag}")
            lines.append(f"  {c['message']}")
            if c.get("recommendation"):
                lines.append(f"  Hint: {c['recommendation']}")
        lines.append("")
    lines.append(f"Run at: {summary.get('created_at', 'unknown')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Approval inspector
# ---------------------------------------------------------------------------


def inspect_approvals(requests: list[ApprovalRequest]) -> dict[str, Any]:
    return {
        "total": len(requests),
        "by_status": _count_by(requests, "status"),
        "requests": [
            {
                "approval_id": r.approval_id,
                "reason": r.reason,
                "status": r.status,
                "requested_by": r.requested_by,
                "created_at": r.created_at,
                "resolved_at": r.resolved_at,
            }
            for r in requests
        ],
    }


def render_approvals(summary: dict[str, Any]) -> str:
    lines: list[str] = ["# Approval Requests", ""]
    lines.append(f"Total: {summary.get('total', 0)}")
    by_status = summary.get("by_status", {})
    if by_status:
        lines.append("By status:")
        for s, c in sorted(by_status.items()):
            lines.append(f"- {s}: {c}")
        lines.append("")
    requests = summary.get("requests", [])
    if requests:
        lines.append("Requests:")
        lines.append("")
        for r in requests:
            tag = f"`[{r['status']}]`"
            lines.append(f"- {tag} **{r['approval_id']}** — {r['reason']}")
            lines.append(f"  By: {r['requested_by']} at {r['created_at']}")
            if r.get("resolved_at"):
                lines.append(f"  Resolved: {r['resolved_at']}")
        lines.append("")
    else:
        lines.append("(no approval requests)")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _count_by(items: list[Any], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        val = getattr(item, attr, None)
        key = str(val) if val is not None else "(none)"
        counts[key] = counts.get(key, 0) + 1
    return counts
