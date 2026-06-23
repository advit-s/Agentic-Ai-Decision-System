# Implementation Report — Local-First Agentic Decision System

> **Date:** 2026-06-23
> **Package version:** 1.18.0-dev
> **Previous milestone:** v1.17 — Local-first foundation
> **Current milestone:** v1.18 — Local product-loop hardening

---

## v1.18 — Local product-loop hardening

### Files changed
| File | Change |
|------|--------|
| `pyproject.toml` | Version bumped from 1.16.2 to 1.18.0-dev |
| `src/decision_system/__init__.py` | Version bumped to 1.18.0-dev |
| `src/decision_system/workflow_engine/models.py` | Added `workspace_id` to `WorkflowDefinition` and `ExecutionContext` |
| `src/decision_system/workflow_engine/engine/executor.py` | Added `workspace_id` parameter; emit `workflow_started` event; fixed `completed_at` for non-terminal states |
| `src/decision_system/workflow_engine/engine/events.py` | Added `workflow_started` to event type literal |
| `src/decision_system/workflow_engine/api.py` | Persist execution events; claim API validation; workspace overview claims; workspace_id in workflow create/update |
| `src/decision_system/workflow_engine/stores/claim_store.py` | Extended `add_claim()` with status, confidence, evidence_ids, review fields |
| `src/decision_system/workflow_engine/nodes/specialist/review_gate.py` | Added `workspace_id` to review records |
| `src/decision_system/workflow_engine/stores/base.py` | Removed duplicate abstract `delete()` method |
| `web/workflow-builder/nginx.conf` | Listen on port 80; added WebSocket `^~` prefix; added missing proxy routes |
| `web/workflow-builder/src/api.js` | Auto-detect localhost:3000; normalised response shapes; added `getBackendMode()` |
| `web/workflow-builder/src/components/WorkflowToolbar.jsx` | Enhanced status badge with local/mock/unavailable labels |
| `scripts/local-smoke-test.sh` | New smoke test script for Docker stack verification |
| `CHANGELOG.md` | Added v1.17 and v1.18 sections |
| `docs/CURRENT_STATE.md` | Updated version, claim store status, frontend live-mode status |

### Bugs fixed
- nginx listens on container port 80, matching Docker Compose port mapping (host 3000 → container 80)
- Frontend auto-detects local backend on localhost:3000 (was only checking ports 8000/8001/8080)
- `completed_at` no longer set on workflows that are still `awaiting_review` (multiple review gates)
- Duplicate abstract `delete()` method removed from `ExecutionStore`
- Execution events now persisted to JSON store (was only in-memory for WebSocket streaming)
- `workflow_started` event now emitted at execution beginning
- Claim API validates `claim_text` not empty and `claim_type` is valid
- Workspace overview includes claim counts and evidence coverage score

### Tests run
```text
tests/test_workflow_engine/test_api.py       — 67 passed
tests/test_workflow_engine/test_executor.py   — passed
tests/test_workflow_engine/test_stores.py     — passed
tests/test_workflow_engine/test_nodes.py      — passed
tests/test_workflow_engine/test_scheduler.py  — 50 passed
tests/test_workflow_engine/ (all)             — 382 passed, 1 skipped (CodeNode disabled)
```

### Commands verified
```text
python -m pytest tests/test_workflow_engine/ -q   # 382 passed, 1 skipped
git diff --check                                    # clean
node --check web/workflow-builder/src/api.js        # syntax OK
```

### Known remaining gaps
- Frontend `npm install` requires network access (sandboxed environment)
- Full test suite (`tests/`) has some slow tests that time out when run together
- Chroma vector store data not yet under `.decision_system/`
- Report export does not yet save to local files
- Legacy decision-run claim ledger is separate from workflow execution claim store
- No WebSocket stream event persistence verification test yet

---

## Summary

This report documents the work done to turn the half-built prototype into a
coherent, reliable, local-first MVP for a **self-hosted Company Intelligence
Automation System** (n8n-style). The work spanned 15 phases targeting
persistence, API completeness, safety, documentation, and local-first startup.

---

## What Changed

### New Files

