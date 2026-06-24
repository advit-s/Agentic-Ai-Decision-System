"""Deterministic local claim verifier v2.

Verifies claims against workspace evidence without requiring an LLM.
Supports multiple verification methods and produces conservative,
local-first results.
"""

from __future__ import annotations

import re
from typing import Any

from decision_system.models import Claim, VerificationResult


# Methods
DIRECT_EVIDENCE = "direct_evidence_reference"
KEYWORD_SEARCH = "keyword_evidence_search"
NUMERIC_MATCH = "numeric_match"
CONTRADICTION_CHECK = "contradiction_keyword_check"
INSUFFICIENT_EVIDENCE = "insufficient_evidence"
MANUAL_REVIEW = "manual_review_required"

# Contradiction markers in text
CONTRADICTION_PATTERNS = [
    re.compile(r"\b(?:but|however|on the other hand|contrary|despite|although)\b", re.IGNORECASE),
    re.compile(r"\b(?:not\s+\w+\s+compliant|not\s+compliant|fails?\s+to\s+meet)\b", re.IGNORECASE),
    re.compile(r"\b(?:decreased|declined|dropped|fell|reduced)\b", re.IGNORECASE),
    re.compile(r"\bincreased\b.*\b(?:risk|concern|issue|problem)\b", re.IGNORECASE),
    re.compile(r"\bCONTRADICTS\b", re.IGNORECASE),
]

# High-risk claim types that need review when unsupported
HIGH_RISK_TYPES = {"recommendation", "decision", "risk"}

# Important terms for scoring evidence quality
IMPORTANT_TERMS_PATTERN = re.compile(
    r"\b(?:revenue|profit|cost|churn|revenue|growth|risk|compliant|"
    r"migration|security|audit|revenue|users|customers|market|"
    r"percent|percentage|increase|decrease|total|annual|quarter|"
    r"monthly|budget|spend|investment|ROI|margin|revenue|loss)\b",
    re.IGNORECASE,
)


