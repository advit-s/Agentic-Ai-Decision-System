"""Security, governance, and audit API endpoints.

Exposes the minimal offline surface needed by the v1.1.2 UI and local
clients: policy status, redaction preview, audit log, and approval
requests.  No auth is added yet; these endpoints are development-only
and assume callers are local."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from decision_system.api.models import ApiError, api_error
from decision_system.security.audit import load_events
from decision_system.security.models import PolicyCheckResult, RedactionPreviewResult
from decision_system.security.policy import run_policy_checks
from decision_system.security.redaction import redact
from decision_system.security.store import load_audit_events as _load_audit_events_fn

router = APIRouter(tags=["security"])


class RedactPreviewRequest(BaseModel):
    text: str = ""


@router.get("/security/policy", response_model=PolicyCheckResult)
def get_security_policy() -> PolicyCheckResult:
    """Run deterministic policy checks and return the result."""
    return run_policy_checks()


@router.post("/security/redact-preview", response_model=RedactionPreviewResult)
def post_security_redact_preview(body: RedactPreviewRequest) -> RedactionPreviewResult:
    """Preview PII / secret redactions for the supplied text."""
    return redact(body.text)


@router.get("/security/audit")
def get_security_audit(limit: int | None = None) -> dict[str, Any]:
    """Return recent audit events."""
    events = _load_audit_events_fn(limit=limit)
    return {
        "events": [
            json.loads(e.model_dump_json()) if hasattr(e, "model_dump_json") else e.model_dump(mode="json")
            for e in events
        ],
        "count": len(events),
    }
