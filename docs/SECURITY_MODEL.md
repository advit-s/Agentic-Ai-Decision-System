# Security Model — Agentic Decision System

> **Version:** 1.27.0-dev
> **Date:** 2026-06-24
> **Status:** Local Governance Foundation (not enterprise-grade)

---

## 1. Local-First Security Assumptions

This system is designed for **local-first, self-hosted** use. All security
mechanisms assume:

- The host machine is trusted by the operator.
- The local filesystem is trusted.
- Network access is controlled by the host environment (firewall, VPN,
  localhost-only binding).
- No cloud identity provider, no SaaS auth service, no external
  authentication authority.

**What this means:**
- There is **no encryption at rest** for local data stores.
- There is **no transport security** (TLS) between locally-bound services
  (though a reverse proxy can add it).
- There is **no brute-force protection** on identity — identity is
  opt-in and session-free.
- There is **no password-based authentication**.

These are **conscious design choices** for a local MVP beta. They are not
oversights. Enterprise deployments should add a reverse proxy, TLS,
and a proper identity provider.

---

## 2. Demo Mode vs Governed Mode

### Demo Mode (default)

- No login or identity required.
- All API endpoints are open.
- Current user is always `local/system` with role `owner`.
- Perfect for quick-start demos, development, and evaluation.

### Governed Mode

- Identity is resolved from the `X-User-Id` request header.
- API routes enforce permissions based on user role.
- Workspace membership is checked for scoped operations.
- Security settings can tighten review, export, and audit requirements.

Switching modes:
```python
# Via API
PUT /identity/settings
{"security_mode": "governed"}

# Programmatic
from decision_system.identity.settings import update_settings
update_settings(security_mode="governed")
```

---

## 3. Identity Model

### User Fields
| Field | Type | Description |
|-------|------|-------------|
| user_id | str | Unique identifier (e.g., `local/system`) |
| display_name | str | Human-readable name |
| role | UserRole | One of: owner, admin, analyst, reviewer, viewer |
| created_at | str | ISO-8601 timestamp |
| updated_at | str | ISO-8601 timestamp |
| metadata | dict | Arbitrary key-value pairs |

### Default User
```json
{
  "user_id": "local/system",
  "display_name": "Local System",
  "role": "owner"
}
```

### User Store
- JSON file at `.decision_system/identity/users.json`
- CRUD via API: `GET/POST/PUT/DELETE /identity/users`
- No authentication — this is a local governance layer

---

## 4. Roles

| Role | Description | Privilege Level |
|------|-------------|-----------------|
| owner | Full control over everything | 5 (highest) |
| admin | Manage workspace, settings, providers, exports | 4 |
| analyst | Upload data, run workflows, create reports | 3 |
| reviewer | Approve/reject review gates | 2 |
| viewer | Read-only access to workspace data | 1 (lowest) |

Roles are ordered: viewer < reviewer < analyst < admin < owner

---

## 5. Permission Matrix

See `GET /identity/permissions` for the full live matrix.

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

---

## 6. Workspace Membership

Each workspace can have its own role assignments for users:

```json
{
  "workspace_id": "ws-123",
  "user_id": "local/alice",
  "role": "analyst"
}
```

Workspace roles **override** the user's global role for operations
scoped to that workspace.

---

## 7. Provider Secret Handling

### Design
- Provider configs use `api_key_env` (env var name) not `api_key` (value).
- `api_key_configured` is a boolean indicating whether the env var is set.
- **No plaintext API keys** are stored in config JSON files.
- **No plaintext API keys** are returned in API responses.
- **No plaintext API keys** are included in exports.
- **No plaintext API keys** appear in audit logs (only metadata about
  the config change, not the key itself).

### Env var pattern
```json
{
  "provider_type": "openai",
  "api_key_env": "OPENAI_API_KEY",
  "api_key_configured": true
}
```

---

## 8. Audit Logging

