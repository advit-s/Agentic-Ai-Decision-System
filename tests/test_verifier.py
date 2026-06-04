from decision_system.ledger.verifier import verify_claims
from decision_system.models import Claim, EvidenceChunk


def test_verifier_marks_claim_without_evidence_as_unsupported():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="technical_analyst",
        claim_text="The legacy server supports OAuth2.",
        claim_type="technical",
    )

    updated, results = verify_claims([claim], [])

    assert updated[0].status == "unsupported"
    assert results[0].verification_notes


def test_verifier_marks_explicit_contradiction():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="risk_analyst",
        claim_text="Migration can happen without downtime.",
        claim_type="risk",
        evidence_ids=["doc-a:chunk-0001"],
    )
    evidence = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="CONTRADICTS: Migration can happen without downtime.",
        )
    ]

    updated, results = verify_claims([claim], evidence)

    assert updated[0].status == "contradicted"
    assert results[0].contradicting_evidence_ids == ["doc-a:chunk-0001"]