| File | Purpose |
|------|---------|
| `web/workflow-builder/Dockerfile` | Multi-stage Docker build: Node build → nginx serve |
| `web/workflow-builder/nginx.conf` | nginx config: API proxy to backend, WebSocket support, SPA fallback |
| `src/decision_system/workflow_engine/stores/claim_store.py` | JSON-backed persistent claim store with list/filter/summary/CRUD |
| `docs/LOCAL_FIRST_SETUP.md` | Complete local-first setup guide (Docker, manual, providers, troubleshooting) |
| `docs/IMPLEMENTATION_REPORT.md` | This report |

### Modified Files

| File | Change |
|------|--------|
| `docker-compose.yml` | Added `frontend` service (nginx on port 3000), named `backend` for inter-service networking, persistent volume |
| `web/workflow-builder/vite.config.js` | Added `host: '0.0.0.0'` for Docker compatibility |
| `src/decision_system/workflow_engine/api.py` | Added workspace-scoped routes (`GET .../workflows`, `.../executions`, `.../reviews`, `.../overview`), claim API routes (`GET/POST/DELETE /claims`, `GET .../claims`, `GET .../claim-summary`), integrated claim store into execution detail |
| `src/decision_system/workflow_engine/nodes/builtin/flow_nodes.py` | CodeNode disabled by default; requires `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true` |
| `src/decision_system/workflow_engine/scheduler/triggers.py` | Added `_parse_cron_field()` supporting step expressions (`*/30`), ranges (`1-5`), comma lists (`0,30`); updated `_cron_matches()` for set-based matching |
| `src/decision_system/models.py` | Extended `Claim` model with `workspace_id`, `execution_id`, `workflow_id`, `node_id`, `review_required`, `review_status`, `metadata` |
| `docs/CURRENT_STATE.md` | Updated all status tables; added local-first readiness, not-ready sections, test commands, next milestone |
| `tests/test_workflow_engine/test_api.py` | Fixed placeholder resume test (501→409); replaced CodeNode with input_text in review-gate tests |
| `tests/test_workflow_engine/test_nodes.py` | Added `test_disabled_by_default` for CodeNode; updated existing tests to set enable env var |

### Previously Completed (by earlier agents)

- Repository stabilization (`.gitignore`, `__pycache__` cleanup, conftest monkey-patch)
- Durable workflow API storage (`.decision_system/` via `DECISION_SYSTEM_DATA_DIR`)
- Execution history/detail/version endpoints (full CRUD + pagination)
- True review-gate pause/resume (DAG stops, API approve/reject, 7 tests)
- Workspace CRUD (create, list, activate)
- Provider CRUD (create, read, update, delete, check, set default)
- Schedule CRUD (create, read, update, delete, toggle, list)
- CLI commands (index, ask, extract-graph, profile-data, etc.)
- React workflow builder frontend (22 components, React Flow canvas)

---

## Major Features Implemented

### 1. Local-First Docker Compose

```yaml
services:
  backend:    # FastAPI on :8000
  frontend:   # nginx serving React on :3000
volumes:
  decision_data:  # maps to .decision_system/
```

- One-command startup: `docker compose up`
- Data persists across restarts
- nginx proxies API calls from frontend to backend
- WebSocket support for execution event streaming

### 2. Workspace-Scoped API Routes

- `GET /workspaces/{id}/workflows` — filter workflows by workspace
- `GET /workspaces/{id}/executions` — filter executions by workspace
- `GET /workspaces/{id}/reviews` — filter reviews by workspace
- `GET /workspaces/{id}/overview` — summary with counts of workflows, executions,
  reviews, schedules, pending reviews
- URL param `_all` returns items across all workspaces

### 3. Persistent Claim Store

- JSON-backed store in `.decision_system/workflow_engine/claims/`
- Each claim stored as individual JSON file + index for listing
- Full CRUD: create, read, list, delete
- Filtering by `workspace_id`, `execution_id`, `workflow_id`
- `summary()` method returns status breakdown + evidence coverage score
- Survives store re-instantiation (proven via test)
- API endpoints:
  - `GET /workspaces/{id}/claims`
  - `GET /executions/{id}/claims`
  - `GET /claims/{id}`
  - `POST /claims`
  - `DELETE /claims/{id}`
  - `GET /executions/{id}/claim-summary`

### 4. Claim Model Extension

The `Claim` model now includes:
```python
workspace_id     # Link to workspace
execution_id     # Link to workflow execution
workflow_id      # Link to workflow definition
node_id          # Link to source node
review_required  # Flag for human review
review_status    # Review gate status
metadata         # Extensible key-value store
```

