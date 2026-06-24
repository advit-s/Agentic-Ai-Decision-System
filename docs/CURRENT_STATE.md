# Current State — Agentic Decision System

 > **Last updated:** 2026-06-23 (v1.25.0-dev — End-to-End Demo Hardening + Local Beta Release Prep)
 > **Package version:** 1.25.0-dev
> **Previous milestone:** v1.23.1 — Finish Document Ingestion Wiring + Test Reliability
> **Current milestone:** v1.25.0 — End-to-End Demo Hardening + Local Beta Release Prep + Data Sources in React Workflow Builder
> **Python:** >=3.11

---

## What is the project?

A **local-first, self-hosted Company Intelligence Automation System** (n8n-style).
Runs on the user's machine, reads local company documents and datasets,
builds an evidence-backed intelligence layer, detects risks/contradictions/patterns,
then uses bounded workflows/agents to create verified decision reports.

---

## Quick start

```bash
# Docker (recommended)
docker compose up
# Open http://localhost:3000

# Manual
python -m pip install -e ".[dev]"
decision-system serve-api --host 0.0.0.0 --port 8000
```

---

## What is production-like

| Area | Status | Notes |
|------|--------|-------|
| CLI framework | ✅ **Production** | Typer-based CLI; all documented commands work offline |
| Document indexing | ✅ **Production** | Chroma-based chunking, loading, and retrieval |
| Document parsing (PDF/DOCX/XLSX) | ✅ **Production** | Local text extraction via pypdf, python-docx, openpyxl; OCR fallback via tesserocr for scanned PDFs |
| Image OCR (PNG/JPG/TIFF) | ✅ **Production** | Local OCR for scanned images via tesserocr; automatic fallback for textless PDFs |
| Claim ledger | ✅ **Production** | Create/store/query claims; statuses (supported, contradicted, unsupported, uncertain, needs_review) |
| Verifier | ✅ **Production** | Check claims against evidence; deterministic local verifier with keyword/contradiction detection |
| Decision report generation | ✅ **Production** | Trust report format with verification summary, evidence quality, contradictions, and clear status separation |
| Claim verification v2 | ✅ **Production** | Deterministic local verifier; supported/contradicted/unsupported/uncertain/needs_review statuses |
| Evidence resolver | ✅ **Production** | Workspace-scoped evidence reference resolution with isolation |
| Contradiction detection | ✅ **Production** | Pattern-based detection for metrics, status, risk conflicts |
| Evidence quality scoring | ✅ **Production** | Strong/moderate/weak/missing/contradicted labels per claim |
| Verification API | ✅ **Production** | Claim, execution, and workspace-level verification endpoints |
| Verification workflow nodes | ✅ **Production** | ClaimVerifierNode, ContradictionScanNode, VerificationSummaryNode |
| Evidence Synthesis workflow node | ✅ **Production** | AI-assisted evidence synthesis with optional auto-verification |
| Provider runtime | ✅ **Production** | Unified interface for fake, Ollama, OpenAI-compatible providers |
| Provider configuration | ✅ **Production** | Local file-based provider store with env-var API keys |
| Provider API | ✅ **Production** | Full CRUD, health checks, model listing, connection testing |
| Prompt templates | ✅ **Production** | Grounded templates with anti-hallucination instructions |
| Structured output parser | ✅ **Production** | Robust JSON/markdown/plain text parser |
| AI-assisted report draft | ✅ **Production** | Optional AI-assisted report summarizing with trust preservation |
| Demo workflows | ✅ **Production** | AI-Assisted Evidence Synthesis demo workflow |
| Trust report format | ✅ **Production** | Verification summary, evidence table, contradictions, recommended next actions |
| Local trust evaluation | ✅ **Production** | 53+ tests covering verification scenarios |
| Verification API client | ✅ **Production** | Frontend JS client methods for all verification and trust report endpoints |
| Claim Ledger verification UI | ✅ **Production** | Status badges, evidence quality, verify button, filter-by-status |
| Execution verification UI | ✅ **Production** | Verification summary panel with metrics and trigger actions |
| Workspace trust dashboard | ✅ **Production** | Trust health labels, metrics, recommended next actions |
| Trust report viewer | ✅ **Production** | Sectioned report display with Markdown and JSON export |
| Contradiction UI | ✅ **Production** | Contradiction scanning, listing, and detail views |
| Audit event wiring | ✅ **Production** | Verification/report actions emit scoped audit events |
| Observability metrics | ✅ **Production** | Verification and report duration/count/confidence metrics |
| Knowledge graph extraction | ✅ **Production** | Deterministic extraction from sentence patterns; JSON store |
| Ontology mapping | ✅ **Production** | Maps CSV columns to ontology concepts |
| CSV data profiling | ✅ **Production** | Profile company datasets with quality/detection stats |
| Insight/risk detection | ✅ **Production** | Deterministic detectors for missing data, quality, concentration, revenue risk |
| Orchestration dispatcher | ✅ **Production** | Bounded specialist agent dispatch with judge |
| War-room protocol | ✅ **Production** | Structured append-only artifacts for bounded agent context |
| Backend test suite | ✅ **Production** | 486+ passing tests; offline-capable |
| Provider abstraction | ✅ **Production** | OpenAI, Ollama, NVIDIA NIM, fake provider |
| Security scanner | ✅ **Production** | Secret scanning, redaction, policy checks |
| Workflow API endpoints | ✅ **Production** | Full CRUD for workflows, schedules, providers, reviews |
| Execution history API | ✅ **Production** | List, detail, delete endpoints with pagination |
| Execution detail API | ✅ **Production** | Node states, event timeline, review requests, metrics |
| Workflow versioning | ✅ **Production** | Version snapshots on create/update; list/get APIs |
| Review-gate pause/resume | ✅ **Production** | True DAG pause; approve/reject/resume via API |
| Workspace management | ✅ **Production** | CRUD workspaces; activate/deactivate; artifact counts |
| Persistent storage | ✅ **Production** | JSON stores under `.decision_system/`; survives restart |
| Docker Compose setup | ✅ **Production** | Backend + frontend services; persistent volume |

