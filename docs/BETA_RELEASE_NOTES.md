# Beta Release Notes — v1.33.0-dev

> **Version:** 1.33.0-dev
> **Milestone:** End-to-End Beta QA + Bug Bash
> **Date:** 2026-06-24
> **Status:** Local MVP Beta — Not Production Ready

---

## What Works

The following features are functional and tested in the local beta:

### Setup & Startup
- One-command local setup via `./scripts/setup-local.sh`
- Backend API server via `./scripts/start-local.sh`
- Frontend dev server via `./scripts/start-local.sh --all`
- Docker Compose orchestration (backend + frontend + nginx)
- Diagnostics via `./scripts/doctor-local.sh`
- Data backup via `./scripts/backup-local-data.sh`
- Safe data reset via `./scripts/reset-local-data.sh`
- Local validation via `./scripts/validate-local.sh`

### Data Ingestion
- File upload: TXT, MD, CSV, JSON, PDF (text-based), DOCX, XLSX
- OCR pipeline for scanned PDFs and images (requires Tesseract)
- Chroma vector indexing and search
- Data-source version/provenance tracking

### Connectors (Read-Only)
- Local folder connector with import/sync
- GitHub connector (public repos)
- URL import connector
- Batch import with progress tracking
- Duplicate detection (hash-based, idempotent)
- Pagination, retry/backoff, rate-limit handling
- Cancel/pause/resume for import jobs
- All connectors are read-only — no external data is modified

### Workflow Engine
- Visual workflow builder (React Flow-based)
- Demo workflows: Local Trust Report Demo, Evidence Search, Evidence Synthesis, Claim Verification, Graph Extraction
- Execution history with node-level detail
- Review Gate with pause/resume
- Fake provider for offline testing (no API key needed)

### Claims & Verification
- Claim extraction from workflow output
- Claim verification with evidence references
- Contradiction scanning
- Claim status labels: verified, unsupported, contradicted, pending

### Knowledge Graph
- Entity/relationship extraction
- Risk and metric extraction
- Interactive graph visualization

### Reports
- Trust report generation
- Markdown export with full citations
- Report sections: executive summary, evidence, claims, risks, graph

### Security & Governance
- Demo mode (default, no auth required)
- Governed mode with RBAC (owner, admin, analyst, reviewer, viewer)
- Audit logging for key actions
- Workspace isolation
- Provider secret redaction

---

## What Is Beta

The following areas are functional but may have rough edges:

- **Frontend error states**: Some edge cases may show unhelpful error messages
- **Empty states**: Some sections may lack onboarding guidance on first use
- **OCR quality**: Depends on local Tesseract installation and image quality
- **Large file handling**: Very large PDFs or datasets may be slow
- **Workflow execution**: Sequential only, no parallel branching
- **Graph extraction quality**: Depends on document content and quality
- **Containerized deployment**: Docker Compose works but smoke tests are environment-dependent

---

## How to Install

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm
- Docker (optional, for containerized setup)
- Tesseract (optional, for OCR)

### Quick Install
```bash
git clone <repo-url>
cd Agentic-Ai-Decision-System
cp .env.example .env
./scripts/setup-local.sh
```

### Start
```bash
# Backend only
./scripts/start-local.sh

# Backend + frontend
./scripts/start-local.sh --all

# Docker (full stack)
docker compose up --build
```

---

## How to Run Demo

```bash
# 1. Start the backend
./scripts/start-local.sh

# 2. Open http://localhost:3000 (Docker) or http://localhost:5173 (dev)

# 3. Follow the demo path:
#    - Create/select workspace
#    - Upload sample data from demo/sample-data/
#    - Parse and index files
#    - Configure fake provider
#    - Run "Local Trust Report Demo" workflow
#    - View claims, graph, and report
```

For the full 18-step walkthrough, see [DEMO_PATH.md](./DEMO_PATH.md).

---

## How to Validate

```bash
# Run all baseline checks
./scripts/validate-local.sh

# Run diagnostics
./scripts/doctor-local.sh

# Run specific test suites
python -m pytest tests/test_system -q
python -m pytest tests/test_connectors -q
python -m pytest tests/test_security -q
python -m pytest tests/test_data_sources -q
python -m pytest tests/test_verification -q
python -m pytest tests/test_providers -q
python -m pytest tests/test_graph_api -q
python -m pytest tests/test_workflow_engine/test_api.py -q

# Frontend tests
cd web/workflow-builder && npm test

# Frontend build
cd web/workflow-builder && npm run build
```

---

## Known Limitations

1. **Not production-ready**: This is a local MVP beta candidate. No enterprise auth, no encryption at rest, no audit stream to external systems.
2. **Single-user**: Demo mode is default. Governed mode provides basic RBAC but no multi-user session management.
3. **OCR depends on Tesseract**: If Tesseract is not installed, OCR features are unavailable. Text-based PDFs and documents still work.
4. **English only**: Only English (`eng`) Tesseract language data is bundled.
5. **Sequential workflow execution**: No parallel branching support.
6. **Chroma in-memory**: Vector store is file-based but loaded at startup.
7. **Docker smoke**: Environment-dependent; may not run in all sandbox environments.
8. **No write connectors**: All connectors are read-only. External data is never modified.
9. **Notion/Drive connectors**: Disabled/planned. Not active in this release.
10. **No SSO**: No single sign-on or enterprise identity provider integration.

---

## How to Report Bugs

Report bugs by opening a GitHub issue with:

- **Version**: 1.33.0-dev
- **Environment**: OS, Python version, Node version, Docker (if used)
- **Steps to reproduce**: What you did, what you expected, what happened
- **Logs**: Relevant output from `.decision_system/logs/` or terminal
- **Screenshots**: If applicable

---

## Recommended Test Path

For reviewers, follow this order:

1. Run `./scripts/doctor-local.sh` and `./scripts/validate-local.sh`
2. Start the app (`./scripts/start-local.sh --all`)
3. Open the frontend at http://localhost:5173
4. Follow the demo path in [DEMO_PATH.md](./DEMO_PATH.md)
5. Verify each step creates expected artifacts
6. Test backup/reset scripts
7. Compare against [BETA_QA_CHECKLIST.md](./BETA_QA_CHECKLIST.md)
8. Report any failures or rough edges

---

*These release notes are for v1.33.0-dev, the End-to-End Beta QA + Bug Bash milestone.*
*This software is provided as-is for local evaluation purposes.*
