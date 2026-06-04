from decision_system.models import EvidenceChunk
from decision_system.rag.retriever import retrieve_evidence
from decision_system.rag.vector_store import index_chunks


def test_retrieval_returns_citation_ready_evidence(tmp_path):
    store_dir = tmp_path / "chroma"
    chunks = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning and staged deployment.",
        )
    ]

    index_chunks(chunks, store_dir=store_dir, collection_name="test_chunks")
    results = retrieve_evidence(
        "billing rollback migration",
        store_dir=store_dir,
        collection_name="test_chunks",
        top_k=3,
    )

    assert len(results) == 1
    assert results[0].evidence_id == "doc-a:chunk-0001"
    assert results[0].source_filename == "billing.md"
    assert results[0].score is not None
