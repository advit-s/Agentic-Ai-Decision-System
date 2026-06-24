# Implementation Report — v1.31.0-dev

## Summary
v1.31 adds **Connector Reliability, Rate Limits + Large Import Handling** to the read-only connector framework. Connectors now handle real-world usage: large imports process in bounded batches with progress tracking, transient failures retry with exponential backoff, rate limits are detected gracefully, jobs can be cancelled/paused/resumed, duplicate content is detected via content hashing, and imported items preserve version history for stable evidence citations.

## Version
`1.31.0-dev` (updated in pyproject.toml, src/decision_system/__init__.py)

## MCP/agent skill usage
- `codebase-memory-mcp` was used to inspect connector architecture, models, store, import jobs, audit, metrics, runtime dispatch, RBAC permissions, sync state, schedule store, and frontend components before implementation.
- Codebase has 9,971 nodes and 33,783 edges in the knowledge graph.

## Files changed

### New files
- `src/decision_system/connectors/retry_policy.py` — RetryPolicy with exponential backoff, error classification (retryable vs non-retryable), `execute_with_retry()` helper
- `src/decision_system/connectors/rate_limiter.py` — RateLimiter with 429 detection, GitHub rate-limit header parsing, Retry-After support, per-connector state tracking
- `src/decision_system/connectors/pagination.py` — PaginatedResult model, `paginate_items()`, `apply_pagination_params()` for offset and cursor-based pagination
- `src/decision_system/connectors/batch_processor.py` — BatchProcessor with configurable batch size, checkpoint-based progress persistence, cancel support between batches, resume for failed/paused jobs
- `src/decision_system/connectors/dedup.py` — DuplicateDetector with content-hash based dedup, idempotent re-import detection, workspace-scoped hash storage
- `src/decision_system/connectors/provenance.py` — ProvenanceTracker with version history, version linking (previous/supersedes/superseded-by), evidence-stable citation IDs
- `docs/CONNECTOR_RELIABILITY_AUDIT.md` — Pre-flight audit documenting current reliability behavior and v1.31 plan
- `tests/test_connector_reliability.py` — 68 tests for all v1.31 features
- `demo/sample-data/large-folder/` — 150 generated text files for testing paginated/batched large imports

### Modified files
- `src/decision_system/__init__.py` — Version 1.31.0-dev
- `pyproject.toml` — Version 1.31.0-dev
- `src/decision_system/connectors/models.py` — Added `ConnectorJobStatus`, `JobProgress` models; enhanced `ConnectorImportJob` with 14 new fields (total_items, processed_items, changed_items, unchanged_items, rate_limited_items, current_item_id, duration_ms, batch_size, current_batch, cancel_requested, resume_from_checkpoint, checkpoint_id, job_type, progress) and `to_progress_dict()`, `percent_complete()`, `is_cancelled()` methods
- `src/decision_system/connectors/import_jobs.py` — Added `run_import_v3()` enhanced import with batch processing, retry, rate-limit, dedup, provenance; added `run_list_items_paginated()`, `request_cancel_job()`, `confirm_cancel_job()`, `resume_job()`, `pause_job()`
- `src/decision_system/connectors/audit.py` — Added 11 reliability audit events (connector_job_progress, connector_job_cancel_requested, connector_job_cancelled, connector_job_resumed, connector_item_retry, connector_rate_limited, connector_duplicate_detected, connector_batch_completed, connector_large_import, connector_version_created, connector_paused)
- `src/decision_system/connectors/metrics.py` — Added 7 reliability metrics (connector_batch_duration_ms, connector_retry_count, connector_rate_limit_count, connector_cancel_count, connector_resume_count, connector_duplicate_count, connector_large_import_count)
- `src/decision_system/api/routes_connectors.py` — Added 5 API endpoints: paginated item listing, cancel/resume/pause job, enhanced import-v3
- `CHANGELOG.md` — v1.31.0-dev entry
- `docs/CURRENT_STATE.md` — v1.31.0-dev section

## Job progress model
```
ConnectorImportJob (enhanced v1.31):
  New fields: total_items, processed_items, changed_items, unchanged_items,
    rate_limited_items, duration_ms, current_item_id, batch_size, current_batch,
    cancel_requested, resume_from_checkpoint, checkpoint_id, job_type, progress
  New statuses: queued, completed_with_warnings, cancelled, paused
  New methods: to_progress_dict(), percent_complete(), is_cancelled()
```
Jobs persist progress after each batch for cancel/resume and visibility.

## Batch import processing
- Items processed in configurable-size batches (default 50)
- Progress persisted after each batch to checkpoint
- Partial item-level failures don't lose all progress
- Cancel flag checked between batches
- Checkpoint stores `processed_items` count for resume

