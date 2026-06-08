"""Connector job orchestration: validate definition, run dry-run or real import."""

from __future__ import annotations

import json
from pathlib import Path

from decision_system.connectors.local_files import (
    run_dry_run as _run_local_dry_run,
    run_local_files_import as _run_local_import,
)
from decision_system.connectors.models import (
    ConnectorDefinition,
    ConnectorDryRunResult,
    ConnectorImportResult,
)
from decision_system.connectors.stubs import ExternalConnectorError
from decision_system.connectors.stubs import run_stub_dry_run
from decision_system.connectors.stubs import run_stub_import
from decision_system.connectors.store import save_job


def _store_connector_job_as_artifact(job, settings) -> None:
    """Store connector import job as workspace artifact if active workspace exists.

    This is best-effort: failures are logged but never block an import.
    """
    try:
        from decision_system.config import load_settings as _load_settings
        from decision_system.storage.models import (
            ArtifactType,
            StoredArtifact,
        )
        from decision_system.storage.repositories import (
            ArtifactRepository,
            WorkspaceRepository,
        )
        from decision_system.storage.sqlite_store import DatabaseConnection
        from decision_system.storage.export_import import init_workspace_dir
        from decision_system.storage.migrations import run_migrations

        if settings is None:
            settings = _load_settings()

        db_path = Path(settings.workspace_db_path)
        if not db_path.exists():
            return

        init_workspace_dir()
        conn = DatabaseConnection(db_path)
        try:
            conn.connect()
            run_migrations(conn.connect())
            ws_repo = WorkspaceRepository(conn)
            ws = ws_repo.get_active()
            if ws is None:
                return

            artifact = StoredArtifact(
                artifact_id=job.job_id,
                workspace_id=ws.workspace_id,
                artifact_type=ArtifactType.CONNECTOR_IMPORT_JOB,
                source_path=job.source_path,
                title=f"Connector import job ({job.connector_id})",
                metadata={
                    "connector_id": job.connector_id,
                    "status": job.status,
                    "imported_count": len(job.imported_files),
                    "skipped_count": len(job.skipped_files),
                    "created_at": job.created_at.isoformat()
                    if job.created_at
                    else None,
                },
                content=json.loads(job.model_dump_json()),
            )
            ArtifactRepository(conn).add(artifact)
        finally:
            conn.close()
    except Exception:
        pass  # best-effort only


def validate_connector_id(
    connector_id: str,
) -> ConnectorDefinition:
    """Return the definition or raise a descriptive error."""
    from decision_system.connectors.registry import (
        get_connector_definition,
        list_connectors,
    )

    definition = get_connector_definition(connector_id)
    if definition is None:
        available = ", ".join(
            c.connector_id for c in list_connectors()
        )
        raise ValueError(
            f"Unknown connector '{connector_id}'. "
            f"Available connectors: {available}."
        )
    return definition
def run_dry_run(
    connector_id: str,
    source_path: str | Path,
) -> ConnectorDryRunResult:
    """Dispatch a dry-run to the right connector implementation.

    Returns structured results. For stub connectors, returns an empty
    dry-run with a warning describing the stub status.
    """
    definition = validate_connector_id(connector_id)

    if definition.is_stub:
        return run_stub_dry_run(connector_id, definition)

    if definition.connector_type.value == "local-files":
        return _run_local_dry_run(connector_id, source_path)

    return ConnectorDryRunResult(
        connector_id=connector_id,
        source_path=str(source_path),
        files=[],
        skipped_files=[],
        warnings=[
            f"Connector '{connector_id}' has no dry-run implementation yet."
        ],
        would_import_count=0,
    )


def run_import(
    connector_id: str,
    source_path: str | Path,
) -> ConnectorImportResult:
    """Dispatch a real import to the right connector implementation.

    Stub connectors raise ExternalConnectorError with a clear message.
    Local files connector copies/skips files into generated output dirs.
    When an active workspace exists, the import job is also stored as a
    workspace artifact for auditability.
    """
    definition = validate_connector_id(connector_id)

    if definition.is_stub:
        run_stub_import(connector_id, definition)

    if definition.connector_type.value == "local-files":
        result = _run_local_import(connector_id, source_path)
        save_job(result.job)
        _store_connector_job_as_artifact(result.job, None)
        return result

    raise ExternalConnectorError(
        f"Connector '{connector_id}' has no import implementation in v1.1."
    )


def resolve_tags(connector_id: str) -> str:
    """Return a human-readable tag set for a connector (used in CLI output)."""
    from decision_system.connectors.registry import get_connector_definition

    definition = get_connector_definition(connector_id)
    if definition is None:
        return "unknown"
    if definition.is_stub:
        return "stub"
    return "real"
