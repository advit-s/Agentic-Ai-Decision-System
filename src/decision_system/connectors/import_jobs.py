"""Connector job orchestration: validate definition, run dry-run or real import.

Supports local-files, GitHub, and URL connectors for v1.28.
Import jobs are persisted with rich tracking fields.

v1.31 adds: batch processing, pagination, retry/backoff, rate-limit handling,
cancel/pause/resume, duplicate detection, and provenance/versioning.
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
    ConnectorFetchedContent,
    ConnectorImportJob,
    ConnectorImportResult,
    ConnectorRuntimeItem,
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
    record_job_cancel_requested,
    record_job_cancelled,
    record_job_resumed,
    record_job_paused,
    record_item_retry,
    record_rate_limited,
    record_duplicate_detected,
    record_batch_completed,
    record_large_import,
    record_version_created,
)
from decision_system.connectors.metrics import (
    record_import_duration,
    record_items_found,
    record_items_imported,
    record_items_failed,
    record_error,
    record_batch_duration,
    record_retry_count,
    record_rate_limit_count,
    record_cancel_count,
    record_resume_count,
    record_duplicate_count,
    record_large_import_count,
)
from decision_system.connectors.runtime_dispatch import (
    test_connection,
    list_items,
    sync,
)
from decision_system.connectors.config_store import get_config_store
from decision_system.connectors.batch_processor import (
    BatchProcessor,
    get_batch_processor,
    reset_batch_processor,
)
from decision_system.connectors.pagination import (
    apply_pagination_params,
    paginate_items,
    PaginatedResult,
)
from decision_system.connectors.retry_policy import (
    RetryPolicy,
    get_retry_policy,
    reset_retry_policy,
)
from decision_system.connectors.rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    reset_rate_limiter,
)
from decision_system.connectors.dedup import (
    DuplicateDetector,
    DuplicateResult,
    get_duplicate_detector,
    reset_duplicate_detector,
)
from decision_system.connectors.provenance import (
    ProvenanceTracker,
    SourceVersion,
    get_provenance_tracker,
    reset_provenance_tracker,
)


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


# ---------------------------------------------------------------------------
# v1.28 Import (run_import_v2)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# v1.31 Enhanced import with batch processing, retry, rate-limit, dedup, provenance
# ---------------------------------------------------------------------------


def run_list_items_paginated(
    connector_id: str,
    path: str = "",
    page: int = 1,
    page_size: int = 50,
    config_id: str | None = None,
    workspace_id: str | None = None,
) -> PaginatedResult:
    """List items with pagination support (v1.31)."""
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None and config_id:
        cfg = store.load(workspace_id, config_id)
    if cfg is None:
        return PaginatedResult(items=[], total_count=0, page=page, page_size=page_size)

    items = list_items(cfg, path)
    return apply_pagination_params(items, page=page, page_size=page_size)


def run_import_v3(
    connector_id: str,
    workspace_id: str | None = None,
    item_ids: list[str] | None = None,
    batch_size: int = 50,
    enable_dedup: bool = True,
    enable_provenance: bool = True,
) -> ConnectorImportResult:
    """v1.31 enhanced import with batch processing, retry, rate-limit, dedup, provenance.

    Processes items in bounded batches with:
    - Progress persistence after each batch
    - Retry with exponential backoff for transient failures
    - Rate-limit detection and graceful handling
    - Content-based duplicate detection
    - Version/provenance tracking for changed items
    - Cancel support (checks between batches)
    - Checkpoint-based resume

    Args:
        connector_id: Connector identifier.
        workspace_id: Workspace scope.
        item_ids: Optional subset of items to import.
        batch_size: Number of items per batch (default 50).
        enable_dedup: Whether to deduplicate content by hash (default True).
        enable_provenance: Whether to track version history (default True).

    Returns:
        ConnectorImportResult with final job state.
    """
    store = get_config_store()
    cfg = store.load(workspace_id, connector_id)
    if cfg is None:
        raise ValueError(f"Connector config not found: {connector_id}")

    definition = validate_connector_id(cfg.connector_type.value)
    if definition.is_stub:
        raise ExternalConnectorError(
            f"Connector '{cfg.connector_type.value}' is not available."
        )

    job_id = str(uuid4())
    start_time = time.time()
    started_at = datetime.now(timezone.utc)

    # Audit large imports
    record_import_started(
        connector_id=cfg.connector_id,
        workspace_id=workspace_id,
        config_name=cfg.name,
    )

    # Initialize job with progress tracking
    job = ConnectorImportJob(
        job_id=job_id,
        workspace_id=workspace_id,
        connector_id=cfg.connector_id,
        status="queued",
        job_type="import",
        started_at=started_at,
        created_at=started_at,
        batch_size=batch_size,
    )
    save_job(job)
    _store_connector_job_as_artifact(job, None)

    # Get dedup and provenance trackers
    dedup = get_duplicate_detector() if enable_dedup else None
    provenance = get_provenance_tracker() if enable_provenance else None

    try:
        # Get items to import
        items: list[ConnectorRuntimeItem] = list_items(cfg)
        if item_ids is not None:
            item_ids_set = set(item_ids)
            items = [i for i in items if i.external_id in item_ids_set]

        total = len(items)
        if total > 100:
            record_large_import(cfg.connector_id, total, workspace_id)
            record_large_import_count(cfg.connector_id)

        if not items:
            job.status = "completed"
            job.total_items = 0
            job.completed_at = datetime.now(timezone.utc)
            job.duration_ms = (time.time() - start_time) * 1000
            save_job(job)
            record_import_completed(
                connector_id=cfg.connector_id, items_imported=0,
                items_skipped=0, items_failed=0, job_id=job_id,
                workspace_id=workspace_id,
            )
            return ConnectorImportResult(job=job, dry_run=False)

        # Process via batch processor
        processor = get_batch_processor()
        processor.batch_size = batch_size

        def fetch_item_fn(item: ConnectorRuntimeItem) -> ConnectorFetchedContent | None:
            """Fetch a single item with dedup and provenance tracking."""
            from decision_system.connectors.runtime_dispatch import fetch_item

            content = fetch_item(cfg, item)
            if not content:
                return None

            # Compute content hash
            content_bytes = content.content_bytes or (content.content_text or "").encode("utf-8")
            import hashlib
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            # Check dedup
            if dedup:
                dup_result = dedup.check_duplicate(
                    cfg.connector_id, item.external_id, content_hash,
                    source_url=item.source_url, workspace_id=workspace_id,
                )
                if dup_result.is_unchanged:
                    record_duplicate_detected(
                        cfg.connector_id, item.external_id, content_hash,
                        workspace_id=workspace_id,
                    )
                    record_duplicate_count(cfg.connector_id)
                    # Return content but mark as unchanged via metadata
                    if content.metadata is None:
                        content.metadata = {}
                    content.metadata["dup_status"] = "unchanged"
                    content.metadata["dup_existing_version"] = dup_result.existing_version
                    return content

                if dup_result.is_changed:
                    record_duplicate_detected(
                        cfg.connector_id, item.external_id, content_hash,
                        workspace_id=workspace_id,
                    )

            # Record import in dedup store
            if dedup:
                dedup.record_import(
                    cfg.connector_id, item.external_id, content_hash,
                    source_id=content.external_id,
                    source_url=item.source_url,
                    workspace_id=workspace_id,
                )

            # Track provenance
            if provenance and content_hash:
                source_url = item.source_url or ""
                modified_at = item.modified_at.isoformat() if item.modified_at else None
                version = provenance.create_version(
                    cfg.connector_id, item.external_id, content_hash,
                    job_id=job_id, source_url=source_url,
                    label=item.title,
                    external_modified_at=modified_at,
                    workspace_id=workspace_id,
                )
                record_version_created(
                    cfg.connector_id, item.external_id, version.version_number,
                    workspace_id=workspace_id,
                )
                if content.metadata is None:
                    content.metadata = {}
                content.metadata["version_number"] = version.version_number
                content.metadata["source_version_id"] = version.version_id

            return content

        # Run batch processing
        job = processor.process_items(
            job, items, fetch_item_fn,
            progress_callback=lambda j: _store_connector_job_as_artifact(j, None),
        )

        # Record final audit
        record_import_completed(
            connector_id=cfg.connector_id,
            items_imported=job.items_imported,
            items_skipped=job.items_skipped,
            items_failed=job.items_failed,
            job_id=job_id,
            workspace_id=workspace_id,
        )

        # Metrics
        duration_ms = job.duration_ms or ((time.time() - start_time) * 1000)
        record_import_duration(cfg.connector_id, duration_ms,
                               items_imported=job.items_imported,
                               items_failed=job.items_failed)
        record_items_found(cfg.connector_id, job.total_items)
        record_items_imported(cfg.connector_id, job.items_imported)
        if job.items_failed:
            record_items_failed(cfg.connector_id, job.items_failed)

        return ConnectorImportResult(
            job=job,
            dry_run=False,
            imported_count=job.items_imported,
            skipped_count=job.items_skipped,
            failed_count=job.items_failed,
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
        job.errors = list(job.errors or []) + [str(e)]
        job.duration_ms = duration_ms
        job.completed_at = datetime.now(timezone.utc)
        save_job(job)

        return ConnectorImportResult(
            job=job,
            dry_run=False,
            imported_count=job.items_imported,
            skipped_count=job.items_skipped,
            failed_count=job.items_failed or 1,
        )


# ---------------------------------------------------------------------------
# Cancel / Resume / Pause (v1.31)
# ---------------------------------------------------------------------------


def request_cancel_job(job_id: str) -> dict[str, Any]:
    """Request cancellation of a running import job."""
    from decision_system.connectors.store import get_job

    job = get_job(job_id)
    if job is None:
        return {"success": False, "message": f"Job not found: {job_id}"}

    if job.status not in ("running", "queued"):
        return {"success": False, "message": f"Job {job_id} is not running (status={job.status})"}

    processor = get_batch_processor()
    processor.request_cancel(job)

    record_job_cancel_requested(
        job_id=job_id, connector_id=job.connector_id,
        workspace_id=job.workspace_id,
    )
    record_cancel_count(job.connector_id)

    return {"success": True, "message": f"Cancel requested for job {job_id}"}


def confirm_cancel_job(job_id: str) -> dict[str, Any]:
    """Confirm that a job was cancelled (update status)."""
    from decision_system.connectors.store import get_job

    job = get_job(job_id)
    if job is None:
        return {"success": False, "message": f"Job not found: {job_id}"}

    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    save_job(job)

    record_job_cancelled(
        job_id=job_id, connector_id=job.connector_id,
        workspace_id=job.workspace_id,
    )

    return {"success": True, "message": f"Job {job_id} cancelled"}


def resume_job(job_id: str) -> dict[str, Any]:
    """Resume a failed, paused, or cancelled job."""
    from decision_system.connectors.store import get_job
    from decision_system.connectors.runtime_dispatch import list_items as rt_list_items

    job = get_job(job_id)
    if job is None:
        return {"success": False, "message": f"Job not found: {job_id}"}

    if job.status not in ("failed", "paused", "cancelled"):
        return {"success": False, "message": f"Job {job_id} is not in a resumable state (status={job.status})"}

    # Get connector config
    store = get_config_store()
    cfg = store.load(job.workspace_id, job.connector_id)
    if cfg is None:
        return {"success": False, "message": f"Connector config not found: {job.connector_id}"}

    # Get items
    items = rt_list_items(cfg)
    processor = get_batch_processor()

    record_job_resumed(
        job_id=job_id, connector_id=job.connector_id,
        workspace_id=job.workspace_id,
    )
    record_resume_count(job.connector_id)

    def fetch_item_fn(item: ConnectorRuntimeItem) -> ConnectorFetchedContent | None:
        from decision_system.connectors.runtime_dispatch import fetch_item
        return fetch_item(cfg, item)

    try:
        updated_job = processor.resume_job(job, items, fetch_item_fn)
        return {"success": True, "job_id": job_id, "status": updated_job.status}
    except Exception as e:
        job.status = "failed"
        job.errors = list(job.errors or []) + [str(e)]
        job.completed_at = datetime.now(timezone.utc)
        save_job(job)
        return {"success": False, "message": str(e)}


def pause_job(job_id: str) -> dict[str, Any]:
    """Pause a running job."""
    from decision_system.connectors.store import get_job

    job = get_job(job_id)
    if job is None:
        return {"success": False, "message": f"Job not found: {job_id}"}

    if job.status != "running":
        return {"success": False, "message": f"Job {job_id} is not running (status={job.status})"}

    job.status = "paused"
    save_job(job)

    record_job_paused(
        job_id=job_id, connector_id=job.connector_id,
        workspace_id=job.workspace_id,
    )

    return {"success": True, "message": f"Job {job_id} paused"}
