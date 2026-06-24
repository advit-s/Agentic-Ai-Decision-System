# Threat Model — Agentic Decision System

> **Version:** 1.27.0-dev
> **Date:** 2026-06-24
> **Status:** Local Governance Foundation (not enterprise-grade)

---

## 1. Scope

This threat model covers the Agentic Decision System running in a
**local-first, self-hosted** deployment. It does not cover:

- Cloud-hosted or multi-tenant deployments (not supported).
- Enterprise identity providers (not yet integrated).
- Network-level attacks (assumes trusted LAN/localhost).
- Physical security of the host machine.

---

## 2. Trust Boundaries

```
┌──────────────────────────────────────────────────────┐
│ Trusted Host                                          │
│  ┌──────────────────────────────────────────────────┐ │
│  │ Decision System Process                           │ │
│  │  - FastAPI server (localhost:8000)                │ │
│  │  - Vite dev server (localhost:5173)               │ │
│  │  - CLI commands                                   │ │
│  │  - File system access (.decision_system/)         │ │
│  │  - Environment variable access (API keys)         │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  ┌──────────────────────────────────────────────────┐ │
│  │ External Services (optional)                      │ │
│  │  - Ollama (localhost:11434)                       │ │
│  │  - OpenAI API (api.openai.com)                    │ │
│  │  - NVIDIA NIM (api.nvcf.nvidia.com)               │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
         ▲
         │ (HTTP)
         ▼
┌──────────────────┐
│ User / Browser    │
│ (localhost)       │
└──────────────────┘
```

Trust boundary 1: Between the host and external AI providers (API keys
sent over HTTPS).
Trust boundary 2: Between the user's browser and the local API
(no authentication in demo mode).

---

## 3. Assets

| Asset | Sensitivity | Location |
|-------|-------------|----------|
| API keys (env vars) | Critical | Process environment |
| Uploaded company files | High | `.decision_system/data_sources/` |
| Evidence chunks | High | Chroma vector store, `.decision_system/` |
| Claims and verification results | Medium | `.decision_system/claim_ledger/` |
| Knowledge graph (entities, risks) | High | `.decision_system/graph/` |
| Workspace data | High | `.decision_system/` |
| Provider configurations | Medium | `.decision_system/providers/` |
| Audit logs | Medium | `.decision_system/security/audit/` |
| Decision reports | Medium | `.decision_system/reports/` |
| Workflow definitions | Low | `.decision_system/workflow_engine/` |

---

## 4. Threat Agents

| Agent | Motivation | Capability |
|-------|------------|------------|
| Local attacker (malicious process) | Data theft, sabotage | Can make HTTP requests to localhost, read/write files |
| Local attacker (non-admin user) | Data access escalation | Has limited file system access, can run CLI |
| External network attacker | Data exfiltration | Can scan for open ports, attempt to access API |
| Insider (authorized user) | Unauthorized data access | Has legitimate access to some data, tries to access more |
| Supply chain (malicious dependency) | Backdoor, data theft | Can execute code in the Python process |

---

## 5. Threats and Mitigations

### T1: Unauthenticated API Access
**Risk:** Any local process can call API endpoints without authentication.

**Severity:** High (demo mode), Low (governed mode with localhost-only)

**Mitigations:**
- Demo mode is the default — simple and convenient for development.
- Governed mode enforces permissions via `X-User-Id` header.
- API is bound to localhost by default.
- All routes have permission checks available.

**Residual risk:** In demo mode, any local process can access all data.

---

### T2: API Key Exposure
**Risk:** Provider API keys are exposed via API responses, logs, or exports.

**Severity:** High

**Mitigations:**
- Keys are stored as environment variable references (`api_key_env`).
- No plaintext keys in config JSON files.
- API responses return `api_key_configured` boolean only.
- Audit events contain only metadata, not key values.
- Exports exclude provider configurations entirely.

**Residual risk:** Keys exist in process memory at runtime. Keylogger
or memory dump could extract them.

---

### T3: Cross-Workspace Data Access
**Risk:** A user with access to one workspace can read data from another.

**Severity:** High

**Mitigations:**
- All data stores accept `workspace_id` as a scoping parameter.
- Workspace membership is required for mutation operations.
- API routes check workspace membership before returning data.

**Residual risk:** Some legacy stores may not fully enforce workspace
isolation for all query patterns.

---

### T4: Unauthorized Export
**Risk:** A viewer or analyst can export sensitive reports without approval.

**Severity:** Medium

**Mitigations:**
- Report export requires `report.export` permission (admin/owner only).
- Export audit events include actor and workspace_id.
- Security settings can tighten export requirements.

**Residual risk:** Admin/owner users can always export.

---

### T5: Review Gate Bypass
**Risk:** A non-reviewer user can approve or reject review gates.

**Severity:** Medium

**Mitigations:**
- Review resolution requires `review.resolve` permission.
- Security settings require reviewer role or higher.
- Review decisions are audited with actor identity.

**Residual risk:** Owner/admin can always resolve reviews.

---

