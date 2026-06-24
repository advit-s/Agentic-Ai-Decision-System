"""Connector job orchestration: validate definition, run dry-run or real import.

Supports local-files, GitHub, and URL connectors for v1.28.
Import jobs are persisted with rich tracking fields.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.connectors.local_files import (
    run_dry_run as _run_local_dry_run,
    run_local_files_import as _run_local_import,
)
from decision_system.connectors.models import (
    ConnectorDefinition,
    ConnectorDryRunResult,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorType,
)
from decision_system.connectors.stubs import ExternalConnectorError
from decision_system.connectors.stubs import run_stub_dry_run
from decision_system.connectors.stubs import run_stub_import
from decision_system.connectors.store import save_job
from decision_system.connectors.audit import (
    record_import_started,
    record_import_completed,
    record_import_failed,
    record_item_imported,
)
from decision_system.connectors.metrics import (
    record_import_duration,
    record_items_found,
    record_items_imported,
    record_items_failed,
)
from decision_system.connectors.runtime_dispatch import (
    test_connection,
    list_items,
    sync,
)
from decision_system.connectors.config_store import get_config_store


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
                    "imported_count": job.items_imported,
                    "skipped_count": job.items_skipped,
                    "failed_count": job.items_failed,
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


def run_import_v2(
    connector_id: str,
    config_id: str | None = None,
    workspace_id: str | None = None,
    item_ids: list[str] | None = None,
) -> ConnectorImportResult:
    """v1.28 import using connector config store and runtime dispatch.

    Loads the connector config from the store, dispatches to the right
    runtime, and persists the import job with rich tracking fields.
    """
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None and config_id:
        cfg = store.load(workspace_id, config_id)
    if cfg is None:
        raise ValueError(f"Connector config not found: {connector_id}")

    definition = validate_connector_id(cfg.connector_type.value)
    if definition.is_stub:
        raise ExternalConnectorError(
            f"Connector '{cfg.connector_type.value}' is not available in v1.28."
        )

    job_id = str(uuid4())
    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    record_import_started(
        connector_id=cfg.connector_id,
        workspace_id=workspace_id,
        config_name=cfg.name,
    )

    job = ConnectorImportJob(
        job_id=job_id,
        workspace_id=workspace_id,
        connector_id=cfg.connector_id,
        status="running",
        started_at=started_at,
        created_at=started_at,
    )

    try:
        result = sync(cfg, item_ids=item_ids)

        duration_ms = (time.time() - start_time) * 1000

        items_found = result.get("items_found", 0)
        items_imported = len(result.get("content_list", []))
        items_skipped = result.get("items_skipped", 0)
        items_failed = result.get("items_failed", 0)

        # Record each imported item
        for content in result.get("content_list", []):
            record_item_imported(
                connector_id=cfg.connector_id,
                external_id=getattr(content, "external_id", ""),
                title=getattr(content, "title", ""),
                workspace_id=workspace_id,
            )

        # Record metrics
        record_import_duration(
            cfg.connector_id, duration_ms,
            items_imported=items_imported, items_failed=items_failed,
        )
        record_items_found(cfg.connector_id, items_found)
        record_items_imported(cfg.connector_id, items_imported)
        if items_failed:
            record_items_failed(cfg.connector_id, items_failed)

        # Build output paths
        output_paths = []
        for content in result.get("content_list", []):
            fname = getattr(content, "filename", "unknown.txt")
            output_paths.append(f".decision_system/connectors/imported/{job_id}/{fname}")

        completed_at = datetime.now(timezone.utc)
        job.status = "completed"
        job.items_found = items_found
        job.items_imported = items_imported
        job.items_skipped = items_skipped
        job.items_failed = items_failed
        job.output_paths = output_paths
        job.completed_at = completed_at

        save_job(job)
        _store_connector_job_as_artifact(job, None)

        record_import_completed(
            connector_id=cfg.connector_id,
            items_imported=items_imported,
            items_skipped=items_skipped,
            items_failed=items_failed,
            job_id=job_id,
            workspace_id=workspace_id,
        )

        return ConnectorImportResult(
            job=job,
            dry_run=False,
            imported_count=items_imported,
            skipped_count=items_skipped,
            failed_count=items_failed,
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        record_import_duration(cfg.connector_id, duration_ms)
        record_error(cfg.connector_id, type(e).__name__)
        record_import_failed(
            connector_id=cfg.connector_id,
            error=str(e),
            workspace_id=workspace_id,
        )

        job.status = "failed"
        job.errors = [str(e)]
        job.completed_at = datetime.now(timezone.utc)
        save_job(job)

        return ConnectorImportResult(
            job=job,
            dry_run=False,
            imported_count=0,
            skipped_count=0,
            failed_count=1,
        )


def run_test_connection(
    connector_id: str,
    config_id: str | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Test connection for a connector config."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None and config_id:
        cfg = store.load(workspace_id, config_id)
    if cfg is None:
        return {"success": False, "message": f"Connector config not found: {connector_id}"}

    return test_connection(cfg)


def run_list_items(
    connector_id: str,
    path: str = "",
    config_id: str | None = None,
    workspace_id: str | None = None,
) -> list[Any]:
    """List items for a connector config."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None and config_id:
        cfg = store.load(workspace_id, config_id)
    if cfg is None:
        return []

    return list_items(cfg, path)


def resolve_tags(connector_id: str) -> str:
    """Return a human-readable tag set for a connector (used in CLI output)."""
    from decision_system.connectors.registry import get_connector_definition

    definition = get_connector_definition(connector_id)
    if definition is None:
        return "unknown"
    if definition.is_stub:
        return "stub"
    return "real"


# Import record_error used in exception handler
from decision_system.connectors.metrics import record_error


# ---------------------------------------------------------------------------
# Incremental sync (v1.29)
# ---------------------------------------------------------------------------


def run_sync(
    connector_id: str,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    """Run incremental sync for a connector.

    Compares content hashes against previous sync state and only imports
    new or changed items. Unchanged items are skipped. Deleted remote
    items are marked but local data is preserved.

    Returns a dict with sync result details.
    """
    from decision_system.connectors.sync_runner import get_sync_runner

    runner = get_sync_runner()
    result = runner.sync_connector(
        connector_id=connector_id,
        workspace_id=workspace_id,
    )
    return {
        "connector_id": result.connector_id,
        "workspace_id": result.workspace_id,
        "status": result.status,
        "items_new": result.items_new,
        "items_changed": result.items_changed,
        "items_unchanged": result.items_unchanged,
        "items_failed": result.items_failed,
        "items_deleted_remote": result.items_deleted_remote,
        "duration_ms": result.duration_ms,
        "job_id": result.job_id,
        "error": result.error,
    }
