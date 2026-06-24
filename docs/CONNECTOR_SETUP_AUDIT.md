# Connector Setup Audit — v1.29 Baseline

> **Audit date:** 2026-06-24
> **Version:** 1.29.0-dev
> **Next milestone:** v1.30 — Connector Expansion + OAuth/Token Setup UX

---

## Current Connector Setup UX

### How a user configures a connector today

1. Open the Connectors page in the React SPA (`ConnectorsPage.jsx`).
2. See a list of available connector types with basic descriptions.
3. Click "Create Connector" and fill in a form:
   - **Local Folder:** Enter a folder path.
   - **GitHub Repository:** Enter a repository URL.
   - **URL Import:** Enter a web page URL.
4. Click "Test Connection" to verify the configuration works.
5. Click "List Items" to see available files/pages.
6. Select items and click "Import" to bring them into the workspace.
7. After import, manage sync/schedule (v1.29).

### Current credential handling

| Connector | Credentials Needed | How Provided | UX |
|-----------|-------------------|-------------|-----|
| Local Folder | None | N/A | Direct path entry |
| GitHub (public) | None (optional GITHUB_TOKEN) | Environment variable | No UI guidance for token setup |
| URL Import | None | N/A | Direct URL entry |
| Notion | N/A (unavailable) | N/A | Shows "Not implemented" |
| Google Drive | N/A (unavailable) | N/A | Shows "Not implemented" |

### Current token behavior

- `GITHUB_TOKEN` is read from `os.environ` in `github_connector.py:_get_headers()`.
- There is no UI indication of whether a token is present.
- Token values could potentially leak into error messages.
- No credential validation on token format.
- No test for missing token vs. wrong token.

### Current read-only guarantees

- **Local Folder:** Copy-only import; never modifies source files.
- **GitHub Repository:** Read-only API calls (GET); no write endpoints used.
- **URL Import:** HTTP GET only; blocks private/internal network addresses.
- **All connectors:** Mode enforced via `ConnectorMode.READ_ONLY` validator on `ConnectorConfig`.

### Current connector limitations

| Limitation | Details |
|-----------|---------|
| No setup schema | Each connector type has ad-hoc config fields; no standardized schema for UI rendering |
| Token setup unclear | Users must know to set `GITHUB_TOKEN` as an env var; no UI guidance |
| No credential status API | API doesn't expose whether tokens are configured (just redacted) |
| No diagnostic detail | `test_connection` returns basic pass/fail; no structured diagnostics |
| Limited GitHub support | Only file listing/import; no issues, PRs, or releases |
| Notion/Drive stubs | Marked unavailable; no UI card explaining planned support |
| No setup wizard | Current create form is a single flat form; no step-by-step guidance |
| Limited item preview | Items show name/type; no size, modified date, sync status, or import status |
| No security review doc | Connector security review doesn't exist as a standalone doc |
| RBAC for setup not explicit | Connector create/edit forms don't explain why actions are disabled |

---

## v1.30 Plan Summary

### Key improvements

1. **Connector setup schema hardening** — Standardized schema per connector type for UI rendering
2. **Token/env-var credential UX** — Clear env-var guidance, safe status API, never expose values
3. **Connector test diagnostics** — Structured test results with clear error messages
4. **GitHub connector expansion** — Issues, PRs, releases read-only import
5. **Notion read-only connector** — Implement or honestly mark as planned/disabled
6. **Google Drive read-only connector** — Implement or honestly mark as planned/disabled
7. **Connector setup wizard UI** — Step-by-step wizard for easier configuration
8. **Connector item preview improvements** — Richer preview with import status and metadata
9. **Connector import mapping** — Consistent metadata mapping for evidence/report citations
10. **Connector security review** — Document known risks and mitigations
11. **Frontend RBAC for connector setup** — Permission-aware UI for setup actions
12. **Audit and observability hardening** — New events for setup flow

### Architectural decisions

- All connectors remain strictly read-only.
- No OAuth flow in this milestone (env-var based only).
- Token values never stored in config or returned from API.
- New connectors follow the same `ConnectorRuntime` interface.
- Frontend consumes connector setup schemas for dynamic form rendering.
- Demo path remains offline-first.

---

## Files to Create/Modify in v1.30

### New files
- `docs/CONNECTOR_SETUP_AUDIT.md` — This document
- `docs/CONNECTOR_SECURITY_REVIEW.md` — Security review
- `src/decision_system/connectors/setup_schemas.py` — Connector setup schemas
- `tests/test_connector_setup.py` — Setup schema and credential tests

### Modified files
- `pyproject.toml` — Version 1.30.0-dev
- `src/decision_system/__init__.py` — Version 1.30.0-dev
- `src/decision_system/connectors/models.py` — Setup schema models
- `src/decision_system/connectors/registry.py` — Enhanced definitions
- `src/decision_system/connectors/github_connector.py` — Issues/PRs/release support
- `src/decision_system/api/routes_connectors.py` — Setup schema API
- `src/decision_system/connectors/audit.py` — New audit events
- `src/decision_system/connectors/metrics.py` — New metrics
- `src/decision_system/security/redaction.py` — Token redaction helpers
- `web/workflow-builder/src/api.js` — New API functions
- `web/workflow-builder/src/components/ConnectorsPage.jsx` — Setup wizard
- `docs/CURRENT_STATE.md` — v1.30 status
- `docs/IMPLEMENTATION_REPORT.md` — Final report
- `CHANGELOG.md` — v1.30 changelog
- `README.md` — If needed

---

## MCP / Codebase Memory Usage

This audit was created using codebase-memory-mcp to inspect:
- `connectors/models.py` — Connector definitions and configs
- `connectors/registry.py` — Built-in connector registry
- `connectors/config_store.py` — Config persistence and secret handling
- `connectors/github_connector.py` — GitHub connector runtime
- `connectors/url_connector.py` — URL connector runtime
- `connectors/audit.py` — Audit events
- `connectors/metrics.py` — Metrics
- `connectors/runtime.py` — Runtime interface
- `connectors/sync_runner.py` — Sync runner
- `api/routes_connectors.py` — API routes
- `identity/models.py` — Permissions
- `web/workflow-builder/src/components/ConnectorsPage.jsx` — Frontend
- `tests/test_connectors.py` — Existing tests
- `tests/test_api_connector.py` — Existing API tests
- `tests/test_connector_sync.py` — Existing sync tests