| Workflow node catalog | ✅ **Production** | Categorized palette: Core, Data, Evidence, AI, Verification, Review, Report, Utility |
| Node configuration panels | ✅ **Production** | Catalog hints, required field markers, provider warnings, safety warnings |
| Workflow validation | ✅ **Production** | Pre-run validation for required fields, disconnected nodes, unsafe nodes |
| Execution debugger | ✅ **Production** | Node status, elapsed time, collapsible inputs/outputs |
| Demo workflow templates | ✅ **Production** | Local Evidence Search, Evidence→AI Synthesis→Verify, Risk Review, Trust Report Generator, Data Profile |
| First-run onboarding | ✅ **Production** | Guided steps for workspace, data upload, provider, demo workflow |
| Provider selection UX | ✅ **Production** | Provider dropdown, required provider warnings, fake provider quick-select |
| Workflow import/export | ✅ **Production** | JSON export and import workflows |
| Workflow version visibility | ✅ **Production** | Version history display, saved state indicator |
| Empty/error state polish | ✅ **Production** | Helpful messages and next-action guidance |

## What is prototype-only

| Area | Status | Notes |
|------|--------|-------|
| Audit logging | ✅ **Production** | Verification/report actions emit audit events with workspace/execution/claim scope |
| Observability metrics | ✅ **Production** | Verification and report actions emit metrics for duration, counts, confidence |
| Claim ledger APIs | ✅ **Production** | JSON-backed durable claim store for workflow executions |
| Report export API | ✅ **Production** | Trust reports can be viewed in UI and exported as Markdown or JSON |
| Workspace export/import | 🟡 **Prototype** | Basic export exists; not fully tested |
| Connectors | 🟡 **Prototype** | Local file import works; stubs for remote exist |
| Provider experiments | 🟡 **Prototype** | Modules exist; not wired into main flow |
| Schedule manager | 🟡 **Prototype** | CRUD works; cron parser supports full syntax |
| Background scheduler | 🟡 **Prototype** | Uses asyncio; can block test cleanup |
| Webhook receiver | 🟡 **Prototype** | Works; not deeply tested |

## What is mock-only

| Area | Status | Notes |
|------|--------|-------|
| Workspace CRUD | ✅ **Live** | Mock fallback when backend unavailable |
| Data Sources upload | ✅ **Live** | Upload, parse, index via API; mock fallback |
| Evidence Search | ✅ **Live** | Backend evidence search; mock fallback |
| Provider Manager | ✅ **Live** | CRUD, health checks; mock fallback |
| Execution history | ✅ **Live** | Backend connected; mock fallback |
| Claim verification | ✅ **Live** | Backend verification; mock fallback |
| Trust Dashboard | ✅ **Live** | Backend connected; mock fallback |
| Report generation | ✅ **Live** | Backend report generation/export; mock fallback |
| Schedule management | ✅ **Live** | Backend CRUD; mock fallback |
| Review gates | ✅ **Live** | Backend review resolution; mock fallback |
| Workflow versions/diff | 🔴 **Mock** | Mock data when backend unavailable |

> **Note:** All features work in mock mode (no backend needed) or live mode
> (backed by FastAPI). The React app auto-detects backend availability.

## What is live-backend connected

