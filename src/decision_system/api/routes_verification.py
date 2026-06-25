"""Verification API endpoints for claims, contradictions, and trust scoring."""

from __future__ import annotations

from pathlib import Path
from decision_system._data_root import get_data_root

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import (
    require_permission,
    require_workspace_permission,
)
from decision_system.api.models import ApiError, ErrorResponse
from decision_system.models import (
    Claim,
    ContradictionRecord,
    EvidenceQuality,
    VerificationResult,
    VerificationSummary,
)
from decision_system.workflow_engine.stores.claim_store import JSONClaimStore
from decision_system.verification.service import VerificationService
from decision_system.security.audit import append_event
from decision_system.observability.metrics import MetricsCollector, MetricType

router = APIRouter(tags=["verification"])


def _get_claim_store() -> JSONClaimStore | None:
    """Get the default claim store from config."""
    try:
        from decision_system.config import load_settings
        settings = load_settings()
        store_dir = Path(settings.store_dir) if settings.store_dir else get_data_root()
        return JSONClaimStore(store_dir=store_dir)
    except Exception:
        return None


def _get_verification_service() -> VerificationService:
    """Get a verification service instance."""
    store = _get_claim_store()
    return VerificationService(claim_store=store)


def _record_verification_metrics(metrics_collector, claim_results, duration_ms=0):
    """Record observability metrics for verification actions."""
    try:
        collector = metrics_collector or MetricsCollector()
        total = len(claim_results)
        contradicted = sum(1 for r in claim_results if r.get("status") == "contradicted")
        unsupported = sum(1 for r in claim_results if r.get("status") == "unsupported")
        uncertain = sum(1 for r in claim_results if r.get("status") == "uncertain")
        needs_review = sum(1 for r in claim_results if r.get("status") == "needs_review")

        collector.record("verification_duration_ms", duration_ms, MetricType.TIMER)
        collector.record("claims_verified_count", total, MetricType.COUNTER, {"action": "verify"})
        collector.record("contradictions_found_count", contradicted, MetricType.COUNTER)
        collector.record("unsupported_claims_count", unsupported, MetricType.COUNTER)
        collector.record("uncertain_claims_count", uncertain, MetricType.COUNTER)
        collector.record("needs_review_claims_count", needs_review, MetricType.COUNTER)

        confidences = [r.get("confidence") for r in claim_results if r.get("confidence")]
        numeric_confidences = []
        for c in confidences:
            try:
                numeric_confidences.append(float(c))
            except (ValueError, TypeError):
                pass
        if numeric_confidences:
            avg_conf = sum(numeric_confidences) / len(numeric_confidences)
            collector.record("average_confidence", avg_conf, MetricType.GAUGE)
    except Exception:
        pass


_metrics_collector = None
def _get_metrics_collector():
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


# ------------------------------------------------------------------
# Request/Response models
# ------------------------------------------------------------------


class VerifyClaimRequest(BaseModel):
    workspace_id: str | None = None


class ContradictionScanResponse(BaseModel):
    contradictions: list[dict]
    count: int


class ClaimVerificationResponse(BaseModel):
    claim_id: str
    status: str
    confidence: str
    verification_notes: str
    verification_method: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_snippets: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    evidence_quality: str | None = None
    evidence_quality_detail: dict | None = None


