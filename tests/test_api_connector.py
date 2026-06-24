"""Tests for the FastAPI connector endpoints."""
from __future__ import annotations

import pytest


class TestConnectorList:
    async def test_list_returns_json(self, async_client):
        response = await async_client.get("/connectors")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        payload = response.json()
        assert isinstance(payload, dict)
        assert "connectors" in payload

    async def test_lists_all_five_connectors(self, async_client):
        response = await async_client.get("/connectors")
        payload = response.json()
        ids = [c["connector_id"] for c in payload["connectors"]]
        assert "local-files" in ids
        assert "github" in ids
        assert "url-import" in ids
        assert "notion" in ids
        assert "google-drive" in ids
        assert len(set(ids)) == 5

    async def test_local_files_is_real(self, async_client):
        response = await async_client.get("/connectors")
        payload = response.json()
        lf = next(c for c in payload["connectors"] if c["connector_id"] == "local-files")
        assert lf["status"] == "real"
        assert lf["supports_import"] is True
        assert lf["supports_dry_run"] is True

    async def test_external_connectors_are_unavailable(self, async_client):
        response = await async_client.get("/connectors")
        payload = response.json()
        for c in payload["connectors"]:
            if c["connector_id"] in ("notion", "google-drive"):
                assert c["status"] == "unavailable"
                assert c["is_stub"] is True
                assert c["supports_import"] is False


class TestConnectorDetail:
    async def test_local_files_detail(self, async_client):
        response = await async_client.get("/connectors/local-files")
        assert response.status_code == 200
        d = response.json()["definition"]
        assert d["connector_id"] == "local-files"
        assert d["is_stub"] is False
        assert d["supports_dry_run"] is True

    async def test_github_is_real(self, async_client):
        response = await async_client.get("/connectors/github")
        assert response.status_code == 200
        d = response.json()["definition"]
        assert d["is_stub"] is False
        assert d["status"] == "real"

    async def test_notion_is_unavailable(self, async_client):
        response = await async_client.get("/connectors/notion")
        assert response.status_code == 200
        d = response.json()["definition"]
        assert d["is_stub"] is True
        assert d["status"] == "unavailable"

    async def test_google_drive_is_unavailable(self, async_client):
        response = await async_client.get("/connectors/google-drive")
        assert response.status_code == 200
        d = response.json()["definition"]
        assert d["is_stub"] is True
        assert d["status"] == "unavailable"

    async def test_unknown_returns_404(self, async_client):
        response = await async_client.get("/connectors/does-not-exist")
        assert response.status_code == 404


class TestConnectorJobs:
    async def test_list_jobs_returns_json(self, async_client):
        response = await async_client.get("/connectors/jobs")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        payload = response.json()
        if isinstance(payload, dict):
            assert "jobs" in payload
        else:
            assert isinstance(payload, list)

    async def test_empty_jobs_list(self, async_client):
        response = await async_client.get("/connectors/jobs")
        payload = response.json()
        assert isinstance(payload, dict)
        assert isinstance(payload["jobs"], list)


class TestConnectorConfigCRUD:
    async def test_create_connector_config(self, async_client):
        response = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Test Local Folder",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp/test"},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "connector" in payload
        assert payload["connector"]["name"] == "Test Local Folder"
        assert payload["connector"]["mode"] == "read_only"

    async def test_list_workspace_connectors(self, async_client):
        response = await async_client.get("/workspaces/default/connectors")
        assert response.status_code == 200
        payload = response.json()
        assert "connectors" in payload
        assert isinstance(payload["connectors"], list)

    async def test_get_connector_config(self, async_client):
        # Create first
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "My Connector",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp/data"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        # Get it
        response = await async_client.get(f"/workspaces/default/connectors/{cid}")
        assert response.status_code == 200
        payload = response.json()
        assert payload["connector"]["connector_id"] == cid
        assert payload["connector"]["name"] == "My Connector"

    async def test_update_connector_config(self, async_client):
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Original",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        response = await async_client.put(
            f"/workspaces/default/connectors/{cid}",
            json={"name": "Updated Name"},
        )
        assert response.status_code == 200
        assert response.json()["connector"]["name"] == "Updated Name"

    async def test_delete_connector_config(self, async_client):
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "To Delete",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        response = await async_client.delete(f"/workspaces/default/connectors/{cid}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    async def test_get_nonexistent_returns_404(self, async_client):
        response = await async_client.get("/workspaces/default/connectors/nonexistent-id")
        assert response.status_code == 404

    async def test_create_invalid_type_returns_400(self, async_client):
        response = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Bad",
                "connector_type": "nonexistent-type",
                "config": {},
            },
        )
        assert response.status_code == 400

    async def test_create_unavailable_type_returns_400(self, async_client):
        response = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Notion",
                "connector_type": "notion",
                "config": {},
            },
        )
        assert response.status_code == 400

    async def test_secrets_redacted(self, async_client):
        response = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Secret Test",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp", "api_key": "supersecret123"},
            },
        )
        assert response.status_code == 200
        config = response.json()["connector"]["config"]
        assert config.get("api_key") == "***REDACTED***"

    async def test_mode_is_always_read_only(self, async_client):
        response = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Read Only Test",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        assert response.status_code == 200
        assert response.json()["connector"]["mode"] == "read_only"


class TestConnectorOperations:
    async def test_test_connection(self, async_client):
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Test Conn",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        response = await async_client.post(f"/workspaces/default/connectors/{cid}/test")
        assert response.status_code == 200
        payload = response.json()
        assert "result" in payload
        assert "success" in payload["result"]

    async def test_list_items(self, async_client):
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "List Items Test",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        response = await async_client.get(f"/workspaces/default/connectors/{cid}/items")
        assert response.status_code == 200
        payload = response.json()
        assert "items" in payload
        assert "count" in payload

    async def test_import_creates_job(self, async_client):
        create_resp = await async_client.post(
            "/workspaces/default/connectors",
            json={
                "name": "Import Test",
                "connector_type": "local-files",
                "config": {"folder_path": "/tmp"},
            },
        )
        cid = create_resp.json()["connector"]["connector_id"]

        response = await async_client.post(
            f"/workspaces/default/connectors/{cid}/import",
            json={"item_ids": None},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "result" in payload
        assert "job_id" in payload["result"]
