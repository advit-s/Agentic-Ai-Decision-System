# Implementation Report — v1.28 Connector Read-Only Imports + External Knowledge Sync

> **Date:** 2026-06-24
> **Package version:** 1.28.0-dev
> **Previous milestone:** v1.27.2 — Test Harness + Docker Smoke + Release Baseline

---

## Summary

v1.28 implements **read-only connector imports** — the ability to bring external
knowledge into the local workspace safely via Local Folder, GitHub Repository,
and URL connectors. All connectors are strictly read-only, workspace-scoped,
audited, and permission-gated.

### What was built

- **Connector config store** — JSON-backed persistence with workspace scoping
- **Connector runtime interface** — Abstract base + fake runtime for testing
- **Local Folder Connector** — Read-only local directory scan/import with path traversal protection
- **GitHub Repository Connector** — Public repo file listing + content fetch via API
- **URL / Web Page Import Connector** — HTTP fetch with HTML extraction and SSRF protection
- **Full CRUD API** — Workspace-scoped endpoints with RBAC enforcement
- **Import job tracking** — Rich jobs with items_found/imported/skipped/failed
- **Connector audit events** — All operations recorded in the audit log
- **Connector metrics** — Import duration, item counts, error rates
- **Connector RBAC** — connector.read, connector.manage, connector.import permissions
- **Frontend Connector Manager** — React component for managing connectors
- **Connector audit document** — docs/CONNECTOR_AUDIT.md

### Safety measures

- All connectors enforce `mode = read_only` at the model level (Pydantic validator)
- Local Folder: path traversal detection, protected file filtering, no source modification
- GitHub: no write API calls, file size limits, content-type filtering
- URL: private/internal network blocking (SSRF protection), response size limits, timeouts
- Secrets are redacted from API responses
- RBAC permissions enforced on every endpoint

## Version

- `src/decision_system/__init__.py`: `1.28.0-dev`
- `pyproject.toml`: `1.28.0-dev`
- `/health` endpoint returns `1.28.0-dev`

## Files Changed

### New files
| File | Purpose |
|------|---------|
| `src/decision_system/connectors/config_store.py` | Connector config persistence |
| `src/decision_system/connectors/runtime.py` | Runtime interface + fake |
| `src/decision_system/connectors/runtime_dispatch.py` | Runtime dispatch |
| `src/decision_system/connectors/github_connector.py` | GitHub connector |
| `src/decision_system/connectors/url_connector.py` | URL connector |
| `src/decision_system/connectors/audit.py` | Connector audit events |
| `src/decision_system/connectors/metrics.py` | Connector metrics |
| `web/workflow-builder/src/components/ConnectorsPage.jsx` | Frontend UI |
| `docs/CONNECTOR_AUDIT.md` | Connector architecture audit |

### Modified files
| File | Change |
|------|--------|
| `pyproject.toml` | Version 1.28.0-dev |
| `src/decision_system/__init__.py` | Version 1.28.0-dev |
| `src/decision_system/connectors/models.py` | Enhanced models |
| `src/decision_system/connectors/registry.py` | New connector types |
| `src/decision_system/connectors/local_files.py` | LocalFolderConnectorRuntime |
| `src/decision_system/connectors/import_jobs.py` | v1.28 import flow |
| `src/decision_system/connectors/__init__.py` | New exports |
| `src/decision_system/api/routes_connectors.py` | Full CRUD API |
| `src/decision_system/identity/models.py` | Connector permissions |
| `web/workflow-builder/src/api.js` | Connector API functions |
| `web/workflow-builder/src/App.jsx` | ConnectorsPage integration |
| `web/workflow-builder/src/components/AppNav.jsx` | Navigation |
| `tests/test_connectors.py` | Updated for new registry |
| `tests/test_api_connector.py` | Updated for new API |
| `docs/CURRENT_STATE.md` | v1.28 state |
| `CHANGELOG.md` | v1.28 changelog |

## Connector Model/Store

