"""JSON file-based version store for workflow definitions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.workflow_engine.models import WorkflowVersion


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, default=str))


class JSONVersionStore:
    """Workflow version store backed by JSON files.

    Each workflow version is stored as a single file:
    ``<store_dir>/versions/<workflow_id>/v<number>.json``

    An index file tracks all versions per workflow.
    """

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir / "versions"
        _ensure_dir(self._dir)

    def _workflow_dir(self, workflow_id: str) -> Path:
        d = self._dir / workflow_id
        _ensure_dir(d)
        return d

    def _version_path(self, workflow_id: str, version_number: int) -> Path:
        return self._workflow_dir(workflow_id) / f"v{version_number}.json"

    def _index_path(self, workflow_id: str) -> Path:
        return self._workflow_dir(workflow_id) / "_index.json"

    def _load_index(self, workflow_id: str) -> list[int]:
        data = _read_json(self._index_path(workflow_id))
        return data if isinstance(data, list) else []

    def _save_index(self, workflow_id: str, numbers: list[int]) -> None:
        _write_json(self._index_path(workflow_id), numbers)

    def create_version(
        self,
        workflow_id: str,
        definition: dict[str, Any],
        change_summary: str = "",
        created_by: str = "api",
    ) -> WorkflowVersion:
        """Create a new version snapshot for a workflow.

        The version number is auto-incremented based on existing versions.
        """
        numbers = self._load_index(workflow_id)
        version_number = max(numbers) + 1 if numbers else 1

        # Compute content hash for change detection
        content_str = json.dumps(definition, sort_keys=True, default=str)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]

        version = WorkflowVersion(
            version_id=f"ver-{uuid4().hex[:12]}",
            workflow_id=workflow_id,
            version_number=version_number,
            definition=definition,
            content_hash=content_hash,
            change_summary=change_summary,
            created_at=datetime.now(timezone.utc),
            created_by=created_by,
        )

        _write_json(
            self._version_path(workflow_id, version_number),
            version.model_dump(mode="json"),
        )

        if version_number not in numbers:
            numbers.append(version_number)
            self._save_index(workflow_id, numbers)

        return version

    def load_version(self, workflow_id: str, version_number: int) -> WorkflowVersion | None:
        """Load a specific version of a workflow."""
        data = _read_json(self._version_path(workflow_id, version_number))
        if data is None:
            return None
        return WorkflowVersion(**data)

    def load_version_by_id(self, version_id: str) -> WorkflowVersion | None:
        """Find a version by its UUID across all workflows."""
        if not self._dir.exists():
            return None
        for wf_dir in self._dir.iterdir():
            if not wf_dir.is_dir():
                continue
            numbers = self._load_index(wf_dir.name)
            for num in numbers:
                data = _read_json(self._version_path(wf_dir.name, num))
                if data and data.get("version_id") == version_id:
                    return WorkflowVersion(**data)
        return None

    def list_versions(self, workflow_id: str) -> list[WorkflowVersion]:
        """List all versions for a workflow, newest first."""
        numbers = self._load_index(workflow_id)
        versions: list[WorkflowVersion] = []
        for num in sorted(numbers, reverse=True):
            v = self.load_version(workflow_id, num)
            if v is not None:
                versions.append(v)
        return versions

    def get_latest_version_number(self, workflow_id: str) -> int:
        """Get the latest version number for a workflow."""
        numbers = self._load_index(workflow_id)
        return max(numbers) if numbers else 0
