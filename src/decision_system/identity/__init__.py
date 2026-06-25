"""Local identity, user, and role models for the governance system.

This module provides the local-first identity foundation used by the
permission system, workspace membership, and audit log. No cloud auth,
passwords, or sessions are required — identity is an opt-in governance
layer that defaults to a local owner user in demo mode.
"""

from __future__ import annotations

from decision_system.identity.models import (
    ALL_PERMISSIONS,
    ROLE_PERMISSIONS,
    LocalUser,
    Permission,
    UserRole,
    WorkspaceMembership,
    get_default_local_user,
)

__all__ = [
    "LocalUser",
    "UserRole",
    "WorkspaceMembership",
    "Permission",
    "ROLE_PERMISSIONS",
    "ALL_PERMISSIONS",
    "get_default_local_user",
]