- `ConnectorConfig` with workspace_id, mode=read_only, secret_refs, status tracking
- `ConnectorConfigStore` — JSON file-backed CRUD under `.decision_system/connectors/configs/`
- Secret values are resolved from environment variables, never stored in config files
- Mode is validated at construction time (cannot be changed from read_only)

## Connector Runtimes

- `ConnectorRuntime` ABC: test_connection, list_items, fetch_item, sync
- `FakeConnectorRuntime` for testing with canned data
- `LocalFolderConnectorRuntime` — directory scan with skip logic, path safety
- `GitHubConnectorRuntime` — GitHub API v3, base64 content decoding, rate-limit handling
- `UrlConnectorRuntime` — HTTP fetch, HTML text extraction, private address blocking

## Connector APIs

- Full CRUD at `/workspaces/{workspace_id}/connectors/...`
- Backward-compatible v1.1 endpoints at `/connectors/...`
- Test: `POST /workspaces/{workspace_id}/connectors/{id}/test`
- List items: `GET /workspaces/{workspace_id}/connectors/{id}/items`
- Import: `POST /workspaces/{workspace_id}/connectors/{id}/import`
- Jobs: `GET /workspaces/{workspace_id}/connector-jobs`

## RBAC/Governance

- `connector.read` — viewer/reviewer can list and view
- `connector.manage` — admin/owner can create/update/delete
- `connector.import` — analyst/admin/owner can import
- 403 returned for unauthorized operations with clear error messages

## Frontend Connector UI

- Connectors section in sidebar navigation (between Data Sources and Knowledge Graph)
- List view with status badges and type icons
- Create form for Local Folder, GitHub Repo, URL connectors
- Detail view with config preview
- Test connection button
- Item listing with checkbox selection
- Import workflow with "Import All" and "Import Selected"
- Import job history viewer
- Read-only mode badge displayed on all connector cards

## Data Source Integration

Imported connector content is stored in `.decision_system/connectors/imported/` and
can be processed through the normal parse/index pipeline. Connector citations
include source metadata (GitHub: owner/repo/path, URL: title + URL, Local: filename).

## Evidence/Report Citation

`ConnectorCitation` model provides:
- `to_display_string()` — human-readable citation for reports
- `to_evidence_metadata()` — metadata dict for evidence search results
- Connector type-specific formatting (GitHub, URL, Local, Notion, Google Drive)

## Audit/Observability

- 9 connector audit event types: created, updated, deleted, tested, items_listed,
  import_started, import_completed, import_failed, item_imported
- 5 connector metrics: import_duration_ms, items_found/imported/failed count, error_count
- All events go through the existing JSONL audit log
- All metrics go through the existing observability store

## Tests Added

- Connector config store tests (via API)
- Connector API CRUD tests (create, list, get, update, delete)
- Test connection API test
- List items API test
- Import API test
- Secrets redaction test
- Mode enforcement test
- Invalid connector type test
- Unavailable connector type test

Total: 91 connector tests pass (62 unit + 29 API/integration)

## Commands Run

```bash
# Backend connector tests
python -m pytest tests/test_connectors.py -q    # 62 passed
python -m pytest tests/test_api_connector.py -q  # 29 passed

# Frontend build
cd web/workflow-builder && npm run build         # Build succeeded
```

## Known Limitations

- **Notion and Google Drive connectors** are not implemented (marked as unavailable)
- **Connector scheduling and incremental sync** not implemented (recommended for v1.29)
- **Docker smoke and E2E smoke** are environment-blocked (same as v1.27.2)
- **Imported content must manually be parsed/indexed** after import (no auto-parse yet)
- **GitHub connector requires public repos** or GITHUB_TOKEN for private repos
- **URL connector only imports single pages** — no site crawling
- **No import retry logic** for transient failures
- **Frontend tests for ConnectorsPage** not yet added (component added, tests pending)

## Recommended Next Milestone

**v1.29 — Connector Scheduling + Incremental Sync**

After the read-only connector foundation, the next step is:
- Scheduled connector imports (cron-like)
- Incremental sync (content hash tracking, skip unchanged files)
- Auto-parse/index after import
- Import retry with backoff
- Frontend tests for connector UI
- Additional connectors (Notion read-only, Google Drive read-only)
