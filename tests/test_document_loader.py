from decision_system.rag.loader import load_documents


def test_load_documents_reads_md_and_txt(tmp_path):
    docs_dir = tmp_path / "company_docs"
    docs_dir.mkdir()
    (docs_dir / "plan.md").write_text("Migration plan", encoding="utf-8")
    (docs_dir / "notes.txt").write_text("Incident notes", encoding="utf-8")
    (docs_dir / "ignore.json").write_text("{}", encoding="utf-8")

    docs = load_documents(docs_dir)

    assert len(docs) == 2
    assert {doc["source_filename"] for doc in docs} == {"plan.md", "notes.txt"}
    assert all(doc["document_id"].startswith("doc-") for doc in docs)