class VerificationSummaryResponse(BaseModel):
    summary: VerificationSummary
    claims: list[dict] = Field(default_factory=list)


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post("/claims/{claim_id}/verify")
async def verify_claim(claim_id: str, req: VerifyClaimRequest, user: LocalUser = Depends(require_permission(Permission.CLAIM_VERIFY))) -> dict:
    """Verify a single claim and update its status."""
    service = _get_verification_service()
    result = service.verify_claim_by_id(
        claim_id, workspace_id=req.workspace_id
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found")

    verification, quality = result
    try:
        append_event("claim_verified", f"Claim {claim_id} verified as {verification.status}", metadata={
            "claim_id": claim_id,
            "status": verification.status,
            "confidence": verification.confidence,
            "workspace_id": req.workspace_id or "",
        })
    except Exception:
        pass
    try:
        claim_result = [{"status": verification.status, "confidence": verification.confidence}]
        _record_verification_metrics(_get_metrics_collector(), claim_result)
    except Exception:
        pass
    return {
        "claim_id": claim_id,
        "status": verification.status,
        "confidence": verification.confidence,
        "verification_notes": verification.verification_notes,
        "verification_method": verification.verification_method,
        "evidence_ids": verification.evidence_ids,
        "evidence_snippets": verification.evidence_snippets,
        "contradicting_evidence_ids": verification.contradicting_evidence_ids,
        "evidence_quality": quality.quality_label,
        "evidence_quality_detail": quality.model_dump(mode="json"),
    }


@router.post("/executions/{execution_id}/claims/verify")
async def verify_execution_claims(
    execution_id: str, req: VerifyClaimRequest, user: LocalUser = Depends(require_permission(Permission.CLAIM_VERIFY))
) -> dict:
    """Verify all claims for an execution."""
    service = _get_verification_service()
    results = service.verify_execution_claims(
        execution_id, workspace_id=req.workspace_id
    )
    claim_results = []
    for verification, quality in results:
        claim_results.append({
            "claim_id": verification.claim_id,
            "status": verification.status,
            "confidence": verification.confidence,
            "verification_notes": verification.verification_notes,
            "verification_method": verification.verification_method,
            "evidence_ids": verification.evidence_ids,
            "evidence_snippets": verification.evidence_snippets,
            "contradicting_evidence_ids": verification.contradicting_evidence_ids,
        "evidence_quality": quality.quality_label,
        })

    try:
        append_event("execution_claims_verified", f"Verified {len(claim_results)} claims for execution {execution_id}", metadata={
            "execution_id": execution_id,
            "total": len(claim_results),
            "workspace_id": req.workspace_id or "",
        })
    except Exception:
        pass

    try:
        _record_verification_metrics(_get_metrics_collector(), claim_results)
    except Exception:
        pass

    return {
        "execution_id": execution_id,
        "total": len(claim_results),
        "claims": claim_results,
    }


@router.post("/workspaces/{workspace_id}/claims/verify")
async def verify_workspace_claims(workspace_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.CLAIM_VERIFY))) -> dict:
    """Verify all claims in a workspace."""
    service = _get_verification_service()
    results = service.verify_workspace_claims(workspace_id)
    claim_results = []
    for verification, quality in results:
        claim_results.append({
            "claim_id": verification.claim_id,
            "status": verification.status,
            "confidence": verification.confidence,
            "verification_notes": verification.verification_notes,
            "verification_method": verification.verification_method,
            "evidence_ids": verification.evidence_ids,
            "evidence_snippets": verification.evidence_snippets,
            "contradicting_evidence_ids": verification.contradicting_evidence_ids,
        "evidence_quality": quality.quality_label,
        })

    try:
        append_event("workspace_claims_verified", f"Verified {len(claim_results)} claims for workspace {workspace_id}", metadata={
            "workspace_id": workspace_id,
            "total": len(claim_results),
        })
    except Exception:
        pass

    try:
        _record_verification_metrics(_get_metrics_collector(), claim_results)
    except Exception:
        pass

    return {
        "workspace_id": workspace_id,
        "total": len(claim_results),
        "claims": claim_results,
    }


@router.get("/claims/{claim_id}/verification")
async def get_claim_verification(claim_id: str, user: LocalUser = Depends(require_permission(Permission.CLAIM_VERIFY))) -> dict:
    """Get existing verification for a claim."""
    store = _get_claim_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Claim store not available")
    claim = store.load(claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim '{claim_id}' not found")

    return {
        "claim_id": claim.claim_id,
        "status": claim.status,
        "confidence": claim.confidence,
        "verification_notes": claim.verification_notes,
        "evidence_ids": claim.evidence_ids,
        "evidence_snippets": claim.evidence_snippets,
        "contradicting_evidence_ids": claim.contradicting_evidence_ids,
        "evidence_quality": getattr(claim, "evidence_quality", None),
        "review_required": claim.review_required,
    }


@router.get("/executions/{execution_id}/verification-summary")
async def get_execution_verification_summary(execution_id: str, user: LocalUser = Depends(require_permission(Permission.CLAIM_VERIFY))) -> dict:
    """Get verification summary for an execution."""
    service = _get_verification_service()
    summary = service.get_verification_summary(execution_id=execution_id)
    return {
        "execution_id": execution_id,
        "summary": summary.model_dump(mode="json"),
    }


@router.get("/workspaces/{workspace_id}/verification-summary")
async def get_workspace_verification_summary(workspace_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.CLAIM_VERIFY))) -> dict:
    """Get verification summary for a workspace."""
    service = _get_verification_service()
    summary = service.get_verification_summary(workspace_id=workspace_id)
    return {
        "workspace_id": workspace_id,
        "summary": summary.model_dump(mode="json"),
    }


@router.post("/workspaces/{workspace_id}/contradictions/scan")
async def scan_workspace_contradictions(workspace_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.CLAIM_VERIFY))) -> ContradictionScanResponse:
    """Scan workspace evidence for contradictions."""
    service = _get_verification_service()
    contradictions = service.scan_workspace_contradictions(workspace_id)
    try:
        append_event("contradiction_scan_run", f"Scanned contradictions for workspace {workspace_id}: found {len(contradictions)}", metadata={
            "workspace_id": workspace_id,
            "count": len(contradictions),
        })
    except Exception:
        pass
    try:
        _get_metrics_collector().record("contradictions_found_count", len(contradictions), MetricType.COUNTER, {"workspace_id": workspace_id})
    except Exception:
        pass
    return ContradictionScanResponse(
        contradictions=[c.model_dump(mode="json") for c in contradictions],
        count=len(contradictions),
    )


@router.get("/workspaces/{workspace_id}/contradictions")
async def list_workspace_contradictions(workspace_id: str) -> ContradictionScanResponse:
    """List stored contradictions for a workspace."""
    # For now, scan on demand
    return await scan_workspace_contradictions(workspace_id)


@router.get("/claims/{claim_id}/contradictions")
async def get_claim_contradictions(claim_id: str) -> ContradictionScanResponse:
    """Scan for contradictions related to a claim."""
    service = _get_verification_service()
    contradictions = service.scan_claim_contradictions(claim_id)
    return ContradictionScanResponse(
        contradictions=[c.model_dump(mode="json") for c in contradictions],
        count=len(contradictions),
    )
