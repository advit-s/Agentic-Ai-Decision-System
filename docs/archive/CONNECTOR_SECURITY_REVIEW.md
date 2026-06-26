# Connector Security Review — v1.30

> **Review date:** 2026-06-24
> **Version:** 1.30.0-dev
> **Scope:** All built-in connectors

---

## Security Principles

1. **All connectors are read-only.** No connector can create, update, or delete
   data on external systems. This is enforced at the model level via
   `ConnectorMode.READ_ONLY` with a Pydantic validator.
2. **No plaintext token storage.** Token values are never stored in connector
   configs. They are referenced via environment variable names only.
3. **No token values in API responses.** All API responses redact token values.
   The `/credential-status` endpoint returns only boolean presence indicators.
4. **Workspace isolation.** All connector data is scoped to a workspace.
5. **Audit trail.** All connector operations are logged to the audit log.

---

## Connector-Specific Risks

### Local Folder Connector

| Risk | Severity | Mitigation |
|------|----------|------------|
| Path traversal | **High** | `_reject_connector_path()` blocks absolute system directories, symlinks, and path components with `..`. Path is resolved and validated before any file access. |
| Access to sensitive files | **Medium** | Only files with supported extensions (.md, .txt, .csv, .json, .yml, .xml, .html) are imported. Hidden files (dotfiles) are excluded. |
| Large file import | **Low** | File size limits are enforced (configurable, default 10 MB). |
| Source file modification | **None** | Files are copied, never modified. |

### GitHub Repository Connector

| Risk | Severity | Mitigation |
|------|----------|------------|
| Unauthorized private repo access | **Medium** | Only public repos work without a token. GITHUB_TOKEN env var is optional and never stored in config. |
| Token leakage in error messages | **Medium** | All error messages are passed through `redact_connector_token()` before returning. |
| Rate limit exhaustion | **Low** | Public API has rate limits; token increases limits. No automatic retry. |
| Write operations | **None** | Only GET endpoints are used. No POST/PUT/PATCH/DELETE calls are made. |

### URL / Web Page Import Connector

| Risk | Severity | Mitigation |
|------|----------|------------|
| SSRF (Server-Side Request Forgery) | **High** | `_is_private_host()` blocks all private/internal network addresses (10.x.x.x, 172.16-31.x.x, 192.168.x.x, 127.x.x.x, localhost). Only HTTP/HTTPS URLs are accepted. |
| Large response DoS | **Medium** | Response size is limited to 10 MB. Streaming download with early termination. |
| Content-type bypass | **Low** | Only text/html content types are imported. Binary content is rejected. |
| Redirect following | **Low** | Redirects are followed but only to public addresses (SSRF check applies to final URL). |

### Notion Connector (Planned / Disabled)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token leakage | **Medium** | Will use env-var only (NOTION_API_KEY). Never stored in config. |
| Write operations | **None** | Read-only API integration designed from the start. |

### Google Drive Connector (Planned / Disabled)

| Risk | Severity | Mitigation |
|------|----------|------------|
| Token leakage | **Medium** | Will use env-var only (GOOGLE_DRIVE_TOKEN). Never stored in config. |
| Unauthorized file access | **Medium** | Scoped to user's token permissions. Workspace isolation applied after import. |
| Write operations | **None** | Read-only API scope requested. |

---

## Token/Secret Handling

| Concern | Status |
|---------|--------|
| Token values stored in config | **Never.** Only env-var names are referenced. |
| Token values in API responses | **Never.** Token status endpoints return boolean presence only. |
| Token values in logs | **Redacted.** `redact_connector_token()` is applied to all log/audit/error messages. |
| Token values in error messages | **Redacted.** The `test_connection` response is sanitized. |
| Token values in audit events | **Redacted.** Audit events use the sanitized response. |
| Token validation | **Partial.** Connectors validate tokens on use (by attempting API calls), not on configuration. |

---

## RBAC for Connectors

| Permission | Viewer | Reviewer | Analyst | Admin/Owner |
|-----------|--------|----------|---------|-------------|
| connector.read | ✅ | ✅ | ✅ | ✅ |
| connector.manage | ❌ | ❌ | ❌ | ✅ |
| connector.import | ❌ | ❌ | ✅ | ✅ |
| connector.sync | ❌ | ❌ | ✅ | ✅ |
| connector.schedule | ❌ | ❌ | ❌ | ✅ |

- **Viewer/Reviewer:** Can list connectors and see setup schemas but cannot create, test, import, or sync.
- **Analyst:** Can import and sync if permission allows.
- **Admin/Owner:** Full connector management.

---

## Audit Coverage

| Event | Recorded |
|-------|----------|
| Connector created | ✅ |
| Connector updated | ✅ |
| Connector deleted | ✅ |
| Connector tested | ✅ |
| Items listed | ✅ |
| Import started/completed/failed | ✅ |
| Item imported | ✅ |
| Setup started/tested/completed/failed | ✅ (v1.30) |
| Credentials missing | ✅ (v1.30) |
| Item previewed | ✅ (v1.30) |
| Sync started/completed/failed | ✅ (v1.29) |
| Schedule created/updated/deleted/toggled | ✅ (v1.29) |

---

## Network Security

| Control | Status |
|---------|--------|
| HTTP timeout (connect) | 10 seconds |
| HTTP timeout (total) | 30 seconds |
| Max response size | 10 MB |
| Private address blocking | ✅ (URL connector) |
| Content-type validation | ✅ (URL connector) |
| HTTPS enforced | Recommended, not enforced |
| Max redirects | 5 (httpx default) |

---

## Known Gaps (Deferred)

| Gap | Reason | Target |
|-----|--------|--------|
| OAuth flow | Not implemented; env-var only | Future milestone |
| Token validation on config save | Would require testing connectivity on every save | v1.31 |
| Rate limit handling | No automatic backoff or retry | v1.31 |
| Large file streaming | Files are loaded into memory | v1.31 |
| Network policy controls | No per-connector allow/deny list | Future |
| Certificate validation | Uses httpx defaults (verify=True) | No change needed |
| Credential rotation | No mechanism to rotate tokens without restart | Future |
