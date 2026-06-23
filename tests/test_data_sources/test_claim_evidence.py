"""Tests for claims linked to evidence references."""

import tempfile
from pathlib import Path

from decision_system.models import Claim
from decision_system.workflow_engine.stores.claim_store import JSONClaimStore


def test_claim_with_evidence_ids():
    claim = Claim(
        claim_id="c1",
        run_id="r1",
        source_agent="test",
        claim_text="Test claim",
    claim_type="assumption",
        evidence_ids=["ev1", "ev2"],
        source_ids=["src1"],
        chunk_ids=["chunk1"],
        evidence_snippets=["Revenue declined 10%"],
    )
    assert claim.evidence_ids == ["ev1", "ev2"]
    assert claim.source_ids == ["src1"]
    assert claim.evidence_snippets == ["Revenue declined 10%"]


def test_store_claim_with_evidence():
    with tempfile.TemporaryDirectory() as tmp:
        store = JSONClaimStore(Path(tmp))
        claim = store.add_claim(
            claim_text="Risk is high",
            source_agent="analyst",
            evidence_ids=["ev1", "ev2"],
            source_ids=["src1"],
            chunk_ids=["ch1"],
            evidence_snippets=["Customer churn rate increased"],
            workspace_id="ws1",
            execution_id="exec1",
        )
        assert claim.evidence_ids == ["ev1", "ev2"]
        assert claim.source_ids == ["src1"]
        assert claim.evidence_snippets == ["Customer churn rate increased"]

        loaded = store.load(claim.claim_id)
        assert loaded is not None
        assert loaded.source_ids == ["src1"]


def test_summary_evidence_coverage():
    with tempfile.TemporaryDirectory() as tmp:
        store = JSONClaimStore(Path(tmp))
        # Create a claim with evidence
        store.add_claim(
            claim_text="Claim with evidence",
            source_agent="test",
            evidence_ids=["ev1"],
            workspace_id="ws1",
            execution_id="exec1",
        )
        # Create a claim without evidence
        store.add_claim(
            claim_text="Claim without evidence",
            source_agent="test",
            workspace_id="ws1",
            execution_id="exec1",
        )
        summary = store.summary(workspace_id="ws1", execution_id="exec1")
        assert summary["total"] == 2
        assert summary["claims_with_evidence"] >= 1
        assert summary["claims_without_evidence"] >= 0
        assert "evidence_coverage_score_v2" in summary
