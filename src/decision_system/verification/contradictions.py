"""Local contradiction detection across evidence and claims.

Detects contradictions using deterministic pattern matching:
- Same metric, different value
- Same entity, opposite status
- Same date/event with conflicting statements
- Risk present/absent conflicts
- Claim contradicted by evidence text
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from decision_system.models import ContradictionRecord

# Patterns for detecting metric values
METRIC_PATTERN = re.compile(
    r"(?:^|\s)(\d+[.,]?\d*)\s*(%|percent|dollars|USD|EUR|GBP|million|billion|thousand|users|customers|churn)(?:$|\s|[.,!?])",
    re.IGNORECASE,
)

# Patterns for detecting status statements
STATUS_PATTERN = re.compile(
    r"\b(?:is\s+(?:not\s+)?(?:compliant|approved|certified|valid|active|enabled|supported)|"
    r"is\s+(?:SOC2|ISO|GDPR|HIPAA|PCI)\s+(?:compliant|non-compliant|certified))\b",
    re.IGNORECASE,
)

# Patterns for risk statements
RISK_PRESENT = re.compile(
    r"\b(?:risk|vulnerability|threat|issue|concern|problem|breach|incident)\b",
    re.IGNORECASE,
)
RISK_ABSENT = re.compile(
    r"\b(?:no\s+(?:risk|vulnerability|threat|issue|concern)|"
    r"not\s+(?:at\s+)?risk|risk-free|no\s+known)\b",
    re.IGNORECASE,
)

# Date patterns
DATE_PATTERN = re.compile(
    r"\b(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)


class ContradictionDetector:
    """Detects contradictions between evidence chunks and claims.

    Uses deterministic patterns - does not require an LLM.
    """

    def __init__(self, evidence_resolver: Any | None = None):
        self._resolver = evidence_resolver

    def _get_resolver(self):
        if self._resolver is None:
            from decision_system.evidence.resolver import EvidenceResolver

            self._resolver = EvidenceResolver()
        return self._resolver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_evidence(
        self,
        evidence_texts: list[dict[str, str]],
        workspace_id: str | None = None,
    ) -> list[ContradictionRecord]:
        """Scan a list of evidence texts for internal contradictions.

        Each dict should have 'id' and 'text' keys.
        """
        contradictions: list[ContradictionRecord] = []
        n = len(evidence_texts)

        # Compare every pair
        for i in range(n):
            for j in range(i + 1, n):
                a = evidence_texts[i]
                b = evidence_texts[j]
                result = self._compare_evidence(a, b, workspace_id)
                contradictions.extend(result)

        return contradictions

    def scan_claim_against_evidence(
        self,
        claim_text: str,
        evidence_texts: list[dict[str, str]],
        workspace_id: str | None = None,
        claim_id: str | None = None,
    ) -> list[ContradictionRecord]:
        """Scan if any evidence contradicts a claim."""
        contradictions: list[ContradictionRecord] = []

        for ev in evidence_texts:
            result = self._compare_claim_evidence(claim_text, ev, workspace_id, claim_id)
            if result:
                contradictions.append(result)

        return contradictions

    # ------------------------------------------------------------------
    # Internal comparison methods
    # ------------------------------------------------------------------

    def _compare_evidence(
        self, a: dict[str, str], b: dict[str, str], workspace_id: str | None
    ) -> list[ContradictionRecord]:
        """Compare two evidence items for contradictions."""
        records: list[ContradictionRecord] = []

        # 1. Check metric conflicts
        metric_result = self._check_metric_conflict(a, b)
        if metric_result:
            records.append(
                self._make_record(
                    workspace_id=workspace_id,
                    source_id_a=a.get("id", a.get("evidence_id", "")),
                    chunk_id_a=a.get("chunk_id", ""),
                    source_id_b=b.get("id", b.get("evidence_id", "")),
                    chunk_id_b=b.get("chunk_id", ""),
                    type="metric_conflict",
                    description=metric_result,
                    severity="high",
                )
            )

        # 2. Check opposite status
        status_result = self._check_opposite_status(a, b)
        if status_result:
            records.append(
                self._make_record(
                    workspace_id=workspace_id,
                    source_id_a=a.get("id", a.get("evidence_id", "")),
                    chunk_id_a=a.get("chunk_id", ""),
                    source_id_b=b.get("id", b.get("evidence_id", "")),
                    chunk_id_b=b.get("chunk_id", ""),
                    type="opposite_status",
                    description=status_result,
                    severity="high",
                )
            )

        # 3. Check risk present vs absent
        risk_result = self._check_risk_conflict(a, b)
        if risk_result:
            records.append(
                self._make_record(
                    workspace_id=workspace_id,
                    source_id_a=a.get("id", a.get("evidence_id", "")),
                    chunk_id_a=a.get("chunk_id", ""),
                    source_id_b=b.get("id", b.get("evidence_id", "")),
                    chunk_id_b=b.get("chunk_id", ""),
                    type="risk_conflict",
                    description=risk_result,
                    severity="medium",
                )
            )

        return records

    def _compare_claim_evidence(
        self,
        claim_text: str,
        evidence: dict[str, str],
        workspace_id: str | None,
        claim_id: str | None,
    ) -> ContradictionRecord | None:
        """Check if a single evidence item contradicts a claim."""
        ev_text = evidence.get("text", evidence.get("chunk_text", ""))

        # Check metric conflicts between claim and evidence
        claim_metrics = METRIC_PATTERN.findall(claim_text)
        ev_metrics = METRIC_PATTERN.findall(ev_text)

        if claim_metrics and ev_metrics:
            for cm in claim_metrics:
                for em in ev_metrics:
                    if cm[1].lower() == em[1].lower() and cm[0] != em[0]:
                        return self._make_record(
                            workspace_id=workspace_id,
                            source_id_a="claim:" + (claim_id or ""),
                            chunk_id_a="",
                            source_id_b=evidence.get("id", evidence.get("evidence_id", "")),
                            chunk_id_b=evidence.get("chunk_id", ""),
                            type="claim_contradicted",
                            description=(
                                f"Claim states '{cm[0]} {cm[1]}' but evidence says '{em[0]} {em[1]}'"
                            ),
                            severity="high",
                            claim_id=claim_id,
                        )

        # Check opposite status
        claim_has_not = "not " in claim_text.lower() or "no " in claim_text.lower()
        ev_has_not = "not " in ev_text.lower() or "no " in ev_text.lower()

        if claim_has_not != ev_has_not:
            # One says it IS, the other says it IS NOT - check shared terms
            claim_terms = set(re.findall(r"\b[a-zA-Z]{4,}\b", claim_text.lower()))
            ev_terms = set(re.findall(r"\b[a-zA-Z]{4,}\b", ev_text.lower()))
            shared = claim_terms & ev_terms
            if len(shared) >= 3:
                return self._make_record(
                    workspace_id=workspace_id,
                    source_id_a="claim:" + (claim_id or ""),
                    chunk_id_a="",
                    source_id_b=evidence.get("id", evidence.get("evidence_id", "")),
                    chunk_id_b=evidence.get("chunk_id", ""),
                    type="claim_contradicted",
                    description="One source asserts a condition that another denies.",
                    severity="medium",
                    claim_id=claim_id,
                )

        return None

    # ------------------------------------------------------------------
    # Pattern checks
    # ------------------------------------------------------------------

    def _check_metric_conflict(self, a: dict, b: dict) -> str | None:
        """Check if two evidence items have metric conflicts."""
        text_a = a.get("text", a.get("chunk_text", ""))
        text_b = b.get("text", b.get("chunk_text", ""))

        metrics_a = METRIC_PATTERN.findall(text_a)
        metrics_b = METRIC_PATTERN.findall(text_b)

        for ma in metrics_a:
            for mb in metrics_b:
                if ma[1].lower() == mb[1].lower() and ma[0] != mb[0]:
                    return f"Metric '{ma[1]}' has conflicting values: '{ma[0]}' vs '{mb[0]}'"
        return None

    def _check_opposite_status(self, a: dict, b: dict) -> str | None:
        """Check if two evidence items have opposite statuses."""
        text_a = a.get("text", a.get("chunk_text", ""))
        text_b = b.get("text", b.get("chunk_text", ""))

        # Extract status phrases
        statuses_a = STATUS_PATTERN.findall(text_a)
        statuses_b = STATUS_PATTERN.findall(text_b)

        if statuses_a and statuses_b:
            for sa in statuses_a:
                for sb in statuses_b:
                    # One says "is compliant", other says "is not compliant"
                    if ("not" in str(sa).lower()) != ("not" in str(sb).lower()):
                        return "Contradictory status statements detected."
        return None

    def _check_risk_conflict(self, a: dict, b: dict) -> str | None:
        """Check if one evidence says risk present and another says absent."""
        text_a = a.get("text", a.get("chunk_text", ""))
        text_b = b.get("text", b.get("chunk_text", ""))

        a_risk = RISK_PRESENT.search(text_a) and not RISK_ABSENT.search(text_a)
        b_risk = RISK_PRESENT.search(text_b) and not RISK_ABSENT.search(text_b)
        a_no_risk = RISK_ABSENT.search(text_a)
        b_no_risk = RISK_ABSENT.search(text_b)

        if (a_risk and b_no_risk) or (a_no_risk and b_risk):
            return "One source indicates risk, another denies it."

        return None

    # ------------------------------------------------------------------
    # Record factory
    # ------------------------------------------------------------------

    def _make_record(
        self,
        workspace_id: str | None = None,
        source_id_a: str = "",
        chunk_id_a: str = "",
        source_id_b: str = "",
        chunk_id_b: str = "",
        type: str = "statement_conflict",
        description: str = "",
        severity: str = "medium",
        claim_id: str | None = None,
    ) -> ContradictionRecord:
        """Create a ContradictionRecord."""
        return ContradictionRecord(
            contradiction_id=str(uuid4()),
            workspace_id=workspace_id or "",
            claim_id=claim_id,
            source_id_a=source_id_a,
            chunk_id_a=chunk_id_a,
            source_id_b=source_id_b,
            chunk_id_b=chunk_id_b,
            type=type,  # type: ignore[arg-type]
            description=description,
            severity=severity,  # type: ignore[arg-type]
            confidence="medium",
            created_at=datetime.now(timezone.utc),
        )
