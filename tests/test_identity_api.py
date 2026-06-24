"""Tests for identity API routes.

All tests are offline using the FastAPI TestClient in mock mode.
No external services or API keys required.
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


class TestIdentityAPI:
    """Test the /identity/* endpoints."""

    def test_get_my_identity(self, client):
        """GET /identity/me returns the current user and permissions."""
        resp = client.get("/identity/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data
        assert "permissions" in data
        assert "security_mode" in data
        assert data["user"]["user_id"] == "local/system"
        assert data["user"]["role"] == "owner"
        assert isinstance(data["permissions"], list)
        assert len(data["permissions"]) > 0

    def test_get_my_identity_includes_all_permissions(self, client):
        """Default owner user has all permissions."""
        resp = client.get("/identity/me")
        data = resp.json()
        perms = data["permissions"]
        important_perms = [
            "settings.manage",
            "audit.read",
            "report.export",
            "review.resolve",
            "provider.manage",
            "workspace.manage",
        ]
        for p in important_perms:
            assert p in perms, f"Expected {p} in owner permissions"

    def test_list_users(self, client):
        """GET /identity/users returns the default user."""
        resp = client.get("/identity/users")
        assert resp.status_code == 200
        users = resp.json()
        assert isinstance(users, list)
        assert len(users) >= 1
        assert any(u["user_id"] == "local/system" for u in users)

    def test_create_user(self, client):
        """POST /identity/users creates a new user."""
        resp = client.post("/identity/users", json={
            "display_name": "Test Analyst",
            "role": "analyst",
        })
        assert resp.status_code == 200
        user = resp.json()
        assert user["display_name"] == "Test Analyst"
        assert user["role"] == "analyst"
        assert user["user_id"] != "local/system"

    def test_create_user_minimal(self, client):
        """POST /identity/users with just display_name."""
        resp = client.post("/identity/users", json={
            "display_name": "Minimal User",
        })
        assert resp.status_code == 200
        user = resp.json()
        assert user["display_name"] == "Minimal User"
        # Default role should be viewer
        assert user["role"] == "viewer"

    def test_get_user_by_id(self, client):
        """GET /identity/users/{user_id} returns a specific user."""
        # Create a user first
        create_resp = client.post("/identity/users", json={
            "display_name": "Specific User",
            "role": "reviewer",
        })
        user_id = create_resp.json()["user_id"]

        resp = client.get(f"/identity/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Specific User"

    def test_get_user_not_found(self, client):
        """GET /identity/users/{user_id} returns 404 for unknown user."""
        resp = client.get("/identity/users/nonexistent-user")
        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "user_not_found"

    def test_update_user(self, client):
        """PUT /identity/users/{user_id} updates a user."""
        create_resp = client.post("/identity/users", json={
            "display_name": "Original Name",
            "role": "viewer",
        })
        user_id = create_resp.json()["user_id"]

        resp = client.put(f"/identity/users/{user_id}", json={
            "display_name": "Updated Name",
            "role": "admin",
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["display_name"] == "Updated Name"
        assert updated["role"] == "admin"

    def test_delete_user(self, client):
        """DELETE /identity/users/{user_id} removes a user."""
        create_resp = client.post("/identity/users", json={
            "display_name": "Delete Me",
            "role": "viewer",
        })
        user_id = create_resp.json()["user_id"]

        resp = client.delete(f"/identity/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify user is gone
        get_resp = client.get(f"/identity/users/{user_id}")
        assert get_resp.status_code == 404

    def test_delete_default_user_returns_400(self, client):
        """DELETE /identity/users/local/system returns 400."""
        resp = client.delete("/identity/users/local/system")
        assert resp.status_code == 400
        assert "cannot_delete_default" in resp.json()["detail"]["code"]


class TestMembershipAPI:
    """Test the /workspaces/{id}/memberships endpoints."""

    def test_list_memberships(self, client):
        """GET /workspaces/{id}/memberships returns memberships."""
        resp = client.get("/workspaces/ws-1/memberships")
        assert resp.status_code == 200
        memberships = resp.json()
        assert isinstance(memberships, list)

    def test_add_membership(self, client):
        """POST /workspaces/{id}/memberships adds a user to a workspace."""
        # Create a user first
        user_resp = client.post("/identity/users", json={
            "display_name": "Member User",
            "role": "analyst",
        })
        user_id = user_resp.json()["user_id"]

        resp = client.post("/workspaces/ws-1/memberships", json={
            "user_id": user_id,
            "role": "analyst",
        })
        assert resp.status_code == 200
        m = resp.json()
        assert m["workspace_id"] == "ws-1"
        assert m["user_id"] == user_id
        assert m["role"] == "analyst"

    def test_add_membership_user_not_found(self, client):
        """POST /workspaces/{id}/memberships with unknown user returns 404."""
        resp = client.post("/workspaces/ws-1/memberships", json={
            "user_id": "nonexistent",
            "role": "viewer",
        })
        assert resp.status_code == 404

    def test_update_membership(self, client):
        """PUT /workspaces/{id}/memberships/{user_id} updates role."""
        user_resp = client.post("/identity/users", json={
            "display_name": "Update Member",
            "role": "viewer",
        })
        user_id = user_resp.json()["user_id"]

        # Add membership
        client.post("/workspaces/ws-1/memberships", json={
            "user_id": user_id,
            "role": "viewer",
        })

        # Update role
        resp = client.put(f"/workspaces/ws-1/memberships/{user_id}", json={
            "role": "admin",
        })
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_remove_membership(self, client):
        """DELETE /workspaces/{id}/memberships/{user_id} removes membership."""
        user_resp = client.post("/identity/users", json={
            "display_name": "Remove Member",
            "role": "viewer",
        })
        user_id = user_resp.json()["user_id"]

        # Add membership
        client.post("/workspaces/ws-1/memberships", json={
            "user_id": user_id,
            "role": "viewer",
        })

        # Remove
        resp = client.delete(f"/workspaces/ws-1/memberships/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "removed"


class TestSecuritySettingsAPI:
    """Test the /identity/settings endpoints."""

    def test_get_security_settings(self, client):
        """GET /identity/settings returns security settings."""
        resp = client.get("/identity/settings")
        assert resp.status_code == 200
        settings = resp.json()
        assert "security_mode" in settings
        assert settings["security_mode"] in ("demo", "governed")

    def test_update_security_settings_mode(self, client):
        """PUT /identity/settings updates security mode."""
        resp = client.put("/identity/settings", json={
            "security_mode": "governed",
        })
        assert resp.status_code == 200
        assert resp.json()["security_mode"] == "governed"

        # Verify persist
        get_resp = client.get("/identity/settings")
        assert get_resp.json()["security_mode"] == "governed"

    def test_update_security_settings_export_admin(self, client):
        """PUT /identity/settings toggles export admin requirement."""
        resp = client.put("/identity/settings", json={
            "exports_require_admin": True,
        })
        assert resp.status_code == 200
        assert resp.json()["exports_require_admin"] is True

    def test_update_security_settings_review_role(self, client):
        """PUT /identity/settings toggles review role requirement."""
        resp = client.put("/identity/settings", json={
            "review_requires_reviewer_role": False,
        })
        assert resp.status_code == 200
        assert resp.json()["review_requires_reviewer_role"] is False

    def test_update_security_settings_retention(self, client):
        """PUT /identity/settings changes audit retention."""
        resp = client.put("/identity/settings", json={
            "audit_retention_days": 180,
        })
        assert resp.status_code == 200
        assert resp.json()["audit_retention_days"] == 180


class TestPermissionsAPI:
    """Test the /identity/permissions endpoint."""

    def test_get_permission_matrix(self, client):
        """GET /identity/permissions returns the permission matrix."""
        resp = client.get("/identity/permissions")
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data
        assert "permissions" in data
        assert "matrix" in data
        assert "owner" in data["roles"]
        assert "settings.manage" in data["permissions"]

    def test_permission_matrix_owner_has_all(self, client):
        """Owner role has all permissions."""
        resp = client.get("/identity/permissions")
        data = resp.json()
        owner_perms = data["matrix"]["owner"]
        all_perms = data["permissions"]
        for p in all_perms:
            assert p in owner_perms, f"Owner missing permission: {p}"

    def test_permission_matrix_viewer_limited(self, client):
        """Viewer role has limited permissions."""
        resp = client.get("/identity/permissions")
        data = resp.json()
        viewer_perms = data["matrix"]["viewer"]
        # Viewer should have evidence.search and claim.manage
        assert "evidence.search" in viewer_perms
        # Viewer should NOT have settings.manage or provider.manage
        assert "settings.manage" not in viewer_perms
        assert "provider.manage" not in viewer_perms
