"""Sync runner service for connector incremental sync (v1.29).

Finds due schedules, runs sync, updates sync state, emits audit/metrics.
Does not require external worker infrastructure.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel

from decision_system.connectors.audit import (
    record_sync_completed,
    record_sync_failed,
    record_sync_item_changed,
    record_sync_item_new,
    record_sync_item_unchanged,
    record_sync_started,
)
from decision_system.connectors.config_store import get_config_store
from decision_system.connectors.metrics import (
    record_sync_duration,
    record_sync_items_count,
)
from decision_system.connectors.models import (
    ConnectorImportJob,
)
from decision_system.connectors.runtime_dispatch import sync as runtime_sync
from decision_system.connectors.schedule import (
    ScheduleStore,
    get_schedule_store,
)
from decision_system.connectors.store import save_job
from decision_system.connectors.sync_state import (
    SyncStateStore,
    get_sync_state_store,
)


class SyncResult(BaseModel):
    """Result of a single sync run."""

    connector_id: str
    workspace_id: str | None = None
    items_new: int = 0
    items_changed: int = 0
    items_unchanged: int = 0
    items_failed: int = 0
    items_deleted_remote: int = 0
    duration_ms: float = 0
    job_id: str = ""
    status: str = "completed"  # completed | failed | completed_with_warnings
    error: str | None = None
    evidence_bridge_result: dict | None = None


logger = logging.getLogger(__name__)


class SyncRunner:
    """Runner for connector incremental sync."""

    def __init__(
        self,
        sync_state_store: SyncStateStore | None = None,
        schedule_store: ScheduleStore | None = None,
    ) -> None:
        self._sync_store = sync_state_store or get_sync_state_store()
        self._schedule_store = schedule_store or get_schedule_store()

    def sync_connector(
        self,
        connector_id: str,
        workspace_id: str | None = None,
    ) -> SyncResult:
        """Run incremental sync for a specific connector."""
        start_time = time.time()
        result = SyncResult(
            connector_id=connector_id,
            workspace_id=workspace_id,
        )

        record_sync_started(connector_id=connector_id, workspace_id=workspace_id)

        try:
            # Load connector config
            store = get_config_store()
            cfg = store.load(workspace_id, connector_id)
            if cfg is None:
                raise ValueError(f"Connector config not found: {connector_id}")

            # Load previous sync state
            prev_state = {
                item.external_id: item
                for item in self._sync_store.get_sync_state(workspace_id, connector_id)
            }

            # Run runtime sync to get current items
            sync_result = runtime_sync(cfg)
            content_list = sync_result.get("content_list", [])

            # Track which external_ids we have seen
            seen_ids: set[str] = set()

            job_id = str(uuid4())
            job = ConnectorImportJob(
                job_id=job_id,
                workspace_id=workspace_id,
                connector_id=connector_id,
                status="running",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )

            for content in content_list:
                external_id = getattr(content, "external_id", "")
                if not external_id:
                    continue

                seen_ids.add(external_id)

                # Compute hash of content
                content_text = getattr(content, "content_text", "") or ""
                content_bytes = getattr(content, "content_bytes", None)
                if content_bytes:
                    content_hash = self._sync_store.compute_hash(content_bytes)
                else:
                    content_hash = self._sync_store.compute_hash(content_text)

                prev = prev_state.get(external_id)

                if prev is None:
                    status = "new"
                    result.items_new += 1
                    record_sync_item_new(
                        connector_id=connector_id,
                        external_id=external_id,
                        workspace_id=workspace_id,
                    )
                elif prev.content_hash != content_hash:
                    status = "changed"
                    result.items_changed += 1
                    record_sync_item_changed(
                        connector_id=connector_id,
                        external_id=external_id,
                        workspace_id=workspace_id,
                    )
                else:
                    status = "unchanged"
                    result.items_unchanged += 1
                    record_sync_item_unchanged(
                        connector_id=connector_id,
                        external_id=external_id,
                        workspace_id=workspace_id,
                    )

                self._sync_store.mark_seen(
                    workspace_id,
                    connector_id,
                    external_id,
                    content_hash=content_hash,
                    status=status,
                )

            # Mark items not seen this run as deleted_remote
            for ext_id, prev in prev_state.items():
                if ext_id not in seen_ids and prev.status != "deleted_remote":
                    self._sync_store.mark_deleted_remote(workspace_id, connector_id, ext_id)
                    result.items_deleted_remote += 1

            # Update job
            completed_at = datetime.now(timezone.utc)
            job.status = "completed"
            job.items_found = len(content_list)
            job.items_imported = result.items_new + result.items_changed
            job.items_skipped = result.items_unchanged
            job.completed_at = completed_at
            save_job(job)

            # Update schedule last_run
            schedule = self._schedule_store.find_schedule_for_connector(workspace_id, connector_id)
            if schedule is not None:
                schedule.last_run_at = completed_at
                schedule.next_run_at = schedule.calculate_next_run()
                self._schedule_store.update_schedule(workspace_id, schedule)

            # Record metrics
            duration_ms = (time.time() - start_time) * 1000
            record_sync_duration(
                connector_id,
                duration_ms,
                items_new=result.items_new,
                items_changed=result.items_changed,
                items_unchanged=result.items_unchanged,
                items_failed=result.items_failed,
            )
            record_sync_items_count(connector_id, "new", result.items_new)
            record_sync_items_count(connector_id, "changed", result.items_changed)
            record_sync_items_count(connector_id, "unchanged", result.items_unchanged)
            if result.items_failed:
                record_sync_items_count(connector_id, "failed", result.items_failed)

            result.duration_ms = duration_ms
            result.job_id = job_id

            # Reindex new/changed content into evidence system
            if workspace_id and content_list and (result.items_new > 0 or result.items_changed > 0):
                try:
                    from decision_system.connectors.evidence_bridge import (
                        persist_connector_content,
                    )

                    bridge_result = persist_connector_content(
                        workspace_id=workspace_id,
                        content_list=[
                            c for c in content_list if getattr(c, "external_id", "") in seen_ids
                        ],
                        connector_name=cfg.name,
                        connector_id=cfg.connector_id,
                    )
                    logger.info(
                        "Sync evidence bridge: %d data sources, %d chunks, %d indexed",
                        bridge_result.get("data_sources_created", 0),
                        bridge_result.get("chunks_parsed", 0),
                        bridge_result.get("chunks_indexed", 0),
                    )
                    result.evidence_bridge_result = bridge_result
                except Exception as bridge_err:
                    logger.warning("Sync evidence bridge failed: %s", bridge_err)
                    result.evidence_bridge_result = {"error": str(bridge_err)}
                    if result.status == "completed":
                        result.status = "completed_with_warnings"

            # Reconcile deleted_remote items: mark associated DataSources as archived
            if result.items_deleted_remote > 0 and workspace_id:
                try:
                    from decision_system.data_sources.store import DataSourceStore

                    ds_store = DataSourceStore()
                    deleted_count = 0
                    for ext_id in list(getattr(result, "_deleted_ids", [])):
                        ds = ds_store.find_by_metadata(
                            workspace_id=workspace_id,
                            key="external_id",
                            value=ext_id,
                        )
                        if ds and ds.status != "archived":
                            ds.status = "archived"
                            ds.updated_at = datetime.now(timezone.utc)
                            if ds.metadata is None:
                                ds.metadata = {}
                            ds.metadata["archived_at"] = datetime.now(timezone.utc).isoformat()
                            ds.metadata["archived_reason"] = "connector_sync_deleted_remote"
                            ds_store.save(ds)
                            deleted_count += 1
                    if deleted_count:
                        logger.info(
                            "Archived %d DataSources for deleted_remote items", deleted_count
                        )
                except Exception as reconcile_err:
                    logger.warning("Deleted_remote reconciliation failed: %s", reconcile_err)

            record_sync_completed(
                connector_id=connector_id,
                items_new=result.items_new,
                items_changed=result.items_changed,
                items_unchanged=result.items_unchanged,
                items_failed=result.items_failed,
                workspace_id=workspace_id,
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            result.duration_ms = duration_ms
            result.status = "failed"
            result.error = str(e)

            record_sync_failed(
                connector_id=connector_id,
                error=str(e),
                workspace_id=workspace_id,
            )

            # Save failure job
            job = ConnectorImportJob(
                job_id=str(uuid4()),
                workspace_id=workspace_id,
                connector_id=connector_id,
                status="failed",
                errors=[str(e)],
                started_at=datetime.fromtimestamp(start_time, tz=timezone.utc),
                completed_at=datetime.now(timezone.utc),
                created_at=datetime.fromtimestamp(start_time, tz=timezone.utc),
            )
            save_job(job)

            return result

    def run_due_schedules(self) -> list[SyncResult]:
        """Find and run all due connector schedules."""
        due_schedules = self._schedule_store.list_due_schedules()
        results: list[SyncResult] = []

        for schedule in due_schedules:
            result = self.sync_connector(
                connector_id=schedule.connector_id,
                workspace_id=schedule.workspace_id,
            )
            results.append(result)

        return results


# Module-level singleton
_default_runner: SyncRunner | None = None


def get_sync_runner() -> SyncRunner:
    global _default_runner
    if _default_runner is None:
        _default_runner = SyncRunner()
    return _default_runner


def reset_sync_runner() -> None:
    global _default_runner
    _default_runner = None
