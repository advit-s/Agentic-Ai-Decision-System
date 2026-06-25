"""Local JSON-backed store for users and workspace memberships.

Stores user profiles and workspace membership records under
``.decision_system/identity/``. In demo mode, only the default local
owner user is available.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_system._data_root import get_data_root
from decision_system.identity.models import (
    LocalUser,
    UserRole,
    WorkspaceMembership,
    get_default_local_user,
)

# ---------------------------------------------------------------------------
# Default paths
# ---------------------------------------------------------------------------


def _default_identity_dir() -> Path:
    return get_data_root() / "identity"


def _default_users_file() -> Path:
    return _default_identity_dir() / "users.json"


def _default_memberships_file() -> Path:
    return _default_identity_dir() / "memberships.json"


# ---------------------------------------------------------------------------
# User store
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    _default_identity_dir().mkdir(parents=True, exist_ok=True)


def _load_users(path: Path | None = None) -> dict[str, dict[str, Any]]:
    if path is None:
        path = _default_users_file()
    if not path.exists():
        return {}
    try:
        with path.open("r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(
    users: dict[str, dict[str, Any]],
    path: Path | None = None,
) -> None:
    _ensure_dirs()
    if path is None:
        path = _default_users_file()
    with path.open("w") as f:
        json.dump(users, f, indent=2, default=str)


def get_user(user_id: str) -> LocalUser | None:
    """Get a user by ID. Returns None if not found."""
    users = _load_users()
    raw = users.get(user_id)
    if raw is None:
        return None
    return LocalUser.model_validate(raw)


def list_users() -> list[LocalUser]:
    """List all local users."""
    users = _load_users()
    return [LocalUser.model_validate(raw) for raw in users.values()]


def save_user(user: LocalUser) -> LocalUser:
    """Save a user. Creates or updates."""
    users = _load_users()
    user.updated_at = datetime.now(timezone.utc).isoformat()
    users[user.user_id] = user.model_dump(mode="json")
    _save_users(users)
    return user


def delete_user(user_id: str) -> bool:
    """Delete a user. Returns True if deleted, False if not found."""
    users = _load_users()
    if user_id not in users:
        return False
    del users[user_id]
    _save_users(users)
    return True


def get_or_create_default_user() -> LocalUser:
    """Get the default local user, creating it if it doesn't exist."""
    default = get_user("local/system")
    if default is not None:
        return default
    user = get_default_local_user()
    save_user(user)
    return user


def create_user(
    display_name: str,
    role: UserRole = UserRole.VIEWER,
    metadata: dict[str, Any] | None = None,
) -> LocalUser:
    """Create a new local user with a random ID."""
    user = LocalUser(
        user_id=f"local/{uuid.uuid4().hex[:12]}",
        display_name=display_name,
        role=role,
        metadata=metadata or {},
    )
    save_user(user)
    return user


# ---------------------------------------------------------------------------
# Membership store
# ---------------------------------------------------------------------------


def _load_memberships(path: Path | None = None) -> list[dict[str, Any]]:
    if path is None:
        path = _default_memberships_file()
    if not path.exists():
        return []
    try:
        with path.open("r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_memberships(
    memberships: list[dict[str, Any]],
    path: Path | None = None,
) -> None:
    _ensure_dirs()
    if path is None:
        path = _default_memberships_file()
    with path.open("w") as f:
        json.dump(memberships, f, indent=2, default=str)


def get_membership(workspace_id: str, user_id: str) -> WorkspaceMembership | None:
    """Get a user's membership in a workspace. Returns None if not found."""
    memberships = _load_memberships()
    for raw in memberships:
        if raw.get("workspace_id") == workspace_id and raw.get("user_id") == user_id:
            return WorkspaceMembership.model_validate(raw)
    return None


def list_memberships(workspace_id: str | None = None) -> list[WorkspaceMembership]:
    """List memberships, optionally filtered by workspace."""
    memberships = _load_memberships()
    result = []
    for raw in memberships:
        if workspace_id is None or raw.get("workspace_id") == workspace_id:
            result.append(WorkspaceMembership.model_validate(raw))
    return result


def save_membership(membership: WorkspaceMembership) -> WorkspaceMembership:
    """Save a workspace membership. Creates or updates."""
    memberships = _load_memberships()
    membership.updated_at = datetime.now(timezone.utc).isoformat()
    # Remove old entry if exists
    memberships = [
        m
        for m in memberships
        if not (
            m.get("workspace_id") == membership.workspace_id
            and m.get("user_id") == membership.user_id
        )
    ]
    memberships.append(membership.model_dump(mode="json"))
    _save_memberships(memberships)
    return membership


def delete_membership(workspace_id: str, user_id: str) -> bool:
    """Delete a workspace membership. Returns True if deleted."""
    memberships = _load_memberships()
    before = len(memberships)
    memberships = [
        m
        for m in memberships
        if not (m.get("workspace_id") == workspace_id and m.get("user_id") == user_id)
    ]
    if len(memberships) == before:
        return False
    _save_memberships(memberships)
    return True


def ensure_owner_membership(workspace_id: str) -> WorkspaceMembership:
    """Ensure the default local owner has membership in the given workspace.

    Called when creating a new workspace to guarantee the owner has access.
    """
    existing = get_membership(workspace_id, "local/system")
    if existing is not None:
        return existing
    membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_id="local/system",
        role=UserRole.OWNER,
    )
    save_membership(membership)
    return membership
