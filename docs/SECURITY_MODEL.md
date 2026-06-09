# Security Model

## Current State (Prototype)

The Agentic Decision System is a **local-only prototype** with no production
security controls. This document describes the current security posture honestly.

## Authentication

**Status: Not implemented.**

- No user authentication (JWT, OAuth, session tokens).
- All CLI and API operations run as the local OS user.
- The API binds to `127.0.0.1` by default (localhost only).
- No RBAC: all operations available to all local users.

## Authorization

**Status: Not implemented.**

- No role-based access control.
- No permission checks on any operation.
- The approval workflow is a record-keeping mechanism, not an enforcement layer.

## Data Protection

**Status: Local files only, no encryption.**

- Company documents and generated state stored as local files.
- Chroma vector store uses local SQLite.
- No encryption at rest.
- No encryption in transit (local API only, no TLS).
- The `scan-secrets` and `redact-preview` tools help identify sensitive data
  but do not enforce redaction.

## Secret Management

**Status: Environment variables only.**

- Provider API keys stored in `.env` files or environment variables.
- No secrets vault (HashiCorp Vault, AWS Secrets Manager, etc.).
- The secret scanner identifies potential leaks in source code.
- The policy check verifies `.env` is not tracked by git.

## Network Security

**Status: Local host only.**

- FastAPI binds to `127.0.0.1:8000` by default.
- No TLS termination.
- No CORS configuration.
- No rate limiting.
- No firewall rules.
- Docker deployment exposes port 8000 only.

## Audit and Logging

**Status: Local JSONL audit log.**

- Security-relevant events (secret scans, policy checks, redactions, approvals)
  are logged to `.decision_system/security/audit/audit_log.jsonl`.
- No log retention policy.
- No centralized log collection.
- No tamper protection on audit logs.

## Input Validation

**Status: Basic Pydantic validation.**

- API requests validated through Pydantic models.
- No comprehensive input sanitization.
- No file upload validation beyond extension checking.
- Path traversal is mitigated by resolving and checking paths.

## Connector Security

**Status: Only local-files connector is real.**

- The `local-files` connector copies files locally with no network calls.
- GitHub, Jira, Slack, and Email connectors are offline stubs.
- No real credentials are stored for stub connectors.
- The policy check verifies stubs do not make network calls.

## War Room / Orchestration Security

**Status: Deterministic simulation only.**

- War-room agents are deterministic artifact generators, not live LLM agents.
- Higher context is deep-frozen (read-only for lower-level agents).
- Common workspace is append-only.
- Judge/verifier checks outputs before they influence final reports.
- No autonomous external actions (emails, tickets, deployments).

## Planned Improvements

1. Add OAuth2/JWT authentication for API access.
2. Add RBAC for role-based operation restrictions.
3. Add TLS for API transport encryption.
4. Add secrets vault integration.
5. Add audit log retention and tamper protection.
6. Add rate limiting and input sanitization.
7. Add comprehensive connector security review before enabling real connectors.
