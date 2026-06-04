from decision_system.ledger.claim_ledger import ClaimLedger
from decision_system.models import Claim, EvidenceChunk


def test_claim_defaults_to_pending():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="technical_analyst",
        claim_text="Billing migration requires rollback planning.",
        claim_type="technical",
    )

    assert claim.status == "pending"
    assert claim.evidence_ids == []
    assert claim.confidence == "low"


def test_evidence_chunk_preserves_source_metadata():
    chunk = EvidenceChunk(
        evidence_id="doc-a:chunk-0001",
        document_id="doc-a",
        source_path="company_docs/plan.md",
        source_filename="plan.md",
        chunk_id="chunk-0001",
        text="Migration requires rollback planning.",
    )

    assert chunk.source_filename == "plan.md"
    assert chunk.chunk_id == "chunk-0001"


def test_ledger_preserves_contradicted_claims():
    ledger = ClaimLedger()
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="risk_analyst",
        claim_text="Migration can happen without downtime.",
        claim_type="risk",
    )

    ledger.add_claims([claim])
    ledger.update_status(
        claim_id="claim-1",
        status="contradicted",
        confidence="high",
        verification_notes="Evidence explicitly contradicts the claim.",
        contradicting_evidence_ids=["doc-a:chunk-0001"],
    )

    stored = ledger.all_claims()[0]
    assert stored.status == "contradicted"
    assert stored.contradicting_evidence_ids == ["doc-a:chunk-0001"]
