# AGENTS.md - Agent Instructions for the Agentic Decision System

This file is for coding agents (Codex, Claude Code, and similar) who modify this
repository. Read it before changing code, docs, or tests.

## Project Purpose

This is a **Company Intelligence Engine** - a local-first, self-hosted application
that uses company documents and data to produce evidence-backed decision reports.
It has a **single React SPA** (`web/workflow-builder/`) as the main product UI
alongside a backend FastAPI server and CLI tools. It ingests PDF/DOCX/XLSX/MD/TXT/CSV/JSON
files (with OCR for scanned documents), indexes them in a local Chroma vector store,
runs bounded LangGraph workflows, extracts claims, verifies them, and produces cited
Markdown reports. It manages workspace-scoped data, extracts entities/relationships
into a knowledge graph, profiles datasets, maps columns to an ontology, detects
patterns/vulnerabilities, and runs a bounded war-cabinet agent context protocol.

The product is offline-capable, testable without API keys, and runs locally via
Docker Compose or manual setup.

## Architecture Summary

```text
Workspace-scoped data -> chunker -> Chroma -> retriever -> LangGraph workflow:
  retrieve_evidence -> technical_analyst -> risk_analyst -> claim_extraction ->
  verifier -> report_writer -> Markdown Decision Report

PDF/DOCX/XLSX/Images -> parser/OCR -> text -> chunks -> Chroma

company_docs/ -> deterministic graph extractor -> .decision_system/graph/

company_data/ -> CSV profiler -> .decision_system/data_profiles/

.data stores + graph + ontology + insights + orchestration -> context builder

Business question -> HigherContext -> AgentDispatchSpec -> CommonWorkspace
  -> deterministic specialist artifacts -> deterministic judge -> persisted run
```

Key sub-packages: `rag/`, `graph/`, `ledger/`, `reports/`, `graphing/`,
`data_catalog/`, `data_sources/`, `ontology/`, `insights/`, `orchestration/`,
`war_room/`, `evals/`, `workflow_engine/`, `api/`, `verification/`,
`providers/`, `storage/`.

Frontend: `web/workflow-builder/` — React 18 + React Flow SPA with 10 sections:
Demo Flow, Workflow Builder, Data Sources, Evidence Search, Execution History,
Claim Ledger, Trust Dashboard, Reports, Providers, Settings.

## Non-Negotiable Rules

1. **Fake/offline mode is the default.** `DECISION_PROVIDER=fake`. All demos and
   tests must pass without a real API key.
2. **React SPA is the main UI.** The `web/workflow-builder/` React app is the
   primary product UI. The legacy `web/` static prototype is preserved as a
   historical reference only. Core logic remains backend/API owned — the SPA
   is a consumer of the API, not the decision engine itself.
3. **Local JSON/SQLite storage is fine.** Use `.decision_system/` for persistent
   workspace data, graph stores, provider configs, and runtime state. No external
   database (PostgreSQL, MySQL) or ORM is approved. No auth system (JWT, OAuth,
   RBAC) unless explicitly planned.
4. **No real external API calls in tests.** Tests must pass offline using the
   fake provider or mocked endpoints.
5. **No unbounded agent chat.** War-cabinet and workflows use structured,
   append-only artifacts — not chat transcripts.
6. **Final reports must remain evidence/ledger/context grounded.** Claims go
   through the claim ledger. The report writer renders from ledger state, not
   raw agent prose.
7. **Generated state stays out of commits.** `.decision_system/`, `__pycache__/`,
   `.pytest_cache/`, `evals/results/*.json`, `company_data/imported_*`, and
   `node_modules/` are generated or local. They must remain untracked.
8. **Tests are mandatory.** Every feature or fix ships with tests.
9. **Agent instructions are balanced.** Fix small and medium issues directly.
   Escalate only when a change is large enough to warrant a written patch plan.
10. **Workspace isolation is required.** All operations must respect workspace
    boundaries. Data sources, evidence, claims, providers, workflows, and reports
    are scoped to a workspace.
11. **Evidence references are mandatory.** Every extracted fact, entity,
    relationship, risk, or metric must include source evidence IDs. Facts without
    evidence must be marked `unverified`.

## Commands

```bash
# Python virtual environment (always use this)
python -m venv .venv && source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate                              # Windows
python -m pip install -e ".[dev]"

# Frontend
cd web/workflow-builder && npm install && npm run build  # Build React SPA
cd web/workflow-builder && npm run dev                   # Dev server (Vite)

# Install (editable with dev extras)
python -m venv .venv && .venv\Scripts\activate   # Windows
python -m venv .venv && source .venv/bin/activate # macOS/Linux
python -m pip install -e ".[dev]"

# Tests (gating step - run before claiming done)
python -m pytest -q

# Smoke commands (offline, no API key needed)
decision-system index
decision-system inspect-index
decision-system ask "Should we migrate billing?"

# Docker (recommended for full demo)
docker compose up --build
# Open http://localhost:3000

# Backend API server
decision-system serve-api --host 0.0.0.0 --port 8000

# Data pipeline
decision-system init-data-catalog
decision-system seed-demo-data --force
decision-system profile-data
decision-system detect-patterns

# Graph / ontology / orchestration / war-room
decision-system extract-graph
decision-system map-ontology
decision-system run-orchestration "Where are we losing money?"
decision-system run-war-room "Where are we losing money?"

# Repo hygiene
decision-system check-hygiene
decision-system check-hygiene --json

# Eval / demo scripts
decision-system eval
python -m pytest tests/test_verification -q
cd web/workflow-builder && npm test

# Health
python -m pytest tests/test_data_sources -q
python -m pytest tests/test_providers -q
python -m pytest tests/test_workflow_engine/test_api.py -q
```

## Review Checklist

Before submitting work:

- [ ] Working tree is clean (`git status --short`).
- [ ] `python -m pytest -q` passes (exit code 0).
- [ ] No new `.env` or real API keys in any tracked file.
- [ ] No tracked artifacts (`.decision_system/`, `__pycache__/`,
      `.pytest_cache/`, `*.pyc`, `node_modules/`, imported CSVs).
- [ ] `.gitignore` covers generated files.
- [ ] Workspace isolation is respected (data is scoped, not global).
- [ ] All extracted facts include evidence references.
- [ ] README and CHANGELOG updated if behavior changed.
- [ ] Tests added for new functionality.
- [ ] `decision-system check-hygiene` passes (warnings are OK, failures are not).
- [ ] CLAUDE.md version history updated if scope changed.
- [ ] Frontend builds (`cd web/workflow-builder && npm run build`).
- [ ] No scope creep: no external database, no auth system, no enterprise
      connectors, no new LLM providers, no unbounded agents.

## Codex Guidance

**Fix small/medium issues directly.** If a change touches a few files, adds a
small helper, fixes a bug, or updates a test - do it. Do not open a review
request for trivial work.

**Large scope changes require a patch plan first.** If a change involves new
agents, new workflow nodes, new providers, new sub-packages, new extraction
systems, or any change to the bounded workflow contract, write a brief plan
(2-5 bullet points: what, why, files affected, tests, risks) and present it
before implementing.

Both Claude Code and Codex follow these rules.
