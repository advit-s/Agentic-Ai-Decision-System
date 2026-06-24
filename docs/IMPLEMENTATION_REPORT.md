# Implementation Report — v1.27 Security, Auth, RBAC + Governance Foundation

> **Date:** 2026-06-24
> **Package version:** 1.27.0-dev
> **Previous milestone:** v1.26.1 — Graph UI, Audit Metrics API + Extraction Quality Hardening

---

## Summary

v1.27 adds a local-first security and governance foundation to make the local
beta safe enough for private company data. The milestone adds:

- Local identity model with 5 roles (owner, admin, analyst, reviewer, viewer)
- Workspace membership with role-based access control
- Declarative permission matrix (17 permissions → 5 roles)
- API route permission enforcement for providers, reviews, exports, settings
- Governance-aware review gates (role enforcement, actor recording, audit)
- Secure export governance (permission checks, audit events)
- Provider secret safety (env-var API keys, redacted responses)
- Workspace-scoped audit log viewer with filters
- Security mode settings (demo | governed)
- Security model and threat model documentation
- 33 new identity/permission tests

## Version

- `src/decision_system/__init__.py`: `1.27.0-dev`
- `pyproject.toml`: `1.27.0-dev`
- `/health` endpoint returns `1.27.0-dev`
- All docs updated to reference v1.27

## MCP / Agent Skill Usage

- **codebase-memory-mcp**: Used to inspect architecture, security modules,
  API routes, storage models, and workspace boundaries before implementation.
  Graph indexed with 9,063 nodes and 29,617 edges.
- **Repo agent instructions** (AGENTS.md, CLAUDE.md): Followed throughout.
- **Phase 0 pre-flight**: All existing tests passed before security changes.

## Security Model

See `docs/SECURITY_MODEL.md` for the full security architecture.

Key design decisions:
- **Local-first**: No cloud auth, no passwords, no sessions — identity is an
  opt-in governance layer.
- **Demo mode**: Default mode — no login required, all access granted.
- **Governed mode**: Permissions enforced via `X-User-Id` header.
- **Provider secrets**: Env-var-based API keys only (`api_key_env`), never
  stored or returned in plaintext.

## Identity Model

- **LocalUser**: user_id, display_name, role, timestamps, metadata
- **Default user**: `local/system` with `owner` role
- **Store**: JSON files under `.decision_system/identity/`
- **API**: `GET/POST/PUT/DELETE /identity/users`
- **Current user**: `GET /identity/me` returns user + effective permissions

## Workspace Roles

- **WorkspaceMembership**: workspace_id, user_id, role, timestamps
- **Membership store**: JSON files under `.decision_system/identity/memberships.json`
- **API**: `GET/POST/PUT/DELETE /workspaces/{id}/memberships`
- **Role fallback**: Workspace role overrides global role for scoped operations

## Permission Matrix

| Permission | owner | admin | analyst | reviewer | viewer |
|------------|-------|-------|---------|----------|--------|
| workspace.read | ✅ | ✅ | ✅ | ✅ | ✅ |
| workspace.manage | ✅ | ✅ | ❌ | ❌ | ❌ |
| data_source.upload | ✅ | ✅ | ✅ | ❌ | ❌ |
| data_source.delete | ✅ | ✅ | ✅ | ❌ | ❌ |
| data_source.parse_index | ✅ | ✅ | ✅ | ❌ | ❌ |
| evidence.search | ✅ | ✅ | ✅ | ✅ | ✅ |
| workflow.create | ✅ | ✅ | ✅ | ❌ | ❌ |
| workflow.update | ✅ | ✅ | ✅ | ❌ | ❌ |
| workflow.execute | ✅ | ✅ | ✅ | ❌ | ❌ |
| review.resolve | ✅ | ✅ | ❌ | ✅ | ❌ |
| claim.verify | ✅ | ✅ | ✅ | ❌ | ❌ |
| graph.extract | ✅ | ✅ | ✅ | ❌ | ❌ |
| provider.manage | ✅ | ✅ | ❌ | ❌ | ❌ |
| report.generate | ✅ | ✅ | ✅ | ❌ | ❌ |
| report.export | ✅ | ✅ | ❌ | ❌ | ❌ |
| audit.read | ✅ | ✅ | ✅ | ✅ | ✅ |
| settings.manage | ✅ | ✅ | ❌ | ❌ | ❌ |

API: `GET /identity/permissions` returns the full matrix.

## API Enforcement

Routes with permission enforcement:
- `POST/PUT/DELETE /providers/*` → `provider.manage`
- `POST /reviews/{id}/resolve` → `review.resolve` + reviewer role check
- `GET /reviews` → `audit.read`
- `GET /reports/{id}/export` → `report.export` + admin role check (optional)
- `GET/POST/PUT/DELETE /identity/*` → `settings.manage`
- `GET /workspaces/{id}/audit/*` → `audit.read`
- `GET/POST/PUT/DELETE /workspaces/{id}/memberships` → `workspace.manage`
- `GET /identity/permissions` → `audit.read`
- `GET/PUT /identity/settings` → `settings.manage`

## Frontend Permission States

- Frontend build passes (39 tests, 11 test files).
- No frontend permission UI changes in this milestone — the API layer
  enforces permissions and returns 403 for unauthorized actions.
- Future milestone should add role-aware UI states.

## Review Governance

- Review resolution requires `review.resolve` permission.
- Security settings require reviewer role or higher (`review_requires_reviewer_role`).
- Review decisions record the actor (user_id).
- Audit events include review_id, action, actor, and notes.
- Tests cover permission denial for unauthorized review resolution.

