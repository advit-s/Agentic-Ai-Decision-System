"""Repository classes for workspace, artifact, and settings CRUD."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from decision_system.storage.models import (
    ArtifactType,
    StoredArtifact,
    Workspace,
)
from decision_system.storage.sqlite_store import DatabaseConnection


class WorkspaceRepository:
    """CRUD operations for the ``workspaces`` table."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    @classmethod
    def from_conn(cls, conn: DatabaseConnection) -> WorkspaceRepository:
        """Create a repository bound to an existing connection."""
        return cls(conn)

    def create(self, workspace: Workspace) -> Workspace:
        now = _utc_now()
        ws = workspace.model_copy(update={"created_at": now, "updated_at": now})
        self._conn.execute(
            """
            INSERT INTO workspaces (workspace_id, name, description, active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                ws.workspace_id,
                ws.name,
                ws.description,
                1 if ws.active else 0,
                _iso(ws.created_at),
                _iso(ws.updated_at),
            ),
        )
        self._conn.connect().commit()
        return ws

    def get_by_name(self, name: str) -> Workspace | None:
        cur = self._conn.execute(
            "SELECT * FROM workspaces WHERE name = ?",
            (name,),
        )
        row = cur.fetchone()
        return _row_to_workspace(row) if row else None

    def get_by_id(self, workspace_id: str) -> Workspace | None:
        cur = self._conn.execute(
            "SELECT * FROM workspaces WHERE workspace_id = ?",
            (workspace_id,),
        )
        row = cur.fetchone()
        return _row_to_workspace(row) if row else None

    def list_all(self) -> list[Workspace]:
        cur = self._conn.execute("SELECT * FROM workspaces ORDER BY name")
        return [_row_to_workspace(r) for r in cur.fetchall()]

    def get_active(self) -> Workspace | None:
        cur = self._conn.execute("SELECT * FROM workspaces WHERE active = 1 LIMIT 1")
        row = cur.fetchone()
        return _row_to_workspace(row) if row else None

    def set_active(self, workspace_id: str) -> None:
        self._conn.execute("UPDATE workspaces SET active = 0")
        self._conn.execute(
            "UPDATE workspaces SET active = 1, updated_at = ? WHERE workspace_id = ?",
            (_iso(datetime.now(timezone.utc)), workspace_id),
        )
        self._conn.connect().commit()

    def update(self, workspace: Workspace) -> Workspace:
        updated = workspace.model_copy(update={"updated_at": datetime.now(timezone.utc)})
        self._conn.execute(
            """
            UPDATE workspaces
            SET name = ?, description = ?, active = ?, updated_at = ?
            WHERE workspace_id = ?
            """,
            (
                updated.name,
                updated.description,
                1 if updated.active else 0,
                _iso(updated.updated_at),
                updated.workspace_id,
            ),
        )
        self._conn.connect().commit()
        return updated

    def delete(self, workspace_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM workspaces WHERE workspace_id = ?",
            (workspace_id,),
        )
        self._conn.connect().commit()
        return cur.rowcount > 0

    def ensure_exists(self, workspace: Workspace) -> Workspace:
        """Create workspace if it does not already exist by name.
        Returns the existing or newly created workspace.
        Existing workspace descriptions are NOT overwritten (idempotent init behavior).
        """
        existing = self.get_by_name(workspace.name)
        if existing is not None:
            return existing
        return self.create(workspace)

    def ensure_active(self, workspace_id: str) -> Workspace:
        """Activate the given workspace if not already active."""
        ws = self.get_by_id(workspace_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {workspace_id}")
        if not ws.active:
            self.set_active(workspace_id)
            ws = self.get_by_id(workspace_id)
        return ws


class ArtifactRepository:
    """CRUD operations for the ``artifacts`` table."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    @classmethod
    def from_conn(cls, conn: DatabaseConnection) -> ArtifactRepository:
        """Create a repository bound to an existing connection."""
        return cls(conn)

    def add(self, artifact: StoredArtifact) -> StoredArtifact:
        now = _utc_now()
        art = artifact.model_copy(update={"created_at": now, "updated_at": now})
        self._conn.execute(
            """
            INSERT INTO artifacts
            (artifact_id, workspace_id, artifact_type, source_path, title,
             metadata_json, content_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                art.artifact_id,
                art.workspace_id,
                art.artifact_type.value,
                art.source_path,
                art.title,
                json.dumps(art.metadata),
                json.dumps(art.content),
                _iso(art.created_at),
                _iso(art.updated_at),
            ),
        )
        self._conn.connect().commit()
        return art

    def get_by_id(self, artifact_id: str) -> StoredArtifact | None:
        cur = self._conn.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?",
            (artifact_id,),
        )
        return _row_to_artifact(cur.fetchone())

    def get_by_workspace(self, workspace_id: str) -> list[StoredArtifact]:
        cur = self._conn.execute(
            "SELECT * FROM artifacts WHERE workspace_id = ? ORDER BY created_at DESC",
            (workspace_id,),
        )
        return [a for a in (_row_to_artifact(r) for r in cur.fetchall()) if a is not None]

    def get_by_type(self, workspace_id: str, artifact_type: ArtifactType) -> list[StoredArtifact]:
        cur = self._conn.execute(
            "SELECT * FROM artifacts WHERE workspace_id = ? AND artifact_type = ? ORDER BY created_at DESC",
            (workspace_id, artifact_type.value),
        )
        return [a for a in (_row_to_artifact(r) for r in cur.fetchall()) if a is not None]

    def count_by_type(self, workspace_id: str) -> dict[str, int]:
        cur = self._conn.execute(
            "SELECT artifact_type, COUNT(*) as cnt FROM artifacts WHERE workspace_id = ? GROUP BY artifact_type",
            (workspace_id,),
        )
        return {row["artifact_type"]: row["cnt"] for row in cur.fetchall()}

    def delete(self, artifact_id: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM artifacts WHERE artifact_id = ?",
            (artifact_id,),
        )
        self._conn.connect().commit()
        return cur.rowcount > 0

    def add_many(self, artifacts: list[StoredArtifact]) -> list[StoredArtifact]:
        """Add multiple artifacts in a single batch."""
        now = _utc_now()
        rows = []
        for art in artifacts:
            stamped = art.model_copy(update={"created_at": now, "updated_at": now})
            rows.append(
                (
                    stamped.artifact_id,
                    stamped.workspace_id,
                    stamped.artifact_type.value,
                    stamped.source_path,
                    stamped.title,
                    json.dumps(stamped.metadata),
                    json.dumps(stamped.content),
                    _iso(stamped.created_at),
                    _iso(stamped.updated_at),
                )
            )
        self._conn.executemany(
            """
            INSERT INTO artifacts
            (artifact_id, workspace_id, artifact_type, source_path, title,
             metadata_json, content_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        self._conn.connect().commit()
        return artifacts


class SettingsRepository:
    """Key-value store for persistent application settings."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn

    def get(self, key: str, default: str = "") -> str:
        cur = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        )
        row = cur.fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str) -> None:
        self._conn.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.connect().commit()

    def delete(self, key: str) -> bool:
        cur = self._conn.execute(
            "DELETE FROM settings WHERE key = ?",
            (key,),
        )
        self._conn.connect().commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _row_to_workspace(row: dict[str, Any] | None) -> Workspace | None:
    if row is None:
        return None
    return Workspace(
        workspace_id=row["workspace_id"],
        name=row["name"],
        description=row.get("description", ""),
        active=bool(row.get("active", 0)),
        created_at=_parse_iso(row.get("created_at", "")),
        updated_at=_parse_iso(row.get("updated_at", "")),
    )


def _row_to_artifact(row: dict[str, Any] | None) -> StoredArtifact | None:
    if row is None:
        return None
    atype_str = row.get("artifact_type", "unknown")
    try:
        atype = ArtifactType(atype_str)
    except ValueError:
        atype = ArtifactType.UNKNOWN
    return StoredArtifact(
        artifact_id=row["artifact_id"],
        workspace_id=row["workspace_id"],
        artifact_type=atype,
        source_path=row.get("source_path", ""),
        title=row.get("title", ""),
        metadata=_json_loads(row.get("metadata_json", "{}")),
        content=_json_loads(row.get("content_json", "{}")),
        created_at=_parse_iso(row.get("created_at", "")),
        updated_at=_parse_iso(row.get("updated_at", "")),
    )


def _json_loads(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_iso(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)
