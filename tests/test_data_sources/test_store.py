"""Tests for data source store (create/list/get/delete/workspace-scoped)."""

import tempfile
from pathlib import Path

from decision_system.data_sources.store import DataSourceStore
from decision_system.data_sources.models import DataSourceChunk


def test_create_and_load():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds = store.create(
            workspace_id="ws1",
            name="test.txt",
            source_type="document",
            file_type="txt",
            original_filename="test.txt",
            local_path="/tmp/test.txt",
        )
        assert ds.source_id is not None
        assert ds.workspace_id == "ws1"
        assert ds.status == "uploaded"

        loaded = store.load("ws1", ds.source_id)
        assert loaded is not None
        assert loaded.name == "test.txt"
        assert loaded.file_type == "txt"


def test_list_by_workspace():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        store.create("ws1", "a.txt", "document", "txt", "a.txt", "/tmp/a.txt")
        store.create("ws1", "b.csv", "dataset", "csv", "b.csv", "/tmp/b.csv")

        sources = store.list_by_workspace("ws1")
        assert len(sources) == 2

        # Different workspace should be empty
        sources2 = store.list_by_workspace("ws2")
        assert len(sources2) == 0


def test_delete():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds = store.create("ws1", "d.txt", "document", "txt", "d.txt", "/tmp/d.txt")
        sid = ds.source_id

        assert store.load("ws1", sid) is not None
        assert store.delete("ws1", sid) is True
        assert store.load("ws1", sid) is None
        assert store.delete("ws1", sid) is False  # already gone


def test_update_status():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds = store.create("ws1", "s.txt", "document", "txt", "s.txt", "/tmp/s.txt")

        updated = store.update_status("ws1", ds.source_id, "parsed")
        assert updated is not None
        assert updated.status == "parsed"

        updated2 = store.update_status("ws1", ds.source_id, "failed", "parse error")
        assert updated2 is not None
        assert updated2.status == "failed"
        assert updated2.error_message == "parse error"


def test_store_and_load_chunks():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds = store.create("ws1", "d.txt", "document", "txt", "d.txt", "/tmp/d.txt")

        chunks = [
            DataSourceChunk(chunk_id="c1", source_id=ds.source_id, workspace_id="ws1", text="chunk one", chunk_index=0),
            DataSourceChunk(chunk_id="c2", source_id=ds.source_id, workspace_id="ws1", text="chunk two", chunk_index=1),
        ]
        store.save_chunks(chunks)

        loaded = store.load_chunks("ws1", ds.source_id)
        assert len(loaded) == 2
        assert loaded[0].text == "chunk one"

        # Delete chunks
        store.delete_chunks("ws1", ds.source_id)
        assert len(store.load_chunks("ws1", ds.source_id)) == 0


def test_keyword_search():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds1 = store.create("ws1", "risks.txt", "document", "txt", "risks.txt", "/tmp/risks.txt")
        ds2 = store.create("ws1", "revenue.csv", "dataset", "csv", "revenue.csv", "/tmp/revenue.csv")

        # Store chunks for search
        store.save_chunks([
            DataSourceChunk(chunk_id="c1", source_id=ds1.source_id, workspace_id="ws1",
                          text="Customer churn risk is high this quarter", chunk_index=0),
            DataSourceChunk(chunk_id="c2", source_id=ds1.source_id, workspace_id="ws1",
                          text="Revenue growth is slowing down", chunk_index=1),
            DataSourceChunk(chunk_id="c3", source_id=ds2.source_id, workspace_id="ws1",
                          text="Monthly revenue: 100k, 120k, 110k", chunk_index=0),
        ])

        # Search for "risk"
        results = store.search_chunks_keyword("ws1", "risk")
        assert len(results) >= 1
        assert any("risk" in r.text.lower() for r in results)

        # Search for "revenue"
        results = store.search_chunks_keyword("ws1", "revenue")
        assert len(results) >= 2

        # Workspace isolation
        results = store.search_chunks_keyword("ws2", "risk")
        assert len(results) == 0

        # Limit
        results = store.search_chunks_keyword("ws1", "revenue", limit=1)
        assert len(results) <= 1


def test_store_uploaded_file():
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        path = store.store_uploaded_file("ws1", "src1", "test.txt", b"hello world")
        assert Path(path).exists()
        assert Path(path).read_bytes() == b"hello world"

        # Verify file under correct path
        files_dir = Path(tmp) / "files" / "ws1"
        assert files_dir.exists()
        assert len(list(files_dir.iterdir())) == 1
