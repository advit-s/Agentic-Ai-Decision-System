"""Data-source version/provenance tracking for connectors (v1.31).

Tracks version history for imported items so that evidence citations
remain valid when items are re-imported with changes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from decision_system._data_root import get_data_root
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class SourceVersion:
    """A version entry for an imported data source."""
    version_id: str = field(default_factory=lambda: str(uuid4()))
    connector_id: str = ""
    external_id: str = ""
    version_number: int = 1
    previous_source_id: str = ""
    supersedes_source_id: str = ""
    superseded_by_source_id: str = ""
    imported_from_job_id: str = ""
    content_hash: str = ""
    source_url: str = ""
    label: str = ""
    imported_at: str = ""  # ISO timestamp
    external_modified_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "connector_id": self.connector_id,
            "external_id": self.external_id,
            "version_number": self.version_number,
            "previous_source_id": self.previous_source_id,
            "supersedes_source_id": self.supersedes_source_id,
            "superseded_by_source_id": self.superseded_by_source_id,
            "imported_from_job_id": self.imported_from_job_id,
            "content_hash": self.content_hash,
            "source_url": self.source_url,
            "label": self.label,
            "imported_at": self.imported_at,
            "external_modified_at": self.external_modified_at,
        }


class ProvenanceTracker:
    """Tracks version history for imported connector data sources.

    When an item is re-imported with different content, a new version
    is created and linked to the previous version. Existing evidence
    citations referencing the old version remain valid.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._base_dir = Path(base_dir) if base_dir else get_data_root() / "connectors" / "provenance"
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _store_path(self, connector_id: str, external_id: str, workspace_id: str | None = None) -> Path:
        scope = workspace_id if workspace_id else "_global"
        d = self._base_dir / scope / connector_id
        d.mkdir(parents=True, exist_ok=True)
        return d / f"{external_id}.json"

    def get_versions(
        self, connector_id: str, external_id: str,
        workspace_id: str | None = None,
    ) -> list[SourceVersion]:
        """Get all versions for a given item."""
        path = self._store_path(connector_id, external_id, workspace_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return [SourceVersion(**v) for v in data]
        except Exception:
            return []

    def get_latest_version(
        self, connector_id: str, external_id: str,
        workspace_id: str | None = None,
    ) -> SourceVersion | None:
        """Get the latest version of an item."""
        versions = self.get_versions(connector_id, external_id, workspace_id)
        if not versions:
            return None
        return max(versions, key=lambda v: v.version_number)

    def create_version(
        self,
        connector_id: str,
        external_id: str,
        content_hash: str,
        job_id: str = "",
        source_url: str = "",
        label: str = "",
        external_modified_at: str | None = None,
        workspace_id: str | None = None,
    ) -> SourceVersion:
        """Create a new version for an imported item.

        If a previous version exists, links the new version to it.
        """
        versions = self.get_versions(connector_id, external_id, workspace_id)
        previous = max(versions, key=lambda v: v.version_number) if versions else None

        version_number = (previous.version_number + 1) if previous else 1
        previous_source_id = previous.version_id if previous else ""

        new_version = SourceVersion(
            connector_id=connector_id,
            external_id=external_id,
            version_number=version_number,
            previous_source_id=previous_source_id,
            imported_from_job_id=job_id,
            content_hash=content_hash,
            source_url=source_url,
            label=label,
            imported_at=datetime.now(timezone.utc).isoformat(),
            external_modified_at=external_modified_at,
        )

        # Update previous version's superseded_by
        if previous:
            previous.superseded_by_source_id = new_version.version_id
            self._save_versions(connector_id, external_id, versions + [new_version], workspace_id)
        else:
            self._save_versions(connector_id, external_id, [new_version], workspace_id)

        return new_version

    def _save_versions(
        self, connector_id: str, external_id: str,
        versions: list[SourceVersion],
        workspace_id: str | None = None,
    ) -> None:
        path = self._store_path(connector_id, external_id, workspace_id)
        data = [v.to_dict() for v in versions]
        path.write_text(
            json.dumps(data, indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def get_source_id_for_version(
        self, connector_id: str, external_id: str,
        version_number: int,
        workspace_id: str | None = None,
    ) -> str | None:
        """Get the source_id for a specific version of an item."""
        versions = self.get_versions(connector_id, external_id, workspace_id)
        for v in versions:
            if v.version_number == version_number:
                return v.version_id
        return None


# Default singleton
_default_tracker: ProvenanceTracker | None = None


def get_provenance_tracker() -> ProvenanceTracker:
    global _default_tracker
    if _default_tracker is None:
        _default_tracker = ProvenanceTracker()
    return _default_tracker


def reset_provenance_tracker() -> None:
    global _default_tracker
    _default_tracker = None
