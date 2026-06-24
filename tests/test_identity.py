"""Tests for the local identity, role, and permission system.

All tests are offline and require no external services or API keys.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from decision_system.identity.models import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    LocalUser,
    Permission,
    UserRole,
    WorkspaceMembership,
    get_default_local_user,
)
from decision_system.identity.settings import (
    SecuritySettings,
    is_demo_mode,
    load_settings,
    save_settings,
    update_settings,
)
from decision_system.identity.store import (
    create_user,
    delete_membership,
    delete_user,
    ensure_owner_membership,
    get_membership,
    get_or_create_default_user,
    get_user,
    list_memberships,
    list_users,
    save_membership,
    save_user,
)


# ================================================================
# Identity models
# ================================================================


class TestLocalUser:
    def test_default_user(self) -> None:
        user = get_default_local_user()
        assert user.user_id == "local/system"
        assert user.display_name == "Local System"
        assert user.role == UserRole.OWNER

    def test_user_custom_role(self) -> None:
        user = LocalUser(
            user_id="local/test-user",
            display_name="Test User",
            role=UserRole.ANALYST,
        )
        assert user.user_id == "local/test-user"
        assert user.role == UserRole.ANALYST

    def test_user_serialization(self) -> None:
        user = LocalUser(
            user_id="local/test",
            display_name="Test",
            role=UserRole.VIEWER,
        )
        data = user.model_dump(mode="json")
        assert data["user_id"] == "local/test"
        assert data["role"] == "viewer"

    def test_user_deserialization(self) -> None:
        data = {
            "user_id": "local/deserialize",
            "display_name": "Deserialized",
            "role": "admin",
        }
        user = LocalUser.model_validate(data)
        assert user.role == UserRole.ADMIN


class TestWorkspaceMembership:
    def test_membership_creation(self) -> None:
        m = WorkspaceMembership(
            workspace_id="ws-1",
            user_id="local/test",
            role=UserRole.ANALYST,
        )
        assert m.workspace_id == "ws-1"
        assert m.role == UserRole.ANALYST
        assert m.created_at is not None

    def test_membership_serialization(self) -> None:
        m = WorkspaceMembership(
            workspace_id="ws-1", user_id="local/u1", role=UserRole.REVIEWER,
        )
        data = m.model_dump(mode="json")
        assert data["role"] == "reviewer"


# ================================================================
# Permission matrix
# ================================================================


class TestPermissionMatrix:
    def test_all_roles_have_permissions(self) -> None:
        for role in UserRole:
            assert role in ROLE_PERMISSIONS, f"Role {role} missing from matrix"

    def test_owner_has_all_permissions(self) -> None:
        owner_perms = ROLE_PERMISSIONS[UserRole.OWNER]
        assert len(owner_perms) == len(ALL_PERMISSIONS)

    def test_viewer_has_limited_permissions(self) -> None:
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER]
        assert Permission.WORKSPACE_READ in viewer_perms
        assert Permission.EVIDENCE_SEARCH in viewer_perms
        assert Permission.AUDIT_READ in viewer_perms
        assert Permission.WORKSPACE_MANAGE not in viewer_perms
        assert Permission.PROVIDER_MANAGE not in viewer_perms
        assert Permission.REPORT_EXPORT not in viewer_perms
        assert Permission.REVIEW_RESOLVE not in viewer_perms

    def test_analyst_can_upload_and_execute(self) -> None:
        analyst_perms = ROLE_PERMISSIONS[UserRole.ANALYST]
        assert Permission.DATA_SOURCE_UPLOAD in analyst_perms
        assert Permission.WORKFLOW_EXECUTE in analyst_perms
        assert Permission.REPORT_GENERATE in analyst_perms
        assert Permission.PROVIDER_MANAGE not in analyst_perms

    def test_reviewer_can_resolve_reviews(self) -> None:
        reviewer_perms = ROLE_PERMISSIONS[UserRole.REVIEWER]
        assert Permission.REVIEW_RESOLVE in reviewer_perms
        assert Permission.WORKFLOW_CREATE not in reviewer_perms
        assert Permission.PROVIDER_MANAGE not in reviewer_perms

    def test_admin_has_provider_manage(self) -> None:
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]
        assert Permission.PROVIDER_MANAGE in admin_perms
        assert Permission.SETTINGS_MANAGE in admin_perms


# ================================================================
# Identity store
# ================================================================


class TestUserStore:
    def test_get_or_create_default(self) -> None:
        user = get_or_create_default_user()
        assert user.user_id == "local/system"
        assert user.role == UserRole.OWNER

    def test_create_and_get_user(self) -> None:
        user = create_user("Alice", role=UserRole.ANALYST)
        assert user.display_name == "Alice"
        assert user.role == UserRole.ANALYST
        assert user.user_id.startswith("local/")

        fetched = get_user(user.user_id)
        assert fetched is not None
        assert fetched.display_name == "Alice"

    def test_list_users_includes_default(self) -> None:
        users = list_users()
        assert any(u.user_id == "local/system" for u in users)

    def test_delete_user(self) -> None:
        user = create_user("DeleteMe")
        assert get_user(user.user_id) is not None
        assert delete_user(user.user_id) is True
        assert get_user(user.user_id) is None

    def test_delete_nonexistent_user(self) -> None:
        assert delete_user("nonexistent") is False


class TestMembershipStore:
    def test_ensure_owner_membership(self) -> None:
        m = ensure_owner_membership("test-ws-1")
        assert m.workspace_id == "test-ws-1"
        assert m.user_id == "local/system"
        assert m.role == UserRole.OWNER

    def test_get_membership(self) -> None:
        ensure_owner_membership("test-ws-2")
        m = get_membership("test-ws-2", "local/system")
        assert m is not None
        assert m.role == UserRole.OWNER

    def test_list_memberships(self) -> None:
        ensure_owner_membership("test-ws-3")
        memberships = list_memberships("test-ws-3")
        assert len(memberships) >= 1

    def test_delete_membership(self) -> None:
        ensure_owner_membership("test-ws-4")
        assert delete_membership("test-ws-4", "local/system") is True
        assert get_membership("test-ws-4", "local/system") is None

    def test_save_membership_updates_role(self) -> None:
        ensure_owner_membership("test-ws-5")
        m = get_membership("test-ws-5", "local/system")
        assert m is not None
        m.role = UserRole.ADMIN
        save_membership(m)
        updated = get_membership("test-ws-5", "local/system")
        assert updated is not None
        assert updated.role == UserRole.ADMIN


# ================================================================
# Permission checking
# ================================================================


class TestPermissionCheck:
    def test_user_has_permission(self) -> None:
        from decision_system.identity.permissions import user_has_permission
        owner = get_default_local_user()
        assert user_has_permission(owner, Permission.PROVIDER_MANAGE) is True
        assert user_has_permission(owner, Permission.WORKSPACE_MANAGE) is True

    def test_user_lacks_permission(self) -> None:
        from decision_system.identity.permissions import user_has_permission
        viewer = LocalUser(user_id="local/v", display_name="Viewer", role=UserRole.VIEWER)
        assert user_has_permission(viewer, Permission.PROVIDER_MANAGE) is False
        assert user_has_permission(viewer, Permission.WORKSPACE_MANAGE) is False

    def test_workspace_role_overrides_global(self) -> None:
        from decision_system.identity.permissions import user_has_permission
        viewer = LocalUser(user_id="local/v", display_name="Viewer", role=UserRole.VIEWER)
        save_membership(WorkspaceMembership(
            workspace_id="ws-admin",
            user_id="local/v",
            role=UserRole.ADMIN,
        ))
        assert user_has_permission(viewer, Permission.PROVIDER_MANAGE, workspace_id="ws-admin") is True
        assert user_has_permission(viewer, Permission.PROVIDER_MANAGE) is False


# ================================================================
# Security settings
# ================================================================


class TestSecuritySettings:
    def test_default_is_demo(self) -> None:
        assert load_settings().security_mode == "demo"

    def test_update_mode(self) -> None:
        update_settings(security_mode="governed")
        settings = load_settings()
        assert settings.security_mode == "governed"
        # Reset
        update_settings(security_mode="demo")

    def test_exports_require_admin_default(self) -> None:
        assert load_settings().exports_require_admin is True

    def test_review_requires_reviewer_role_default(self) -> None:
        assert load_settings().review_requires_reviewer_role is True

    def test_is_demo_mode(self) -> None:
        update_settings(security_mode="demo")
        assert is_demo_mode() is True
        update_settings(security_mode="governed")
        assert is_demo_mode() is False
        update_settings(security_mode="demo")

    def test_security_settings_serialization(self) -> None:
        settings = load_settings()
        data = settings.model_dump(mode="json")
        assert data["security_mode"] in ("demo", "governed")


# ================================================================
# Role hierarchy
# ================================================================


class TestRoleHierarchy:
    def test_role_is_at_least(self) -> None:
        from decision_system.identity.permissions import role_is_at_least
        assert role_is_at_least(UserRole.OWNER, UserRole.VIEWER) is True
        assert role_is_at_least(UserRole.ADMIN, UserRole.VIEWER) is True
        assert role_is_at_least(UserRole.ANALYST, UserRole.VIEWER) is True
        assert role_is_at_least(UserRole.VIEWER, UserRole.OWNER) is False
        assert role_is_at_least(UserRole.REVIEWER, UserRole.ANALYST) is False
        assert role_is_at_least(UserRole.OWNER, UserRole.OWNER) is True

    def test_get_user_role(self) -> None:
        from decision_system.identity.permissions import get_user_role
        owner = get_default_local_user()
        assert get_user_role(owner) == UserRole.OWNER
        assert get_user_role(owner, workspace_id="nonexistent") == UserRole.OWNER
