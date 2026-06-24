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
        assert "jira" in ids
        assert "slack" in ids
        assert "email" in ids
        assert len(set(ids)) == 5

    async def test_local_files_is_real(self, async_client):
        response = await async_client.get("/connectors")
        payload = response.json()
        lf = next(c for c in payload["connectors"] if c["connector_id"] == "local-files")
        assert lf["status"] == "real"
        assert lf["supports_import"] is True
        assert lf["supports_dry_run"] is True

    async def test_external_connectors_are_stubs(self, async_client):
        response = await async_client.get("/connectors")
        payload = response.json()
        for c in payload["connectors"]:
            if c["connector_id"] != "local-files":
                assert c["status"] == "stub"
                assert c["supports_import"] is False


class TestConnectorDetail:
    async def test_local_files_detail(self, async_client):
        response = await async_client.get("/connectors/local-files")
        assert response.status_code == 200
        d = response.json()["definition"]
        assert d["connector_id"] == "local-files"
        assert d["is_stub"] is False
        assert d["supports_dry_run"] is True

    async def test_github_is_stub(self, async_client):
        response = await async_client.get("/connectors/github")
        assert response.status_code == 200
        assert response.json()["definition"]["is_stub"] is True

    async def test_jira_is_stub(self, async_client):
        response = await async_client.get("/connectors/jira")
        assert response.status_code == 200
        assert response.json()["definition"]["is_stub"] is True

    async def test_slack_is_stub(self, async_client):
        response = await async_client.get("/connectors/slack")
        assert response.status_code == 200
        assert response.json()["definition"]["is_stub"] is True

    async def test_email_is_stub(self, async_client):
        response = await async_client.get("/connectors/email")
        assert response.status_code == 200
        assert response.json()["definition"]["is_stub"] is True

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
