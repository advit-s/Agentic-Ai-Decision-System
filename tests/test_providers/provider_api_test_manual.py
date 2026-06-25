"""Tests for the provider API endpoints."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Disable scheduler before importing app
from decision_system.api.app import set_scheduler_enabled

set_scheduler_enabled(False)

from decision_system.api.app import create_app


@pytest.fixture
def client(tmp_path: Path):
    """Create a test client with isolated storage."""
    os.environ["DECISION_SYSTEM_DATA_DIR"] = str(tmp_path)
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    os.environ.pop("DECISION_SYSTEM_DATA_DIR", None)
    if tmp_path.exists():
        shutil.rmtree(tmp_path, ignore_errors=True)


class TestProviderAPI:
    def test_list_empty(self, client):
        response = client.get("/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["providers"] == []

    def test_create_provider(self, client):
        response = client.post(
            "/providers",
            json={
                "name": "Local Ollama",
                "provider_type": "ollama",
                "base_url": "http://localhost:11434",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Local Ollama"
        assert data["provider_type"] == "ollama"
        assert data["base_url"] == "http://localhost:11434"
        assert "provider_id" in data

    def test_create_and_get(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Fake Provider",
                "provider_type": "fake",
            },
        )
        assert create_resp.status_code == 201
        provider_id = create_resp.json()["provider_id"]

        get_resp = client.get(f"/providers/{provider_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "Fake Provider"

    def test_get_nonexistent(self, client):
        response = client.get("/providers/nonexistent-id")
        assert response.status_code == 404

    def test_update_provider(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Test Provider",
                "provider_type": "fake",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        update_resp = client.put(
            f"/providers/{provider_id}",
            json={
                "default_model": "gpt-4",
            },
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["default_model"] == "gpt-4"

    def test_delete_provider(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Delete Me",
                "provider_type": "fake",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        delete_resp = client.delete(f"/providers/{provider_id}")
        assert delete_resp.status_code == 204

        get_resp = client.get(f"/providers/{provider_id}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent(self, client):
        response = client.delete("/providers/nonexistent")
        assert response.status_code == 404

    def test_list_after_create(self, client):
        client.post("/providers", json={"name": "Fake", "provider_type": "fake"})
        client.post("/providers", json={"name": "Ollama", "provider_type": "ollama"})

        response = client.get("/providers")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2

    def test_status_fake(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Fake",
                "provider_type": "fake",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        response = client.get(f"/providers/{provider_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] in ("configured", "healthy")

    def test_status_missing_api_key(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "OpenAI",
                "provider_type": "openai",
                "api_key_env": "MISSING_KEY_XYZ",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        response = client.get(f"/providers/{provider_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "missing_config"

    def test_test_fake_provider(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Fake Test",
                "provider_type": "fake",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        response = client.post(f"/providers/{provider_id}/test")
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_test_nonexistent(self, client):
        response = client.post("/providers/nonexistent/test")
        assert response.status_code == 404

    def test_models_endpoint(self, client):
        create_resp = client.post(
            "/providers",
            json={
                "name": "Fake Models",
                "provider_type": "fake",
            },
        )
        provider_id = create_resp.json()["provider_id"]

        response = client.get(f"/providers/{provider_id}/models")
        assert response.status_code == 200
        data = response.json()
        assert data["provider_id"] == provider_id

    def test_provider_types_list(self, client):
        response = client.get("/providers/types/list")
        assert response.status_code == 200
        data = response.json()
        assert "fake" in data
        assert "ollama" in data
        assert "openai_compatible" in data

    def test_default_provider(self, client):
        client.post("/providers", json={"name": "Fake", "provider_type": "fake"})
        client.post("/providers", json={"name": "Ollama", "provider_type": "ollama"})

        response = client.get("/providers/default")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Fake"

    def test_default_empty(self, client):
        response = client.get("/providers/default")
        assert response.status_code == 200
        assert response.json() is None
