"""Verification services for claims, evidence, and contradictions.

This package provides:
- Local deterministic claim verification
- Contradiction detection across evidence
- Evidence quality scoring
"""

from decision_system.verification.contradictions import ContradictionDetector
from decision_system.verification.quality import EvidenceQualityScorer
from decision_system.verification.verifier import ClaimVerifier

__all__ = ["ClaimVerifier", "ContradictionDetector", "EvidenceQualityScorer"]