## Export Governance

- Report export requires `report.export` permission.
- Security settings can require admin role (`exports_require_admin`).
- Export audit events include actor, workspace_id, report_id, and format.
- Exports never include provider secrets (verified by design).

## Provider Secret Handling

- Provider configs use `api_key_env` (env var name) not `api_key` (value).
- `api_key_configured` boolean indicates whether env var is set.
- No plaintext API keys stored in config JSON files.
- No plaintext API keys returned in API responses.
- No plaintext API keys included in exports.
- Provider config changes emit audit events.

## Audit Log Viewer

- `GET /workspaces/{id}/audit/events` with filters (event_type, actor, date range)
- `GET /workspaces/{id}/audit/summary` for aggregate counts
- Actor identity resolved from identity system (not hardcoded `"local-user"`)
- API requires `audit.read` permission

## Workspace Isolation

- All data stores accept `workspace_id` as scoping parameter
- Workspace membership required for mutation operations
- Cross-workspace access requires appropriate membership
- Existing workspace isolation in graph, data sources, and evidence stores

## Tests Added

New identity tests (`tests/test_identity.py`, 33 tests):
- `TestLocalUser` — default user, custom roles, serialization
- `TestWorkspaceMembership` — creation, serialization
- `TestPermissionMatrix` — all roles, owner has all, viewer limited, analyst/reviewer specific
- `TestUserStore` — CRUD operations, default user
- `TestMembershipStore` — owner membership, CRUD, role updates
- `TestPermissionCheck` — has/lacks permission, workspace role override
- `TestSecuritySettings` — defaults, mode switching, serialization
- `TestRoleHierarchy` — role ordering, `role_is_at_least`, `get_user_role`

## Commands Run

```bash
# Pre-flight
git status
git diff --check
python -m pytest tests/test_data_sources -q  # 60 passed
python -m pytest tests/test_verification -q   # 68 passed
python -m pytest tests/test_providers -q      # 48 passed
python -m pytest tests/test_workflow_engine/test_api.py -q  # 85 passed
python -m pytest tests/test_security.py       # 64 passed

# Identity tests
python -m pytest tests/test_identity.py -q    # 33 passed

# Full validation
python -m pytest tests/test_security.py tests/test_data_sources tests/test_verification tests/test_providers tests/test_workflow_engine/test_api.py tests/test_graph_store.py tests/test_extractor_v2.py tests/test_graph_api.py tests/test_graph_nodes.py tests/test_graph_audit.py tests/test_identity.py -q  # 490 passed

# Frontend
cd web/workflow-builder && npm test           # 39 passed
cd web/workflow-builder && npm run build      # build succeeded

# Git hygiene
git diff --check                              # clean
```

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| `src/decision_system/identity/__init__.py` | Identity package init with exports |
| `src/decision_system/identity/models.py` | LocalUser, WorkspaceMembership, Permission, UserRole, ROLE_PERMISSIONS |
| `src/decision_system/identity/store.py` | JSON-backed user and membership store |
| `src/decision_system/identity/permissions.py` | Permission checking layer, FastAPI dependencies |
| `src/decision_system/identity/settings.py` | Security mode settings (demo/governed) |
| `src/decision_system/api/routes_identity.py` | Identity API endpoints (users, memberships, settings, permissions) |
| `src/decision_system/api/routes_audit.py` | Workspace-scoped audit log API with filters |
| `tests/test_identity.py` | 33 identity/permission tests |
| `docs/SECURITY_GOVERNANCE_AUDIT.md` | Pre-implementation security audit |
| `docs/SECURITY_MODEL.md` | Security architecture documentation |
| `docs/THREAT_MODEL.md` | Threat model with 10 threats |

### Modified Files
| File | Change |
|------|--------|
| `src/decision_system/__init__.py` | Version 1.26.1-dev → 1.27.0-dev |
| `pyproject.toml` | Version 1.26.1-dev → 1.27.0-dev |
| `src/decision_system/api/app.py` | Registered routes_identity and routes_audit |
| `src/decision_system/api/routes_providers.py` | Added permission enforcement to CRUD routes |
| `src/decision_system/api/routes_execution_reports.py` | Added export permission enforcement |
| `src/decision_system/security/audit.py` | Actor identity resolution from identity system |
| `src/decision_system/workflow_engine/api.py` | Permission enforcement on review/review resolve routes |
| `tests/test_graph_api.py` | Version string updated |
| `CHANGELOG.md` | Added v1.27 section |
| `docs/CURRENT_STATE.md` | Version/milestone update |
| `docs/DEMO_PATH.md` | Version update |
| `docs/IMPLEMENTATION_REPORT.md` | This report |

## Known Limitations

1. **No frontend permission UI** — The frontend does not yet have role-aware
   UI states. Users see all buttons regardless of role. Future work.
2. **No password authentication** — Identity is header-based (`X-User-Id`).
   No login screen, no sessions, no tokens.
3. **No encryption at rest** — Data is stored as plain JSON/SQLite files.
4. **No transport security** — No TLS between services (add reverse proxy).
5. **Demo mode is default** — Permissions are enforced only in governed mode.
6. **Audit log integrity** — No cryptographic signing of audit events.
7. **Some routes not yet permission-gated** — Data source, workflow, and
   graph routes use workspace scoping but don't enforce granular permissions.
8. **Workspace membership not yet required for all operations** — Some
   stores accept workspace_id but don't fail when missing.

## Recommended Next Milestone

**v1.28 — Connector Read-Only Imports + External Knowledge Sync**