### 5. Execution Detail → Claim Integration

Execution detail endpoint (`GET /executions/{id}/detail`) now returns:
- `claim_refs` — full claim list for the execution
- `claim_summary` — status breakdown (supported, contradicted, unsupported, etc.)

### 6. CodeNode Safety

- **Disabled by default** — raises `RuntimeError` with clear message
- Enable via `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true`
- Test covers both disabled and enabled states
- UI should mark node as unsafe/disabled

### 7. Cron Parser Enhancement

Before: Only `*` (wildcard) and exact digits (`9`)
After: Full cron field support:
- `*` — wildcard (all values)
- `N` — exact match (`9` = 9th minute/hour)
- `*/N` — step expression (`*/30` = every 30 units)
- `N-M` — range (`1-5` = Monday-Friday for day-of-week)
- `N,M,O` — comma list (`0,30` = at 0 and 30)
- Combined expressions like `*/30 9-17 * * 1-5`

### 8. Documentation

- **`docs/LOCAL_FIRST_SETUP.md`** — Complete guide with:
  - Docker Compose quick start
  - Manual development setup
  - Data storage structure
  - AI provider setup (Ollama, OpenAI-compatible, OpenAI API)
  - Testing commands
  - CLI reference
  - Architecture diagram
  - Troubleshooting
- **`docs/CURRENT_STATE.md`** — Updated with:
  - Production/prototype/mock/live-backend status tables
  - Local-first readiness section
  - Known limitations
  - Test commands and next milestone

---

## Storage Architecture

All persistent data lives under `.decision_system/`:

```text
.decision_system/
├── workflow_engine/
│   ├── workflows/       # Workflow JSON definitions
│   ├── executions/      # Execution states (survive restart)
│   ├── versions/        # Workflow version snapshots
│   ├── claims/          # Claim records (NEW — persistent)
│   ├── schedules/       # Schedule definitions
│   └── events/          # Execution event timelines
├── runs/                 # Decision report runs
├── reviews/              # Review gate records
├── audits/               # Audit event logs
├── providers.json        # Provider configurations
└── workspaces/           # Workspace data
```

Key: No `tempfile.mkdtemp()` usage for live API storage.

---

## API Endpoints

