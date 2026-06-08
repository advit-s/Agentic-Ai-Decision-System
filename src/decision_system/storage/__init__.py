"""Local SQLite workspace persistence for the decision-system.

v1.0 adds an optional local workspace layer that stores artifacts in a
SQLite database under ``.decision_system/workspaces/workspaces.sqlite``.
The system keeps generated JSON outputs alongside workspace metadata,
so the existing inspectable JSON workflow is preserved.
"""

from decision_system.storage.models import ArtifactType, WorkspaceStatus
from decision_system.storage.sqlite_store import create_tables
from decision_system.storage.migrations import run_migrations
from decision_system.storage.repositories import (
    WorkspaceRepository,
    ArtifactRepository,
    SettingsRepository,
)
from decision_system.storage.inspector import WorkspaceInspector
from decision_system.storage.export_import import (
    WorkspaceExporter,
    WorkspaceImporter,
)

__all__ = [
    "ArtifactType",
    "WorkspaceStatus",
    "create_tables",
    "run_migrations",
    "WorkspaceRepository",
    "ArtifactRepository",
    "SettingsRepository",
    "WorkspaceInspector",
    "WorkspaceExporter",
    "WorkspaceImporter",
]
