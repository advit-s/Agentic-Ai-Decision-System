# Current State — Agentic Decision System

> **Last updated:** 2026-06-23
> **Package version:** 1.19.0-dev
> **Previous milestone:** v1.18 — Local product-loop hardening
> **Current milestone:** v1.19 — Local Data Sources + Evidence Intelligence Layer
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
| Claim ledger | ✅ **Production** | Create/store/query claims; statuses (supported, contradicted, unsupported, uncertain) |
| Verifier | ✅ **Production** | Check claims against evidence; deterministic fake-LLM mode by default |
| Decision report generation | ✅ **Production** | Renders from ledger state; Markdown output with citations |
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

## What is prototype-only

| Area | Status | Notes |
|------|--------|-------|
| Audit logging | 🟡 **Prototype** | Basic audit for workflow execution; more events needed |
| Observability metrics | 🟡 **Prototype** | Modules exist; not consistently wired to normal flows |
| Claim ledger APIs | 🟡 **Prototype** | Claims exist in-memory per run; no persistent claim store yet |
 | Claim ledger APIs | ✅ **Live** | JSON-backed durable claim store for workflow executions |
| Report export API | 🟡 **Prototype** | Reports can be generated; local file export not finalized |
| Workspace export/import | 🟡 **Prototype** | Basic export exists; not fully tested |
| Connectors | 🟡 **Prototype** | Local file import works; stubs for remote exist |
| Provider experiments | 🟡 **Prototype** | Modules exist; not wired into main flow |
| Schedule manager | 🟡 **Prototype** | CRUD works; cron parser supports full syntax |
| Background scheduler | 🟡 **Prototype** | Uses asyncio; can block test cleanup |
| Webhook receiver | 🟡 **Prototype** | Works; not deeply tested |

## What is mock-only

| Area | Status | Notes |
|------|--------|-------|
| Frontend live-mode | 🔴 **Mock** | Frontend uses mock data by default; can switch to live backend |
 | Frontend live-mode | ✅ **Live** | Auto-detects backend on localhost:3000 (Docker); mock still available |
| Execution history UI | 🔴 **Mock** | ExecutionHistory component uses mock data without live backend |
| Execution detail UI | 🔴 **Mock** | ExecutionPanel expects real detail endpoint (exists now) |
| Claim ledger panel | 🔴 **Mock** | Panel exists; requires claim API endpoints |
| Report panel | 🔴 **Mock** | Not yet connected to report generation API |
| Execution compare | 🔴 **Mock** | Component exists; mock data only |
| Workflow diff | 🔴 **Mock** | Component exists; mock data only |

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
| Document management | ✅ **Live** | Upload, list, delete documents |
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

1. **Frontend requires npm build.** The React workflow builder needs `npm install && npm run build` before Docker Compose will serve it. Until built, the simpler static frontend at `web/` is served instead.
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

Continuing from v1.19, the next areas of focus are:

1. **PDF/DOCX/XLSX parsing support** — Broader file type coverage
2. **Frontend Data Sources page polish** — Rich data source management UI
3. **Workspace export/import** — Reliable backup/restore
4. **Frontend live-mode polish** — Wire mock-only components to real API
5. **Docker Compose v2** — Improved Docker startup and networking
