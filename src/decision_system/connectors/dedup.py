"""Duplicate detection and import idempotency for connectors (v1.31).

Uses content_hash + external_id + source_url to detect duplicates.
Supports idempotent re-imports and duplicate warnings.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from decision_system._data_root import get_data_root
from decision_system.connectors.models import ConnectorFetchedContent

logger = logging.getLogger(__name__)


@dataclass
class DuplicateResult:
    """Result of duplicate detection for a single item."""

    is_duplicate: bool = False
    is_unchanged: bool = False
    is_changed: bool = False
    existing_hash: str = ""
    current_hash: str = ""
    existing_source_id: str = ""
    existing_version: int = 0
    message: str = ""


class DuplicateDetector:
    """Detects duplicate and unchanged items during import.

    Uses a JSON store under .decision_system/connectors/dedup/ to
    track content hashes per connector.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else get_data_root() / "connectors" / "dedup"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _store_path(self, connector_id: str, workspace_id: str | None = None) -> Path:
        scope = workspace_id if workspace_id else "_global"
        d = self._base_dir / scope
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{connector_id}.json"

    def _load_hashes(self, connector_id: str, workspace_id: str | None = None) -> dict[str, Any]:
        path = self._store_path(connector_id, workspace_id)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_hashes(
        self,
        connector_id: str,
        data: dict[str, Any],
        workspace_id: str | None = None,
    ) -> None:
        path = self._store_path(connector_id, workspace_id)
        path.write_text(
            json.dumps(data, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def compute_hash(self, content: ConnectorFetchedContent) -> str:
        """Compute content hash for dedup."""
        if content.content_bytes:
            raw = content.content_bytes
        elif content.content_text:
            raw = content.content_text.encode("utf-8")
        else:
            raw = b""
        return hashlib.sha256(raw).hexdigest()

    def check_duplicate(
        self,
        connector_id: str,
        external_id: str,
        content_hash: str,
        source_url: str | None = None,
        workspace_id: str | None = None,
    ) -> DuplicateResult:
        """Check if an item is a duplicate based on content hash.

        Returns result indicating whether the item is duplicate,
        unchanged, or changed compared to previous import.
        """
        hashes = self._load_hashes(connector_id, workspace_id)
        key = f"{external_id}"
        existing = hashes.get(key)

        if existing is None:
            return DuplicateResult(is_duplicate=False, current_hash=content_hash)

        existing_hash = existing.get("hash", "")
        existing_source = existing.get("source_id", "")
        existing_version = existing.get("version", 0)

        if existing_hash == content_hash:
            return DuplicateResult(
                is_duplicate=True,
                is_unchanged=True,
                existing_hash=existing_hash,
                current_hash=content_hash,
                existing_source_id=existing_source,
                existing_version=existing_version,
                message=f"Item '{external_id}' unchanged (same content hash)",
            )
        else:
            return DuplicateResult(
                is_duplicate=False,
                is_changed=True,
                existing_hash=existing_hash,
                current_hash=content_hash,
                existing_source_id=existing_source,
                existing_version=existing_version,
                message=f"Item '{external_id}' content changed (new hash={content_hash[:8]}...)",
            )

    def record_import(
        self,
        connector_id: str,
        external_id: str,
        content_hash: str,
        source_id: str = "",
        source_url: str | None = None,
        workspace_id: str | None = None,
        version: int = 1,
    ) -> None:
        """Record an imported item's hash for future dedup checks."""
        hashes = self._load_hashes(connector_id, workspace_id)
        key = f"{external_id}"

        # Bump version on update
        existing = hashes.get(key, {})
        new_version = existing.get("version", 0) + 1 if existing else version

        hashes[key] = {
            "hash": content_hash,
            "source_id": source_id,
            "source_url": source_url or "",
            "version": new_version,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "external_id": external_id,
        }
        self._save_hashes(connector_id, hashes, workspace_id)

    def clear_connector(self, connector_id: str, workspace_id: str | None = None) -> None:
        """Clear dedup state for a connector."""
        path = self._store_path(connector_id, workspace_id)
        if path.exists():
            path.unlink()


# Default singleton
_default_detector: DuplicateDetector | None = None


def get_duplicate_detector() -> DuplicateDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = DuplicateDetector()
    return _default_detector


def reset_duplicate_detector() -> None:
    global _default_detector
    _default_detector = None
