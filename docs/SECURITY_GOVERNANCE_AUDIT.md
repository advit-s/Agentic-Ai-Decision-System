# Security & Governance Audit — v1.26.1 Baseline

> **Date:** 2026-06-24
> **Version:** 1.26.1-dev
> **Audit scope:** Current auth state, workspace isolation, audit system, provider secrets, export behavior, review gates, frontend permission assumptions

---

## 1. Current Auth State

| Aspect | Status | Details |
|--------|--------|---------|
| User identity | ❌ **None** | No user model exists. All audit events use hardcoded `"local-user"` actor. |
| Authentication | ❌ **None** | No login, no passwords, no sessions, no tokens. |
| Roles/Permissions | ❌ **None** | No role model, no permission matrix. |
| Demo mode | ✅ **Implicit** | App starts without any login prompt. No auth middleware. |

**Risk:** Any local process can call any API endpoint with no identity check.

---

## 2. Current Workspace Isolation

| Aspect | Status | Details |
|--------|--------|---------|
| Workspace CRUD | ✅ **Exists** | SQLite-backed with `WorkspaceRepository`. |
| Artifact scoping | ✅ **Partial** | Most stores accept `workspace_id`. Chroma metadata includes `workspace_id`. |
| Cross-workspace checks | ⚠️ **Informal** | Some stores filter by workspace_id, but no centralized enforcement layer. |
| Membership model | ❌ **None** | No workspace membership/role system. Any caller can access any workspace. |

**Risk:** No access control on workspaces. Any local user/process can create, read, modify, or delete any workspace.

---

## 3. Current Audit System

| Aspect | Status | Details |
|--------|--------|---------|
| Audit event model | ✅ **Exists** | `AuditEvent` in `security/models.py` with event_id, event_type, actor, message, metadata, created_at. |
| Audit writer | ✅ **Exists** | JSONL-based `append_event()` in `security/audit.py`. |
| Audit reader | ✅ **Exists** | `load_events()` with optional limit. |
| Event types | ✅ **Partial** | Verification, report, graph, and some workflow events emit audit records. |
| Audit API | ✅ **Exists** | `GET /security/audit` returns all events (no workspace scoping, no filters). |
| Actor identity | ❌ **Missing** | Actor is always `"local-user"`. No real user identity in events. |
| Workspace-scoped audit | ❌ **Missing** | No `GET /workspaces/{id}/audit/events` endpoint. No workspace filter. |
| Audit UI | ❌ **Missing** | Frontend has no Audit Log page/section. |

**Gaps:** Events lack real actor identity; no workspace-scoped queries; no event-type/date-range filters; no audit UI.

---

## 4. Current Provider Secret Handling

| Aspect | Status | Details |
|--------|--------|---------|
| Provider model | ✅ **Exists** | `ProviderConfig` in `providers/models.py` with api_key, api_key_env, etc. |
| API key env var | ✅ **Supported** | `api_key_env` allows loading keys from environment. |
| Secret redaction in API | ❌ **Missing** | Provider API likely returns full `api_key` value. |
| Secret redaction in exports | ❌ **Missing** | Exports could include plaintext secrets. |
| Config change audit | ❌ **Missing** | Provider config changes not audited. |
| UI secret visibility | ❌ **Missing** | No `api_key_present` boolean pattern. |

**Risk:** Provider API keys may be exposed via API responses, exports, and logs.

---

## 5. Current Export Behavior

| Aspect | Status | Details |
|--------|--------|---------|
| Report export | ✅ **Exists** | Markdown and JSON export via `reports/exporter.py`. |
| Workspace export | 🟡 **Prototype** | Basic workspace export/import exists. |
| Export permissions | ❌ **None** | No permission check before export. |
| Export audit | ⚠️ **Partial** | Some report exports emit audit events. |
| Secret safety in exports | ❌ **None** | No check for provider secrets in export payloads. |

**Risk:** Sensitive data can be exported by any caller without governance.

---

## 6. Current Review Gate Behavior

| Aspect | Status | Details |
|--------|--------|---------|
| Review gate model | ✅ **Exists** | Workflow pause/resume via review gates. |
| Review resolution API | ✅ **Exists** | `POST /reviews/{id}/resolve`. |
| Role check on review | ❌ **None** | No permission check on who can resolve reviews. |
| Review audit | ⚠️ **Partial** | Audit events exist but don't include actor identity. |

**Risk:** Any caller can approve/reject review gates.

---

## 7. Current Frontend Permission Assumptions

| Aspect | Status | Details |
|--------|--------|---------|
| Auth state | ❌ **None** | No user context in React. |
| Permission-aware UI | ❌ **None** | All buttons/actions visible to all users. |
| 403 handling | ❌ **None** | No graceful 403 error handling in API client. |
| Role-based visibility | ❌ **None** | No role-based hiding/disabling of UI elements. |

**Risk:** Frontend exposes all actions regardless of user role.

---

## 8. Security Gaps Summary

| # | Gap | Severity | Phase |
|---|-----|----------|-------|
| 1 | No user identity model | Critical | P2 |
| 2 | No workspace membership/roles | Critical | P3 |
| 3 | No permission system | Critical | P4 |
| 4 | API routes not enforcing permissions | High | P5 |
| 5 | Frontend not permission-aware | High | P6 |
| 6 | Review gates not role-enforced | High | P7 |
| 7 | Exports not governed | Medium | P8 |
| 8 | Provider secrets may leak | High | P9 |
| 9 | No audit log viewer/UI | Medium | P10 |
| 10 | Cross-workspace isolation unenforced | High | P11 |
| 11 | No security mode settings | Medium | P12 |
| 12 | No security/threat model docs | Medium | P13 |

---

## 9. v1.27 Fixes

See `docs/IMPLEMENTATION_REPORT.md` after v1.27 completion for the full list of fixes applied.

Target fixes:
- Local identity model with roles (owner, admin, analyst, reviewer, viewer)
- Workspace membership with role assignment
- Permission matrix (14+ permissions mapped to roles)
- API route permission enforcement via dependency
- Frontend permission-aware states
- Role-enforced review gates
- Export governance with audit
- Provider secret redaction in API/exports/logs
- Audit log viewer API with filters
- Workspace isolation enforcement
- Security mode (demo | governed)
- Security model and threat model docs

---

## 10. Future Enterprise Gaps

- OAuth/SSO/SAML integration
- Cloud identity provider
- JWT tokens and session management
- API key-based service auth
- Fine-grained ABAC/ReBAC
- Audit webhook forwarding
- SIEM integration
- Encryption at rest
- Secrets vault integration (HashiCorp Vault, etc.)
- Multi-region audit compliance
- SOC2/ISO27001 evidence collection
