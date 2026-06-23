"""Tests for trust report v2 rendering."""

from __future__ import annotations

import pytest

from decision_system.models import (
    Claim,
    ContradictionRecord,
    VerificationSummary,
    ReportClaimEntry,
    EvidenceTableEntry,
)
from decision_system.reports.trust_renderer import render_trust_report


class TestTrustReport:
    """Tests for trust report v2."""

    def test_report_without_claims(self):
        """Report with no claims still renders with empty sections."""
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=[],
        )
        assert report is not None
        assert report.markdown is not None
        assert len(report.markdown) > 0
        # Should have key sections
        assert "Executive Summary" in report.markdown
        assert "Verification Summary" in report.markdown
        assert "Warnings and Limitations" in report.markdown

    def test_report_with_supported_claim(self):
        """Report shows supported claims."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="Revenue grew by 20%.",
                claim_type="metric", status="supported",
                confidence="high",
                evidence_ids=["ev-1"],
                evidence_snippets=["Revenue grew 20%"],
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Revenue grew by 20%" in report.markdown
        assert "Supported Claims" in report.markdown
        assert report.verification_summary is not None
        assert report.verification_summary.total_claims == 1
        assert report.verification_summary.supported_claims == 1

    def test_report_with_contradicted_claim(self):
        """Report clearly shows contradicted claims."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="Churn is 5%.",
                claim_type="metric", status="contradicted",
                confidence="medium",
                contradicting_evidence_ids=["ev-2"],
                verification_notes="Evidence shows 12% churn.",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Churn is 5%" in report.markdown
        assert "Contradicted Claims" in report.markdown
        assert report.verification_summary.contradicted_claims == 1

    def test_report_with_unsupported_claim(self):
        """Report shows unsupported claims."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="Market is growing.",
                claim_type="assumption", status="unsupported",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Market is growing" in report.markdown
        assert "Unsupported Claims" in report.markdown
        assert "Warnings and Limitations" in report.markdown

    def test_report_with_uncertain_claim(self):
        """Report shows uncertain claims."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="Maybe revenue is growing.",
                claim_type="metric", status="uncertain",
                confidence="low",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Maybe revenue is growing" in report.markdown
        assert "Uncertain Claims" in report.markdown

    def test_report_with_needs_review_claim(self):
        """Report shows claims needing review."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="We should migrate immediately.",
                claim_type="recommendation", status="needs_review",
                review_required=True,
                verification_notes="No evidence found for high-risk recommendation.",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "We should migrate immediately" in report.markdown
        assert "Claims Needing Review" in report.markdown

    def test_report_hides_nothing(self):
        """Report must not hide contradicted or unsupported claims."""
        claims = [
            Claim(claim_id="s1", run_id="r1", source_agent="test",
                  claim_text="Supported.", claim_type="assumption",
                  status="supported", confidence="high"),
            Claim(claim_id="u1", run_id="r1", source_agent="test",
                  claim_text="Unsupported.", claim_type="assumption",
                  status="unsupported"),
            Claim(claim_id="c1", run_id="r1", source_agent="test",
                  claim_text="Contradicted.", claim_type="metric",
                  status="contradicted"),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Supported." in report.markdown
        assert "Unsupported." in report.markdown
        assert "Contradicted." in report.markdown

    def test_report_with_verification_summary(self):
        """Report includes verification summary."""
        summary = VerificationSummary(
            total_claims=5,
            supported_claims=2,
            contradicted_claims=1,
            unsupported_claims=1,
            uncertain_claims=1,
            needs_review_claims=0,
            average_confidence=0.6,
            evidence_coverage_score=0.4,
        )
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=[],
            verification_summary=summary,
        )
        assert "5" in report.markdown
        assert "2" in report.markdown  # supported
        assert "1" in report.markdown  # contradicted

    def test_report_with_contradictions(self):
        """Report includes contradiction records."""
        from datetime import datetime, timezone
        contradictions = [
            ContradictionRecord(
                contradiction_id="ctr-1",
                source_id_a="ev-1",
                chunk_id_a="",
                source_id_b="ev-2",
                chunk_id_b="",
                type="metric_conflict",
                description="Revenue: 25% vs 10%",
                severity="high",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=[],
            contradictions=contradictions,
        )
        assert "Contradictions" in report.markdown
        assert "Revenue: 25% vs 10%" in report.markdown

    def test_report_evidence_table(self):
        """Report includes evidence table."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="Revenue grew.", claim_type="metric",
                status="supported", confidence="medium",
                evidence_ids=["ev-1"],
                evidence_snippets=["Revenue grew 20%"],
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        assert "Evidence Table" in report.markdown

    def test_integrity_unsupported_visible(self):
        """Unsupported claims are NOT hidden in the report - they are clearly visible."""
        claims = [
            Claim(
                claim_id="c1", run_id="r1", source_agent="test",
                claim_text="This claim has no evidence.",
                claim_type="assumption", status="unsupported",
            ),
        ]
        report = render_trust_report(
            question="Test?",
            run_id="run-1",
            claims=claims,
        )
        # The "Unsupported Claims" section must be present
        assert "Unsupported Claims" in report.markdown
        # The claim text must appear
        assert "This claim has no evidence" in report.markdown
