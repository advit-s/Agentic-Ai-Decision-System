"""High-level verification service that ties together verifier, contradiction
detector, and quality scorer for use by APIs and workflow nodes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from decision_system.models import (
    Claim,
    ContradictionRecord,
    EvidenceQuality,
    VerificationResult,
    VerificationSummary,
)
from decision_system.verification.contradictions import ContradictionDetector
from decision_system.verification.quality import EvidenceQualityScorer
from decision_system.verification.verifier import ClaimVerifier


class VerificationService:
    """High-level verification service.

    Orchestrates verification, contradiction detection, and quality scoring.
    Provides workspace-scoped verification with persistent results.
    """

    def __init__(
        self,
        claim_store: Any | None = None,
        evidence_resolver: Any | None = None,
    ):
        self._claim_store = claim_store
        self._verifier = ClaimVerifier(evidence_resolver=evidence_resolver)
        self._detector = ContradictionDetector(evidence_resolver=evidence_resolver)
        self._scorer = EvidenceQualityScorer()
        self._evidence_resolver = evidence_resolver

    # ------------------------------------------------------------------
    # Claim verification
    # ------------------------------------------------------------------

    def verify_claim(
        self,
        claim: Claim,
        workspace_id: str | None = None,
    ) -> tuple[VerificationResult, EvidenceQuality]:
        """Verify a single claim and score evidence quality.

        Returns:
            Tuple of (VerificationResult, EvidenceQuality).
        """
        result = self._verifier.verify_claim(claim, workspace_id=workspace_id)
        quality = self._scorer.score(result)

        # Update claim store if available
        if self._claim_store and claim.claim_id:
            self._update_claim_verification(claim.claim_id, result, quality)

        return result, quality

    def verify_claim_by_id(
        self,
        claim_id: str,
        workspace_id: str | None = None,
    ) -> tuple[VerificationResult, EvidenceQuality] | None:
        """Verify a claim by its ID using the claim store."""
        if not self._claim_store:
            return None
        claim = self._claim_store.load(claim_id)
        if claim is None:
            return None
        return self.verify_claim(claim, workspace_id=workspace_id or claim.workspace_id)

    def verify_execution_claims(
        self,
        execution_id: str,
        workspace_id: str | None = None,
    ) -> list[tuple[VerificationResult, EvidenceQuality]]:
        """Verify all claims for an execution."""
        if not self._claim_store:
            return []
        claims = self._claim_store.list(execution_id=execution_id)
        if workspace_id:
            claims = [c for c in claims if c.workspace_id == workspace_id]
        results = []
        for claim in claims:
            result, quality = self.verify_claim(
                claim, workspace_id=workspace_id or claim.workspace_id
            )
            results.append((result, quality))
        return results

    def verify_workspace_claims(
        self,
        workspace_id: str,
    ) -> list[tuple[VerificationResult, EvidenceQuality]]:
        """Verify all claims in a workspace."""
        if not self._claim_store:
            return []
        claims = self._claim_store.list(workspace_id=workspace_id)
        results = []
        for claim in claims:
            result, quality = self.verify_claim(claim, workspace_id=workspace_id)
            results.append((result, quality))
        return results

    # ------------------------------------------------------------------
    # Contradiction scanning
    # ------------------------------------------------------------------

    def scan_workspace_contradictions(
        self,
        workspace_id: str,
        claim_id: str | None = None,
    ) -> list[ContradictionRecord]:
        """Scan workspace evidence for contradictions."""
        evidence_texts = self._get_workspace_evidence_texts(workspace_id)
        if not evidence_texts:
            return []
        return self._detector.scan_evidence(evidence_texts, workspace_id=workspace_id)

    def scan_claim_contradictions(
        self,
        claim_id: str,
        workspace_id: str | None = None,
    ) -> list[ContradictionRecord]:
        """Scan if any workspace evidence contradicts a claim."""
        if not self._claim_store:
            return []
        claim = self._claim_store.load(claim_id)
        if claim is None:
            return []
        evidence_texts = self._get_workspace_evidence_texts(
            workspace_id or claim.workspace_id or ""
        )
        if not evidence_texts:
            return []
        return self._detector.scan_claim_against_evidence(
            claim.claim_text,
            evidence_texts,
            workspace_id=workspace_id or claim.workspace_id,
            claim_id=claim_id,
        )

    # ------------------------------------------------------------------
    # Verification summary
    # ------------------------------------------------------------------

    def get_verification_summary(
        self,
        workspace_id: str | None = None,
        execution_id: str | None = None,
    ) -> VerificationSummary:
        """Compute verification summary for a workspace or execution."""
        if not self._claim_store:
            return VerificationSummary()

        claims = self._claim_store.list(workspace_id=workspace_id, execution_id=execution_id)

        if not claims:
            return VerificationSummary()

        total = len(claims)
        supported = sum(1 for c in claims if c.status in ("supported", "verified"))
        contradicted = sum(1 for c in claims if c.status == "contradicted")
        unsupported = sum(1 for c in claims if c.status == "unsupported")
        uncertain = sum(1 for c in claims if c.status == "uncertain")
        needs_review = sum(1 for c in claims if c.status in ("needs_review",))

        # Confidence
        confidences = {"high": 1.0, "medium": 0.5, "low": 0.0}
        avg_conf = sum(confidences.get(c.confidence, 0.0) for c in claims) / max(total, 1)

        # Coverage
        with_evidence = sum(1 for c in claims if c.evidence_ids or c.evidence_snippets)
        coverage = round(with_evidence / max(total, 1), 2)

        # Evidence quality counts
        strong = 0
        moderate = 0
        weak = 0
        missing = 0
        contradiction_count = 0
        for c in claims:
            if c.contradicting_evidence_ids:
                contradiction_count += 1
            eq = getattr(c, "evidence_quality", None)
            if eq == "strong":
                strong += 1
            elif eq == "moderate":
                moderate += 1
            elif eq == "weak":
                weak += 1
            elif eq == "contradicted":
                contradiction_count += 1
            elif eq == "missing" or eq is None:
                missing += 1

        # Also count contradictions from claim contradicting_evidence_ids
        claim_contradictions = sum(1 for c in claims if c.contradicting_evidence_ids)

        return VerificationSummary(
            total_claims=total,
            supported_claims=supported,
            contradicted_claims=contradicted,
            unsupported_claims=unsupported,
            uncertain_claims=uncertain,
            needs_review_claims=needs_review,
            average_confidence=round(avg_conf, 2),
            evidence_coverage_score=coverage,
            strong_evidence_count=strong,
            moderate_evidence_count=moderate,
            weak_evidence_count=weak,
            missing_evidence_count=missing,
            contradiction_count=contradiction_count + claim_contradictions,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_claim_verification(
        self,
        claim_id: str,
        result: VerificationResult,
        quality: EvidenceQuality,
    ) -> None:
        """Update a claim's verification fields in the store."""
        if not self._claim_store:
            return
        claim = self._claim_store.load(claim_id)
        if claim is None:
            return

        updated = claim.model_copy(
            update={
                "status": result.status,
                "confidence": result.confidence,
                "verification_notes": result.verification_notes,
                "evidence_ids": result.evidence_ids or claim.evidence_ids,
                "source_ids": result.source_ids or claim.source_ids,
                "chunk_ids": result.chunk_ids or claim.chunk_ids,
                "evidence_snippets": result.evidence_snippets or claim.evidence_snippets,
                "contradicting_evidence_ids": result.contradicting_evidence_ids
                or claim.contradicting_evidence_ids,
                "evidence_quality": quality.quality_label,
                "verification_method": result.verification_method,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        self._claim_store.save(updated)

    def _get_workspace_evidence_texts(self, workspace_id: str) -> list[dict[str, str]]:
        """Get evidence texts for a workspace for contradiction scanning."""
        texts: list[dict[str, str]] = []

        # Try keyword search to gather evidence
        try:
            from decision_system.data_sources.store import DataSourceStore

            store = DataSourceStore()
            # Get a broad sample of evidence chunks
            chunks = store.search_chunks_keyword(workspace_id=workspace_id, query="", limit=50)
            for chunk in chunks:
                d = (
                    chunk
                    if isinstance(chunk, dict)
                    else chunk.model_dump(mode="json")
                    if hasattr(chunk, "model_dump")
                    else {}
                )
                texts.append(
                    {
                        "id": d.get("evidence_id", d.get("id", "")),
                        "chunk_id": d.get("chunk_id", ""),
                        "text": d.get("text", d.get("chunk_text", "")),
                    }
                )
        except Exception:
            pass

        return texts
