"""JSON export and import for workspace bundles."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from decision_system.path_util import ensure_safe_generated_write_path
from decision_system.storage.models import (
    StoredArtifact,
    Workspace,
    WorkspaceExport,
)
from decision_system.storage.sqlite_store import DatabaseConnection
from decision_system.storage.repositories import (
    ArtifactRepository,
    WorkspaceRepository,
)

WORKSPACE_DIR = Path(".decision_system") / "workspaces"
EXPORT_DIR = WORKSPACE_DIR / "exports"
DEFAULT_DB_PATH = WORKSPACE_DIR / "workspaces.sqlite"

# Artifact types that are safe to include in exports.
# Raw datasets are stored as metadata references, not file blobs.
_EXPORTABLE_TYPES: set[str] = {
    "document",
    "data_profile",
    "ontology_map",
    "insight_store",
    "decision_report",
    "orchestration_run",
    "war_room_run",
    "provider_eval_run",
    "audit_event",
    "unknown",
}


def get_default_db_path() -> Path:
    return DEFAULT_DB_PATH


def init_workspace_dir() -> Path:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    return WORKSPACE_DIR


class WorkspaceExporter:
    """Serialize a workspace and its artifacts to JSON."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn
        self._ws_repo = WorkspaceRepository.from_conn(conn)
        self._art_repo = ArtifactRepository.from_conn(conn)

    def export_workspace(
        self,
        workspace_id: str,
        output_path: str | Path | None = None,
    ) -> Path:
        ws = self._ws_repo.get_by_id(workspace_id)
        if ws is None:
            raise ValueError(f"Workspace not found: {workspace_id}")

        artifacts = self._art_repo.get_by_workspace(workspace_id)

        # Only export safe artifact types; skip raw datasets
        filtered = [
            a
            for a in artifacts
            if a.artifact_type.value in _EXPORTABLE_TYPES
        ]

        bundle = WorkspaceExport(workspace=ws, artifacts=filtered)

        if output_path is None:
            EXPORT_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = "".join(
                c if c.isalnum() or c in ("-", "_") else "_"
                for c in ws.name
            )
            output_path = EXPORT_DIR / f"{safe_name}.json"

        output_path = Path(output_path)
        # Guard against overwriting tracked source files.
        # Only paths under .decision_system/ are accepted for exports.
        try:
            output_path = ensure_safe_generated_write_path(output_path)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            bundle.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        return output_path


class WorkspaceImporter:
    """Import a workspace from an exported JSON file."""

    def __init__(self, conn: DatabaseConnection) -> None:
        self._conn = conn
        self._ws_repo = WorkspaceRepository.from_conn(conn)
        self._art_repo = ArtifactRepository.from_conn(conn)

    def import_workspace(
        self,
        input_path: str | Path,
        *,
        force: bool = False,
    ) -> WorkspaceExport:
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Import file not found: {input_path}")

        raw = input_path.read_text(encoding="utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in import file: {exc}") from exc

        # Basic schema validation
        if "workspace" not in payload:
            raise ValueError(
                "Invalid workspace export: missing 'workspace' key."
            )
        if "version" not in payload:
            raise ValueError("Invalid workspace export: missing 'version' key.")

        bundle = WorkspaceExport.model_validate(payload)

        existing = self._ws_repo.get_by_name(bundle.workspace.name)
        if existing is not None and not force:
            raise ValueError(
                f"Workspace '{bundle.workspace.name}' already exists. "
                "Use --force to overwrite."
            )

        if existing is not None and force:
            # Delete artifacts first (no ON DELETE CASCADE in schema)
            for existing_art in self._art_repo.get_by_workspace(existing.workspace_id):
                self._art_repo.delete(existing_art.artifact_id)
            self._ws_repo.delete(existing.workspace_id)

        # Re-import with fresh IDs to avoid collisions for new imports
        ws_id = bundle.workspace.workspace_id
        ws = Workspace(
            workspace_id=ws_id,
            name=bundle.workspace.name,
            description=bundle.workspace.description,
            active=False,
        )
        self._ws_repo.create(ws)

        imported_artifacts: list[StoredArtifact] = []
        for art in bundle.artifacts:
            new_id = art.artifact_id
            imported = StoredArtifact(
                artifact_id=new_id,
                workspace_id=ws_id,
                artifact_type=art.artifact_type,
                source_path=art.source_path,
                title=art.title,
                metadata=art.metadata,
                content=art.content,
            )
            imported_artifacts.append(imported)

        if imported_artifacts:
            self._art_repo.add_many(imported_artifacts)

        self._conn.connect().commit()
        return bundle
