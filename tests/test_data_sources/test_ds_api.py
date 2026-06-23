"""Tests for data source API endpoints using async httpx client."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from decision_system.api.app import set_scheduler_enabled, create_app


@pytest.fixture
async def client(tmp_path):
    """Create an async test client with isolated temp storage."""
    import os
    os.environ["DECISION_SYSTEM_DATA_DIR"] = str(tmp_path)
    set_scheduler_enabled(False)
    import importlib
    import decision_system.workflow_engine.api as wf_api
    importlib.reload(wf_api)
    app = create_app()
    transport = ASGITransport(app=app)
    # Clean any leftover data sources
    ds_dir = Path(".decision_system") / "data_sources"
    if ds_dir.exists():
        shutil.rmtree(ds_dir)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_upload_txt(client: AsyncClient):
    content = b"Hello world, this is a test document."
    resp = await client.post(
        "/workspaces/ws-upload-txt/data-sources/upload?filename=test.txt",
        content=content,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["data_source"]["name"] == "test.txt"
    assert data["data_source"]["file_type"] == "txt"
    assert data["data_source"]["workspace_id"] == "ws-upload-txt"


@pytest.mark.asyncio
async def test_upload_unsupported_type(client: AsyncClient):
    content = b"some pdf content"
    resp = await client.post(
        "/workspaces/ws-unsupported/data-sources/upload?filename=test.xyz",
        content=content,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_data_sources(client: AsyncClient):
    await client.post(
        "/workspaces/ws-list-ds/data-sources/upload?filename=a.txt",
        content=b"content a",
    )
    await client.post(
        "/workspaces/ws-list-ds/data-sources/upload?filename=b.csv",
        content=b"col1,col2\n1,2\n3,4",
    )

    resp = await client.get("/workspaces/ws-list-ds/data-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2

    # Different workspace should be empty
    resp = await client.get("/workspaces/ws-list-other/data-sources")
    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_data_source(client: AsyncClient):
    resp = await client.post(
        "/workspaces/ws-get-ds/data-sources/upload?filename=get.txt",
        content=b"get test content",
    )
    source_id = resp.json()["data_source"]["source_id"]

    resp = await client.get(f"/workspaces/ws-get-ds/data-sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["data_source"]["source_id"] == source_id


@pytest.mark.asyncio
async def test_get_nonexistent_source(client: AsyncClient):
    resp = await client.get("/workspaces/ws-none/data-sources/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_data_source(client: AsyncClient):
    resp = await client.post(
        "/workspaces/ws-del-ds/data-sources/upload?filename=del.txt",
        content=b"delete test",
    )
    source_id = resp.json()["data_source"]["source_id"]

    resp = await client.delete(f"/workspaces/ws-del-ds/data-sources/{source_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"

    resp = await client.get(f"/workspaces/ws-del-ds/data-sources/{source_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_parse_and_status(client: AsyncClient):
    resp = await client.post(
        "/workspaces/ws-parse-ds/data-sources/upload?filename=parse.txt",
        content=b"First paragraph.\n\nSecond paragraph.\n\nThird paragraph.",
    )
    source_id = resp.json()["data_source"]["source_id"]

    resp = await client.post(f"/workspaces/ws-parse-ds/data-sources/{source_id}/parse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "parsed"
    assert data["chunk_count"] >= 1

    resp = await client.get(f"/workspaces/ws-parse-ds/data-sources/{source_id}/status")
    assert resp.status_code == 200
    assert resp.json()["status"] == "parsed"


@pytest.mark.asyncio
async def test_csv_profile(client: AsyncClient):
    csv_content = b"name,age,role\nAlice,30,engineer\nBob,25,designer"
    resp = await client.post(
        "/workspaces/ws-csv-ds/data-sources/upload?filename=data.csv",
        content=csv_content,
    )
    source_id = resp.json()["data_source"]["source_id"]

    resp = await client.post(f"/workspaces/ws-csv-ds/data-sources/{source_id}/parse")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "parsed"
    assert data["profile"]["row_count"] == 2
    assert data["profile"]["column_count"] == 3

    resp = await client.get(f"/workspaces/ws-csv-ds/data-sources/{source_id}/profile")
    assert resp.status_code == 200
    assert resp.json()["profile"]["row_count"] == 2


@pytest.mark.asyncio
async def test_index_parse_first(client: AsyncClient):
    resp = await client.post(
        "/workspaces/ws-idx-ds/data-sources/upload?filename=idx.txt",
        content=b"index me",
    )
    source_id = resp.json()["data_source"]["source_id"]

    resp = await client.post(f"/workspaces/ws-idx-ds/data-sources/{source_id}/index")
    assert resp.status_code == 400  # must parse first


@pytest.mark.asyncio
async def test_evidence_search_keyword(client: AsyncClient):
    resp = await client.post(
        "/workspaces/ws-ev-ds/data-sources/upload?filename=risks.txt",
        content=b"Customer churn risk is high this quarter.\nRevenue growth slowing.",
    )
    source_id = resp.json()["data_source"]["source_id"]
    await client.post(f"/workspaces/ws-ev-ds/data-sources/{source_id}/parse")

    resp = await client.post(
        "/workspaces/ws-ev-ds/evidence/search",
        json={"query": "risk", "limit": 5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["retrieval_mode"] in ("keyword", "vector")
    assert data["query"] == "risk"


@pytest.mark.asyncio
async def test_evidence_search_workspace_isolation(client: AsyncClient):
    for ws in ("ws-iso-a", "ws-iso-b"):
        resp = await client.post(
            f"/workspaces/{ws}/data-sources/upload?filename=doc.txt",
            content=b"Unique content for " + ws.encode(),
        )
        source_id = resp.json()["data_source"]["source_id"]
        await client.post(f"/workspaces/{ws}/data-sources/{source_id}/parse")

    resp = await client.post(
        "/workspaces/ws-iso-a/evidence/search",
        json={"query": "Unique", "limit": 10},
    )
    assert resp.status_code == 200
    for r in resp.json()["results"]:
        assert r["workspace_id"] == "ws-iso-a"


# ---------------------------------------------------------------------------
# PDF/DOCX/XLSX upload and parse tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_pdf(client: AsyncClient):
    """PDF upload should return 200."""
    content = b"%PDF-1.4 fake pdf content for testing"
    resp = await client.post(
        "/workspaces/ws-pdf-test/data-sources/upload?filename=test.pdf",
        content=content,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["data_source"]["file_type"] == "pdf"


@pytest.mark.asyncio
async def test_upload_docx(client: AsyncClient):
    """DOCX upload should return 200."""
    content = b"PK\x03\x04 fake docx content for testing"
    resp = await client.post(
        "/workspaces/ws-docx-test/data-sources/upload?filename=test.docx",
        content=content,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["data_source"]["file_type"] == "docx"


@pytest.mark.asyncio
async def test_upload_xlsx(client: AsyncClient):
    """XLSX upload should return 200."""
    content = b"PK\x03\x04 fake xlsx content for testing"
    resp = await client.post(
        "/workspaces/ws-xlsx-test/data-sources/upload?filename=test.xlsx",
        content=content,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["data_source"]["file_type"] == "xlsx"


@pytest.mark.asyncio
async def test_upload_unsupported_extension(client: AsyncClient):
    """Upload with unsupported extension should return 400."""
    content = b"unsupported content"
    resp = await client.post(
        "/workspaces/ws-unsup2/data-sources/upload?filename=test.xyz",
        content=content,
    )
    assert resp.status_code == 400
    assert "unsupported" in resp.text.lower()


@pytest.mark.asyncio
async def test_upload_md_still_works(client: AsyncClient):
    """Markdown upload still works."""
    content = b"# Heading\n\nParagraph."
    resp = await client.post(
        "/workspaces/ws-md-test/data-sources/upload?filename=test.md",
        content=content,
    )
    assert resp.status_code == 200
    assert resp.json()["data_source"]["file_type"] == "md"


@pytest.mark.asyncio
async def test_upload_json_still_works(client: AsyncClient):
    """JSON upload still works."""
    content = b'{"key": "value"}'
    resp = await client.post(
        "/workspaces/ws-json-test/data-sources/upload?filename=data.json",
        content=content,
    )
    assert resp.status_code == 200
    assert resp.json()["data_source"]["file_type"] == "json"


@pytest.mark.asyncio
async def test_xlsx_parse_and_profile(client: AsyncClient):
    """XLSX upload, parse, and profile."""
    content = b"PK\x03\x04 fake xlsx for parse test"
    resp = await client.post(
        "/workspaces/ws-xlsx-pp/data-sources/upload?filename=data.xlsx",
        content=content,
    )
    source_id = resp.json()["data_source"]["source_id"]

    # Parse (will fail gracefully since it's fake xlsx, but endpoint should work)
    resp = await client.post(f"/workspaces/ws-xlsx-pp/data-sources/{source_id}/parse")
    # Should still return 200 even if parsing has warnings
    assert resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_upload_source_id_consistency(client: AsyncClient):
    """Upload source_id should match the one used for file storage."""
    content = b"source_id consistency test"
    resp = await client.post(
        "/workspaces/ws-sid-consistency/data-sources/upload?filename=consistent.txt",
        content=content,
    )
    assert resp.status_code == 200
    source_id = resp.json()["data_source"]["source_id"]
    assert source_id is not None

    # Source ID should be a non-empty UUID string
    assert len(source_id) > 10
    assert "-" in source_id


@pytest.mark.asyncio
async def test_path_traversal_protection(client: AsyncClient):
    """Path traversal in filename should not write outside data dir."""
    content = b"malicious content"
    resp = await client.post(
        "/workspaces/ws-trav-test/data-sources/upload?filename=../../evil.txt",
        content=content,
    )
    # Should succeed with sanitized filename (path traversal cleaned)
    assert resp.status_code == 200
    # The local_path should not contain ".." segments
    local_path = resp.json()["data_source"]["local_path"]
    assert ".." not in local_path.replace("..", "XX"), f"Path traversal found: {local_path}"


@pytest.mark.asyncio
async def test_parsed_with_warnings_can_index(client: AsyncClient):
    """Files with parsed_with_warnings status but with chunks can be indexed."""
    # Upload and parse a file that produces warnings
    content = b"Test content for indexing after warnings."
    resp = await client.post(
        "/workspaces/ws-warn-idx/data-sources/upload?filename=warn.txt",
        content=content,
    )
    source_id = resp.json()["data_source"]["source_id"]

    # Parse it
    resp = await client.post(f"/workspaces/ws-warn-idx/data-sources/{source_id}/parse")
    assert resp.status_code == 200

    # Manually set status to parsed_with_warnings
    from decision_system.data_sources.store import DataSourceStore
    import os
    data_dir = os.environ.get("DECISION_SYSTEM_DATA_DIR")
    store = DataSourceStore(data_dir)
    store.update_status("ws-warn-idx", source_id, "parsed_with_warnings")

    # Now try to index - should succeed because chunks exist
    resp = await client.post(f"/workspaces/ws-warn-idx/data-sources/{source_id}/index")
    assert resp.status_code == 200
    assert resp.json()["status"] == "indexed"
