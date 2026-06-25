"""CLI sub-commands for v1.2 Security, Governance, and Audit.

All commands are deterministic, local-only, and require no external services.
Heavy imports are deferred inside command functions so CLI import stays fast.
"""

from __future__ import annotations

import json
from typing import Any

import typer
from rich.console import Console

# ---------------------------------------------------------------------------
# Sub-apps for security and approval commands
# ---------------------------------------------------------------------------

security_app = typer.Typer(
    name="security",
    help="Security, governance, and audit utilities.",
    no_args_is_help=True,
)

approval_app = typer.Typer(
    name="approval",
    help="Local approval-request workflow.",
    no_args_is_help=True,
)

console = Console()


# ---------------------------------------------------------------------------
# Security commands
# ---------------------------------------------------------------------------


def _to_jsonable(value: Any) -> Any:
    """Convert Pydantic models and nested structures to JSON-safe dicts."""
    from pydantic import BaseModel  # noqa: PLC0415

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


@security_app.command("scan-secrets")
def _cmd_scan_secrets(
    path: str = typer.Option(
        ".",
        "--path",
        help="Root path to scan for secrets.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Scan local files for obvious secrets and credentials."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_secret_scan,
        render_secret_scan,
    )
    from decision_system.security.secret_scan import (  # noqa: PLC0415
        scan_repo,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_secret_scan,
    )

    result = scan_repo(path)
    save_secret_scan(result)
    append_event(
        "secret_scan_run",
        f"Scanned {result.files_scanned} files; {len(result.findings)} findings ({result.overall_status})",
        metadata={
            "files_scanned": result.files_scanned,
            "files_skipped": result.files_skipped,
            "findings_count": len(result.findings),
            "status": result.overall_status,
        },
    )
    if json_output:
        payload = inspect_secret_scan(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_secret_scan(inspect_secret_scan(result)))


@security_app.command("redact-preview")
def _cmd_redact_preview(
    text: str = typer.Argument(..., help="Text to preview redacted."),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Preview PII / secret redactions without modifying any file."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_redaction,
        render_redaction,
    )
    from decision_system.security.redaction import (  # noqa: PLC0415
        redact,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_redaction_result,
    )

    result = redact(text)
    save_redaction_result(result)
    append_event(
        "redact_preview",
        f"Redacted {result.finding_count} spans in preview text",
        metadata={"finding_count": result.finding_count},
    )
    if json_output:
        payload = inspect_redaction(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_redaction(inspect_redaction(result)))


@security_app.command("audit-log")
def _cmd_audit_log(
    limit: int = typer.Option(
        20,
        "--limit",
        help="Maximum events to display.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Inspect the local JSONL audit log."""
    from decision_system.security.audit import (  # noqa: PLC0415
        load_events,
        render_audit_log,
    )

    events = load_events(limit=limit)
    if json_output:
        from decision_system.security.inspector import (  # noqa: PLC0415
            inspect_audit_log,
        )

        payload = inspect_audit_log(events)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_audit_log(events, limit=limit))


@security_app.command("policy-check")
def _cmd_policy_check(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Run deterministic policy checks against the repo layout."""
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_policy,
        render_policy,
    )
    from decision_system.security.policy import (  # noqa: PLC0415
        run_policy_checks,
    )
    from decision_system.security.store import (  # noqa: PLC0415
        save_policy_result,
    )

    result = run_policy_checks()
    save_policy_result(result)
    append_event(
        "policy_check_run",
        f"Policy check: {result.overall_status.upper()} "
        f"({result.passed_count}/{len(result.checks)} passed)",
        metadata={
            "passed": result.passed_count,
            "failed": result.failed_count,
            "warnings": result.warning_count,
            "status": result.overall_status,
        },
    )
    if json_output:
        payload = inspect_policy(result)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_policy(inspect_policy(result)))
    if result.overall_status == "fail":
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Approval commands
# ---------------------------------------------------------------------------


@approval_app.command("request")
def _cmd_approval_request(
    reason: str = typer.Option(
        "user-requested operation",
        "--reason",
        help="Why this approval is needed.",
    ),
    requested_by: str = typer.Option(
        "local-user",
        "--requested-by",
        help="Identity of the requester (no real auth yet).",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Create a new local approval-request record."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        create_approval,
    )
    from decision_system.security.audit import append_event  # noqa: PLC0415
    from decision_system.security.store import (  # noqa: PLC0415
        save_approval_request,
    )

    request = create_approval(reason, requested_by=requested_by)
    save_approval_request(request)
    append_event(
        "approval_created",
        f"Approval {request.approval_id} created by {requested_by}: {reason}",
        metadata={
            "approval_id": request.approval_id,
            "status": request.status,
            "reason": reason[:200],
        },
    )
    if json_output:
        typer.echo(json.dumps(request.model_dump(mode="json"), indent=2))
    else:
        console.print(
            f"Created approval request: {request.approval_id}\n"
            f"Reason: {reason}\n"
            f"Requested by: {requested_by}\n"
            f"Status: {request.status}\n"
            f"Created: {request.created_at}"
        )


@approval_app.command("list")
def _cmd_approval_list(
    status: str = typer.Option(
        "pending",
        "--status",
        help="Filter by status: pending, approved, rejected, cancelled.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """List local approval-request records."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        list_approvals,
    )
    from decision_system.security.inspector import (  # noqa: PLC0415
        inspect_approvals,
        render_approvals,
    )

    filter_val: str | None = status if status else None
    requests = list_approvals(status_filter=filter_val)
    if json_output:
        payload = inspect_approvals(requests)
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print(render_approvals(inspect_approvals(requests)))


@approval_app.command("inspect")
def _cmd_approval_inspect(
    approval_id: str = typer.Argument(
        ...,
        help="ID of the approval request to inspect.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit structured JSON instead of Markdown.",
    ),
) -> None:
    """Inspect a single local approval-request record."""
    from decision_system.security.approvals import (  # noqa: PLC0415
        inspect_approval,
    )

    request = inspect_approval(approval_id)
    if request is None:
        console.print(f"[red]Approval request not found: {approval_id}[/red]")
        raise typer.Exit(code=1)
    if json_output:
        typer.echo(json.dumps(request.model_dump(mode="json"), indent=2))
    else:
        console.print(f"ID:       {request.approval_id}")
        console.print(f"Reason:   {request.reason}")
        console.print(f"Status:   {request.status}")
        console.print(f"By:       {request.requested_by}")
        console.print(f"Created:  {request.created_at}")
        console.print(f"Resolved: {request.resolved_at or '(active)'}")
        if request.metadata:
            console.print("Metadata:")
            for k, v in request.metadata.items():
                console.print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# Registration helper (called from cli.py)
# ---------------------------------------------------------------------------


def register_security_commands(main_app: typer.Typer) -> None:
    """Attach security and approval sub-apps to the main CLI."""
    main_app.add_typer(security_app)
    main_app.add_typer(approval_app)
