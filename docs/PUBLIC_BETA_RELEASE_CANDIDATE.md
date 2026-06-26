# Public Beta Handoff — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Integration Hardening and Truth-in-Claim Alignment
> **Date:** 2026-06-26
> **Status:** Beta handoff candidate — blockers identified, not yet release-ready

---

## Summary

This is a **beta handoff candidate** for the Agentic AI Decision System — a local-first, self-hosted company intelligence workbench. Several integration blockers must be resolved before outside beta review (see [Blockers](#blockers) below).

## What's Included

- Document ingestion (PDF, DOCX, XLSX, MD, TXT, CSV, JSON + OCR)
- Chroma vector search with workspace isolation
- DAG workflow engine with scheduling and event streaming
- Knowledge graph extraction (entities, relationships, risks, metrics)
- Claim ledger with deterministic verification
- Trust report generation with Markdown export
- Read-only connectors (Local Folder, GitHub, URL import)
- Visual workflow builder (React Flow-based SPA)
- Local RBAC governance mode
- Audit logging

## What's Not Included

- Enterprise authentication or SSO
- Encryption at rest
- Write-back connectors (external data is never modified)
- Cloud-hosted deployment

## Blockers

The following [P0 integration gaps](https://github.com/nicholasgriffintn/Agentic-Ai-Decision-System/issues) must be resolved before outside beta review:

1. **Connector imports not integrated with evidence search** — Connector-synced content does not yet flow into the parse → chunk → index → searchable evidence pipeline.
2. **Incremental sync does not reindex** — Sync state updates without reconciling indexed evidence.
3. **Docker + demo path not runtime-verified** — Fresh-clone startup and demo flow have not been validated end-to-end in a clean environment.

## What to Test (After Blockers)

Priority areas:
1. Fresh install and setup
2. Document upload, parsing, and indexing
3. Demo workflow execution
4. Claim verification and contradiction detection
5. Knowledge graph extraction
6. Trust report generation and export

## Install Options

```bash
# Docker (recommended for full demo)
docker compose up --build

# Local scripts
cp .env.example .env
./scripts/setup-local.sh
./scripts/start-local.sh --all
```

## How to Submit Feedback

1. Collect diagnostics: `./scripts/collect-diagnostics.sh`
2. Use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.yml)
3. Or use the [Beta Feedback template](.github/ISSUE_TEMPLATE/beta_feedback.yml)

## Known Limitations

See [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md) for the full list.

Key limitations:
- Not production-ready
- No enterprise auth
- No encryption at rest
- OCR requires local Tesseract
- Read-only connectors only
- Sequential workflows only
- English only

## Security Honesty

This is a **local MVP beta candidate**. It is not production-ready. The verifier checks whether local workspace evidence appears to support, contradict, or fail to support claims. It is deterministic and conservative, not a perfect truth engine.
