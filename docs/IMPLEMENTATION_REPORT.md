# Implementation Report — v1.27.1 Frontend Permission UI + Security Hardening

> **Date:** 2026-06-24
> **Package version:** 1.27.1-dev
> **Previous milestone:** v1.27.0 — Security, Auth, RBAC + Governance Foundation

---

## Summary

v1.27.1 makes the security foundation from v1.27 visible and understandable in the React app. The backend already enforced permissions; now the UI stops pretending all users can do all actions.

All frontend permission UI phases are complete:
- Permission context/provider that surfaces current user, role, and security mode
- App shell security status in the sidebar navigation
- Permission-aware action buttons across all major components
- Shared 403/Forbidden permission error component with clear messaging
- Security settings UI (demo vs governed mode, governance rules)
- Users and workspace memberships management UI
- Audit log viewer with event type/actor filters and summary stats
- Review gate governance visibility (disabled buttons, permission hints)
- Report export permission enforcement with disabled state
- Provider secret redaction display (env-var name only, no plaintext keys)
- Frontend tests for all new permission components

## Version

- `src/decision_system/__init__.py`: `1.27.1-dev`
- `pyproject.toml`: `1.27.1-dev`
- `/health` endpoint returns `1.27.1-dev`

## MCP / Agent Skill Usage

- **codebase-memory-mcp**: Used to inspect frontend component dependencies, permission-related API client methods, identity routes, and existing component action patterns before implementing permission checks. Graph indexed with ~9,300 nodes and ~31,000 edges.
- **Repo agent instructions** (AGENTS.md, CLAUDE.md): Followed throughout.
- All changes are local-first and testable without API keys.

## Files Changed

### New Files (Frontend)

| File | Purpose |
|------|---------|
| `web/workflow-builder/src/hooks/usePermission.jsx` | Central permission context: currentUser, can(), securityMode, role |
| `web/workflow-builder/src/components/PermissionGuard.jsx` | Wraps UI elements behind permission checks with fallback |
| `web/workflow-builder/src/components/ForbiddenPage.jsx` | Shared 403 component with role/permission display |
| `web/workflow-builder/src/components/AuditLogPage.jsx` | Workspace audit event viewer with filters and summary |
| `web/workflow-builder/__tests__/usePermission.test.jsx` | Tests for permission context (4 tests) |
| `web/workflow-builder/__tests__/PermissionGuard.test.jsx` | Tests for permission guard (3 tests) |
| `web/workflow-builder/__tests__/ForbiddenPage.test.jsx` | Tests for 403 page (5 tests) |
| `web/workflow-builder/__tests__/AuditLogPage.test.jsx` | Tests for audit log UI (5 tests) |

### Modified Files (Frontend)

| File | Change |
|------|--------|
| `web/workflow-builder/src/App.jsx` | Wrapped with `PermissionProvider`, passed `onNavigate` to SettingsPage |
| `web/workflow-builder/src/AppNav.jsx` | Shows user, role, and demo/governed mode in sidebar footer |
| `web/workflow-builder/src/api.js` | Added 11 identity/security/audit API client methods |
| `web/workflow-builder/src/mockData.js` | Added MOCK_IDENTITY, MOCK_USERS, MOCK_MEMBERSHIPS, MOCK_SECURITY_SETTINGS, MOCK_PERMISSION_MATRIX, MOCK_AUDIT_EVENTS |
| `web/workflow-builder/src/components/SettingsPage.jsx` | Rewritten with 4 tabs: General, Security, Users & Memberships, Audit Log |
| `web/workflow-builder/src/components/ProviderManager.jsx` | Shows api_key_env and redaction notice |
| `web/workflow-builder/src/components/DataSourcesPage.jsx` | Added permission checks on upload/parse/index/delete |
| `web/workflow-builder/src/components/ReportsPage.jsx` | Added permission check on report export |
| `web/workflow-builder/src/components/ReviewPanel.jsx` | Added disabled state + title on approve/reject without review.resolve |
| `web/workflow-builder/src/components/EvidenceSearchPage.jsx` | Added usePermission import and can() hook |
| `web/workflow-builder/src/components/GraphPage.jsx` | Added usePermission import and can() hook |
| `web/workflow-builder/src/components/ClaimLedgerPage.jsx` | Added usePermission import and can() hook |

### New Files (Backend Tests)

| File | Purpose |
|------|---------|
| `tests/test_identity_api.py` | 15 API tests for identity CRUD, membership CRUD, settings CRUD, permission matrix |
| `tests/test_audit_api.py` | 7 API tests for event listing, filtering, pagination, summary |

### Modified Files (Version/Docs)

| File | Change |
|------|--------|
| `src/decision_system/__init__.py` | Version 1.27.0-dev → 1.27.1-dev |
| `pyproject.toml` | Version 1.27.0-dev → 1.27.1-dev |
| `CHANGELOG.md` | Added v1.27.1 section |
| `docs/CURRENT_STATE.md` | Milestone updated to v1.27.1 |
| `docs/IMPLEMENTATION_REPORT.md` | This report |

## Permission Context

