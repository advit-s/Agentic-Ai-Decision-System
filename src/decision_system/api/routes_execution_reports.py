"""Execution report endpoints — generate, list, and export reports from execution evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from decision_system.api.models import api_error
from decision_system.security.audit import append_event
from decision_system.observability.metrics import MetricsCollector, MetricType

router = APIRouter(tags=["execution-reports"])


class ReportExportRequest(BaseModel):
    format: str = "markdown"


def _get_execution_store_path() -> Path:
    """Get the execution store path."""
    return Path(".decision_system") / "workflow_engine"


def _find_execution(execution_id: str) -> dict[str, Any] | None:
    """Load execution data from JSON store."""
    exec_dir = _get_execution_store_path() / "executions"
    exec_file = exec_dir / f"{execution_id}.json"
    if not exec_file.exists():
        return None
    try:
        return json.loads(exec_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _load_claims_for_execution(execution_id: str) -> list[dict[str, Any]]:
    """Load claims linked to an execution."""
    try:
        from decision_system.workflow_engine.stores.claim_store import JSONClaimStore
        store = JSONClaimStore(Path(".decision_system"))
        claims = store.list(execution_id=execution_id)
        return [c.model_dump(mode="json") for c in claims]
    except Exception:
        return []


def _generate_report_data(
    execution: dict[str, Any],
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate report data from execution and claims."""
    execution_id = execution.get("execution_id", "")
    workflow_id = execution.get("workflow_id", "")
    workspace_id = execution.get("workspace_id", "")
    status = execution.get("status", "unknown")

    # Gather evidence references from claims
    evidence_ids: list[str] = []
    evidence_snippets: list[str] = []
    source_ids: list[str] = []

    for c in claims:
        for eid in c.get("evidence_ids", []):
            if eid not in evidence_ids:
                evidence_ids.append(eid)
        for snippet in c.get("evidence_snippets", []):
            if snippet not in evidence_snippets:
                evidence_snippets.append(snippet)
        for sid in c.get("source_ids", []):
            if sid not in source_ids:
                source_ids.append(sid)

    # Get event timeline
    events = execution.get("events", [])
    timeline_summary = [
        {
            "event_type": e.get("event_type", e.get("type", "unknown")),
            "timestamp": e.get("timestamp", e.get("created_at", "")),
            "data": e.get("data", {}),
        }
        for e in events
    ]

    # Build report
    report_data: dict[str, Any] = {
        "report_id": str(uuid4()),
        "workspace_id": workspace_id,
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": f"Report for execution {execution_id} of workflow {workflow_id}",
        "workflow_status": status,
        "claims": claims,
        "claim_statuses": {},
        "evidence_references": {
            "evidence_ids": evidence_ids,
            "source_ids": source_ids,
            "evidence_snippets": evidence_snippets,
        },
        "event_timeline_summary": timeline_summary,
        "warnings": [],
    }

    # Claim status summary
    for c in claims:
        cid = c.get("claim_id", "")
        cstatus = c.get("status", "unknown")
        report_data["claim_statuses"][cid] = cstatus

    if not evidence_ids and not evidence_snippets:
        report_data["warnings"].append("No evidence references found in claims")

    return report_data


