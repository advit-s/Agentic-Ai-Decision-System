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
        "/workspaces/ws-unsupported/data-sources/upload?filename=test.pdf",
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
