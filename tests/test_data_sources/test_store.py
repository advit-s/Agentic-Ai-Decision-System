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


# ---------------------------------------------------------------------------
# Phase 2: DataSourceStore honors DECISION_SYSTEM_DATA_DIR
# ---------------------------------------------------------------------------


import os


def test_default_base_dir_uses_env_var():
    """DataSourceStore without arguments should use DECISION_SYSTEM_DATA_DIR."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["DECISION_SYSTEM_DATA_DIR"] = tmp
        try:
            store = DataSourceStore()
            # A file created should be in tmp, not .decision_system
            ds = store.create("ws-env", "test.txt", "document", "txt", "test.txt", "/tmp/test.txt")
            source_path = store._source_path("ws-env", ds.source_id)
            assert str(tmp) in str(source_path), f"Expected {tmp} in {source_path}"
        finally:
            del os.environ["DECISION_SYSTEM_DATA_DIR"]


def test_path_traversal_sanitization():
    """sanitize_filename should remove path components."""
    from decision_system.data_sources.store import sanitize_filename
    assert sanitize_filename("../../evil.txt") == "evil.txt"
    assert sanitize_filename("/etc/passwd") == "passwd"
    assert sanitize_filename("normal.txt") == "normal.txt"
    assert sanitize_filename("") == "unnamed_file"


def test_store_uploaded_file_with_path_traversal():
    """store_uploaded_file should sanitize path traversal filenames."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        path_str = store.store_uploaded_file("ws-trav", "src1", "../../evil.txt", b"test")
        path = Path(path_str)
        # File should be inside tmp/files/ws-trav/
        assert str(path).startswith(str(Path(tmp) / "files" / "ws-trav"))
        assert path.exists()
        assert path.read_bytes() == b"test"


def test_create_with_explicit_source_id():
    """store.create() should accept an optional source_id."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        from uuid import uuid4
        my_id = str(uuid4())
        ds = store.create(
            workspace_id="ws-sid",
            name="test.txt",
            source_type="document",
            file_type="txt",
            original_filename="test.txt",
            local_path="/tmp/test.txt",
            source_id=my_id,
        )
        assert ds.source_id == my_id


def test_delete_removes_uploaded_file():
    """delete should remove the uploaded file."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        store.store_uploaded_file("ws-del", "src-del", "del.txt", b"delete me")
        file_path = store.get_uploaded_file_path("ws-del", "src-del", "del.txt")
        assert file_path.exists()
        store.delete_uploaded_file("ws-del", "src-del", "del.txt")
        assert not file_path.exists()


def test_search_returns_original_filename():
    """Evidence search results should show original_filename, not stored path."""
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        store = DataSourceStore(base_dir=tmp)
        ds = store.create(
            workspace_id="ws-orig",
            name="stored_uuid_report.pdf",  # stored name
            source_type="document",
            file_type="pdf",
            original_filename="Q2_Financial_Report.pdf",  # original name
            local_path="/tmp/stored_uuid_report.pdf",
        )
        store.save_chunks([
            DataSourceChunk(
                chunk_id="c1", source_id=ds.source_id, workspace_id="ws-orig",
                text="Revenue grew 15% this quarter", chunk_index=0,
            ),
        ])
        results = store.search_chunks_keyword("ws-orig", "revenue")
        assert len(results) >= 1
        # Source name should be original filename, not stored name
        assert results[0].source_name == "Q2_Financial_Report.pdf"
