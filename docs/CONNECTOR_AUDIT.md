# Connector Architecture Audit — v1.28

## Existing Connector Code

### v1.1 Connector Framework (baseline)
The codebase already had a v1.1 connector framework in `src/decision_system/connectors/`:

| File | Purpose |
|------|---------|
| `models.py` | Pydantic models: ConnectorType, ConnectorDefinition, ConnectorDryRunResult, ConnectorImportJob/Result |
| `registry.py` | Built-in connector definitions (local-files real, github/jira/slack/email stubs) |
| `store.py` | JSON file-based import job persistence under `.decision_system/connectors/jobs/` |
| `local_files.py` | Dry-run scan and file-based import with path traversal protection |
| `import_jobs.py` | Dispatch dry-run and import to connectors |
| `inspector.py` | Serialization helpers for API responses |
| `stubs.py` | Placeholder stubs for external connectors |
| `cli_connectors.py` | CLI sub-commands for connector operations |

### v1.1 API Routes
`src/decision_system/api/routes_connectors.py` — minimal endpoints:
- `GET /connectors` — list definitions
- `GET /connectors/{id}` — get definition
- `GET /connectors/jobs` — list jobs
- `POST /connectors/{id}/dry-run` — dry-run
- `POST /connectors/{id}/import` — import

### v1.1 Tests
- `tests/test_connectors.py` — 62 unit tests for models, registry, local files, store, stubs, dispatch
- `tests/test_api_connector.py` — 11 integration tests for API endpoints
- `tests/test_connector_cli.py` — CLI command tests

## Security Assumptions (v1.1)
1. Path traversal is blocked — absolute system directories are rejected
2. Protected files (.env, key files, symlinks) are skipped
3. Secrets are not required for stub connectors
4. No external network calls are made by stubs
5. Imports are copy-only — original files are never modified

## What v1.28 Adds

### Enhanced Connector Model (`models.py`)
- `ConnectorConfig` — persisted configuration with workspace_id, mode=read_only, secret_refs
- `ConnectorConfigStatus` — configured/missing_config/healthy/offline/error
- `ConnectorMode` — read_only enforced by validator
- `ConnectorRuntimeItem` — items returned by connector listing
- `ConnectorFetchedContent` — fetched content from connector
- `ConnectorCitation` — evidence/report citation metadata
- New `ConnectorType` values: url-import, notion, google-drive

### Connector Config Store (`config_store.py`)
- JSON file-backed persistence under `.decision_system/connectors/configs/`
- Workspace-scoped and global connector configs
- CRUD: create, load, save, list, delete
- Secret resolution from environment variables

### Connector Runtime Interface (`runtime.py`)
- Abstract base class `ConnectorRuntime` with: test_connection, list_items, fetch_item, sync
- `FakeConnectorRuntime` for testing

### Connector Runtime Dispatch (`runtime_dispatch.py`)
- Maps connector types to runtime implementations

### GitHub Connector (`github_connector.py`)
- Lists files from public GitHub repositories via API
- Fetches file content via base64 decoding
- Optional GITHUB_TOKEN for rate-limit increases
- Only imports supported text/code file types
- 10 MB file size limit

### URL Connector (`url_connector.py`)
- Fetches URL content with HTTP GET
- Extracts HTML title and text content
- Blocks private/internal network addresses (SSRF protection)
- 10 MB response size limit
- Content-type validation

### Audit Module (`audit.py`)
- Typed audit events for all connector operations
- Events: created, updated, deleted, tested, items_listed, import_started, import_completed, import_failed, item_imported
- Integrated with existing security audit log

### Metrics Module (`metrics.py`)
- Connector observability metrics
- Metrics: import_duration_ms, items_found_count, items_imported_count, items_failed_count, error_count

### Enhanced Import Jobs (`import_jobs.py`)
- Rich tracking fields: items_found, items_imported, items_skipped, items_failed, errors
- v1.28 import flow through config store + runtime dispatch
- Audit event emission during import lifecycle
- Metric recording

### Richer API Routes (`routes_connectors.py`)
Full CRUD with workspace scoping and RBAC:
- `GET /connectors` — list definitions
- `GET /connectors/jobs` — list all jobs
- `GET /connectors/{id}` — get definition
- `POST /connectors/{id}/dry-run` — dry-run (v1.1 compat)
- `POST /connectors/{id}/import` — import (v1.1 compat)
- `GET /workspaces/{workspace_id}/connectors` — list configs
- `POST /workspaces/{workspace_id}/connectors` — create config
- `GET /workspaces/{workspace_id}/connectors/{id}` — get config
- `PUT /workspaces/{workspace_id}/connectors/{id}` — update config
- `DELETE /workspaces/{workspace_id}/connectors/{id}` — delete config
- `POST /workspaces/{workspace_id}/connectors/{id}/test` — test connection
- `GET /workspaces/{workspace_id}/connectors/{id}/items` — list items
- `POST /workspaces/{workspace_id}/connectors/{id}/import` — import items
- `GET /workspaces/{workspace_id}/connector-jobs` — list jobs
- `GET /workspaces/{workspace_id}/connector-jobs/{id}` — get job

