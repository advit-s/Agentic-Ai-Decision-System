"""Permission checking layer for the local governance system.

Provides FastAPI dependency ``require_permission()`` that checks the
current user's role against the permission matrix, and helper functions
for non-route code.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request

from decision_system.identity.models import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    LocalUser,
    Permission,
    UserRole,
)
from decision_system.identity.store import (
    get_membership,
    get_or_create_default_user,
    list_memberships,
)
from decision_system.identity.settings import is_demo_mode as settings_is_demo


# ---------------------------------------------------------------------------
# Current user context
# ---------------------------------------------------------------------------
# In demo mode, the current user is always the default local owner.
# In governed mode, the current user is determined by the request context
# (header, cookie, or session). For now, we use a simple header-based
# approach that can be upgraded to real auth later.
# ---------------------------------------------------------------------------

_DEMO_OVERRIDE: bool | None = None


def set_demo_override(enabled: bool) -> None:
    """Force demo mode for testing. None = auto-detect."""
    global _DEMO_OVERRIDE
    _DEMO_OVERRIDE = enabled


def _is_demo_mode() -> bool:
    """Detect whether we are running in demo mode.

    Uses override first (for testing), then falls back to the authoritative
    security settings on disk.
    """
    if _DEMO_OVERRIDE is not None:
        return _DEMO_OVERRIDE
    return settings_is_demo()


def get_current_user(request: Request = None) -> LocalUser:
    """Get the current user from the request context.

    In demo mode, returns the default local owner.
    In governed mode, reads ``X-User-Id`` header to identify the user.
    Falls back to the default local user if no header is present.
    """
    if _is_demo_mode():
        return get_or_create_default_user()

    # In governed mode, X-User-Id header is required
    user_id = ""
    if request is None or not request.headers.get("X-User-Id", ""):
        raise HTTPException(
            status_code=401,
            detail={
                "code": "missing_user_id",
                "message": "X-User-Id header is required in governed mode.",
            },
        )
    user_id = request.headers["X-User-Id"]

    from decision_system.identity.store import get_user
    user = get_user(user_id)
    if user is None:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "user_not_found",
                "message": f"User '{user_id}' not found in governed mode.",
            },
        )
    return user


# ---------------------------------------------------------------------------
# Permission checking
# ---------------------------------------------------------------------------


def user_has_permission(
    user: LocalUser,
    permission: Permission,
    workspace_id: str | None = None,
) -> bool:
    """Check whether a user has a given permission.

    If ``workspace_id`` is provided, the user's workspace-specific role
    is checked first. Falls back to the user's global role.
    """
    role = user.role

    # Check workspace-specific role if workspace_id is given
    if workspace_id is not None:
        membership = get_membership(workspace_id, user.user_id)
        if membership is not None:
            role = membership.role

    allowed = ROLE_PERMISSIONS.get(role, set())
    return permission in allowed


def require_permission(permission: Permission) -> Any:
     """FastAPI dependency factory that checks the current user has the given permission.

     Usage::

         @router.get("/workspaces/{id}")
         def get_workspace(
             id: str,
             user: LocalUser = Depends(require_permission(Permission.WORKSPACE_READ)),
         ):
             ...

     Raises ``HTTPException(403)`` if the user lacks the required permission.
     """

     def _dependency(
         request: Request = None,
     ) -> LocalUser:
         user = get_current_user(request)
         if not user_has_permission(user, permission, None):
             raise HTTPException(
                 status_code=403,
                 detail={
                     "code": "permission_denied",
                     "message": f"User '{user.user_id}' lacks required permission '{permission.value}'.",
                     "details": {
                         "user_id": user.user_id,
                         "role": user.role.value,
                         "permission": permission.value,
                     },
                 },
             )
         return user

     return _dependency


# ---------------------------------------------------------------------------
# Workspace-scoped permission dependency
# ---------------------------------------------------------------------------


def require_workspace_permission(permission: Permission) -> Any:
     """Create a FastAPI dependency that checks a workspace-scoped permission.

     The workspace_id is extracted from the route path parameter ``id``
     or ``workspace_id``.

     Usage::

         @router.get("/workspaces/{id}/data-sources")
         def list_data_sources(
             id: str,
             user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ)),
         ):
             ...
     """

     def _dependency(
         request: Request,
     ) -> LocalUser:
         # Try to extract workspace_id from path params
         workspace_id = request.path_params.get("id") or request.path_params.get("workspace_id")
         user = get_current_user(request)
         if not user_has_permission(user, permission, workspace_id):
             raise HTTPException(
                 status_code=403,
                 detail={
                     "code": "permission_denied",
                     "message": f"User '{user.user_id}' lacks required permission '{permission.value}'.",
                     "details": {
                         "user_id": user.user_id,
                         "role": user.role.value,
                         "permission": permission.value,
                         "workspace_id": workspace_id,
                     },
                 },
             )
         return user

     return _dependency


def get_user_role(user: LocalUser, workspace_id: str | None = None) -> UserRole:
    """Get the effective role of a user, considering workspace membership."""
    if workspace_id is not None:
        membership = get_membership(workspace_id, user.user_id)
        if membership is not None:
            return membership.role
    return user.role


def role_is_at_least(current: UserRole, minimum: UserRole) -> bool:
    """Check if a role is at least as privileged as the minimum.

    Roles ordered: owner > admin > analyst > reviewer > viewer
    """
    ORDER = [UserRole.VIEWER, UserRole.REVIEWER, UserRole.ANALYST, UserRole.ADMIN, UserRole.OWNER]
    return ORDER.index(current) >= ORDER.index(minimum)