def _save_report(workspace_id: str, report_data: dict[str, Any]) -> Path:
    """Save report locally under .decision_system/reports/{workspace_id}/."""
    reports_dir = Path(".decision_system") / "reports" / workspace_id
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_path = reports_dir / f"{report_data['report_id']}.json"
    report_path.write_text(
        json.dumps(report_data, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return report_path


def _export_markdown(report_data: dict[str, Any]) -> str:
    """Render report as Markdown with evidence references."""
    lines = [
        "# Execution Report",
        "",
        f"**Generated:** {report_data['created_at']}",
        f"**Workspace:** {report_data['workspace_id']}",
        f"**Execution:** {report_data['execution_id']}",
        f"**Workflow:** {report_data['workflow_id']}",
        f"**Status:** {report_data['workflow_status']}",
        "",
        "## Summary",
        "",
        report_data["summary"],
        "",
    ]

    # Claims section
    claims = report_data.get("claims", [])
    lines.extend([
        "## Claims",
        "",
        f"Total claims: {len(claims)}",
        "",
    ])

    for c in claims:
        status_icon = {
            "supported": "✓",
            "verified": "✓",
            "unsupported": "✗",
            "contradicted": "⚡",
            "pending": "?",
        }.get(c.get("status", ""), "?")
        lines.append(f"### {status_icon} {c.get('claim_text', '(no text)')}")
        lines.append(f"- **Status:** {c.get('status', 'unknown')}")
        lines.append(f"- **Confidence:** {c.get('confidence', 'unknown')}")
        lines.append(f"- **Source:** {c.get('source_agent', 'unknown')}")

        evidence_ids = c.get("evidence_ids", [])
        if evidence_ids:
            lines.append(f"- **Evidence IDs:** {', '.join(evidence_ids)}")

        snippets = c.get("evidence_snippets", [])
        for s in snippets:
            lines.append(f"  > {s}")
        lines.append("")

    # Evidence references
    evidence_refs = report_data.get("evidence_references", {})
    if evidence_refs.get("evidence_ids") or evidence_refs.get("evidence_snippets"):
        lines.extend(["## Evidence References", ""])
        for eid in evidence_refs.get("evidence_ids", []):
            lines.append(f"- `{eid}`")
        for ref in evidence_refs.get("source_ids", []):
            lines.append(f"- Source: `{ref}`")
        for snippet in evidence_refs.get("evidence_snippets", []):
            lines.append(f"> {snippet}")
        lines.append("")

    # Event timeline
    timeline = report_data.get("event_timeline_summary", [])
    if timeline:
        lines.extend(["## Event Timeline", ""])
        for event in timeline:
            lines.append(f"- **{event.get('event_type', 'event')}** at {event.get('timestamp', '?')}")
        lines.append("")

    # Warnings
    warnings = report_data.get("warnings", [])
    if warnings:
        lines.extend(["## Warnings", ""])
        for w in warnings:
            lines.append(f"- ⚠ {w}")
        lines.append("")

    return "\n".join(lines)


@router.post("/executions/{execution_id}/report")
def generate_execution_report(execution_id: str) -> dict[str, Any]:
    """Generate a report from a workflow execution with evidence references.

    Report is saved locally under .decision_system/reports/{workspace_id}/.
    """
    execution = _find_execution(execution_id)
    if execution is None:
        raise api_error(404, "execution_not_found", f"Execution {execution_id} not found")

    workspace_id = execution.get("workspace_id", "")
    if not workspace_id:
        raise api_error(400, "missing_workspace", "Execution has no workspace_id")

    claims = _load_claims_for_execution(execution_id)
    report_data = _generate_report_data(execution, claims)
    saved_path = _save_report(workspace_id, report_data)

    # Emit audit event
    try:
        append_event("trust_report_generated", f"Trust report {report_data['report_id']} generated for execution {execution_id}", metadata={
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "report_id": report_data["report_id"],
            "claim_count": len(claims),
        })
    except Exception:
        pass
    try:
        _emit_audit_event("report_generated", {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "report_id": report_data["report_id"],
            "claim_count": len(claims),
        })
    except Exception:
        pass

    try:
        collector = MetricsCollector()
        collector.record("trust_report_generation_duration_ms", 0, MetricType.TIMER, {
            "execution_id": execution_id,
            "workspace_id": workspace_id,
            "report_id": report_data["report_id"],
            "claim_count": str(len(claims)),
        })
        collector.record("claims_verified_count", len(claims), MetricType.COUNTER, {
            "action": "report_generated",
            "execution_id": execution_id,
        })
    except Exception:
        pass

    return {
        "status": "ok",
        "report": report_data,
        "saved_path": str(saved_path),
    }


@router.get("/workspaces/{workspace_id}/reports")
def list_workspace_reports(workspace_id: str) -> dict[str, Any]:
    """List all reports in a workspace."""
    reports_dir = Path(".decision_system") / "reports" / workspace_id
    if not reports_dir.exists():
        return {"workspace_id": workspace_id, "reports": [], "count": 0}

    reports: list[dict[str, Any]] = []
    for f in sorted(reports_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            reports.append({
                "report_id": data.get("report_id", f.stem),
                "execution_id": data.get("execution_id", ""),
                "workflow_id": data.get("workflow_id", ""),
                "created_at": data.get("created_at", ""),
                "claim_count": len(data.get("claims", [])),
            })
        except (json.JSONDecodeError, OSError):
            continue

    return {
        "workspace_id": workspace_id,
        "reports": reports,
        "count": len(reports),
    }


@router.get("/reports/{report_id}")
def get_report(report_id: str, workspace_id: str | None = Query(None)) -> dict[str, Any]:
    """Get a report by ID, optionally scoped to a workspace."""
    if workspace_id:
        search_dirs = [Path(".decision_system") / "reports" / workspace_id]
    else:
        search_dirs = list(Path(".decision_system").glob("reports/*/"))

    for reports_dir in search_dirs:
        if not reports_dir.exists():
            continue
        report_file = reports_dir / f"{report_id}.json"
        if report_file.exists():
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
                return {"status": "ok", "report": data}
            except (json.JSONDecodeError, OSError):
                continue

    raise api_error(404, "report_not_found", f"Report {report_id} not found")


@router.get("/reports/{report_id}/export")
def export_report(
    report_id: str,
    format: str = Query("markdown", alias="format"),
    workspace_id: str | None = Query(None),
) -> dict[str, Any]:
    """Export a report in markdown or json format."""
    # Find the report
    result = get_report(report_id, workspace_id)
    report_data = result["report"]

    if format == "markdown":
        content = _export_markdown(report_data)
    elif format == "json":
        content = json.dumps(report_data, indent=2, default=str)
    else:
        raise api_error(400, "invalid_format", f"Unsupported format: {format}")

    # Emit audit event
    try:
        append_event("trust_report_exported", f"Trust report {report_id} exported as {format}", metadata={
            "report_id": report_id,
            "workspace_id": report_data.get("workspace_id", ""),
            "format": format,
        })
    except Exception:
        pass
    try:
        _emit_audit_event("report_exported", {
            "report_id": report_id,
            "workspace_id": report_data.get("workspace_id", ""),
            "format": format,
        })
    except Exception:
        pass

    return {
        "format": format,
        "content": content,
        "report_id": report_id,
    }


def _emit_audit_event(event_type: str, data: dict[str, Any]) -> None:
    """Emit an audit event for observability."""
    try:
        from decision_system.observability.store import record_metric_point
        record_metric_point(
            name=f"audit.{event_type}",
            value=1.0,
            tags=data,
        )
    except Exception:
        pass