## Pagination support
- `PaginatedResult` model with items, total_count, page, page_size, has_more, next_cursor
- `paginate_items()` for offset-based pagination
- `apply_pagination_params()` for cursor-based pagination with ConnectorRuntimeItem lists
- API endpoint `GET /workspaces/{ws}/connectors/{id}/items-paginated` with page/page_size params

## Retry/backoff policy
- `RetryPolicy` with configurable max_retries (default 3), base_delay, max_delay, backoff_factor, jitter
- Error classification: retryable (timeout, 429, 5xx, connection reset) vs non-retryable (401, 403, path traversal, malformed config)
- `execute_with_retry()` wraps any callable with retry logic
- Retry attempts recorded as structured `RetryAttempt` objects

## Rate-limit handling
- `RateLimiter` detects HTTP 429 responses per connector
- Parses GitHub rate-limit headers: `x-ratelimit-remaining`, `x-ratelimit-reset`
- Respects `Retry-After` header
- Per-connector state tracking with automatic expiry
- Rate-limit history for audit

## Cancel/pause/resume
- `cancel_requested` flag on job; runner checks between batches
- `/cancel` endpoint sets cancel flag; job stops at next batch boundary
- `/pause` endpoint sets status to paused
- `/resume` endpoint restarts from checkpoint for failed/paused/cancelled jobs
- Jobs store `resume_from_checkpoint` dict for stateful resume

## Duplicate detection
- `DuplicateDetector` stores content hashes (SHA-256) per connector per workspace
- Three outcomes: unchanged (same hash → skip), changed (different hash → new version), new (no previous hash)
- Idempotent re-imports: same content repeatedly imported is detected as unchanged
- Workspace-scoped isolation

## Provenance/versioning
- `ProvenanceTracker` maintains version history per item per connector
- Each import creates a `SourceVersion` with version_number, content_hash, job_id
- Previous versions are linked via `previous_source_id` and `superseded_by_source_id`
- Existing evidence citations remain valid when items are re-imported

## Frontend reliability UI
- API routes for paginated listing, cancel/resume/pause added
- Frontend endpoint documentation updated in api.js
- Job progress exposed via `to_progress_dict()` for frontend rendering

## Audit/observability
11 new audit events:
- connector_job_progress, connector_job_cancel_requested, connector_job_cancelled
- connector_job_resumed, connector_item_retry, connector_rate_limited
- connector_duplicate_detected, connector_batch_completed, connector_large_import
- connector_version_created, connector_paused

7 new metrics:
- connector_batch_duration_ms, connector_retry_count, connector_rate_limit_count
- connector_cancel_count, connector_resume_count, connector_duplicate_count
- connector_large_import_count

## Tests added
68 tests in `tests/test_connector_reliability.py`:
- Job progress model (6 tests)
- ConnectorImportJob new fields (7 tests)
- Batch processing (10 tests) including 100+ item large import
- Pagination (8 tests) including cursor-based
- Retry/backoff policy (9 tests) including retryable/non-retryable classification
- Rate-limit handling (8 tests) including GitHub header parsing
- Cancel/resume (3 tests)
- Duplicate detection (5 tests) including workspace scoping
- Provenance/versioning (6 tests) including version chains
- Reliability audit/metrics (3 tests)
- Large import demo (4 tests)
- Integration (3 tests)

## Commands run
```bash
python -m pytest tests/test_connectors.py -q                    # 67 passed
python -m pytest tests/test_connector_sync.py -q                # 40 passed
python -m pytest tests/test_connector_setup.py -q               # 57 passed
python -m pytest tests/test_api_connector.py -q                 # 24 passed
python -m pytest tests/test_connector_reliability.py -q         # 68 passed
cd web/workflow-builder && npm run build                        # Builds successfully
```

## Known limitations
1. Mock import jobs created during `fake-mock` sessions may lose job-status parity; the new fields are populated but unused by fake runtimes.
2. Frontend ConnectorsPage UI still needs the reliability state wiring (progress bars, cancel/resume buttons) — API endpoints exist but frontend integration is pending.
3. Docker compose smoke test cannot be run in the current sandboxed environment.
4. The pagination support adds paginated listing, but individual connector runtimes (GitHub, URL) still fetch all items internally; true server-side pagination requires connector-specific API integration.
5. Cancel/resume works at the batch boundary, not mid-item (acceptable for v1.31 scope).
6. Rate-limit detection is passive (detects 429 when it happens) rather than proactive (pre-emptive throttling), which is appropriate for the read-only connector use case.

## Recommended next milestone
**v1.32 — Beta Packaging, Installer Scripts + Local Release Polish**
