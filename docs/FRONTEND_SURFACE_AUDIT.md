# Frontend Surface Audit

> **Date:** 2026-06-23
> **Version:** 1.24.0-dev
> **Scope:** All frontend surfaces in the repository

---

## Summary

There are **two frontend surfaces** in this repository:

| Surface | Location | Served by Docker | Status |
|---------|----------|-----------------|--------|
| Legacy static UI | `web/` | No | **Deprecated** — v1.7 prototype mock-up |
| React Workflow Builder | `web/workflow-builder/` | Yes (port 3000) | **Main product UI** |

---

## Surface 1: Legacy Static UI (`web/`)

### Overview

A standalone HTML/CSS/JS single-page application at `web/index.html`. It is a
v1.7-era prototype that pre-dates the React app. It works entirely from mock
data in `web/mock-data/` (13 JSON files).

### Features

| Feature | Status | APIs Used |
|---------|--------|-----------|
| Dashboard | ✅ Mock-only | None (reads `mock-data/dashboard.json`) |
| Decision Brief | ✅ Mock-only | None (reads `mock-data/report.json`) |
| Data & Ontology | ✅ Mock-only | None (reads `mock-data/ontology.json`, `mock-data/data-profiles.json`) |
| War Room | ✅ Mock-only | None (reads `mock-data/war-room.json`) |
| Workflows | ✅ Mock-only | None (reads `mock-data/dashboard.json`) |
| Workspaces | ✅ Mock-only | None (reads `mock-data/dashboard.json`) |
| Data Sources | ✅ Mock-only | None (reads `mock-data/dashboard.json`) |
| Connectors | ✅ Mock-only | None (reads `mock-data/connectors.json`) |
| Security & Governance | ✅ Mock-only | None (reads `mock-data/security.json`) |
| Observability | ✅ Mock-only | None (reads `mock-data/observability.json`) |

### Assessment

- **All features are mock-only.** No backend integration.
- **88 helper functions** in `app.js` — no framework.
- Shows "v1.7 prototype" in the brand header.
- Navigates via `data-view` attributes and JS event handlers.
- **Not served by Docker.** The `docker-compose.yml` only serves the React app.
- **Not in active development.**
- Contains a "Workflows" nav item that links to the React app concept but is
  entirely mock data.

### What Should Be Migrated Into React

- The "Data Sources" page concept (file upload in legacy static UI).
- The "Data & Ontology" visualizations (could inspire React components).
- The "War Room" concept (bounded agent protocol display).

### Deprecation Plan

- Keep `web/` as-is for historical reference.
- Remove stale references from docs (e.g., "PDF unsupported" text).
- Do not link to it from the React app or Docker.
- Do not delete — some mock-data JSON files may inform future React mock data.

---

## Surface 2: React Workflow Builder (`web/workflow-builder/`)

### Overview

A **React 18 + React Flow** SPA at `web/workflow-builder/`. This is the main
product frontend, served by Docker on port 3000. It supports two modes:

- **Mock mode** (default) — works offline with simulated data in `mockData.js`
- **Live mode** — connects to the FastAPI backend at configured URL

### Architecture

```
web/workflow-builder/
├── src/
│   ├── main.jsx            — Entry point
│   ├── App.jsx             — Root component (961 lines)
│   ├── App.css             — Global styles
│   ├── api.js              — HTTP/WS client + mock fallback
│   ├── mockData.js         — Mock data for offline mode
│   ├── nodeTypes.js        — Node type registry
│   ├── templates.js        — Workflow templates
│   ├── workflowValidation.js — Validation logic
│   ├── setupTests.js       — Test setup
│   ├── components/         — 27 React components
│   ├── hooks/              — Custom hooks
│   └── styles/             — 10 CSS files
├── __tests__/              — 10 test files
├── dist/                   — Built output
├── Dockerfile              — Multi-stage build (Node build + nginx serve)
├── nginx.conf              — Reverse proxy to backend
├── vite.config.js          — Vite config with test settings
└── vitest.config.js        — Vitest config
```

### Current Features (Live Status)

