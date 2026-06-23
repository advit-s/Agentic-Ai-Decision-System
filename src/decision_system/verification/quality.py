"""Evidence quality scoring for verified claims.

Calculates quality labels based on evidence count, resolution status,
source diversity, contradictions, and overlap strength.
"""

from __future__ import annotations

from typing import Any

from decision_system.models import EvidenceQuality, VerificationResult, EvidenceQuality


class EvidenceQualityScorer:
    """Scores evidence quality for verified claims.

    Quality labels:
    - strong: multiple resolved evidence refs, no contradiction
    - moderate: one good evidence ref, no contradiction
    - weak: low overlap or unclear evidence
    - missing: no resolved evidence
    - contradicted: contradiction found
    """

    def score(
        self,
        verification: VerificationResult,
    ) -> EvidenceQuality:
        """Score evidence quality from a verification result.

        Args:
            verification: The verification result to score.

        Returns:
            EvidenceQuality with label and details.
        """
        evidence_count = len(verification.evidence_ids or [])
        source_count = len(set(verification.source_ids or []))
        contradicting_count = len(verification.contradicting_evidence_ids or [])
        has_contradiction = contradicting_count > 0
        has_direct_reference = evidence_count > 0

        # Resolved vs missing
        resolved_ids = [
            eid for eid in (verification.evidence_ids or [])
            if eid and eid not in (verification.contradicting_evidence_ids or [])
        ]
        resolved_count = len(resolved_ids)
        missing_count = evidence_count - resolved_count
        has_cross_source_support = source_count > 1

        # Coverage score: ratio of evidence types covered
        coverage = 0.0
        if evidence_count > 0:
            coverage = min((resolved_count / max(evidence_count, 1)) * 0.5 + 0.5, 1.0)
        if has_cross_source_support:
            coverage = min(coverage + 0.2, 1.0)

        # Quality label
        if has_contradiction:
            quality_label = "contradicted"
        elif resolved_count >= 2 and has_cross_source_support:
            quality_label = "strong"
        elif resolved_count >= 1:
            quality_label = "moderate"
        elif evidence_count > 0:
            quality_label = "weak"
        else:
            quality_label = "missing"

        return EvidenceQuality(
            evidence_count=evidence_count,
            resolved_evidence_count=resolved_count,
            missing_evidence_count=missing_count,
            source_count=source_count,
            has_direct_reference=has_direct_reference,
            has_cross_source_support=has_cross_source_support,
            has_contradiction=has_contradiction,
            coverage_score=round(coverage, 2),
            quality_label=quality_label,  # type: ignore[arg-type]
        )

    def score_from_claim_data(
        self,
        evidence_ids: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
        source_ids: list[str] | None = None,
    ) -> EvidenceQuality:
        """Score evidence quality directly from claim data fields."""
        evidence_ids = evidence_ids or []
        contradicting_ids = contradicting_evidence_ids or []
        source_ids = source_ids or []

        evidence_count = len(evidence_ids)
        contradicting_count = len(contradicting_ids)
        has_contradiction = contradicting_count > 0
        has_direct_reference = evidence_count > 0

        resolved_ids = [eid for eid in evidence_ids if eid not in contradicting_ids]
        resolved_count = len(resolved_ids)
        missing_count = evidence_count - resolved_count
        source_count = len(set(source_ids))
        has_cross_source_support = source_count > 1

        coverage = 0.0
        if evidence_count > 0:
            coverage = min((resolved_count / max(evidence_count, 1)) * 0.5 + 0.5, 1.0)
        if has_cross_source_support:
            coverage = min(coverage + 0.2, 1.0)

        if has_contradiction:
            quality_label = "contradicted"
        elif resolved_count >= 2 and has_cross_source_support:
            quality_label = "strong"
        elif resolved_count >= 1:
            quality_label = "moderate"
        elif evidence_count > 0:
            quality_label = "weak"
        else:
            quality_label = "missing"

        return EvidenceQuality(
            evidence_count=evidence_count,
            resolved_evidence_count=resolved_count,
            missing_evidence_count=missing_count,
            source_count=source_count,
            has_direct_reference=has_direct_reference,
            has_cross_source_support=has_cross_source_support,
            has_contradiction=has_contradiction,
            coverage_score=round(coverage, 2),
            quality_label=quality_label,  # type: ignore[arg-type]
        )
