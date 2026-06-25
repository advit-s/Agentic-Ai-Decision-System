from decision_system.ledger.verifier import verify_claims
from decision_system.llm.fake_provider import FakeProvider
from decision_system.models import AgentMemo, EvidenceChunk


def test_fake_provider_returns_structured_memos_and_claims():
    evidence = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning.",
        )
    ]
    provider = FakeProvider()

    technical = provider.technical_memo("Should we migrate billing?", evidence)
    risk = provider.risk_memo("Should we migrate billing?", evidence, technical)
    claims = provider.extract_claims("run-1", [technical, risk])

    assert isinstance(technical, AgentMemo)
    assert isinstance(risk, AgentMemo)
    assert claims
    assert claims[0].evidence_ids == ["doc-a:chunk-0001"]


def test_fake_provider_preserves_per_chunk_claim_citations_for_verification():
    evidence = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning.",
        ),
        EvidenceChunk(
            evidence_id="doc-a:chunk-0002",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0002",
            text="CONTRADICTS: Billing migration requires rollback planning.",
        ),
    ]
    provider = FakeProvider()

    technical = provider.technical_memo("Should we migrate billing?", evidence)
    risk = provider.risk_memo("Should we migrate billing?", evidence, technical)
    claims = provider.extract_claims("run-1", [technical, risk])
    verified_claims, _ = verify_claims(claims, evidence)

    statuses = {claim.status for claim in verified_claims}
    assert "verified" in statuses
    assert "contradicted" in statuses


def test_workflow_runs_to_final_report_without_loops():
    from decision_system.graph.workflow import build_workflow

    graph = build_workflow()
    result = graph.invoke(
        {
            "run_id": "run-1",
            "question": "Should we migrate billing?",
            "top_k": 3,
            "retrieved_evidence": [
                EvidenceChunk(
                    evidence_id="doc-a:chunk-0001",
                    document_id="doc-a",
                    source_path="company_docs/billing.md",
                    source_filename="billing.md",
                    chunk_id="chunk-0001",
                    text="Billing migration requires rollback planning.",
                )
            ],
        }
    )

    assert result["final_report"].markdown.startswith("# Decision Report")
    assert result["claims"]
    assert all(claim.status != "pending" for claim in result["claims"])