| Feature | Status | APIs Used |
|---------|--------|-----------|
| Workflow Canvas (DAG editor) | ✅ Live | `GET /workflows/nodes`, `GET /workflows`, `POST/PUT /workflows` |
| Node Palette (30+ types) | ✅ Live | `GET /workflows/nodes` |
| Node Configuration Panel | ✅ Live | Local state |
| Workflow Execution | ✅ Live | `POST /workflows/{id}/execute`, WebSocket stream |
| Execution Panel (live events) | ✅ Live | WebSocket `/executions/{id}/stream` |
| Execution History | ✅ Live | `GET /executions/history` |
| Execution Compare | ✅ Live | Local state from history |
| Workflow Diff (versions) | ✅ Live | `GET /workflows/{id}/versions` |
| Schedule Manager | ✅ Live | CRUD `/schedules` |
| Provider Manager | ✅ Live | CRUD `/providers` |
| Review Panel | ✅ Live | `GET /reviews`, `POST /reviews/{id}/resolve` |
| Trust Dashboard | ✅ Live | Verification + contradiction + report APIs |
| Claim Verification | ✅ Live | `POST /claims/{id}/verify` |
| Report Generation | ✅ Live | `POST /executions/{id}/report`, `GET /reports/{id}` |
| Template Dialog | ✅ Live | Local templates |
| Theme Toggle | ✅ Live | localStorage |
| Shortcuts Help | ✅ Live | Local |
| Onboarding Panel | ✅ Mock-only | Local state |
| Validation Dialog | ✅ Live | Local validation |

### What Is Missing (Not Yet in React App)

| Feature | Where It Lives | Priority |
|---------|---------------|----------|
| Workspace selector | Not implemented anywhere | 🔴 High |
| Data Sources page | Legacy `web/` (mock-only) | 🔴 High |
| Evidence Search UI | Not implemented anywhere | 🟡 Medium |
| Claim Ledger | Trust Dashboard has partial coverage | 🟡 Medium |
| Reports section | Trust Dashboard has partial coverage | 🟡 Medium |
| Workspace context sharing | Not implemented | 🔴 High |

### What Is Mock-Only in React App

- **OnboardingPanel** — hardcoded content, no backend API
- **Execution event streaming** — falls back to simulated events in mock mode
- **Provider health checks** — returns fake "ok" in mock mode

### API Proxy Configuration

The nginx config proxies these paths to `backend:8000`:
- `/workflows`, `/executions`, `/reviews`, `/schedules`, `/providers`
- `/webhook`, `/health`, `/workspaces`, `/claims`, `/reports`
- `/documents`, `/observability`, `/security`, `/connectors`
- `/docs`, `/openapi.json`
- WebSocket upgrades for `/executions/`

SPA fallback: all other routes serve `index.html`.

---

## Docker Serving Summary

The `docker-compose.yml` serves:

| Service | Image | Exposed Port | Content |
|---------|-------|-------------|---------|
| `backend` | Dockerfile (root) | 8000 | FastAPI Python backend |
| `frontend` | `web/workflow-builder/Dockerfile` | 3000 | React Workflow Builder SPA |

The legacy `web/` static UI is **not** served by Docker.

---

## Backend API Surface

The FastAPI backend provides routes under these path prefixes (all live):

| Path Prefix | Purpose | Live Status |
|-------------|---------|-------------|
| `/workspaces` | Workspace CRUD + overview | ✅ |
| `/workflows` | Workflow CRUD + execution | ✅ |
| `/executions` | Execution history + detail | ✅ |
| `/providers` | Provider CRUD + health checks | ✅ |
| `/schedules` | Schedule CRUD | ✅ |
| `/claims` | Claim management + verification | ✅ |
| `/reports` | Report generation + export | ✅ |
| `/reviews` | Review gate CRUD | ✅ |
| `/health` | Health check | ✅ |
| `/docs` | OpenAPI docs | ✅ |

---

## Migration Priority

1. **Workspace selector** — needed by all other sections for context
2. **Data Sources page** — core user flow for uploading/parsing/indexing files
3. **Evidence Search panel** — needed for verifying search workflow nodes
4. **Provider Manager integration** — already exists as panel, needs main nav
5. **Execution History** — already exists as panel, needs main nav
6. **Claim Ledger** — needs dedicated page (partial in Trust Dashboard)
7. **Trust Dashboard** — already exists as panel, needs main nav
8. **Reports section** — needs dedicated page (partial in Trust Dashboard)
9. **Local demo flow** — guided demo from workspace to report export

---

## Key Metrics

| Metric | Legacy `web/` | React `workflow-builder/` |
|--------|---------------|--------------------------|
| Framework | None (vanilla JS) | React 18 + React Flow 11 |
| Lines of JS/JSX | ~3,500 (app.js + mock data) | ~5,000 (src/ + tests) |
| CSS files | 1 | 11 |
| Components | 0 | 27 |
| Tests | 0 | 10 files |
| Docker support | No | Yes |
| Backend integration | None | Full (via nginx proxy) |
| Mock data | 13 JSON files | 1 JS module |
| Build step | No | Vite |
| Last active update | v1.7 era | Active |
