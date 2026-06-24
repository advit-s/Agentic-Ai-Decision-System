"""Pydantic models for the local identity and governance system.

All models are plain Pydantic v2 ``BaseModel`` classes that work offline
without any database, auth service, or external dependency. They provide the
local-first identity foundation: users, roles, workspace membership, and
a declarative permission matrix.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


class UserRole(StrEnum):
    """Local user roles for workspace-level access control.

    Roles are ordered from most to least privileged:
    owner > admin > analyst > reviewer > viewer
    """

    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


class Permission(StrEnum):
    """Named permissions for the local governance system.

    Each permission controls access to a specific operation or resource
    category. Permissions are assigned to roles via the ``ROLE_PERMISSIONS``
    matrix.
    """

    WORKSPACE_READ = "workspace.read"
    WORKSPACE_MANAGE = "workspace.manage"
    DATA_SOURCE_UPLOAD = "data_source.upload"
    DATA_SOURCE_DELETE = "data_source.delete"
    DATA_SOURCE_PARSE_INDEX = "data_source.parse_index"
    EVIDENCE_SEARCH = "evidence.search"
    WORKFLOW_CREATE = "workflow.create"
    WORKFLOW_UPDATE = "workflow.update"
    WORKFLOW_EXECUTE = "workflow.execute"
    REVIEW_RESOLVE = "review.resolve"
    CLAIM_VERIFY = "claim.verify"
    GRAPH_EXTRACT = "graph.extract"
    PROVIDER_MANAGE = "provider.manage"
    REPORT_GENERATE = "report.generate"
    REPORT_EXPORT = "report.export"
    AUDIT_READ = "audit.read"
    SETTINGS_MANAGE = "settings.manage"


ALL_PERMISSIONS: list[Permission] = list(Permission)

# ---------------------------------------------------------------------------
# Role → Permission matrix
# ---------------------------------------------------------------------------
# The matrix defines which permissions each role grants. More privileged
# roles inherit all permissions of less privileged roles (explicitly listed
# for clarity / testability).
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.OWNER: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_MANAGE,
        Permission.DATA_SOURCE_UPLOAD,
        Permission.DATA_SOURCE_DELETE,
        Permission.DATA_SOURCE_PARSE_INDEX,
        Permission.EVIDENCE_SEARCH,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REVIEW_RESOLVE,
        Permission.CLAIM_VERIFY,
        Permission.GRAPH_EXTRACT,
        Permission.PROVIDER_MANAGE,
        Permission.REPORT_GENERATE,
        Permission.REPORT_EXPORT,
        Permission.AUDIT_READ,
        Permission.SETTINGS_MANAGE,
    },
    UserRole.ADMIN: {
        Permission.WORKSPACE_READ,
        Permission.WORKSPACE_MANAGE,
        Permission.DATA_SOURCE_UPLOAD,
        Permission.DATA_SOURCE_DELETE,
        Permission.DATA_SOURCE_PARSE_INDEX,
        Permission.EVIDENCE_SEARCH,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.REVIEW_RESOLVE,
        Permission.CLAIM_VERIFY,
        Permission.GRAPH_EXTRACT,
        Permission.PROVIDER_MANAGE,
        Permission.REPORT_GENERATE,
        Permission.REPORT_EXPORT,
        Permission.AUDIT_READ,
        Permission.SETTINGS_MANAGE,
    },
    UserRole.ANALYST: {
        Permission.WORKSPACE_READ,
        Permission.DATA_SOURCE_UPLOAD,
        Permission.DATA_SOURCE_DELETE,
        Permission.DATA_SOURCE_PARSE_INDEX,
        Permission.EVIDENCE_SEARCH,
        Permission.WORKFLOW_CREATE,
        Permission.WORKFLOW_UPDATE,
        Permission.WORKFLOW_EXECUTE,
        Permission.CLAIM_VERIFY,
        Permission.GRAPH_EXTRACT,
        Permission.REPORT_GENERATE,
        Permission.AUDIT_READ,
    },
    UserRole.REVIEWER: {
        Permission.WORKSPACE_READ,
        Permission.EVIDENCE_SEARCH,
        Permission.REVIEW_RESOLVE,
        Permission.AUDIT_READ,
    },
    UserRole.VIEWER: {
        Permission.WORKSPACE_READ,
        Permission.EVIDENCE_SEARCH,
        Permission.AUDIT_READ,
    },
}


# ---------------------------------------------------------------------------
# Local user
# ---------------------------------------------------------------------------


class LocalUser(BaseModel):
    """A local user identity for the governance system.

    There is no password, no session, and no cloud auth. The user is
    identified by user_id and display_name. In demo mode, a single
    ``local/system`` user with role ``owner`` is used. In governed mode,
    multiple local users can be created with different roles.
    """

    model_config = {"extra": "forbid"}

    user_id: str = Field(
        default="local/system",
        description="Unique identifier for this local user.",
    )
    display_name: str = Field(
        default="Local System",
        description="Human-readable display name.",
    )
    role: UserRole = Field(
        default=UserRole.OWNER,
        description="Global role assigned to this user.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata (avatar, contact, preferences, etc.).",
    )


def get_default_local_user() -> LocalUser:
    """Return the default local demo user.

    Used when no user identity is configured (demo mode).
    """
    return LocalUser()


# ---------------------------------------------------------------------------
# Workspace membership
# ---------------------------------------------------------------------------


class WorkspaceMembership(BaseModel):
    """A user's role within a specific workspace.

    Workspace roles override (or supplement) the user's global role
    for operations scoped to that workspace.
    """

    model_config = {"extra": "forbid"}

    workspace_id: str = Field(..., description="Workspace this membership applies to.")
    user_id: str = Field(..., description="User who holds this membership.")
    role: UserRole = Field(
        ...,
        description="Role within this workspace.",
    )
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    metadata: dict[str, Any] = Field(default_factory=dict)
