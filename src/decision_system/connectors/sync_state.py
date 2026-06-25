"""Sync state tracking for connector items (v1.29).

Tracks per-item sync state for incremental sync detection:
new, unchanged, changed, deleted_remote, failed, skipped.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from decision_system._data_root import get_data_root


class SyncStateItem(BaseModel):
    """Sync state for a single connector item."""

    sync_state_id: str = Field(default_factory=lambda: str(uuid4()))
    workspace_id: str | None = None
    connector_id: str
    external_id: str
    content_hash: str = ""
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_imported_at: datetime | None = None
    last_modified_at: datetime | None = None
    local_source_id: str | None = None
    status: str = "new"  # new | unchanged | changed | deleted_remote | failed | skipped
    metadata: dict[str, Any] = Field(default_factory=dict)


class SyncStateStore:
    """Persistent JSON-backed store for connector sync state.

    Stores one JSON file per connector per workspace under
    .decision_system/connectors/sync_state/.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = (
            Path(base_dir) if base_dir else get_data_root() / "connectors" / "sync_state"
        )
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _store_path(self, workspace_id: str | None, connector_id: str) -> Path:
        scope = workspace_id if workspace_id else "_global"
        d = self._base_dir / scope
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{connector_id}.json"

    def _load_all(self, workspace_id: str | None, connector_id: str) -> list[SyncStateItem]:
        path = self._store_path(workspace_id, connector_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [SyncStateItem(**item) for item in data]
        except Exception:
            return []

    def _save_all(
        self, workspace_id: str | None, connector_id: str, items: list[SyncStateItem]
    ) -> None:
        path = self._store_path(workspace_id, connector_id)
        data = [item.model_dump(mode="json") for item in items]
        path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")

    def get_sync_state(self, workspace_id: str | None, connector_id: str) -> list[SyncStateItem]:
        """Load all sync state items for a connector."""
        return self._load_all(workspace_id, connector_id)

    def get_item(
        self, workspace_id: str | None, connector_id: str, external_id: str
    ) -> SyncStateItem | None:
        """Get sync state for a specific item."""
        items = self._load_all(workspace_id, connector_id)
        for item in items:
            if item.external_id == external_id:
                return item
        return None

    def upsert_item(self, workspace_id: str | None, item: SyncStateItem) -> None:
        """Insert or update a sync state item."""
        items = self._load_all(workspace_id, item.connector_id)
        found = False
        for i, existing in enumerate(items):
            if existing.external_id == item.external_id:
                items[i] = item
                found = True
                break
        if not found:
            items.append(item)
        self._save_all(workspace_id, item.connector_id, items)

    def mark_seen(
        self,
        workspace_id: str | None,
        connector_id: str,
        external_id: str,
        content_hash: str = "",
        status: str = "unchanged",
    ) -> SyncStateItem:
        """Mark an item as seen during a sync run."""
        item = self.get_item(workspace_id, connector_id, external_id)
        now = datetime.now(timezone.utc)
        if item is None:
            item = SyncStateItem(
                workspace_id=workspace_id,
                connector_id=connector_id,
                external_id=external_id,
                content_hash=content_hash,
                last_seen_at=now,
                status=status,
            )
        else:
            item.last_seen_at = now
            item.content_hash = content_hash or item.content_hash
            item.status = status
        self.upsert_item(workspace_id, item)
        return item

    def mark_deleted_remote(
        self,
        workspace_id: str | None,
        connector_id: str,
        external_id: str,
    ) -> SyncStateItem | None:
        """Mark a previously-seen item as deleted_remote (not seen this sync)."""
        item = self.get_item(workspace_id, connector_id, external_id)
        if item is None:
            return None
        item.status = "deleted_remote"
        self.upsert_item(workspace_id, item)
        return item

    def mark_imported(
        self,
        workspace_id: str | None,
        connector_id: str,
        external_id: str,
        local_source_id: str | None = None,
    ) -> SyncStateItem | None:
        """Mark an item as successfully imported."""
        item = self.get_item(workspace_id, connector_id, external_id)
        if item is None:
            return None
        now = datetime.now(timezone.utc)
        item.last_imported_at = now
        item.status = "unchanged"
        if local_source_id:
            item.local_source_id = local_source_id
        self.upsert_item(workspace_id, item)
        return item

    def delete_connector_state(self, workspace_id: str | None, connector_id: str) -> None:
        """Delete all sync state for a connector (e.g. when connector is removed)."""
        path = self._store_path(workspace_id, connector_id)
        if path.exists():
            path.unlink()

    def compute_hash(self, content: str | bytes) -> str:
        """Compute a SHA-256 hash for content."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()


# Module-level singleton
_default_store: SyncStateStore | None = None


def get_sync_state_store() -> SyncStateStore:
    global _default_store
    if _default_store is None:
        _default_store = SyncStateStore()
    return _default_store


def reset_sync_state_store() -> None:
    global _default_store
    _default_store = None
