"""Workspace inspection helpers for the ``inspect-workspace`` command."""

from __future__ import annotations

from typing import Any

from decision_system.storage.models import WorkspaceStatus
from decision_system.storage.repositories import (
    ArtifactRepository,
    WorkspaceRepository,
)


class WorkspaceInspector:
    """Build ``WorkspaceStatus`` summaries from repository data."""

    def __init__(
        self,
        workspaces: WorkspaceRepository,
        artifacts: ArtifactRepository,
        database_path: str,
    ) -> None:
        self._workspaces = workspaces
        self._artifacts = artifacts
        self._database_path = database_path

    def status(self) -> WorkspaceStatus | None:
        ws = self._workspaces.get_active()
        if ws is None:
            return None
        counts = self._artifacts.count_by_type(ws.workspace_id)
        return WorkspaceStatus(
            workspace=ws,
            artifact_counts=counts,
            database_path=self._database_path,
            created_at=ws.created_at,
        )

    def recent_artifacts(
        self,
        workspace_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        items = self._artifacts.get_by_workspace(workspace_id)
        return [
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type.value,
                "title": a.title,
                "source_path": a.source_path,
                "metadata": a.metadata,
                "created_at": a.created_at.isoformat(),
            }
            for a in items[:limit]
        ]
