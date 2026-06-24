# Connector Reliability Audit

> **Date:** 2026-06-24
> **Version baseline:** 1.30.0-dev
> **Milestone:** v1.31 — Connector Reliability, Rate Limits + Large Import Handling

## MCP Codebase Inspection

Codebase Memory MCP was available and used to inspect connector architecture. The knowledge graph has 9,971 nodes and 33,783 edges covering the full codebase.

## Current Import/Sync Flow

### Import flow (v1.28+)

1. User creates a `ConnectorConfig` via config store (workspace-scoped).
2. `config_store` persists config as JSON under `.decision_system/connectors/configs/`.
3. On import, `run_import_v2` in `import_jobs.py` is called.
4. It loads config from `config_store`, creates a job record, then calls `runtime_dispatch.sync()`.
5. `runtime_dispatch.sync()` maps connector type to runtime:
   - `LOCAL_FILES` → `LocalFolderConnectorRuntime`
   - `GITHUB` → `GitHubConnectorRuntime` (via `github_connector.py`)
   - `URL_IMPORT` → `UrlConnectorRuntime` (via `url_connector.py`)
   - `NOTION`/`GOOGLE_DRIVE` → `FakeConnectorRuntime` (stub)
6. Runtime's `sync()` does a `list_items()` + per-item `fetch_item()` loop.
7. Results are collected in memory and returned.
8. Job record is persisted via `store.save_job()` as JSON under `.decision_system/connectors/jobs/`.

### Sync flow (v1.29)

1. `SyncRunner.sync_connector()` is called (manually or via due schedules).
2. Loads last sync state from `SyncStateStore` (JSON files under `.decision_system/connectors/sync_state/`).
3. Fetches current items via `runtime_dispatch.sync()`.
4. Compares content hashes (SHA-256) to detect new/changed/unchanged items.
5. Items not seen are marked `deleted_remote` (local data preserved).
6. Updates schedule's `last_run_at`/`next_run_at`.
7. Emits audit events and metrics.

## Current Job Lifecycle

| Stage | Implementation |
|-------|----------------|
| Creation | `ConnectorImportJob` created with `job_id`, `workspace_id`, `connector_id`, `status="running"` |
| Running | Items processed in a single batch in memory |
| Completion | Status set to `completed` or `failed`; persisted via `store.save_job()` |
| Persistence | JSON files in `.decision_system/connectors/jobs/` |
| Fields | `job_id`, `workspace_id`, `connector_id`, `status`, `items_found`, `items_imported`, `items_skipped`, `items_failed`, `output_paths`, `errors`, `warnings`, `started_at`, `completed_at` |

**Gaps:** No `total_items`, `processed_items`, `changed_items`, `rate_limited_items`, `current_item_id`, `duration_ms`, `paused`, `cancelled` statuses. No progress tracking.

## Current Retry Behavior

**No structured retry policy exists.** Failures are handled at the top-level exception handler in `import_jobs.py`:
- Any exception → job marked `failed`, error recorded.
- No per-item retry.
- No backoff policy.
- No distinction between retryable vs. non-retryable errors.
- No retry count tracking.

## Current Rate-Limit Behavior

**No structured rate-limit handling exists.** The GitHub connector and URL connector do not inspect rate-limit headers. Rate-limit conditions would manifest as generic connection errors.

## Current Pagination Behavior

**No pagination support in the connector framework.** Key gaps:
- `runtime_dispatch.list_items()` returns a flat list with no pagination parameters.
- `ConnectorRuntime.list_items()` signature has no `page`/`page_size`/`cursor` parameters.
- The API endpoint `GET /workspaces/{ws}/connectors/{id}/items` returns all items at once.
- Local folder connector lists all items directly.

## Current Large Import Risks

1. **Memory pressure:** All items are loaded into memory before processing.
2. **No batching:** Single monolithic import loop with no progress persistence between batches.
3. **No cancellation:** No mechanism to cancel a running import.
4. **No resumption:** Failed imports must restart from scratch.
5. **No timeout awareness:** No protection against slow networks or huge item lists.
6. **No duplicate detection at import time:** Only sync state checks hashes post-hoc.
7. **No versioning:** Re-importing a changed file overwrites previous data sources.
8. **No progress reporting:** Jobs only report final counts, not intermediate progress.

## v1.31 Plan

### Phase 2 — Import Job Progress Model
Add rich progress fields to `ConnectorImportJob`: `total_items`, `processed_items`, `changed_items`, `unchanged_items`, `rate_limited_items`, `current_item_id`, `duration_ms`. Add `queued`, `completed_with_warnings`, `cancelled`, `paused` statuses.

### Phase 3 — Batch Import Processing
Implement bounded batch processing where items are processed in configurable-size batches, progress is persisted after each batch.

### Phase 4 — Pagination Support
Add paginated item listing: `page`, `page_size`, `next_cursor`, `has_more`, `total_count` to `list_items()` and the API endpoint. Update `ConnectorRuntime.list_items()` signature.

### Phase 5 — Retry and Backoff Policy
Add a `RetryPolicy` class with retryable/non-retryable error classification, bounded retries (max 3 attempts), exponential backoff, retry-logging.

### Phase 6 — Rate-Limit Handling
Add rate-limit detection for HTTP connectors (GitHub, URL). Handle 429 responses, inspect rate-limit headers, record `rate_limited` status, respect `Retry-After`.

### Phase 7 — Cancel/Pause/Resume Foundation
Add `cancel_requested`, `paused` status support. Implement checkpoint-based resume for failed/paused jobs.

### Phase 8 — Connector Job APIs
Add cancel/resume endpoints, paginated item listing endpoint, improved job querying.

### Phase 9 — Duplicate Detection and Import Idempotency
Use `content_hash` + `external_id` + `source_url` for duplicate detection. Idempotent re-imports for unchanged content.

### Phase 10 — Data-Source Version/Provenance Safety
Add version tracking for imported items: `version_number`, `previous_source_id`, `supersedes_source_id`, `content_hash`, `external_modified_at`.

### Phase 11 — Frontend Reliability UI
Upgrade the ConnectorsPage with job progress bars, counts, rate-limit warnings, cancel/resume buttons, pagination.

### Phase 12 — Audit and Metrics
Add reliability-specific audit events and metrics.

### Phase 13 — Demo Large Import Path
Create demo fixture for large local folder import (100+ small files).

### Phase 14 — Tests
Comprehensive tests for all new features.

### Phase 15 — Documentation Update
Update all relevant docs.

## Baseline Test Results

| Test Suite | Status |
|------------|--------|
| `tests/test_connectors.py` | ✅ 67 passed |
| `tests/test_connector_sync.py` | ✅ 40 passed |
| `tests/test_connector_setup.py` | ✅ 57 passed |
| `tests/test_api_connector.py` | ✅ 24 passed |
| `tests/test_connector_cli.py` | ⚠️ 15 passed, 3 failed (pre-existing CLI stub message changes) |
| Frontend build | ✅ Builds successfully |