- All audit events are written to `.decision_system/security/audit/audit_log.jsonl`.
- Events include: event_id, event_type, actor (user_id), message, metadata, timestamp.
- Actor is automatically resolved from the identity system (falls back to `"local-user"`).
- API: `GET /workspaces/{id}/audit/events` with filters for event_type, actor, date range.
- API: `GET /workspaces/{id}/audit/summary` for aggregate counts.
- Events are emitted for: provider changes, review resolutions, report exports,
  verification actions, graph extractions, and more.

---

## 9. Export Governance

- Report export requires `report.export` permission.
- Export audit events include actor, workspace_id, report_id, and format.
- Exports **never** include provider secrets.
- Security settings can require admin role for exports (`exports_require_admin`).

---

## 10. Review Gate Governance

- Review resolution requires `review.resolve` permission.
- Security settings require reviewer role or higher (`review_requires_reviewer_role`).
- Review decisions record the actor (user_id).
- Audit events include review_id, action, actor, and notes.

---

## 11. Workspace Isolation

- All data stores accept `workspace_id` as a scoping parameter.
- Data sources, evidence, claims, reports, workflows, graph data, and
  audit events are scoped to a workspace.
- API routes enforce workspace membership for mutation operations.
- Cross-workspace access requires appropriate workspace membership.

---

## 12. What Is Not Implemented

- **Password-based authentication** — No login, no sessions, no tokens.
- **Encryption at rest** — Data is stored as plain JSON/SQLite files.
- **Transport security** — No TLS between services (add reverse proxy).
- **Brute-force protection** — No rate limiting on identity endpoints.
- **Audit webhook / SIEM** — No forwarding of audit events.
- **ABAC / ReBAC** — Attribute-based or relationship-based access control.
- **Multi-factor authentication** — Not applicable without passwords.
- **Secrets vault** — No HashiCorp Vault, AWS Secrets Manager, etc.
- **Cloud identity** — No OAuth, SAML, LDAP, or SSO.
- **Session management** — No token refresh, expiry, or revocation.

---

## 13. Future Enterprise Auth Upgrade Path

The identity system uses clean interfaces that allow future replacement:

1. Replace `get_current_user()` with a JWT/session-based resolver.
2. Add an `authenticate` dependency that validates tokens.
3. Replace the local JSON user store with a database-backed store.
4. Add OAuth/OIDC integration at the middleware level.
5. Encrypt secrets at rest using the host's keychain.

---

## 14. Deployment Recommendations

For private company-data beta:
- Run on a dedicated machine or VM.
- Use `localhost` binding only (no `0.0.0.0`) unless behind a reverse proxy.
- Add a firewall to restrict access to the host.
- Set `security_mode: governed` and create individual user accounts.
- Use environment variables for all API keys.
- Regularly audit the `.decision_system/` directory.
- Backup `.decision_system/` for disaster recovery.
- Consider full-disk encryption on the host.

---

## Connector Security

Connectors follow strict security principles:

### Read-only enforcement
All connectors are enforced read-only at the model level (`ConnectorMode.READ_ONLY`).
No connector can create, update, or delete data on external systems.

### Token/handle handling
- Token values are never stored in connector configurations.
- The `GITHUB_TOKEN`, `NOTION_API_KEY`, and `GOOGLE_DRIVE_TOKEN` are referenced via environment variable names only.
- API credential status endpoints return boolean presence indicators only.
- Token values are redacted from all logs, audit events, and error messages via `redact_connector_token()`.

### SSRF protection
The URL Import connector blocks requests to private/internal network addresses:
- `10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`, `127.x.x.x`, `localhost`
- Response size limited to 10 MB
- Only HTTP/HTTPS URLs accepted

### Path traversal protection
The Local Folder connector:
- Resolves and validates paths before access
- Blocks absolute system directories and symlinks
- Rejects `..` path components
- Only imports supported file extensions

### Audit
All connector operations are recorded in the audit log:
- Create, update, delete, test, list items, import, sync
- Setup events (v1.30): setup started, tested, completed, failed, credentials missing
- See `docs/CONNECTOR_SECURITY_REVIEW.md` for detailed review.
