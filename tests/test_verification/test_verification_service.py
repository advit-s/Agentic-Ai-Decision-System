"""Tests for the high-level VerificationService."""

from __future__ import annotations

import pytest

from decision_system.models import Claim
from decision_system.verification.service import VerificationService


class TestVerificationService:
    """Tests for VerificationService."""

    def test_verify_claim_no_store(self):
        """Verification works without a claim store."""
        claim = Claim(
            claim_id="vs-1", run_id="r1", source_agent="test",
            claim_text="Test claim.", claim_type="assumption",
        )
        service = VerificationService()
        result, quality = service.verify_claim(claim, workspace_id="ws-none")
        assert result.status in ("unsupported",)
        assert quality.quality_label == "missing"

    def test_verify_claim_by_id_no_store(self):
        """verify_claim_by_id returns None without store."""
        service = VerificationService()
        result = service.verify_claim_by_id("nonexistent")
        assert result is None

    def test_verify_execution_claims_no_store(self):
        """verify_execution_claims returns empty without store."""
        service = VerificationService()
        results = service.verify_execution_claims("exec-none")
        assert results == []

    def test_verify_execution_claims(self):
        """verify_execution_claims handles empty results."""
        service = VerificationService()
        results = service.verify_execution_claims("exec-none", workspace_id="ws-none")
        assert results == []

    def test_verify_workspace_claims_no_store(self):
        """verify_workspace_claims returns empty without store."""
        service = VerificationService()
        results = service.verify_workspace_claims("ws-none")
        assert results == []

    def test_get_verification_summary_no_claims(self):
        """Empty summary returns zeros."""
        service = VerificationService()
        summary = service.get_verification_summary("ws-none")
        assert summary.total_claims == 0
        assert summary.supported_claims == 0
        assert summary.contradicted_claims == 0
        assert summary.average_confidence == 0.0

    def test_scan_workspace_contradictions_empty(self):
        """Scan without evidence returns empty."""
        service = VerificationService()
        contradictions = service.scan_workspace_contradictions("ws-none")
        assert contradictions == []

    def test_scan_claim_contradictions_no_store(self):
        """Scan claim contradictions without store returns empty."""
        service = VerificationService()
        contradictions = service.scan_claim_contradictions("cid-none")
        assert contradictions == []
