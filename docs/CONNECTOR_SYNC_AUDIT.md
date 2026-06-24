# Connector Sync Audit — v1.29

## Current connector import behavior (v1.28)

- Connectors are read-only, workspace-scoped, audited, permission-gated.
- `run_import_v2()` in `import_jobs.py` dispatches to runtime dispatch, creates a
  `ConnectorImportJob`, persists it, records audit events, and emits metrics.
- No incremental sync — every import re-fetches all items.
- No sync state tracking — no content hashing or change detection.
- No schedule model — all imports are manual one-shot operations.
- Jobs are stored as JSON in `.decision_system/connectors/jobs/`.

## Current scheduler behavior (v1.28)

The `workflow_engine` has its own schedule model (`WorkflowSchedule`) and
`scheduler_service` for workflow execution. Connector schedules do not exist yet.

## Current sync/job models

- `ConnectorImportJob` — tracks job status, counts, errors.
- `ConnectorImportResult` — lightweight summary.
- `ConnectorJobStore` — JSON persistence in `.decision_system/connectors/jobs/`.
- `ConnectorConfig` — has `last_sync_at` timestamp but no incremental tracking.

## What incremental sync needs

| Need | Current state | v1.29 plan |
|------|--------------|------------|
| Per-item sync state | None | New `SyncStateItem` model + `SyncStateStore` |
| Content hashing | None | SHA-256 hash of fetched content |
| Change detection | None | Compare content_hash across sync runs |
| Deleted remote detection | None | Track `last_seen_at`; mark missing items |
| Schedule persistence | None | New `ConnectorSchedule` model + store |
| Schedule runner | None | New `SyncRunner` service |
| Manual sync trigger | Via import API | New `POST /sync` endpoint |
| Run-due endpoint | None | New `POST /connector-sync/run-due` |
| Sync audit events | Import events only | Add sync-specific events |
| Sync metrics | Import metrics only | Add sync-specific metrics |
| RBAC sync/schedule perms | None | New permissions `connector.sync`, `connector.schedule` |

## Risks

1. **Content hash collisions** — SHA-256 is sufficient for local file integrity.
2. **Large syncs** — all processing is local (disk I/O bound, not network).
3. **Stale state** — deleted-remote won't delete local data (by design).
4. **Secret exposure** — config secrets stay resolved at runtime; sync metadata
   never includes raw secrets.
5. **Workspace isolation** — all sync state is scoped to workspace_id.
6. **Audit bypass** — all sync operations go through audit events; failures
   are captured.

## v1.29 Plan

1. Add `ConnectorSyncStateItem` model + `SyncStateStore` (JSON-backed).
2. Add `ConnectorSchedule` model + `ScheduleStore` (JSON-backed).
3. Add `SyncRunner` service — find due schedules, run sync, update state, emit audit/metrics.
4. Add `run_sync()` to `import_jobs` — compares hashes, imports only new/changed.
5. Add API endpoints for sync trigger, state inspection, schedule CRUD, run-due.
6. Add `connector.sync` and `connector.schedule` permissions.
7. Add sync audit events + metrics.
8. Update frontend ConnectorsPage with sync UI.
9. Add data source versioning metadata for changed items.
10. Update citation formatting.
11. Add demo sync path.
12. Tests for all above.
13. Documentation.

## Acceptance criteria

- Sync state persists locally (JSON store).
- Unchanged items skipped, changed items re-imported.
- New items detected, deleted-remote marked (local data preserved).
- Manual sync via API.
- Schedule CRUD via API.
- Run-due sync runner finds due schedules.
- RBAC enforces sync/schedule permissions.
- Audit events recorded for sync actions.
- Metrics captured for sync runs.
- Frontend shows sync status, history, schedule controls.
- Changed-item imports preserve provenance metadata.
- Reports cite synced content.
- Demo shows local folder incremental sync.
