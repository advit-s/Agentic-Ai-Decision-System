"""In-memory claim ledger for one v0.1 workflow run.

The ledger records material claims before report synthesis. It is deliberately
simple and in-memory for v0.1; a durable database-backed ledger is a future
extension point.
"""

from datetime import datetime, timezone

from decision_system.models import Claim, ClaimStatus, ConfidenceLevel


class ClaimLedger:
    """Store and update claims during a single workflow run."""

    def __init__(self):
        self._claims: dict[str, Claim] = {}

    def add_claims(self, claims: list[Claim]) -> None:
        """Add claims by ID, replacing duplicates from the same run if present."""

        for claim in claims:
            self._claims[claim.claim_id] = claim

    def all_claims(self) -> list[Claim]:
        """Return all claims currently in insertion order."""

        return list(self._claims.values())

    def update_status(
        self,
        claim_id: str,
        status: ClaimStatus,
        confidence: ConfidenceLevel,
        verification_notes: str,
        evidence_ids: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
    ) -> Claim:
        """Update one claim's verification status and evidence links.

        Args:
            claim_id: Claim to update.
            status: New verification status.
            confidence: Confidence assigned by the verifier.
            verification_notes: Human-readable reason for the status.
            evidence_ids: Optional replacement supporting evidence IDs.
            contradicting_evidence_ids: Optional contradiction evidence IDs.

        Returns:
            The updated claim.

        Raises:
            KeyError: If the claim ID does not exist.
        """

        if claim_id not in self._claims:
            raise KeyError(f"Unknown claim_id: {claim_id}")

        claim = self._claims[claim_id]
        updated = claim.model_copy(
            update={
                "status": status,
                "confidence": confidence,
                "verification_notes": verification_notes,
                "evidence_ids": evidence_ids if evidence_ids is not None else claim.evidence_ids,
                "contradicting_evidence_ids": (
                    contradicting_evidence_ids
                    if contradicting_evidence_ids is not None
                    else claim.contradicting_evidence_ids
                ),
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._claims[claim_id] = updated
        return updated