class ClaimVerifier:
    """Deterministic local claim verifier.

    Workspace-scoped. Does not require an LLM. Uses keyword overlap,
    term matching, and contradiction pattern detection.

    The verifier is conservative and does not claim to prove truth.
    """

    def __init__(self, evidence_resolver: Any | None = None):
        """Initialize with optional evidence resolver.

        Args:
            evidence_resolver: An EvidenceResolver instance. If None,
                one will be lazily created when needed.
        """
        self._resolver = evidence_resolver

    def _get_resolver(self):
        if self._resolver is None:
            from decision_system.evidence.resolver import EvidenceResolver
            self._resolver = EvidenceResolver()
        return self._resolver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify_claim(
        self,
        claim: Claim,
        workspace_id: str | None = None,
        evidence_references: list[str] | None = None,
        search_query: str | None = None,
    ) -> VerificationResult:
        """Verify a single claim against workspace evidence.

        Args:
            claim: The claim to verify.
            workspace_id: Workspace for evidence lookup.
            evidence_references: Optional list of evidence IDs to check.
            search_query: Optional custom search query (defaults to claim text).

        Returns:
            VerificationResult with status, confidence, and reasoning.
        """
        eid = claim.claim_id
        resolver = self._get_resolver()

        # Collect evidence IDs to check
        evidence_ids = evidence_references or claim.evidence_ids or []
        query = search_query or claim.claim_text

        # Step 1: Try direct evidence references
        if evidence_ids:
            result = self._check_direct_evidence(
                eid, evidence_ids, workspace_id, claim
            )
            if result is not None:
                return result

        # Step 2: Try keyword search
        kw_result = self._check_keyword_search(eid, query, workspace_id, claim)
        if kw_result is not None:
            return kw_result

        # Step 3: No evidence found
        return self._make_unsupported(eid, claim, "No matching evidence found in workspace.")

    def verify_claims(
        self,
        claims: list[Claim],
        workspace_id: str | None = None,
    ) -> list[VerificationResult]:
        """Verify multiple claims."""
        return [self.verify_claim(c, workspace_id=workspace_id) for c in claims]

    # ------------------------------------------------------------------
    # Internal verification steps
    # ------------------------------------------------------------------

    def _check_direct_evidence(
        self,
        claim_id: str,
        evidence_ids: list[str],
        workspace_id: str | None,
        claim: Claim,
    ) -> VerificationResult | None:
        """Check claims with explicit evidence references."""
        resolver = self._get_resolver()
        resolved = resolver.resolve_many(
            evidence_ids=evidence_ids, workspace_id=workspace_id
        )

        resolved_valid = [r for r in resolved if r.warning is None]
        resolved_missing = [r for r in resolved if r.warning is not None]

        if not resolved_valid:
            return None  # Fall through to keyword search

        # Get snippets from resolved evidence
        snippets = [r.chunk_text for r in resolved_valid if r.chunk_text]

        if not snippets:
            return None

        # Check for contradictions in evidence text
        contradicting_ids = []
        supporting_ids = []
        for r in resolved_valid:
            if self._is_contradictory_text(r.chunk_text, claim.claim_text):
                contradicting_ids.append(r.evidence_id)
            else:
                supporting_ids.append(r.evidence_id)

        if contradicting_ids:
            return VerificationResult(
                claim_id=claim_id,
                status="contradicted",
                evidence_ids=supporting_ids,
                source_ids=list(set(r.source_id for r in resolved_valid if r.source_id)),
                chunk_ids=list(set(r.chunk_id for r in resolved_valid if r.chunk_id)),
                evidence_snippets=[r.chunk_text for r in resolved_valid if r.chunk_text and r.evidence_id not in contradicting_ids],
                contradicting_evidence_ids=contradicting_ids,
                confidence="high",
                verification_notes="Evidence contains statements that contradict this claim.",
                verification_method=DIRECT_EVIDENCE,
            )

        # Score evidence support
        score = self._score_support(snippets, claim.claim_text)
        if score >= 0.3:
            return VerificationResult(
                claim_id=claim_id,
                status="supported",
                evidence_ids=supporting_ids,
                source_ids=list(set(r.source_id for r in resolved_valid if r.source_id)),
                chunk_ids=list(set(r.chunk_id for r in resolved_valid if r.chunk_id)),
                evidence_snippets=snippets,
                confidence="high" if score >= 0.6 else "medium",
                verification_notes=f"Cited evidence supports claim (overlap score: {score:.2f}).",
                verification_method=DIRECT_EVIDENCE,
            )
        else:
            # Weak evidence
            return VerificationResult(
                claim_id=claim_id,
                status="uncertain",
                evidence_ids=supporting_ids,
                source_ids=list(set(r.source_id for r in resolved_valid if r.source_id)),
                chunk_ids=list(set(r.chunk_id for r in resolved_valid if r.chunk_id)),
                evidence_snippets=snippets,
                confidence="low",
                verification_notes="Cited evidence is weak or does not clearly support the claim.",
                verification_method=DIRECT_EVIDENCE,
            )

    def _check_keyword_search(
        self,
        claim_id: str,
        query: str,
        workspace_id: str | None,
        claim: Claim,
    ) -> VerificationResult | None:
        """Search workspace evidence using claim text as query."""
        search_results = self._search_evidence(query, workspace_id)

        if not search_results:
            return None

        # Extract snippets and evidence IDs
        snippets = []
        evidence_ids = []
        for r in search_results:
            text = r.get("text", r.get("chunk_text", ""))
            eid = r.get("evidence_id", r.get("id", ""))
            if text:
                snippets.append(text)
                if eid:
                    evidence_ids.append(eid)

        if not snippets:
            return None

        # Check for contradictions
        contradicting_ids = []
        supporting_ids = []
        for i, s in enumerate(snippets):
            if self._is_contradictory_text(s, claim.claim_text):
                if i < len(evidence_ids):
                    contradicting_ids.append(evidence_ids[i])
            else:
                if i < len(evidence_ids):
                    supporting_ids.append(evidence_ids[i])

        if contradicting_ids:
            return VerificationResult(
                claim_id=claim_id,
                status="contradicted",
                evidence_ids=supporting_ids,
                evidence_snippets=snippets,
                contradicting_evidence_ids=contradicting_ids,
                confidence="high",
                verification_notes="Workspace evidence contains contradictory statements.",
                verification_method=CONTRADICTION_CHECK,
            )

        # Score support
        score = self._score_support(snippets, query)
        if score >= 0.3:
            return VerificationResult(
                claim_id=claim_id,
                status="supported",
                evidence_ids=evidence_ids,
                evidence_snippets=snippets,
                confidence="medium" if score < 0.6 else "high",
                verification_notes=f"Keyword evidence search supports claim (score: {score:.2f}).",
                verification_method=KEYWORD_SEARCH,
            )
        else:
            return VerificationResult(
                claim_id=claim_id,
                status="uncertain",
                evidence_ids=evidence_ids,
                evidence_snippets=snippets,
                confidence="low",
                verification_notes="Evidence found, but overlap with claim is weak.",
                verification_method=KEYWORD_SEARCH,
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _search_evidence(self, query: str, workspace_id: str | None) -> list[dict]:
        """Search workspace evidence using available stores."""
        results: list[dict] = []

        # Try vector search
        try:
            from decision_system.config import load_settings
            from decision_system.rag.retriever import retrieve_evidence

            settings = load_settings()
            chunks = retrieve_evidence(
                query=query,
                store_dir=settings.store_dir,
                collection_name=settings.collection_name,
                top_k=5,
                workspace_id=workspace_id,
            )
            for c in chunks:
                results.append({
                    "evidence_id": c.evidence_id,
                    "text": c.text,
                    "source_name": c.source_filename,
                })
        except Exception:
            pass

        # Try keyword search as fallback
        if not results and workspace_id:
            try:
                from decision_system.data_sources.store import DataSourceStore

                store = DataSourceStore()
                kw_results = store.search_chunks_keyword(
                    workspace_id=workspace_id, query=query, limit=5
                )
                for r in kw_results:
                    d = r if isinstance(r, dict) else r.model_dump(mode="json") if hasattr(r, "model_dump") else {}
                    results.append(d)
            except Exception:
                pass

        return results

    def _score_support(self, snippets: list[str], claim_text: str) -> float:
        """Score how well evidence snippets support a claim.

        Returns a float 0.0-1.0 based on keyword overlap, important term
        matching, and text length ratio.
        """
        if not snippets or not claim_text:
            return 0.0

        # Normalize
        claim_lower = claim_text.lower()
        claim_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", claim_lower))
        claim_important = set(
            m.group(0).lower() for m in IMPORTANT_TERMS_PATTERN.finditer(claim_lower)
        )

        if not claim_words:
            return 0.0

        combined_text = " ".join(snippets).lower()
        evidence_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", combined_text))

        if not evidence_words:
            return 0.0

        # Word overlap
        overlap = claim_words & evidence_words
        overlap_ratio = len(overlap) / len(claim_words)

        # Important term overlap (weighted)
        important_overlap = claim_important & evidence_words
        important_ratio = (
            len(important_overlap) / len(claim_important) if claim_important else 0.0
        )

        # Weighted score: basic overlap + weighted important term match
        score = (overlap_ratio * 0.4) + (important_ratio * 0.6)

        return min(score, 1.0)

    def _is_contradictory_text(self, evidence_text: str, claim_text: str) -> bool:
        """Check if evidence text contradicts a claim using pattern matching."""
        evidence_lower = evidence_text.lower()
        claim_lower = claim_text.lower()

        # Check CONTRADICTS markers
        if "contradicts" in evidence_lower:
            return True

        # Check for negation patterns in evidence relative to claim
        for pattern in CONTRADICTION_PATTERNS:
            if pattern.search(evidence_lower):
                # Positive marker found - check if it's about a similar topic
                claim_words = set(claim_lower.split())
                evidence_words = set(evidence_lower.split())
                shared = claim_words & evidence_words
                if len(shared) >= 2:
                    return True

        # Check opposite direction phrases
        if "not " in evidence_lower or "no " in evidence_lower:
            # Evidence says NOT about something the claim asserts
            claim_key_terms = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_lower))
            evidence_key_terms = set(re.findall(r"\b[a-zA-Z]{4,}\b", evidence_lower))
            shared = claim_key_terms & evidence_key_terms
            if len(shared) >= 3:
                return True

        return False

    def _make_unsupported(
        self, claim_id: str, claim: Claim, reason: str
    ) -> VerificationResult:
        """Create an unsupported verification result."""
        # Check if this is high-risk
        needs_review = claim.claim_type in HIGH_RISK_TYPES

        return VerificationResult(
            claim_id=claim_id,
            status="needs_review" if needs_review else "unsupported",
            confidence="low",
            verification_notes=reason,
            verification_method=INSUFFICIENT_EVIDENCE,
            evidence_ids=[],
        )
