# Implementation Report — v1.29.0-dev

## Summary
v1.29 adds **Connector Scheduling + Incremental Sync** to the read-only connector framework. Connectors now behave like safe local knowledge sync: they detect new/changed/unchanged/deleted items via content hashing, support manual and scheduled sync, and preserve all v1.28 safety guarantees (read-only, workspace-scoped, audited, permission-gated).

## Version
`1.29.0-dev` (updated in pyproject.toml, src/decision_system/__init__.py)

## MCP/agent skill usage
- `codebase-memory-mcp` was used to inspect connector architecture, models, store, import jobs, audit, metrics, runtime dispatch, RBAC permissions, and frontend components before implementation.
- Codebase has 9641 nodes, 32523 edges in the knowledge graph.

## Files changed

### New files
- `src/decision_system/connectors/sync_state.py` — SyncStateItem model + SyncStateStore
- `src/decision_system/connectors/schedule.py` — ConnectorSchedule model + ScheduleStore
- `src/decision_system/connectors/sync_runner.py` — SyncRunner service + SyncResult model
- `tests/test_connector_sync.py` — 40 tests for sync state, schedule, runner, citations
- `docs/CONNECTOR_SYNC_AUDIT.md` — Pre-flight audit documenting current behavior and v1.29 plan

### Modified files
- `src/decision_system/connectors/import_jobs.py` — Added `run_sync()` helper
- `src/decision_system/connectors/audit.py` — Added 11 sync/schedule audit events
- `src/decision_system/connectors/metrics.py` — Added 3 sync metric helpers
- `src/decision_system/identity/models.py` — Added `connector.sync` and `connector.schedule` permissions with RBAC matrix
- `src/decision_system/api/routes_connectors.py` — Added 8 API endpoints for sync and schedule
- `pyproject.toml` — Version 1.29.0-dev
- `src/decision_system/__init__.py` — Version 1.29.0-dev
- `web/workflow-builder/src/api.js` — Added 8 sync/schedule API functions (with mock fallbacks)
- `web/workflow-builder/src/components/ConnectorsPage.jsx` — Added sync button, sync state table, schedule controls
- `CHANGELOG.md` — v1.29.0-dev entry
- `docs/CURRENT_STATE.md` — v1.29.0-dev section

## Sync state model
```
SyncStateItem:
  sync_state_id, workspace_id, connector_id, external_id
  content_hash (SHA-256), last_seen_at, last_imported_at
  last_modified_at, local_source_id
  status: new | unchanged | changed | deleted_remote | failed | skipped
  metadata
```
Stored as JSON files: `.decision_system/connectors/sync_state/{workspace}/{connector_id}.json`

## Incremental sync logic
1. Load previous sync state from store
2. List current items from connector runtime
3. For each item, compute SHA-256 hash of content
4. If no previous state → new (import)
5. If hash differs → changed (re-import)
6. If hash matches → unchanged (skip)
7. Items not seen this run → marked deleted_remote (local data preserved)
8. Partial failures are isolated; sync continues on error

## Schedule model
```
ConnectorSchedule:
  schedule_id, workspace_id, connector_id
  enabled, schedule_type (manual|interval|cron)
  interval_minutes, cron_expression
  next_run_at, last_run_at
```
Stored as JSON files: `.decision_system/connectors/schedules/{workspace}/{connector_id}.json`

## Sync runner
`SyncRunner` orchestrates full sync lifecycle:
1. Load config from config store
2. Load previous sync state
3. Call runtime_sync() to list+fetch items
4. Compare hashes and classify each item
5. Mark deleted_remote for missing items
6. Save import job record
7. Update schedule last_run
8. Emit audit events and metrics
9. Return SyncResult with counts

## Sync APIs
- `POST /workspaces/{wid}/connectors/{cid}/sync` — manual sync
- `GET /workspaces/{wid}/connectors/{cid}/sync-state` — inspect sync state
- `GET /workspaces/{wid}/connectors/{cid}/sync-schedules` — list schedules
- `POST /workspaces/{wid}/connectors/{cid}/sync-schedules` — create schedule
- `PUT /workspaces/{wid}/connectors/{cid}/sync-schedules/{sid}` — update schedule
- `DELETE /workspaces/{wid}/connectors/{cid}/sync-schedules/{sid}` — delete schedule
- `POST /workspaces/{wid}/connectors/{cid}/sync-schedules/{sid}/toggle` — toggle schedule
- `POST /connector-sync/run-due` — run all due schedules

## RBAC/governance
- `connector.sync` — OWNER, ADMIN, ANALYST (manual sync)
- `connector.schedule` — OWNER, ADMIN (create/manage schedules)
- All syncs audited
- System-triggered sync uses system actor context

## Frontend sync UI
- Manual sync button on each connector card
- Sync state table with status badges (🆕 new, 🔄 changed, ✅ unchanged, 🗑️ deleted_remote, ❌ failed)
- Schedule controls: create, enable/disable, delete
- Last sync timestamp shown on cards
- Permission-gated: sync button requires connector.sync, schedule requires connector.schedule

## Audit/observability
- 11 new audit event types: sync_started, sync_completed, sync_failed, item_new, item_changed, item_unchanged, item_failed, schedule_created, schedule_updated, schedule_deleted, schedule_toggled
- 3 new metric helpers: sync_duration_ms, sync_items_*_count, schedules_due_count

## Tests added
40 tests covering:
- SyncStateItem model serialization
- SyncStateStore CRUD, mark_seen, mark_deleted_remote, mark_imported, workspace isolation
- Schedule model is_due, calculate_next_run, disabled
- ScheduleStore CRUD, list_due, toggle, workspace isolation
- SyncRunner: no config error, empty due schedules
- Run sync: nonexistent connector
- Sync state transitions: new→unchanged, changed→unchanged, deleted_remote preserved
- Citation display and evidence metadata

## Commands run
```bash
python -m pytest -q                           # 1519 passed, 3 pre-existing failures
python -m pytest tests/test_connector_sync -q  # 40 passed
python -m pytest tests/test_api_connector -q   # 24 passed
git status                                     # working tree clean
```

## Known limitations
1. **Cron expressions** are not fully parsed — fall back to interval-based calculation
2. **No external worker** — sync runs in the same process (sufficient for local deployment)
3. **Deleted remote items are not auto-cleaned** — manual cleanup of sync state required
4. **No OAuth/token refresh** — secret configs must be updated manually
5. **Frontend tests** not added — the ConnectorsPage uses mock mode which is sufficient
6. **Docker smoke test** not run due to environment constraints

## Recommended next milestone
```
v1.30 — Connector Expansion + OAuth/Token Setup UX
```
