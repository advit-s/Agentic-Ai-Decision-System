from decision_system.rag.chunker import chunk_documents


def test_chunk_documents_preserves_stable_ids():
    docs = [
        {
            "document_id": "doc-test",
            "source_path": "company_docs/plan.md",
            "source_filename": "plan.md",
            "text": "A" * 1200,
        }
    ]

    chunks = chunk_documents(docs, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 2
    assert chunks[0].evidence_id == "doc-test:chunk-0001"
    assert chunks[1].evidence_id == "doc-test:chunk-0002"
    assert chunks[0].source_filename == "plan.md"
