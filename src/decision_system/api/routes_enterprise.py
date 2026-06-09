"""Enterprise readiness assessment API endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from decision_system import __version__

router = APIRouter(tags=["enterprise"])


@router.get("/enterprise-readiness")
def get_enterprise_readiness() -> dict[str, Any]:
    """Return a static enterprise readiness assessment."""
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
        ("All tests pass offline with no API keys", True, "", ""),
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

    return {
        "version": __version__,
        "readiness_level": "prototype-ready",
        "prototype_ready": True,
        "enterprise_ready": False,
        "production_ready": False,
        "passed_count": len(passed_items),
        "missing_count": len(missing_items),
        "passed_items": passed_items,
        "missing_items": missing_items,
    }
