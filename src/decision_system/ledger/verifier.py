"""Deterministic claim verifier for v0.1.

The verifier checks that cited evidence exists and marks explicit contradiction
markers. It is intentionally conservative and does not perform semantic truth
checking yet.
"""

from decision_system.models import Claim, EvidenceChunk, VerificationResult

# v0.1 uses an explicit marker so contradiction behavior is deterministic in
# tests and smoke runs before a semantic verifier exists.
CONTRADICTION_MARKER = "CONTRADICTS:"


def verify_claims(
    claims: list[Claim],
    evidence: list[EvidenceChunk],
) -> tuple[list[Claim], list[VerificationResult]]:
    """Verify claims against retrieved evidence.

    Args:
        claims: Claims extracted from analyst memos.
        evidence: Retrieved evidence chunks available to the workflow.

    Returns:
        Updated claims plus verification results.

    v0.1 limitations:
        Claims without valid citations are unsupported. Claims citing chunks
        containing `CONTRADICTS:` are contradicted. Other cited claims are
        marked verified.
    """

    evidence_by_id = {chunk.evidence_id: chunk for chunk in evidence}
    updated_claims: list[Claim] = []
    results: list[VerificationResult] = []

    for claim in claims:
        cited_evidence = [
            evidence_by_id[evidence_id]
            for evidence_id in claim.evidence_ids
            if evidence_id in evidence_by_id
        ]

        if not cited_evidence:
            updated = claim.model_copy(
                update={
                    "status": "unsupported",
                    "confidence": "low",
                    "verification_notes": "No cited evidence was found for this claim.",
                }
            )
            result = VerificationResult(
                claim_id=claim.claim_id,
                status="unsupported",
                evidence_ids=[],
                confidence="low",
                verification_notes=updated.verification_notes,
            )
        else:
            contradicting_ids = [
                chunk.evidence_id for chunk in cited_evidence if CONTRADICTION_MARKER in chunk.text
            ]
            if contradicting_ids:
                updated = claim.model_copy(
                    update={
                        "status": "contradicted",
                        "confidence": "high",
                        "contradicting_evidence_ids": contradicting_ids,
                        "verification_notes": "Cited evidence explicitly contradicts this claim.",
                    }
                )
                result = VerificationResult(
                    claim_id=claim.claim_id,
                    status="contradicted",
                    evidence_ids=claim.evidence_ids,
                    contradicting_evidence_ids=contradicting_ids,
                    confidence="high",
                    verification_notes=updated.verification_notes,
                )
            else:
                valid_ids = [chunk.evidence_id for chunk in cited_evidence]
                updated = claim.model_copy(
                    update={
                        "status": "verified",
                        "confidence": "high",
                        "evidence_ids": valid_ids,
                        "verification_notes": "Cited evidence supports this claim.",
                    }
                )
                result = VerificationResult(
                    claim_id=claim.claim_id,
                    status="verified",
                    evidence_ids=valid_ids,
                    confidence="high",
                    verification_notes=updated.verification_notes,
                )

        updated_claims.append(updated)
        results.append(result)

    return updated_claims, results
