"""CLI command for v1.5 Enterprise Readiness assessment.

Provides an honest, mostly-static gap analysis distinguishing prototype-ready
from enterprise-ready from production-ready. No external calls or real provider
keys required.
"""

from __future__ import annotations

import json

import typer
from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# Core command logic
# ---------------------------------------------------------------------------


def _cmd_enterprise_readiness(json_output: bool = False) -> None:
    """Honest assessment of enterprise/production readiness."""
    from decision_system import __version__  # noqa: PLC0415

    readiness_level = "prototype-ready"
    passed_items: list[str] = []
    missing_items: list[dict[str, str]] = []

    checks = [
        ("Bounded decision workflow with claim ledger", True, "", ""),
        ("Local document indexing and retrieval", True, "", ""),
        ("Local data catalog, profiling, and ontology mapping", True, "", ""),
        ("Deterministic insight and pattern detection", True, "", ""),
        ("War-room simulation with judge/verifier", True, "", ""),
        ("Local FastAPI backend", True, "", ""),
        ("Provider evaluation harness", True, "", ""),
        ("Secret scanning and redaction preview", True, "", ""),
        ("Policy checks and audit logging", True, "", ""),
        ("Approval request workflow (record-only)", True, "", ""),
        ("Metrics, eval history, quality reports", True, "", ""),
        ("Docker packaging for local deployment", True, "", ""),
        ("Real authentication (JWT/OAuth)", False, "critical",
         "No auth implemented. All operations run as local-user."),
        ("Role-based access control", False, "critical",
         "No RBAC. All local users have full access."),
        ("Tenant isolation", False, "critical",
         "No multi-tenant boundaries."),
        ("Secrets vault", False, "critical",
         "Secrets stored in env vars or .env files only."),
        ("Audit log retention policy", False, "high",
         "JSONL log rotated locally, no retention policy."),
        ("Compliance controls (SOC 2, GDPR, HIPAA)", False, "high",
         "No compliance controls implemented."),
        ("Production connector approvals", False, "high",
         "Only local-files is real; others are stubs."),
        ("Deployment hardening (TLS, rate limiting)", False, "high",
         "No TLS or rate limiting."),
        ("Database persistence", False, "medium",
         "Chroma + JSON files, no RDBMS durability."),
        ("Encrypted storage at rest", False, "medium",
         "All data stored unencrypted locally."),
        ("API input sanitization", False, "medium",
         "Basic Pydantic validation only."),
    ]

    for check in checks:
        if check[1]:
            passed_items.append(check[0])
        else:
            missing_items.append({
                "gap": check[0],
                "severity": check[2] if len(check) > 2 else "medium",
                "notes": check[3] if len(check) > 3 else "",
            })

    if json_output:
        payload = {
            "version": __version__,
            "readiness_level": readiness_level,
            "prototype_ready": True,
            "enterprise_ready": False,
            "production_ready": False,
            "passed_count": len(passed_items),
            "missing_count": len(missing_items),
            "missing_items": missing_items,
        }
        typer.echo(json.dumps(payload, indent=2))
    else:
        console.print("# Enterprise Readiness Assessment")
        console.print("")
        console.print(f"Version: {__version__}")
        console.print(f"Readiness Level: **{readiness_level.upper()}**")
        console.print("")
        console.print("Prototype-Ready: YES")
        console.print("Enterprise-Ready: NO")
        console.print("Production-Ready: NO")
        console.print("")
        console.print(f"## What Works ({len(passed_items)})")
        for item in passed_items:
            console.print(f"  [x] {item}")
        console.print("")
        console.print(f"## What Is Missing ({len(missing_items)})")
        for item in missing_items:
            console.print(
                f"  [ ] {item['gap']} ({item['severity'].upper()})"
            )
            if item["notes"]:
                console.print(f"      {item['notes']}")


# ---------------------------------------------------------------------------
# Registration helper (called from cli.py)
# ---------------------------------------------------------------------------


def register_enterprise_commands(main_app: typer.Typer) -> None:
    """Attach enterprise-readiness command to the main CLI."""

    @main_app.command("enterprise-readiness")
    def _top_enterprise_readiness(
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit JSON readiness report.",
        ),
    ) -> None:
        """Honest assessment of enterprise/production readiness."""
        _cmd_enterprise_readiness(json_output=json_output)