### T6: Audit Log Tampering
**Risk:** An attacker with file system access can modify or delete audit logs.

**Severity:** Medium

**Mitigations:**
- Audit logs are append-only JSONL format (new events appended).
- Logs are readable via API (requires `audit.read` permission).
- No integrity verification (no cryptographic signing).

**Residual risk:** Local file system access allows log tampering.
Future work could add log signing or forwarding.

---

### T7: Local File System Access
**Risk:** An attacker with file system access reads all `.decision_system/` data.

**Severity:** Critical

**Mitigations:**
- Operating system file permissions protect the directory.
- Full-disk encryption is recommended for sensitive deployments.
- No application-level encryption at rest.

**Residual risk:** Any user/process with file system access can read
all data. This is inherent to the local-first design.

---

### T8: Sensitive Data in Logs
**Risk:** API keys, PII, or confidential company data appears in application logs.

**Severity:** Medium

**Mitigations:**
- Audit events do not include plaintext secrets.
- Provider config updates log metadata only.
- PDF/DOCX content is not logged at debug levels.

**Residual risk:** Application logs may contain evidence text, claim
text, or report content.

---

### T9: Dependency Vulnerability
**Risk:** A third-party package has a known security vulnerability.

**Severity:** Medium

**Mitigations:**
- Python dependencies are pinned in `pyproject.toml`.
- Frontend dependencies are pinned in `package-lock.json`.
- No network-accessible attack surface for most attack classes.

**Residual risk:** Regular `pip audit` / `npm audit` should be run
as part of maintenance.

---

### T10: Social Engineering (Insider)
**Risk:** An authorized user extracts data beyond their need-to-know.

**Severity:** Medium

**Mitigations:**
- Role-based access control limits what each role can do.
- Audit logging records who accessed what.
- Workspace isolation prevents cross-workspace access.

**Residual risk:** An admin/owner has access to everything.

---

## 6. Attack Surface

| Component | Attack Surface | Exposure |
|-----------|---------------|----------|
| FastAPI server | HTTP endpoints | Localhost only (configurable) |
| Vite dev server | HTTP endpoints | Localhost only (development) |
| Static file server | Served HTML/JS/CSS | Localhost only |
| CLI commands | Command-line args | Local terminal only |
| Python process | OS-level access | Local user only |
| External AI APIs | HTTPS outbound | Network boundary |

---

## 7. Security Controls Summary

| Control | Type | Status |
|---------|------|--------|
| Permission matrix | Preventive | Implemented |
| Workspace membership | Preventive | Implemented |
| API route enforcement | Preventive | Implemented (partial) |
| Provider secret handling | Preventive | Implemented |
| Audit logging | Detective | Implemented |
| Export governance | Preventive | Implemented |
| Review gate enforcement | Preventive | Implemented |
| Security mode (demo/governed) | Preventive | Implemented |
| Encryption at rest | Preventive | Not implemented |
| Transport security | Preventive | Not implemented (add reverse proxy) |
| Password authentication | Preventive | Not implemented |
| Session management | Preventive | Not implemented |
| Brute-force protection | Preventive | Not implemented |
| Audit integrity | Detective | Not implemented |

---

## 8. Risk Assessment

| Threat | Likelihood | Impact | Risk Level | Mitigated? |
|--------|-----------|--------|------------|------------|
| T1: Unauthenticated API access | High | High | **Critical** | Partial |
| T2: API key exposure | Low | High | **High** | Yes |
| T3: Cross-workspace access | Medium | High | **High** | Partial |
| T4: Unauthorized export | Low | Medium | **Low** | Yes |
| T5: Review gate bypass | Low | Medium | **Low** | Yes |
| T6: Audit log tampering | Medium | Medium | **Medium** | No |
| T7: File system access | Medium | Critical | **High** | No |
| T8: Sensitive data in logs | Medium | Medium | **Medium** | Partial |
| T9: Dependency vulnerability | Low | Medium | **Low** | No |
| T10: Insider threat | Low | Medium | **Low** | Partial |

---

## 9. Recommended Security Improvements

### Short-term (within 1-2 milestones)
1. Add `localhost-only` binding enforcement in governed mode.
2. Add optional audit log signing (HMAC with local key).
3. Add rate limiting on API endpoints.
4. Add content scanning for PII in exports.

### Medium-term (3-6 milestones)
5. Add password-based local authentication.
6. Add optional TLS support.
7. Add session management with expiry.
8. Add encryption at rest for `.decision_system/` data.

### Long-term (post-MVP)
9. Integrate OAuth/OIDC for enterprise auth.
10. Add audit webhook/SIEM forwarding.
11. Add ABAC/ReBAC for fine-grained access control.
12. Add secrets vault integration.

---

## 10. Security Testing

### Automated
- Permission matrix unit tests (`tests/test_identity.py`)
- Route permission enforcement tests (in progress)
- Provider secret handling tests (`tests/test_providers/`)
- Audit event tests (`tests/test_security.py`)

### Manual
- Review gate role enforcement
- Workspace isolation verification
- Export content review (no secrets)
- Audit log review
