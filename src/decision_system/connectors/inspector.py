"""Inspector helpers for connector dry-run results, import jobs, and registry summaries."""

from __future__ import annotations

from typing import Any

from decision_system.connectors.models import (
    ConnectorDefinition,
    ConnectorDryRunResult,
    ConnectorImportJob,
)
from decision_system.connectors.registry import ConnectorRegistry


def inspect_dry_run_result(result: ConnectorDryRunResult) -> dict[str, Any]:
    """Return a structured inspection summary for a dry-run result."""
    return {
        "connector_id": result.connector_id,
        "source_path": result.source_path,
        "would_import_count": result.would_import_count,
        "files": [
            {
                "source_path": f.source_path,
                "filename": f.filename,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "target_category": f.target_category,
                "action": f.action,
                "reason": f.reason,
            }
            for f in result.files
        ],
        "skipped_files": [
            {
                "source_path": f.source_path,
                "filename": f.filename,
                "extension": f.extension,
                "reason": f.reason,
            }
            for f in result.skipped_files
        ],
        "warnings": result.warnings,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def inspect_import_job(job: ConnectorImportJob) -> dict[str, Any]:
    """Return a structured inspection summary for an import job."""
    return {
        "job_id": job.job_id,
        "connector_id": job.connector_id,
        "status": job.status,
        "source_path": job.source_path,
        "imported_count": len(job.imported_files),
        "skipped_count": len(job.skipped_files),
        "imported_files": job.imported_files,
        "skipped_files": job.skipped_files,
        "output_paths": job.output_paths,
        "warnings": job.warnings,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": (job.completed_at.isoformat() if job.completed_at else None),
    }


def render_connector_list(registry: ConnectorRegistry) -> str:
    """Render a human-readable connector list table."""
    lines: list[str] = [
        "# Connectors",
        "",
        "| ID | Name | Type | Status | Real | Import | Dry-Run |",
        "|----|------|------|--------|------|--------|---------|",
    ]
    for definition in registry.list_connectors():
        real_tag = "yes" if definition.status.value == "real" else "no"
        import_tag = "yes" if definition.supports_import else "no"
        dry_run_tag = "yes" if definition.supports_dry_run else "no"
        lines.append(
            "| {id} | {name} | {ctype} | {status} | {real} | {imp} | {dr} |".format(
                id=definition.connector_id,
                name=definition.name,
                ctype=definition.connector_type.value,
                status=definition.status.value,
                real=real_tag,
                imp=import_tag,
                dr=dry_run_tag,
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_connector_detail(definition: ConnectorDefinition) -> str:
    """Render a human-readable detail block for one connector."""
    lines = [
        "# {name} ({id})".format(name=definition.name, id=definition.connector_id),
        "",
        "- **Type:** {ctype}".format(ctype=definition.connector_type.value),
        "- **Status:** {status}".format(status=definition.status.value),
        "- **Real:** {real}".format(real="yes" if definition.status.value == "real" else "no"),
        "- **Stub:** {stub}".format(stub="yes" if definition.is_stub else "no"),
        "- **Description:** {desc}".format(desc=definition.description),
        "- **Capabilities:** {caps}".format(
            caps=", ".join(c.value for c in definition.capabilities) or "(none)"
        ),
        "- **Requires secrets:** {req}".format(req="yes" if definition.requires_secrets else "no"),
        "- **Supports dry-run:** {dr}".format(dr="yes" if definition.supports_dry_run else "no"),
        "- **Supports import:** {imp}".format(imp="yes" if definition.supports_import else "no"),
        "",
    ]
    if definition.is_stub:
        lines.append(
            "> **Note:** This connector is an offline stub and does not "
            "make network calls or require real secrets in v1.1."
        )
        lines.append("")
    return "\n".join(lines)
