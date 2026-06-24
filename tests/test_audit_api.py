"""Tests for workspace audit log API routes.

All tests are offline using the FastAPI TestClient. No external services.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from decision_system.api.app import set_scheduler_enabled
set_scheduler_enabled(False)

from decision_system.api.app import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Set up a test client with isolated temp directories."""
    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "test.md").write_text("Test document.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", f"api_chunks_{uuid4().hex}")
    monkeypatch.setenv("DECISION_PROVIDER", "fake")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    return TestClient(app, raise_server_exceptions=False)


class TestAuditEventsAPI:
    """Test the /workspaces/{id}/audit/* endpoints."""

    def test_list_audit_events(self, client):
        """GET /workspaces/{id}/audit/events returns event list."""
        resp = client.get("/workspaces/ws-1/audit/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert data["total"] >= 0

    def test_audit_events_have_required_fields(self, client):
        """Audit events contain event_id, event_type, actor, created_at."""
        resp = client.get("/workspaces/ws-1/audit/events")
        events = resp.json()["events"]
        if events:
            ev = events[0]
            assert "event_id" in ev
            assert "event_type" in ev
            assert "actor" in ev
            assert "created_at" in ev

    def test_audit_events_pagination(self, client):
        """Audit events support limit and offset."""
        resp = client.get("/workspaces/ws-1/audit/events?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["events"]) <= 5

    def test_audit_events_filter_by_type(self, client):
        """Audit events can be filtered by event_type."""
        resp = client.get("/workspaces/ws-1/audit/events?event_type=workflow_executed")
        assert resp.status_code == 200
        data = resp.json()
        for ev in data["events"]:
            assert ev["event_type"] == "workflow_executed"

    def test_audit_events_filter_by_actor(self, client):
        """Audit events can be filtered by actor."""
        resp = client.get("/workspaces/ws-1/audit/events?actor=local/system")
        assert resp.status_code == 200
        data = resp.json()
        for ev in data["events"]:
            assert ev["actor"] == "local/system"

    def test_audit_summary(self, client):
        """GET /workspaces/{id}/audit/summary returns aggregate counts."""
        resp = client.get("/workspaces/ws-1/audit/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "by_type" in data
        assert "by_actor" in data
        assert isinstance(data["total_events"], int)
        assert isinstance(data["by_type"], dict)
        assert isinstance(data["by_actor"], dict)
