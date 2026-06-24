"""Identity and workspace membership API endpoints.

Provides user CRUD, workspace membership management, and the current
user status endpoint. In demo mode, only the default local owner is
visible. In governed mode, multiple users and memberships can be managed.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from decision_system.api.models import api_error
from decision_system.identity.models import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    LocalUser,
    Permission,
    UserRole,
    WorkspaceMembership,
    get_default_local_user,
)
from decision_system.identity.permissions import (
    get_current_user,
    require_permission,
    require_workspace_permission,
)
from decision_system.identity.settings import load_settings, update_settings
from decision_system.identity.store import (
    create_user,
    delete_membership,
    delete_user,
    ensure_owner_membership,
    get_membership,
    get_user,
    list_memberships,
    list_users,
    save_membership,
    save_user,
)

router = APIRouter(tags=["identity"])


# ---------------------------------------------------------------------------
# Request/Response models
# ---------------------------------------------------------------------------


class CreateUserRequest(BaseModel):
    display_name: str = Field(min_length=1)
    role: UserRole = UserRole.VIEWER
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateUserRequest(BaseModel):
    display_name: str | None = None
    role: UserRole | None = None
    metadata: dict[str, Any] | None = None


class AddMembershipRequest(BaseModel):
    user_id: str = Field(min_length=1)
    role: UserRole = UserRole.VIEWER


class UpdateMembershipRequest(BaseModel):
    role: UserRole


class UserResponse(BaseModel):
    user: LocalUser
    permissions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/identity/me")
def get_my_identity(
    user: LocalUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Return the current user identity and effective permissions."""
    from decision_system.identity.models import ROLE_PERMISSIONS
    perms = sorted(p.value for p in ROLE_PERMISSIONS.get(user.role, set()))
    return {
        "user": user.model_dump(mode="json"),
        "permissions": perms,
        "security_mode": load_settings().security_mode,
    }


@router.get("/identity/users")
def list_all_users(
    user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> list[dict[str, Any]]:
    """List all local users. Requires settings.manage permission."""
    return [u.model_dump(mode="json") for u in list_users()]


@router.get("/identity/users/{user_id}")
def get_user_by_id(
    user_id: str,
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, Any]:
    """Get a user by ID. Requires settings.manage permission."""
    u = get_user(user_id)
    if u is None:
        raise api_error(404, "user_not_found", f"User '{user_id}' not found.")
    return u.model_dump(mode="json")


@router.post("/identity/users")
def create_new_user(
    body: CreateUserRequest,
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, Any]:
    """Create a new local user. Requires settings.manage permission."""
    u = create_user(
        display_name=body.display_name,
        role=body.role,
        metadata=body.metadata,
    )
    return u.model_dump(mode="json")


@router.put("/identity/users/{user_id}")
def update_existing_user(
    user_id: str,
    body: UpdateUserRequest,
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, Any]:
    """Update a user. Requires settings.manage permission."""
    u = get_user(user_id)
    if u is None:
        raise api_error(404, "user_not_found", f"User '{user_id}' not found.")
    if body.display_name is not None:
        u.display_name = body.display_name
    if body.role is not None:
        u.role = body.role
    if body.metadata is not None:
        u.metadata = body.metadata
    save_user(u)
    return u.model_dump(mode="json")


@router.delete("/identity/users/{user_id}")
def delete_existing_user(
    user_id: str,
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, str]:
    """Delete a user. Requires settings.manage permission."""
    if user_id == "local/system":
        raise api_error(400, "cannot_delete_default", "Cannot delete the default local user.")
    if not delete_user(user_id):
        raise api_error(404, "user_not_found", f"User '{user_id}' not found.")
    return {"status": "deleted", "user_id": user_id}


# ---------------------------------------------------------------------------
# Workspace membership endpoints
# ---------------------------------------------------------------------------


@router.get("/workspaces/{id}/memberships")
def list_workspace_memberships(
    id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_MANAGE)),
) -> list[dict[str, Any]]:
    """List memberships for a workspace. Requires workspace.manage permission."""
    return [m.model_dump(mode="json") for m in list_memberships(workspace_id=id)]


@router.post("/workspaces/{id}/memberships")
def add_workspace_membership(
    id: str,
    body: AddMembershipRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_MANAGE)),
) -> dict[str, Any]:
    """Add a user to a workspace with a role. Requires workspace.manage permission."""
    # Verify user exists
    if get_user(body.user_id) is None:
        raise api_error(404, "user_not_found", f"User '{body.user_id}' not found.")
    membership = WorkspaceMembership(
        workspace_id=id,
        user_id=body.user_id,
        role=body.role,
    )
    save_membership(membership)
    return membership.model_dump(mode="json")


@router.put("/workspaces/{id}/memberships/{user_id}")
def update_workspace_membership(
    id: str,
    user_id: str,
    body: UpdateMembershipRequest,
    _user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_MANAGE)),
) -> dict[str, Any]:
    """Update a user's role in a workspace."""
    membership = get_membership(id, user_id)
    if membership is None:
        raise api_error(404, "membership_not_found", f"Membership not found for user '{user_id}' in workspace '{id}'.")
    membership.role = body.role
    save_membership(membership)
    return membership.model_dump(mode="json")


@router.delete("/workspaces/{id}/memberships/{user_id}")
def remove_workspace_membership(
    id: str,
    user_id: str,
    _user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_MANAGE)),
) -> dict[str, str]:
    """Remove a user from a workspace."""
    if not delete_membership(id, user_id):
        raise api_error(404, "membership_not_found", f"Membership not found for user '{user_id}' in workspace '{id}'.")
    return {"status": "removed", "workspace_id": id, "user_id": user_id}


# ---------------------------------------------------------------------------
# Security settings endpoints
# ---------------------------------------------------------------------------


class UpdateSecuritySettingsRequest(BaseModel):
    security_mode: str | None = None
    default_role: UserRole | None = None
    exports_require_admin: bool | None = None
    review_requires_reviewer_role: bool | None = None
    audit_retention_days: int | None = None


@router.get("/identity/settings")
def get_security_settings(
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, Any]:
    """Get current security settings."""
    return load_settings().model_dump(mode="json")


@router.put("/identity/settings")
def update_security_settings(
    body: UpdateSecuritySettingsRequest,
    _user: LocalUser = Depends(require_permission(Permission.SETTINGS_MANAGE)),
) -> dict[str, Any]:
    """Update security settings. Requires settings.manage permission."""
    kwargs = body.model_dump(exclude_none=True)
    settings = update_settings(**kwargs)
    return settings.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Permission matrix endpoint (read-only)
# ---------------------------------------------------------------------------


@router.get("/identity/permissions")
def get_permission_matrix(
    _user: LocalUser = Depends(require_permission(Permission.AUDIT_READ)),
) -> dict[str, Any]:
    """Return the role-to-permission matrix."""
    matrix = {}
    for role, perms in ROLE_PERMISSIONS.items():
        matrix[role.value] = sorted(p.value for p in perms)
    return {
        "roles": [r.value for r in UserRole],
        "permissions": sorted(p.value for p in ALL_PERMISSIONS),
        "matrix": matrix,
    }
