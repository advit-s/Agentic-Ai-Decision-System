# Public Beta Release Candidate — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate + Demo Video Script
> **Date:** 2026-06-24
> **Status:** Public Beta Release Candidate — Not Production Ready

---

## Release Summary

This is the first public beta release candidate of the Agentic AI Decision System — a local-first, self-hosted company intelligence automation app.

**What's included:**
- Document ingestion (PDF, DOCX, XLSX, MD, TXT, CSV, JSON + OCR)
- Chroma vector search with workspace isolation
- Bounded LangGraph analysis workflows
- Knowledge graph extraction (entities, relationships, risks, metrics)
- Claim ledger with deterministic verification
- Trust report generation with Markdown export
- Read-only connectors (Local Folder, GitHub, URL import)
- Visual workflow builder (React Flow-based SPA)
- RBAC governance mode
- Audit logging and observability metrics

**What's not included:**
- Enterprise authentication or SSO
- Encryption at rest
- Write connectors (external data is never modified)
- Parallel workflow execution
- Cloud-hosted deployment

## What to Test

See the [Bug Bash Checklist](./docs/BUG_BASH_CHECKLIST.md) for structured test areas.

Priority areas:
1. Fresh install and setup
2. Document upload, parsing, and indexing
3. Demo workflow execution
4. Claim verification and contradiction detection
5. Knowledge graph extraction
6. Trust report generation and export

## Install Options

```bash
# Docker (recommended)
docker compose up --build

# Local scripts
cp .env.example .env
./scripts/setup-local.sh
./scripts/start-local.sh --all
```

## Validation Status

| Check | Result |
|-------|--------|
| Backend tests | 1,647 passed, 2 skipped |
| Frontend tests | 56 passed, 15 files |
| Frontend build | Successful |
| Shell scripts | All parse without errors |
| Diagnostics safety | No secrets collected |
| Docker smoke | Environment-dependent |
| E2E demo smoke | Requires running backend |

## How to Submit Feedback

1. Collect diagnostics: `./scripts/collect-diagnostics.sh`
2. Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
3. Or use the [Beta Feedback template](.github/ISSUE_TEMPLATE/beta_feedback.yml)

## Known Limitations

See [KNOWN_LIMITATIONS.md](./docs/KNOWN_LIMITATIONS.md) for the full list.

Key limitations:
- Not production-ready
- No enterprise auth
- No encryption at rest
- OCR requires local Tesseract
- Read-only connectors only
- Sequential workflows only
- English only

## Security / Trust Honesty

This is a **local MVP beta candidate**. It is not production-ready and does not yet include enterprise authentication, encryption at rest, or hosted deployment support.

The verifier checks whether local workspace evidence appears to support, contradict, or fail to support claims. It is deterministic and conservative, not a perfect truth engine.