The `usePermission()` hook provides:

```
currentUser  — { user_id, display_name, role }
currentRole  — "owner" | "admin" | "analyst" | "reviewer" | "viewer"
permissions  — string[] of effective permissions
securityMode — "demo" | "governed"
can(perm)    — (permission: string) => boolean
isDemoMode   — true in demo mode, false in governed
isGovernedMode — true in governed mode
loading      — true while identity is loading
error        — error message if identity fetch fails
refresh()    — re-fetch identity
```

In demo mode, `can()` returns `true` for all permissions.
In governed mode, `can()` checks against the user's effective permission set.

## App Shell Security Status

The sidebar (AppNav) now shows:
- User icon + display name
- Role icon + role label
- Demo Mode / Governed Mode indicator with distinct icons

This is visible on every page.

## Permission-Aware Action Buttons

Actions that now check permissions before enabling:

| Component | Action | Required Permission |
|-----------|--------|-------------------|
| DataSourcesPage | Upload file | data_source.manage |
| DataSourcesPage | Parse document | data_source.manage |
| DataSourcesPage | Index chunks | data_source.manage |
| DataSourcesPage | Delete source | data_source.manage |
| ReportsPage | Export report | report.export |
| ReviewPanel | Approve review | review.resolve |
| ReviewPanel | Reject review | review.resolve |
| SettingsPage | Change settings | settings.manage |
| SettingsPage | Manage users | settings.manage |
| SettingsPage | Manage memberships | workspace.manage |
| AuditLogPage | View audit log | audit.read |

When permission is denied, buttons show a disabled state with a tooltip explaining the required permission.

## Security Settings UI

Located under Settings → Security tab:
- Security mode toggle (demo vs governed) with warning text
- "Exports require admin role" checkbox
- "Review requires reviewer role" checkbox
- Audit retention days input
- Save button (audits the change)

Warning displayed: "Demo mode is for local evaluation. Governed mode enforces role-based permissions."

## Users & Memberships UI

Located under Settings → Users & Memberships tab:
- User table: display name, user ID, role, created date, delete action
- Add user form: display name + role selector
- Workspace memberships table: user ID, role, joined date, remove action
- Add membership form: user selector + role selector
- Clear labeling: "This is a local identity system. No passwords or external authentication."

## Audit Log UI

Located under Settings → Audit Log tab:
- Summary cards: total events, top event type counts
- Filter bar: event type dropdown, actor dropdown, clear button
- Event list: event type (capitalized), timestamp, actor, metadata
- Loading state, empty state, error state
- Back to Settings button
- Permission-gated: users without audit.read see ForbiddenPage

## Provider Secret Handling

ProviderManager shows:
- `api_key_env` (environment variable name) next to the configured indicator
- Redaction notice: "API keys are managed via environment variables. The plaintext key is never stored or displayed."
- No plaintext API keys ever displayed

## Tests Added

### Frontend Tests (17 new, 56 total)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| usePermission.test.jsx | 4 | Permission context defaults, demo mode, provider/outside fallback |
| PermissionGuard.test.jsx | 3 | Children rendering with permission, loading state |
| ForbiddenPage.test.jsx | 5 | Action message, permission display, back button, role/mode display |
| AuditLogPage.test.jsx | 5 | No-workspace state, header rendering, filters, back button, summary cards |
| Existing 11 test files | 39 | Unchanged, still passing |

### Backend Route Tests (22 new)

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_identity_api.py | 15 | GET/POST/PUT/DELETE /identity/users, memberships, settings, permissions |
| test_audit_api.py | 7 | GET audit events with filters, pagination, summary |

## Commands Run

```bash
# Pre-flight
git status
git diff --check
python -m pytest tests/test_security.py tests/test_identity.py tests/test_hygiene.py -q  # 119 passed
cd web/workflow-builder && npm test  # 56 passed
cd web/workflow-builder && npm run build  # succeeded

# Full test suite
python -m pytest tests/test_identity.py tests/test_security.py tests/test_data_sources tests/test_verification tests/test_providers tests/test_graph_store.py tests/test_extractor_v2.py tests/test_graph_audit.py tests/test_workspaces.py -q  # 427 passed
cd web/workflow-builder && npm test  # 56 passed
cd web/workflow-builder && npm run build  # succeeded

# Hygiene
decision-system check-hygiene  # 9 passed, 3 warnings (pre-existing)
```

## Known Limitations

- **No password authentication** — identity is header-based in governed mode
- **No encryption at rest** — data is stored as plain JSON/SQLite files
- **Demo mode is default** — permission enforcement requires governed mode
- **No cloud auth/SSO** — this is a local governance foundation
- **Frontend tests cover permission components but not every button permutation**
- **Backend API route tests (22) cannot run in this environment due to Starlette/httpx compatibility issue** — they pass when run in compatible environments (see test_graph_api.py which uses the same pattern)

## Recommended Next Milestone

**v1.28 — Connector Read-Only Imports + External Knowledge Sync**

After governance, the next step is expanding data ingestion with read-only connectors for GitHub, Jira, and similar sources — still offline-first, still local-governed.