### New Endpoints Added

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/workspaces/{id}/workflows` | Workspace-scoped workflow list |
| GET | `/workspaces/{id}/executions` | Workspace-scoped execution list |
| GET | `/workspaces/{id}/reviews` | Workspace-scoped review list |
| GET | `/workspaces/{id}/overview` | Workspace summary counts |
| GET | `/workspaces/{id}/claims` | Workspace-scoped claim list |
| GET | `/executions/{id}/claims` | Execution-scoped claim list |
| GET | `/executions/{id}/claim-summary` | Claim status summary for execution |
| GET | `/claims/{id}` | Single claim detail |
| POST | `/claims` | Create a new claim |
| DELETE | `/claims/{id}` | Delete a claim |

### Existing Endpoints Verified

| Method | Path | Status |
|--------|------|--------|
| GET | `/health` | ✅ Live |
| GET | `/workflows` | ✅ Live |
| POST | `/workflows` | ✅ Live |
| GET | `/workflows/{id}` | ✅ Live |
| PUT | `/workflows/{id}` | ✅ Live |
| DELETE | `/workflows/{id}` | ✅ Live |
| POST | `/workflows/{id}/execute` | ✅ Live |
| GET | `/executions/history` | ✅ Live |
| GET | `/executions/{id}` | ✅ Live |
| GET | `/executions/{id}/detail` | ✅ Live (now includes claim data) |
| DELETE | `/executions/history/{id}` | ✅ Live |
| POST | `/executions/{id}/resume` | ✅ Live |
| GET | `/workflows/{id}/versions` | ✅ Live |
| GET | `/workflows/{id}/versions/{vid}` | ✅ Live |
| GET | `/reviews` | ✅ Live |
| POST | `/reviews/{id}/resolve` | ✅ Live |
| GET | `/schedules` | ✅ Live |
| POST | `/schedules` | ✅ Live |
| GET | `/providers` | ✅ Live |
| POST | `/providers` | ✅ Live |
| POST | `/providers/{name}/check` | ✅ Live |

---

## Test Results

```
251 passed across all test files
0 failed
```

### Test Breakdown

| Test File | Count | Status |
|-----------|-------|--------|
| `test_api.py` | 67 | ✅ Pass |
| `test_scheduler.py` | 76 | ✅ Pass |
| `test_dag.py` | 13 | ✅ Pass |
| `test_executor.py` | 15 | ✅ Pass |
| `test_nodes.py` | 20 | ✅ Pass |
| `test_models.py` | 8 | ✅ Pass |
| `test_stores.py` | 8 | ✅ Pass |
| `test_trigger_nodes.py` | 1 | ✅ Pass |
| `test_config.py` | 2 | ✅ Pass |
| `test_claim_ledger.py` | 5 | ✅ Pass |
| `test_cli.py` | 36 | ✅ Pass |

### Hygiene Check

```
9 passed, 3 warnings (__pycache__, .pytest_cache, .decision_system/ — all expected)
```

---

## Verified Behaviors

### CodeNode Safety
- **Disabled by default:** `RuntimeError` with clear message
- **Enabled:** `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true` — works correctly
- Tests cover both states

### Cron Parser
- `* * * * *` → matches any time
- `*/30 * * * *` → matches every 30 minutes
- `0 9 * * 1-5` → matches weekdays at 9am
- `0,30 * * * *` → matches at 0 and 30 minutes
- `*/30 9-17 * * 1-5` → combined step + range

### Claim Store
- Create, read, list, delete all work
- Filtering by workspace_id, execution_id works
- Summary shows status distribution and coverage score
- **Persistence proven:** Re-initializing store reads previous data
- Workspace-only and execution-only filtering works independently

### Workspace Routes
- All four workspace-scoped endpoints return valid JSON
- Overview endpoint returns accurate counts
- `_all` wildcard returns items across all workspaces

### Review Gate Pause/Resume
- 7 dedicated tests pass
- DAG executor stops at review gates
- Approval resumes execution
- Rejection blocks downstream nodes

---

## Known Remaining Gaps

### 1. Frontend Build (Requires Network)
The React frontend at `web/workflow-builder/` requires `npm install` to download
dependencies from `registry.npmjs.org`. This cannot run in an offline sandbox.
To build:

```bash
cd web/workflow-builder
npm install
npm run build
```

After building, `docker compose up` serves the frontend at `http://localhost:3000`.

### 2. Full Audit/Observability Wiring
Currently only workflow execution emits audit events. The following actions
need audit wiring:
- Review approve/reject/resume
- Report export
- Document index
- Provider config changes
- Workspace CRUD

The audit framework exists (`src/decision_system/security/audit.py`) but not
all call sites are wired.

### 3. Vector Store Data Location
Chroma vector store data is stored at its own default location, not under
`.decision_system/`. A future task should configure Chroma's `persist_directory`
to `.decision_system/vector_store/`.

### 4. Workspace Export/Import
Basic export exists in `src/decision_system/storage/export_import.py` but is
not fully reliable for all artifact types.

### 5. Workflow Builder Mock Data
The React frontend defaults to mock data. Live mode requires setting the
`wfBuilderApiBaseUrl` localStorage key to `http://localhost:8000`.

---

## Commands to Run

### Backend Tests
```bash
python -m pytest -q
```

### Repo Hygiene
```bash
decision-system check-hygiene
```

### Local App (Manual)
```bash
python -m pip install -e ".[dev]"
decision-system serve-api --host 0.0.0.0 --port 8000
```

### Local App (Docker)
```bash
docker compose up
# Then build frontend first:
cd web/workflow-builder && npm install && npm run build
# Or use the Vite dev server:
cd web/workflow-builder && npm install && npm run dev
```

---

## Recommended Next Tickets

1. **Wire audit events** — Add audit logging to review resolve, report export,
   document index, provider changes, workspace CRUD
2. **Move Chroma data** — Configure `persist_directory` to `.decision_system/vector_store/`
3. **Frontend build CI** — Add GitHub Action to build frontend and verify
4. **Workspace export/import** — Reliable backup/restore for all artifact types
5. **Frontend live-mode polish** — Update React components to use real API
   responses instead of mock data
6. **Observability dashboards** — Wire existing metrics modules to normal flows
7. **CodeNode sandbox** — Replace `exec()` with restricted runner (limited builtins,
   no filesystem, timeout, audit)
