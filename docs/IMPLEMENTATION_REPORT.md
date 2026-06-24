# Implementation Report — v1.24 Single App Integration

> **Date:** 2026-06-23
> **Package version:** 1.24.0-dev
> **Previous milestone:** v1.23.1 — Finish Document Ingestion Wiring + Test Reliability

---

## Summary

v1.24 turns the project from a collection of powerful modules into **one coherent
local-first app experience**. The React Workflow Builder is now the clear main
product UI with app-wide sidebar navigation, a workspace selector, data sources
management, evidence search, claim verification, trust reports, and a guided
demo flow — all accessible from a single React application.

## Version

- `src/decision_system/__init__.py`: `1.24.0-dev`
- `pyproject.toml`: `1.24.0-dev`
- `/health` endpoint returns `1.24.0-dev`

## Files Changed

### Backend (Python)
| File | Change |
|------|--------|
| `src/decision_system/__init__.py` | Version `1.23.1-dev` → `1.24.0-dev` |
| `pyproject.toml` | Version `1.23.1-dev` → `1.24.0-dev` |
| `src/decision_system/models.py` | Added optional `workspace_id` field to `EvidenceChunk` |
| `src/decision_system/rag/vector_store.py` | Include `workspace_id` in Chroma metadata |
| `src/decision_system/rag/retriever.py` | Added `workspace_id` parameter with Chroma `where` filter |
| `src/decision_system/verification/verifier.py` | Pass `workspace_id` to `retrieve_evidence` |
| `src/decision_system/api/routes_data_sources.py` | Pass `workspace_id` to `EvidenceChunk` (was silently dropped) |

### Frontend (React)
| File | Change |
|------|--------|
| `web/workflow-builder/src/App.jsx` | App shell with sidebar nav, workspace state, section routing |
| `web/workflow-builder/src/App.css` | ~350 lines of new styles for sidebar, sections, data sources, etc. |
| `web/workflow-builder/src/api.js` | Added workspace, data source, and evidence search API functions |
| `web/workflow-builder/src/components/AppNav.jsx` | **New** — Sidebar navigation with 10 sections |
| `web/workflow-builder/src/components/WorkspaceSelector.jsx` | **New** — Create/select/manage workspaces |
| `web/workflow-builder/src/components/DataSourcesPage.jsx` | **New** — Upload, parse, index, preview, profile data sources |
| `web/workflow-builder/src/components/EvidenceSearchPage.jsx` | **New** — Search evidence with filters |
| `web/workflow-builder/src/components/ClaimLedgerPage.jsx` | **New** — Verify claims, scan contradictions |
| `web/workflow-builder/src/components/ReportsPage.jsx` | **New** — View and export trust reports |
| `web/workflow-builder/src/components/DemoFlow.jsx` | **New** — Guided 6-step local demo |
| `web/workflow-builder/src/components/SettingsPage.jsx` | **Rewritten** — Workspace management + about |

### Docs
| File | Change |
|------|--------|
| `docs/FRONTEND_SURFACE_AUDIT.md` | **New** — Frontend surface map |
| `docs/CURRENT_STATE.md` | Updated mock-only/live tables, version, milestone |
| `docs/IMPLEMENTATION_REPORT.md` | Updated version, milestone |
| `CHANGELOG.md` | Added v1.24.0 section with all changes |

## Frontend Integration Changes

- **App shell navigation**: Sidebar with 10 sections (Demo Flow, Workflow Builder,
  Data Sources, Evidence Search, Execution History, Claim Ledger, Trust Dashboard,
  Reports, Providers, Settings)
- **Backend mode indicator**: Sidebar shows Mock/Live/Offline status
- **Workspace context**: Shared across all sections via React state

## Workspace Integration

- Workspace selector in Settings page
- Create, select, and manage workspaces
- Stats display (sources, chunks, claims, reports)
- Workspace shared across Data Sources, Claims, Trust, Reports sections

## Data Sources UI

- Drag-and-drop + browse file upload
- Supported types: PDF, DOCX, XLSX, CSV, JSON, TXT, MD
- Parse → Index workflow with status indicators
- Chunks preview per source
- CSV/XLSX/JSON profile view (schema, types, missing values)
- Delete with confirmation

## Evidence Search UI

- Query input with file type filter
- Configurable result limit (5/10/20)
- Results with source name, file type icon, text preview, metadata
- File-specific metadata: page number (PDF), sheet name (XLSX), block type (DOCX)
- Copy evidence reference ID

## Provider UI

- Provider Manager is reachable from the sidebar navigation
- Add/configure fake, Ollama, or OpenAI-compatible providers
- Test connection, set default provider

## Execution/Claims/Reports UI

- Execution History section (wraps existing component)
- Claim Ledger with verification summary cards, verify-all, contradiction scan
- Trust Dashboard section (wraps existing component)
- Reports section with viewing and markdown export

## Demo Flow

- 6-step guided demo: Create workspace → Add sample data → Configure fake provider
  → Load demo workflow → Run → Open trust report
- Works entirely without cloud API keys
- Step-by-step progression with completion tracking

## Legacy Web Status

- `web/` (static HTML prototype) kept as-is but labeled as deprecated
- Deprecation notice added to `web/index.html`
- Docker serves only the React workflow builder
- Docs clearly state React app is the main product UI

## Tests Passing

### Frontend
```
10 test files, 35 tests passed
npm run build — builds successfully
```

### Backend (targeted)
```
test_data_sources: 60 passed
test_verification: 68 passed
test_providers: 48 passed
test_workflow_engine/test_api.py: all passed
```

## Commands Run

```bash
python -m pytest tests/test_data_sources -q
python -m pytest tests/test_verification -q
python -m pytest tests/test_providers -q
python -m pytest tests/test_workflow_engine/test_api.py -q
cd web/workflow-builder && npm test
cd web/workflow-builder && npm run build
```

## Known Limitations

- Docker smoke test not run (requires Docker daemon)
- Some backend API endpoints require workspace context
- Demo flow uses mock data emulation when backend is unavailable
- Execution History, Trust Dashboard, and Provider Manager are wrapped existing
  components — deeper integration may be needed in future milestones
- Chroma re-indexing required for existing data to have workspace_id metadata

## Recommended Next Milestone

**v1.25 — End-to-End Demo Hardening + Local Beta Release Prep**

Focus areas:
- End-to-end demo flow polish (guided UX, error handling, empty states)
- Execution History deep integration (filters, search, compare)
- Claim Ledger full implementation (claim list with CRUD, evidence linking)
- Provider Manager UI polish
- Docker smoke test automation
- Frontend test expansion (new section tests, interaction tests)
- Performance optimization (code splitting, lazy loading for large components)
- Local beta release readiness
