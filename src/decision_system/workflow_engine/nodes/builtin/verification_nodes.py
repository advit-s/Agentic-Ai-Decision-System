"""Verification workflow nodes for trust workflows.

Provides:
- ClaimVerifierNode: Verify claims against workspace evidence
- ContradictionScanNode: Scan evidence for contradictions
- VerificationSummaryNode: Generate verification summary for execution
"""

from __future__ import annotations

from decision_system.verification.service import VerificationService
from decision_system.workflow_engine.models import (
    WorkflowNode,
    ExecutionContext,
)


class ClaimVerifierNode(WorkflowNode):
    """Verifies claims against workspace evidence.

    Inputs:
        workspace_id (str): Workspace to search for evidence.
        execution_id (str, optional): Execution to verify claims for.
        claim_ids (list[str], optional): Specific claim IDs to verify.

    Outputs:
        verified_claims (list): Verification results for each claim.
        verification_summary (dict): Summary of verification results.
        warnings (list): Any warnings from verification.
    """

    type: str = "decision_system.verify_claims_v2"
    label: str = "Claim Verifier v2"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "")
        execution_id = inputs.get("execution_id") or self.config.get("execution_id", "")
        claim_ids = inputs.get("claim_ids") or self.config.get("claim_ids", [])

        if not workspace_id:
            return {
                "error": "workspace_id is required",
                "verified_claims": [],
                "verification_summary": {},
                "warnings": ["workspace_id is required"],
            }

        service = VerificationService()
        results = []

        if claim_ids:
            # Verify specific claims by ID
            for cid in claim_ids:
                result = service.verify_claim_by_id(cid, workspace_id=workspace_id)
                if result:
                    verification, quality = result
                    results.append({
                        "claim_id": cid,
                        "status": verification.status,
                        "confidence": verification.confidence,
                        "verification_notes": verification.verification_notes,
                        "verification_method": verification.verification_method,
                        "evidence_quality": quality.quality_label,
                        "evidence_ids": verification.evidence_ids,
                        "evidence_snippets": verification.evidence_snippets,
                        "contradicting_evidence_ids": verification.contradicting_evidence_ids,
                    })
        elif execution_id:
            # Verify all claims for an execution
            pairs = service.verify_execution_claims(execution_id, workspace_id=workspace_id)
            for verification, quality in pairs:
                results.append({
                    "claim_id": verification.claim_id,
                    "status": verification.status,
                    "confidence": verification.confidence,
                    "verification_notes": verification.verification_notes,
                    "verification_method": verification.verification_method,
                    "evidence_quality": quality.quality_label,
                    "evidence_ids": verification.evidence_ids,
                    "evidence_snippets": verification.evidence_snippets,
                    "contradicting_evidence_ids": verification.contradicting_evidence_ids,
                })
        else:
            # Verify all workspace claims
            pairs = service.verify_workspace_claims(workspace_id)
            for verification, quality in pairs:
                results.append({
                    "claim_id": verification.claim_id,
                    "status": verification.status,
                    "confidence": verification.confidence,
                    "verification_notes": verification.verification_notes,
                    "verification_method": verification.verification_method,
                    "evidence_quality": quality.quality_label,
                    "evidence_ids": verification.evidence_ids,
                    "evidence_snippets": verification.evidence_snippets,
                    "contradicting_evidence_ids": verification.contradicting_evidence_ids,
                })

        summary = service.get_verification_summary(
            workspace_id=workspace_id, execution_id=execution_id
        )

        # Emit audit event
        try:
            from decision_system.workflow_engine.engine.events import EventBus
            bus = EventBus()
            bus.emit(
                event_type="claim_verified",
                execution_id=ctx.execution_id or execution_id,
                data={
                    "workspace_id": workspace_id,
                    "claims_verified": len(results),
                    "summary": summary.model_dump(mode="json"),
                },
            )
        except Exception:
            pass

        return {
            "verified_claims": results,
            "verification_summary": summary.model_dump(mode="json"),
            "warnings": [],
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "title": "Workspace ID"},
                "execution_id": {"type": "string", "title": "Execution ID"},
                "claim_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "title": "Claim IDs",
                },
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "execution_id": {"type": "string"},
                "claim_ids": {"type": "array", "items": {"type": "string"}},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "verified_claims": {"type": "array"},
                "verification_summary": {"type": "object"},
                "warnings": {"type": "array"},
                "error": {"type": "string"},
            },
        }


class ContradictionScanNode(WorkflowNode):
    """Scans workspace evidence for contradictions.

    Inputs:
        workspace_id (str): Workspace to scan.
        claim_id (str, optional): Specific claim to check contradictions for.

    Outputs:
        contradictions (list): Detected contradictions.
        contradiction_count (int): Number of contradictions found.
    """

    type: str = "decision_system.contradiction_scan"
    label: str = "Contradiction Scan"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "")
        claim_id = inputs.get("claim_id") or self.config.get("claim_id", "")

        if not workspace_id:
            return {
                "error": "workspace_id is required",
                "contradictions": [],
                "contradiction_count": 0,
            }

        service = VerificationService()

        if claim_id:
            contradictions = service.scan_claim_contradictions(claim_id, workspace_id=workspace_id)
        else:
            contradictions = service.scan_workspace_contradictions(workspace_id)

        # Emit audit event
        try:
            from decision_system.workflow_engine.engine.events import EventBus
            bus = EventBus()
            bus.emit(
                event_type="contradiction_scan_run",
                execution_id=ctx.execution_id or "",
                data={
                    "workspace_id": workspace_id,
                    "contradiction_count": len(contradictions),
                },
            )
        except Exception:
            pass

        return {
            "contradictions": [c.model_dump(mode="json") for c in contradictions],
            "contradiction_count": len(contradictions),
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "title": "Workspace ID"},
                "claim_id": {"type": "string", "title": "Claim ID"},
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "claim_id": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "contradictions": {"type": "array"},
                "contradiction_count": {"type": "integer"},
                "error": {"type": "string"},
            },
        }


class VerificationSummaryNode(WorkflowNode):
    """Generates verification summary for execution or workspace.

    Inputs:
        workspace_id (str): Workspace to summarize.
        execution_id (str, optional): Execution to summarize.

    Outputs:
        verification_summary (dict): Summary with counts and scores.
        warnings (list): Any warnings.
    """

    type: str = "decision_system.verification_summary"
    label: str = "Verification Summary"

    async def execute(self, inputs: dict, ctx: ExecutionContext) -> dict:
        workspace_id = inputs.get("workspace_id") or self.config.get("workspace_id", "")
        execution_id = inputs.get("execution_id") or self.config.get("execution_id", "")

        if not workspace_id and not execution_id:
            return {
                "error": "workspace_id or execution_id is required",
                "verification_summary": {},
                "warnings": ["No workspace or execution specified"],
            }

        service = VerificationService()
        summary = service.get_verification_summary(
            workspace_id=workspace_id or None,
            execution_id=execution_id or None,
        )

        return {
            "verification_summary": summary.model_dump(mode="json"),
            "warnings": [],
        }

    @classmethod
    def get_config_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string", "title": "Workspace ID"},
                "execution_id": {"type": "string", "title": "Execution ID"},
            },
        }

    @classmethod
    def get_input_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "string"},
                "execution_id": {"type": "string"},
            },
        }

    @classmethod
    def get_output_schema(cls) -> dict:
        return {
            "type": "object",
            "properties": {
                "verification_summary": {"type": "object"},
                "warnings": {"type": "array"},
                "error": {"type": "string"},
            },
        }
