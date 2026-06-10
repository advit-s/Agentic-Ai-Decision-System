"""Evidence coverage score for decision reports.

Provides a deterministic coverage score based on claim ledger state.
All values are computed from structured data — no LLM calls, no guesses.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from decision_system.models import Claim, VerificationResult


@dataclass
class CoverageScore:
    """Coverage metrics for a single decision report."""

    total_claims: int = 0
    verified_claims: int = 0
    unsupported_claims: int = 0
    contradicted_claims: int = 0
    pending_claims: int = 0
    evidence_coverage_pct: float = 0.0
    status: str = "no_claims"

    def to_dict(self) -> dict:
        return {
            "total_claims": self.total_claims,
            "verified_claims": self.verified_claims,
            "unsupported_claims": self.unsupported_claims,
            "contradicted_claims": self.contradicted_claims,
            "pending_claims": self.pending_claims,
            "evidence_coverage_pct": round(self.evidence_coverage_pct, 1),
            "status": self.status,
        }


def compute_coverage(
    claims: list[Claim] | None = None,
    verification_results: list[VerificationResult] | None = None,
) -> CoverageScore:
    """Compute the coverage score from claims and/or verification results.

    If both *claims* and *verification_results* are provided, the results
    take precedence for status (since they represent the verifier's final
    decision).  If only *claims* are available, their inline status is used.

    Returns a ``CoverageScore`` dataclass with descriptive fields.
    """
    score = CoverageScore()

    if not claims and not verification_results:
        return score

    # Use verification results as the single source of truth when available
    if verification_results:
        score.total_claims = len(verification_results)
        for vr in verification_results:
            if vr.status == "verified":
                score.verified_claims += 1
            elif vr.status == "unsupported":
                score.unsupported_claims += 1
            elif vr.status == "contradicted":
                score.contradicted_claims += 1
            # "pending" not possible in VerificationResult, but handle it
            else:
                score.pending_claims += 1
    elif claims:
        score.total_claims = len(claims)
        for c in claims:
            if c.status == "verified":
                score.verified_claims += 1
            elif c.status == "unsupported":
                score.unsupported_claims += 1
            elif c.status == "contradicted":
                score.contradicted_claims += 1
            else:
                score.pending_claims += 1

    # Evidence coverage: percentage of non-pending claims that have evidence
    non_pending = score.total_claims - score.pending_claims
    if non_pending > 0:
        supported = score.verified_claims
        score.evidence_coverage_pct = round((supported / non_pending) * 100, 1)
    elif score.total_claims > 0:
        # All pending: coverage is 0 but they exist
        score.evidence_coverage_pct = 0.0

    # Determine overall status
    if score.total_claims == 0:
        score.status = "no_claims"
    elif score.contradicted_claims > 0:
        score.status = "contradictions_found"
    elif score.unsupported_claims > 0:
        score.status = "unsupported_found"
    elif score.evidence_coverage_pct >= 80:
        score.status = "good"
    elif score.evidence_coverage_pct >= 50:
        score.status = "moderate"
    else:
        score.status = "low_coverage"

    return score


def coverage_to_text(score: CoverageScore) -> str:
    """Render a coverage score as human-readable text."""
    lines = [
        "# Evidence Coverage Score",
        "",
        f"Total claims: {score.total_claims}",
        f"Verified: {score.verified_claims}",
        f"Unsupported: {score.unsupported_claims}",
        f"Contradicted: {score.contradicted_claims}",
        f"Pending: {score.pending_claims}",
        "",
        f"Evidence coverage: {score.evidence_coverage_pct}%",
        f"Status: {score.status}",
    ]
    return "\n".join(lines)
