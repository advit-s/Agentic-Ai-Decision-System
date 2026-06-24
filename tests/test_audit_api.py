"""Tests for workspace audit log API routes.

All tests are offline using httpx.AsyncClient with ASGITransport.
No external services.
"""
from __future__ import annotations

import pytest


class TestAuditEventsAPI:
    """Test the /workspaces/{id}/audit/* endpoints."""

    async def test_list_audit_events(self, async_client):
        """GET /workspaces/{id}/audit/events returns event list."""
        resp = await async_client.get("/workspaces/ws-1/audit/events")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)
        assert data["total"] >= 0

    async def test_audit_events_have_required_fields(self, async_client):
        """Audit events contain event_id, event_type, actor, created_at."""
        resp = await async_client.get("/workspaces/ws-1/audit/events")
        events = resp.json()["events"]
        if events:
            ev = events[0]
            assert "event_id" in ev
            assert "event_type" in ev
            assert "actor" in ev
            assert "created_at" in ev

    async def test_audit_events_pagination(self, async_client):
        """Audit events support limit and offset."""
        resp = await async_client.get("/workspaces/ws-1/audit/events?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["events"]) <= 5

    async def test_audit_events_filter_by_type(self, async_client):
        """Audit events can be filtered by event_type."""
        resp = await async_client.get(
            "/workspaces/ws-1/audit/events?event_type=workflow_executed"
        )
        assert resp.status_code == 200
        data = resp.json()
        for ev in data["events"]:
            assert ev["event_type"] == "workflow_executed"

    async def test_audit_events_filter_by_actor(self, async_client):
        """Audit events can be filtered by actor."""
        resp = await async_client.get(
            "/workspaces/ws-1/audit/events?actor=local/system"
        )
        assert resp.status_code == 200
        data = resp.json()
        for ev in data["events"]:
            assert ev["actor"] == "local/system"

    async def test_audit_summary(self, async_client):
        """GET /workspaces/{id}/audit/summary returns aggregate counts."""
        resp = await async_client.get("/workspaces/ws-1/audit/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_events" in data
        assert "by_type" in data
        assert "by_actor" in data
        assert isinstance(data["total_events"], int)
        assert isinstance(data["by_type"], dict)
        assert isinstance(data["by_actor"], dict)