### RBAC Permissions
New permissions added to `identity/models.py`:
- `connector.read` — viewer can list/view connectors
- `connector.manage` — admin/owner can create/update/delete connectors
- `connector.import` — analyst/admin/owner can import connector items

Owner/Admin: all 3 permissions
Analyst: connector.read + connector.import
Reviewer: connector.read
Viewer: connector.read

### Frontend Connector Manager
New React component `ConnectorsPage.jsx` with:
- Connector list view with status badges
- Create connector form (Local Folder, GitHub Repo, URL)
- Connector detail view
- Test connection button
- Item listing with selection for import
- Import job history viewer
- Read-only mode badge on all connectors

## What is Read-Only
All connectors in v1.28 are strictly read-only:
- Local Folder: scan + copy import (never modifies source)
- GitHub: list + fetch (no write API calls)
- URL: HTTP GET only (no POST/PUT/DELETE)

## What is Not Supported in v1.28
- Notion connector (unavailable)
- Google Drive connector (unavailable)
- Jira, Slack, Email connectors (removed from registry)
- Connector scheduling / incremental sync
- Write-back to external systems
- OAuth flows
- Real-time sync

## v1.28 Connector Plan Summary
The connector system has been evolved from v1.1's minimal framework to v1.28's
full read-only import system with:
- Rich connector configs with workspace scoping
- Runtime interface for consistent connector implementations
- Full CRUD API with RBAC
- Audit trail for all connector operations
- Frontend management UI
- Data source integration path for imported content

## Files Changed/Added in v1.28

### New files
- `src/decision_system/connectors/config_store.py` — Connector config persistence
- `src/decision_system/connectors/runtime.py` — Runtime interface + fake
- `src/decision_system/connectors/runtime_dispatch.py` — Runtime dispatch
- `src/decision_system/connectors/github_connector.py` — GitHub connector
- `src/decision_system/connectors/url_connector.py` — URL connector
- `src/decision_system/connectors/audit.py` — Connector audit events
- `src/decision_system/connectors/metrics.py` — Connector metrics
- `web/workflow-builder/src/components/ConnectorsPage.jsx` — Frontend UI
- `docs/CONNECTOR_AUDIT.md` — This audit document

### Modified files
- `pyproject.toml` — Version 1.28.0-dev
- `src/decision_system/__init__.py` — Version 1.28.0-dev
- `src/decision_system/connectors/models.py` — Enhanced models
- `src/decision_system/connectors/registry.py` — New connector types
- `src/decision_system/connectors/local_files.py` — Added LocalFolderConnectorRuntime
- `src/decision_system/connectors/import_jobs.py` — v1.28 import flow
- `src/decision_system/connectors/__init__.py` — New exports
- `src/decision_system/api/routes_connectors.py` — Full CRUD API
- `src/decision_system/identity/models.py` — Connector permissions
- `web/workflow-builder/src/api.js` — Connector API functions
- `web/workflow-builder/src/App.jsx` — ConnectorsPage integration
- `web/workflow-builder/src/components/AppNav.jsx` — Navigation
- `tests/test_connectors.py` — Updated for new registry
- `tests/test_api_connector.py` — Updated for new API
See docs/CONNECTOR_SYNC_AUDIT.md for v1.29 sync audit details.
See docs/CONNECTOR_SETUP_AUDIT.md for v1.30 setup UX audit details.

## v1.30 Additions

### New files
- `src/decision_system/connectors/setup_schemas.py` — Connector setup schema models + built-in schemas
- `src/decision_system/connectors/github_issues.py` — Read-only GitHub Issues, PRs, Releases connector
- `docs/CONNECTOR_SETUP_AUDIT.md` — Connector setup audit document
- `docs/CONNECTOR_SECURITY_REVIEW.md` — Connector security review document
- `tests/test_connector_setup.py` — 57 tests for setup schemas, credentials, diagnostics

### Enhanced security
- Token redaction: `redact_connector_token()` masks tokens in logs/errors/audit
- Safe credential status: API returns boolean presence only, never token values
- Structured test diagnostics: status, reachable, auth_configured, warnings, errors
- GitHub issues/PRs/releases: Read-only API, no write operations
- Notion/Google Drive: Stub status with honest `disabled=true` and env-var guidance

### Enhanced audit/metrics
- New setup events: connector_setup_started, connector_setup_tested, connector_setup_completed, connector_setup_failed, connector_credentials_missing, connector_item_previewed, github_issue_imported
- New metrics: connector_setup_duration_ms, connector_test_success/failure_count, connector_preview_item_count, connector_import_by_type_count
