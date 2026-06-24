# Known Limitations — v1.34.0-dev

> **Last updated:** 2026-06-24
> **Version:** 1.34.0-dev
> **Status:** Local MVP Beta — Not Production Ready

This document centralizes all known limitations. If a limitation is listed here and contradicts another doc, this doc takes precedence.

---

## Beta Status

- **Not production-ready.** This is a local MVP beta candidate for evaluation purposes.
- **No enterprise auth.** Single-user in demo mode. Governed mode provides basic RBAC but no multi-user session management or SSO.
- **No encryption at rest.** Data is stored as plain JSON and SQLite files under `.decision_system/`.
- **No data-in-transit encryption** for local-only deployments (HTTP, not HTTPS). Production deployments should add a reverse proxy with TLS.
- **No audit stream to external systems.** Audit events are stored locally.
- **No warranty or SLA.** This software is provided as-is.

## Setup / Environment

- **Frontend requires `npm install && npm run build`** before Docker Compose will serve it.
- **Docker smoke tests are environment-dependent** — may not run in all sandbox/CI environments.
- **Tesseract required for OCR.** If Tesseract is not installed, OCR features are unavailable. Text-based PDFs and documents still work.
- **Python 3.11+ required.** Older Python versions are not supported.
- **Node.js 18+ required.** Older Node versions may cause frontend build failures.
- **`.env` file is not bundled.** Users must copy `.env.example` to `.env` and configure.

## OCR

- **English only.** Only English (`eng`) Tesseract language data is bundled.
- **OCR quality depends on image quality.** Scanned documents with poor contrast, handwriting, or non-standard fonts may produce low-quality text.
- **OCR is local-only.** No cloud OCR services are used.

## Connectors

- **All connectors are read-only.** External data is never modified.
- **Notion connector: disabled/planned.** Not active in this release.
- **Google Drive connector: disabled/planned.** Not active in this release.
- **Rate-limit handling is best-effort.** GitHub and URL connectors detect HTTP 429, but external rate-limit behavior cannot be guaranteed.
- **Large imports may be slow.** Importing 1000+ items from GitHub or URL connectors will take time proportional to page count.

## Security / Governance

- **Demo mode is the default.** Permission enforcement requires governed mode (`DECISION_SYSTEM_SECURITY_MODE=governed`).
- **No password authentication.** Identity is header-based in governed mode.
- **No role management UI.** Roles are configured via headers in governed mode.
- **Provider secrets stored in local JSON.** Secrets are not encrypted at rest in the provider store.

## Performance / Large Imports

- **Chroma is in-memory (file-backed).** Vector store loads at startup. Very large document collections may increase startup time.
- **Sequential workflow execution only.** No parallel branching support.
- **Large PDFs/datasets may be slow.** Very large files or high page-count documents may take noticeable time to parse and index.
- **374+ `__pycache__` directories** can accumulate. These are gitignored but consume disk space.

## UI / UX

- **Frontend Data Sources page is basic.** Functional but minimal.
- **Some sections lack onboarding guidance** on first use (empty states).
- **Edge case error messages** may be unhelpful in some scenarios.
- **Frontend mock mode** is used when backend is unavailable — some features show mock data.

## Docker

- **Docker Compose is the recommended setup** but Docker may not be available in all environments.
- **Docker smoke tests** (local-smoke-test.sh, e2e-local-demo-smoke.sh) can only be verified when Docker is available.
- **Frontend healthcheck** requires nginx to be running inside the frontend container.

## Future Features (Not Yet Implemented)

- Parallel workflow branching
- Write connectors (modify external data)
- Enterprise SSO / identity provider integration
- Encryption at rest
- External audit stream (SIEM, logging service)
- Multi-user session management
- Notion and Google Drive connectors
- Model fine-tuning or training workflows
- Cloud-hosted deployment option
- Mobile app

---

*This document is updated each milestone. If you discover a new limitation, please open a documentation issue.*