| Area | Status | Notes |
|------|--------|-------|
| FastAPI server | ✅ **Live** | Created via `create_app()` in `api/app.py` |
| Health endpoint | ✅ **Live** | `GET /health` |
| Dashboard endpoint | ✅ **Live** | `GET /dashboard` returns dashboard data |
| Workflow CRUD | ✅ **Live** | Create, read, list, update, delete workflows |
| Workflow execution | ✅ **Live** | Execute workflow, get execution state |
| Execution history | ✅ **Live** | `GET /executions/history`, detail, delete |
| Workflow versions | ✅ **Live** | `GET /workflows/{id}/versions`, version detail |
| Schedule CRUD | ✅ **Live** | Create, read, update, delete, toggle, list schedules |
| Provider CRUD | ✅ **Live** | All provider routes work against backend store |
| Review gate management | ✅ **Live** | `GET /reviews`, `POST /reviews/{id}/resolve` |
| Execution resume | ✅ **Live** | `POST /executions/{id}/resume` with approve/reject |
| Webhook dispatch | ✅ **Live** | Webhook triggers match schedules and execute workflows |
| Workspace CRUD | ✅ **Live** | Basic workspace operations work |
| Workspace-scoped routes | ✅ **Live** | Workflows, executions, reviews, overview by workspace |
| Document management | ✅ **Production** | Upload, list, delete, parse, index, preview documents; supports PDF, DOCX, XLSX, CSV, TXT, MD, JSON |
| Report generation | ✅ **Live** | Generate and view reports |
| Ontology mapping | ✅ **Live** | Map and view ontology |
| Security scanning | ✅ **Live** | Secret scanning, redaction, policy checks |
| Observability data | ✅ **Live** | Metrics and trace endpoints |
| Connector management | ✅ **Live** | List connector types, import jobs |

## Local-first readiness

| Area | Status | Notes |
|------|--------|-------|
| Docker Compose startup | ✅ **Ready** | `docker compose up` starts backend + frontend |
| No cloud API keys required | ✅ **Ready** | Fake provider is default; no keys needed to start |
| Data stored under `.decision_system/` | ✅ **Ready** | All persistent data in one configurable directory |
| Data survives restart | ✅ **Ready** | JSON/SQLite stores persist across restarts |
| Frontend connects to local backend | ✅ **Ready** | nginx proxy in Docker; Vite proxy in dev mode |
| Local AI provider (Ollama) | ✅ **Ready** | Supported and documented |
| Offline CLI commands | ✅ **Ready** | All `decision-system` commands work offline |
| Provider setup screen | 🟡 **Partial** | Provider Manager exists; graceful no-key startup works |

## Not local-first ready yet

| Area | Notes |
|------|-------|
| PDF/DOCX/XLSX parsing | Only txt, md, csv, json supported |
| Vector search with fallback | Vector search requires Chroma; keyword fallback works without it |
| Workspace export/import | Exists in prototype; not fully reliable |
| Frontend Data Sources page | Basic implementation; needs real API connection for full demo |

## Known limitations

1. **Frontend requires npm build.** The React workflow builder needs `npm install && npm run build` before Docker Compose will serve it.
2. **Running all workflow engine tests together** can cause pytest-asyncio event loop issues. Run individual test files.
3. **CodeNode is disabled by default.** Set `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true` to enable (unsafe).
4. **PDF/DOCX/XLSX parsing** is not yet supported.
5. **Vector search** requires Chroma to have indexed data; keyword fallback works without it.
6. **Frontend Data Sources page** is functional but basic.

## Test commands

```bash
# All backend tests
python -m pytest -q

# Workflow engine API tests (67 tests)
python -m pytest tests/test_workflow_engine/test_api.py -q

# Core tests
python -m pytest tests/test_config.py tests/test_claim_ledger.py tests/test_cli.py -q

# Workflow engine unit tests
python -m pytest tests/test_workflow_engine/test_scheduler.py -q
python -m pytest tests/test_workflow_engine/test_stores.py -q
python -m pytest tests/test_workflow_engine/test_dag.py -q

# Frontend tests
cd web/workflow-builder
npm test
npm run build
```

## Local app commands

```bash
# Docker
docker compose up
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000

# Manual backend
python -m pip install -e ".[dev]"
decision-system serve-api --host 0.0.0.0 --port 8000

# Manual frontend (separate terminal)
cd web/workflow-builder
npm install
npm run dev
# Frontend: http://localhost:5173
```

## Next milestone

Continuing from v1.22

1. **PDF/DOCX/XLSX parsing support** — Broader file type coverage
2. **Frontend Data Sources page polish** — Rich data source management UI
3. **Workspace export/import** — Reliable backup/restore
4. **Frontend live-mode polish** — Wire mock-only components to real API
5. **Docker Compose v2** — Improved Docker startup and networking
