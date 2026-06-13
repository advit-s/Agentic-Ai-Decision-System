# Agentic AI Decision System

Backend-first Company Intelligence Engine for local evidence, bounded analysis, claim verification, cited decision reports, and early entity relationship mapping.

## What This Project Does

This project turns local documents into auditable company intelligence. It:

- loads local `.md` and `.txt` documents
- chunks and indexes evidence in a local Chroma vector store
- runs a bounded LangGraph workflow
- creates technical and risk memos
- extracts material claims
- verifies claims against retrieved evidence
- produces a cited decision report from claim ledger state
- extracts deterministic entities and relationships into a local graph-like JSON store
- initializes local structured data folders and profiles fake/demo CSV data
- provides a local mock-first web UI prototype for inspecting generated artifacts

## Why This Exists

The goal is to prototype safer multi-agent decision support and grow toward a Company Intelligence Engine: software that uses past and present company data to surface hidden patterns, vulnerabilities, relationships, contradictions, and risks that are hard for humans to see.

Final reports come from verified claim ledger state, not uncontrolled agent chat. Contradictions, unsupported assumptions, citations, confidence, and human review needs are kept visible instead of being smoothed away.

See [Product Vision](docs/PRODUCT_VISION.md) for the longer two-phase vision: company data understanding first, then bounded orchestration over that intelligence layer.

## Current Features

- 50+ CLI commands covering all subsystems
- local FastAPI API for development clients
- local `.md` / `.txt` documents
- Chroma vector store
- deterministic fake provider
- optional NVIDIA NIM and Ollama providers
- local entity and relationship extraction
- graph-like JSON knowledge store
- local `company_data/` catalog
- CSV profiling for row counts, missing values, numeric summaries, categorical top values, and warnings
- claim ledger
- verifier
- report writer
- inspectability commands
- evaluation command
- deterministic pattern and vulnerability detection
- war-cabinet context protocol with deterministic specialist artifacts and judge interventions
- provider evaluation harness for fake, NVIDIA NIM, and Ollama (offline/mock)
- full product web UI with 9 sections: Dashboard, Decision Brief, Data & Ontology, War Room, Workspaces, Connectors, Security & Governance, Observability, and Enterprise Readiness (v1.7)
- local SQLite workspace persistence with export/import (v1.0)
- safe connector framework with local-files real connector and stub connectors (v1.1)
- deterministic security scanning, redaction preview, audit logging, policy checks, and approval workflow (v1.2)
- local observability metrics, evaluation history, quality reports, and trace summaries (v1.3)
- Docker packaging with compose, dev scripts, and release check scripts (v1.4)
- enterprise readiness assessment with gap analysis (v1.5)
- repository hygiene checker (v1.6)

## Pattern and Vulnerability Detection

```bash
decision-system detect-patterns
decision-system inspect-insights
```

The v0.4 insight engine uses saved data profiles, local CSV datasets, and the local knowledge graph to surface deterministic offline insights such as revenue risk, customer concentration, marketing ROI risk, competitor risk, operations bottlenecks, dependency risks, contradictions, missing data, and data quality issues.

## Insight-Aware Decision Reports

```bash
decision-system build-context "Where are we losing money?"
decision-system build-context "Where are we losing money?" --json
decision-system build-context "Where are we losing money?" --save
decision-system ask "Where are we losing money?" --include-insights
decision-system ask "Where are we losing money?" --orchestrated
decision-system ask "Where are we losing money?" --include-insights --save-context
```

The v0.5 report layer can include relevant ontology concepts, generated insights, orchestration summaries, graph signals, and judge findings in decision reports. Context is built from local `.decision_system` stores and never exposes insights as absolute truth.

## Provider Experiment Layer (v0.7)

```bash
decision-system provider-health
decision-system provider-smoke --provider fake
decision-system eval-provider --provider fake
decision-system provider-smoke --provider nvidia_nim
decision-system provider-smoke --provider ollama
```

v0.7 adds a provider experiment harness for comparing fake, NVIDIA NIM, and Ollama outputs against fixed evaluation cases. The fake provider remains the default and requires no API key. Real providers produce mocked results in tests; they are only contacted when explicitly selected and configured.

- `provider-health`: shows which provider is configured and whether NIM/Ollama have required settings.
- `provider-smoke`: runs one small in-memory evidence case and validates AgentMemo + claims output.
- `eval-provider`: runs all experiment cases from `evals/provider_cases/` and prints pass/fail per case.
- `ask --provider ollama` / `ask --provider nvidia_nim`: uses the selected provider for memo/claim generation. Local retrieval, verifier, claim ledger, and report renderer are unchanged.

NVIDIA NIM is for hosted testing. Ollama is for local model testing. Never commit `.env` or real API keys. The fake provider is the safe default.

## Provider Evaluation

```bash
decision-system eval-providers
decision-system eval-providers --provider fake
decision-system eval-providers --provider ollama
decision-system eval-providers --provider nvidia_nim
decision-system eval-providers --json
decision-system eval-providers --save-results
decision-system inspect-provider-evals
```

Provider evaluation is offline by default. NVIDIA NIM and Ollama are optional test providers and are mocked in automated tests.

> **Command naming note:** `decision-system eval-provider --provider X` (singular) is the older v0.7 experiment smoke/eval command (3 cases, `provider_experiments` path). `decision-system eval-providers` (plural) is the canonical v0.7.1 provider evaluation harness (8 cases, `provider_eval` path). Both commands remain available.

The v0.7.1 harness compares structured memo output, structured claims, contradiction handling, unsupported-claim handling, citation grounding, malformed JSON handling, refusal/failure handling, and timeout/error handling. Saved results are written to `.decision_system/provider_evals/provider_eval_results.json`, which is generated local state and ignored by Git.

## API Backend

```bash
decision-system serve-api
```

FastAPI endpoints expose the existing local decision-system workflow for API clients. The API is local-development only in v0.8 and has no auth or database yet.

Available endpoints:

**v0.8 foundation:**
- `GET /health`
- `POST /documents/index`
- `GET /documents/index/inspect`
- `POST /ask`
- `POST /context/build`
- `POST /orchestration/analyze`
- `POST /orchestration/run`
- `POST /war-room/plan`
- `POST /war-room/run`
- `GET /war-room/latest`
- `POST /ontology/map`
- `GET /ontology`
- `POST /insights/detect`
- `GET /insights`
- `POST /evals/war-room`
- `POST /evals/providers`
- `GET /data-profiles` — saved data profile summary
- `GET /graph` — knowledge graph data
- `GET /dashboard` — aggregated system status

**v1.0 workspaces:**
- `POST /workspaces` — create workspace
- `GET /workspaces` — list workspaces
- `POST /workspaces/{name}/activate` — activate workspace
- `GET /workspaces/status` — active workspace status

**v1.1 connectors:**
- `GET /connectors` — list connectors
- `GET /connectors/{connector_id}` — inspect connector
- `POST /connectors/{connector_id}/dry-run` — preview import
- `POST /connectors/{connector_id}/import` — import files
- `GET /connectors/jobs` — job history

**v1.2 security:**
- `GET /security/policy` — policy check
- `POST /security/redact-preview` — PII redaction preview
- `GET /security/audit` — audit log

**v1.7 observability and enterprise:**
- `GET /observability/metrics` — collected metrics
- `GET /observability/eval-history` — eval run history
- `GET /observability/quality-report` — quality report
- `GET /observability/traces` — trace summaries
- `GET /enterprise-readiness` — readiness assessment

**v1.8 reports:**
- `POST /reports/export` — export latest report (markdown/json/html)
- `GET /reports/latest` — latest report payload
- `GET /reports/coverage` — evidence coverage score
- `GET /reports/audit-timeline` — audit event timeline
- `GET /reports/provider-safety` — provider mode with safety warnings

## Security, Governance, and Audit (v1.2)

```bash
decision-system security scan-secrets
decision-system security scan-secrets --json
decision-system security redact-preview "contact customer@example.com"
decision-system security redact-preview "contact customer@example.com" --json
decision-system security audit-log
decision-system security audit-log --json
decision-system security policy-check
decision-system security policy-check --json
decision-system approval request --reason "testing"
decision-system approval list
decision-system approval list --json
decision-system approval inspect APPROVAL_ID
```

v1.2 adds deterministic local security and governance checks. The secret scanner finds obvious credential patterns (API keys, tokens, private keys, AWS keys) in tracked repo files. The redaction preview shows what PII-like values would be replaced without modifying files. The audit log records security events in a local JSONL file. Policy checks validate repo hygiene (fake provider default, ignored directories, no tracked `.env` files). Approval requests create local approval records for human review workflows. All security features are deterministic, offline, and require no external services, auth server, or secret vault.

## Observability and Evaluation History (v1.3)

```bash
decision-system metrics
decision-system metrics --json
decision-system eval-history
decision-system eval-history --json
decision-system quality-report
decision-system quality-report --json
decision-system trace-summary
decision-system trace-summary --json
```

v1.3 adds a local observability and evaluation history package. Metrics collection supports named metrics with values and labels, persisted to JSONL files. Evaluation run history records pass/fail counts and durations. Quality reports aggregate evaluation results into scored summaries. Trace summaries store workflow run metadata (duration, node count, error count). All data is local JSONL/JSON under `.decision_system/observability/` and ignored by Git.

```bash
# Sub-group access (same commands as top-level aliases)
decision-system observability metrics
decision-system observability eval-history
decision-system observability quality-report
decision-system observability trace-summary
```

## Docker and Local Deployment (v1.4)

```bash
docker build -t decision-system .
docker compose up
```

v1.4 adds a `Dockerfile` for containerized local development with fake/offline defaults (no secrets baked in), a `docker-compose.yml` for single-service deployment, and a `.dockerignore` to exclude secrets and generated state. Two scripts `scripts/dev.sh` and `scripts/dev.ps1` provide local development helpers (install, test, api, smoke, hygiene). Two release check scripts `scripts/release-check.sh` and `scripts/release-check.ps1` verify generated file hygiene before releases. See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for details.

## Final Prototype Hardening (v1.6)

```bash
decision-system check-hygiene
decision-system check-hygiene --json
```

v1.6 is the final prototype hardening pass. Key deliverables:
- **CLI refactoring**: monolith `cli.py` (2018 lines) broken into separate modules for security (`cli_security.py`), observability (`cli_observability.py`), and enterprise (`cli_enterprise.py`), reducing the main file to ~1574 lines
- **Repository hygiene checker**: `decision-system check-hygiene` verifies no generated state, caches, raw datasets, private env files, or agent instruction files are tracked
- **All 50 CLI commands verified working** with fake provider, no API keys required
- **1061 tests passing** offline with no external dependencies
- **Full documentation audit**: README, ARCHITECTURE.md, DECISIONS.md, RELEASE_CHECKLIST.md, CHANGELOG.md updated for all v1.0–v1.6 features
- **Clean generated state scripts**: `clean-generated.sh` and `clean-generated.ps1` for safe cleanup (dry-run by default)

## Enterprise Readiness Assessment (v1.5)

```bash
decision-system enterprise-readiness
decision-system enterprise-readiness --json
```

v1.5 adds an honest assessment distinguishing prototype-ready, enterprise-ready, and production-ready. It audits 13 working prototype capabilities and 11 gaps (auth, RBAC, tenant isolation, secrets vault, compliance, TLS, database persistence, and more). The assessment is a mostly-static checklist. See [docs/ENTERPRISE_READINESS.md](docs/ENTERPRISE_READINESS.md) for the full gap analysis.

## Local Workspaces (v1.0)

```bash
decision-system init-workspace local-demo
decision-system list-workspaces
decision-system use-workspace local-demo
decision-system workspace-status
decision-system inspect-workspace
decision-system inspect-workspace --json
decision-system export-workspace
decision-system import-workspace .decision_system/workspaces/exports/local-demo-export.json
```

v1.0 adds local SQLite-backed workspaces while preserving generated JSON outputs. Workspaces are local-only and do not add auth, cloud sync, or enterprise database support.

- `init-workspace`: create or reuse a named workspace, activate it, and initialise the local SQLite database.
- `list-workspaces`: show all known workspaces and which one is active.
- `use-workspace`: switch the active workspace for subsequent commands.
- `workspace-status`: show the active workspace and artifact type counts.
- `inspect-workspace`: inspect the active workspace metadata and recent artifacts (`--json` for machine-readable output).
- `export-workspace`: save workspace state to `.decision_system/workspaces/exports/<name>.json`.
- `import-workspace`: load a workspace export, with `--force` to overwrite an existing workspace by name.

Raw dataset artifacts are intentionally excluded from exports.

The default database path is `.decision_system/workspaces/workspaces.sqlite`; override it with `DECISION_WORKSPACE_DB`.

## War-Cabinet Agent Context Protocol (v0.6)

```bash
decision-system plan-war-room "Where are we losing money?"
decision-system run-war-room "Where are we losing money?"
decision-system inspect-war-room
```

v0.6 adds a bounded multi-role analysis layer over the existing company intelligence stores. The protocol uses immutable shared context, role-scoped personal contexts, an append-only structured workspace, deterministic artifact generators, and a deterministic judge; no free-form agent chat, no LLM calls.

- **Immutable HigherContext**: frozen Pydantic model shared by all agents.
- **Role dispatch**: keyword-based selection of specialist roles (financial, risk, marketing, technical, and more).
- **Append-only CommonWorkspace**: structured `WorkspaceArtifact` records; no deletion of others' artifacts.
- **Deterministic judge**: 4 rules: unsupported artifacts, high/critical insight links, contradiction links, low confidence warning.
- **Sandboxed tool access**: allow-list only: `read_profiles`, `read_graph`, `read_insights`, `read_context`, `save_artifact`.
- **Persisted runs**: `.decision_system/war_room/runs/<run_id>.json`, ignored by Git.

## War-Room Evaluation

```bash
decision-system eval-war-room
decision-system eval-war-room --json
decision-system eval-war-room --save-results
decision-system eval-providers
decision-system inspect-provider-evals
```

The v0.6.1 evaluation layer runs the actual war-room pipeline for known business questions and checks expected roles, tools, data categories, artifacts, and judge summaries. Quality gates verify higher context deep immutability, personal context references, append-only workspace semantics, judge execution, offline boundaries, and no chat-transcript-shaped artifacts. Saved results go to `.decision_system/evals/war_room_results.json`.

## Local Web UI Prototype

The v0.9 UI is a local prototype for exploring reports, insights, ontology mappings, war-room runs, provider evals, and data profiles. It can run against mock data and does not require auth, database, or real providers.

**Web asset layout.** `web/` is the source/standalone directory for manual or static-server browsing. `src/decision_system/web/` is the packaged copy served by the FastAPI API. Both directories must contain identical content; never edit only one side without mirroring the change.

The UI lives under `web/` and uses static HTML, CSS, JavaScript, and lightweight mock JSON fixtures. It is mock-first, so it works when the backend API is unavailable. It is served automatically at `http://127.0.0.1:8000` when you run the FastAPI API:

```bash
decision-system serve-api
```

Then open `http://127.0.0.1:8000/` in your browser.

Alternatively, you can run it with a simple static server:

```bash
python -m http.server 8765 --directory web
```

Then open `http://localhost:8765`.

The v1.7 product UI includes 9 sections:

- **Dashboard** — system readiness, provider status, quick links, overview metrics
- **Decision Brief** — ask business questions, view claim-verified responses
- **Data & Ontology** — tabbed view of data profiles, ontology mappings, insights, and knowledge graph
- **War Room** — bounded multi-role analysis with judge interventions
- **Workspaces** — artifact tracking, import/export
- **Connectors** — local-files real connector + GitHub/Jira/Slack/Email stubs
- **Security & Governance** — policy status, audit log, approval requests
- **Observability** — metrics, eval history, quality reports, trace summaries
- **Enterprise Readiness** — gap analysis distinguishing prototype vs enterprise vs production readiness

The UI works with or without the API backend running. When the API is available, it fetches live data; otherwise it falls back to mock fixtures.

## Safe Connectors

```bash
decision-system connectors list
decision-system connectors inspect local-files
decision-system connectors dry-run local-files --path company_docs
decision-system connectors import local-files --path company_docs
decision-system connectors inspect-jobs
```

v1.1 adds a safe connector framework for controlled data intake. Only `local-files` is a real connector; GitHub, Jira, Slack, and Email are offline stubs and do not make network calls. No OAuth/token storage is implemented.

```bash
decision-system connectors inspect github
decision-system connectors inspect jira
decision-system connectors inspect slack
decision-system connectors inspect email
```

Stub connectors fail safely with a clear message. Dry-run should always be used before importing. Connector jobs are generated under `.decision_system/connectors/` and are ignored by Git. No source files are deleted or modified during import.

## Visual Workflow Builder (v1.16)

The project includes a **React + React Flow** visual workflow builder at `web/workflow-builder/` with 28 node types across 5 categories (Triggers, Data, AI/Analysis, Output, Flow Control). It connects to the real backend or runs entirely in mock mode.

#### Features (v1.15–v1.16)
- **28 node types**: Manual/Cron/Webhook triggers, Retrieve, Researcher, Critic, Synthesizer, Data Analyst, Technical/Risk Analyst, Extract/Verify Claims, Write Report, War Room, Review Gate, Filter, Merge, Code, and more
- **Drag-and-drop canvas** with custom node cards, per-type icons and colors
- **DAG execution engine** — connect nodes, execute end-to-end, watch live execution events stream via WebSocket
- **Claim Ledger Report** — claim-centric post-execution view with search/filter/sort and one-click JSON export
- **Human Review Gates** — pause execution at review points, approve/reject/request-changes with full audit trail
- **Execution History & Comparison** — persistent history, side-by-side run comparison, claim status evolution
- **Edit-and-Replay** — modify node configs post-execution and replay downstream nodes
- **Workflow Templates** — 5 pre-built starter workflows (Blank, Research Pipeline, Data Analysis, Compliance Audit, Full Decision Pipeline)
- **Provider Management** — manage LLM providers with per-node overrides, test connection health indicators
- **Schedule Management** — cron-triggered automated execution
- **Resizable panels**, dark/light theme, minimap, keyboard shortcuts, animated execution edges

#### Start the Workflow Builder

```bash
cd web/workflow-builder
npm install
npm run dev
```

The builder runs at **`http://localhost:5173`** by default. In mock mode it works without the backend; set the API URL in the toolbar to connect to the FastAPI backend.

#### Architecture
See [docs/WORKFLOW_BUILDER.md](docs/WORKFLOW_BUILDER.md) for the full architecture, component tree, data flow, and API reference.

## What Is Not Included Yet

Not included in this prototype (see also `decision-system enterprise-readiness` for the full gap analysis):

- production frontend or saved workspace app
- production database (uses Chroma + JSONL file stores)
- auth (JWT/OAuth/RBAC — all operations run as local-user)
- tenant isolation (no multi-tenant boundaries)
- secrets vault (secrets stored in env vars or `.env` files only)
- enterprise connectors (only `local-files` is real; GitHub/Jira/Slack/Email are stubs)
- autonomous external actions (send emails, create tickets, call APIs)
- audit log retention policy (JSONL rotated locally, no formal policy)
- compliance controls (SOC 2, GDPR, HIPAA)
- deployment hardening (TLS, rate limiting)
- encrypted storage at rest (all data unencrypted locally)
- API input sanitization (basic Pydantic validation only)

## Architecture

```text
company_docs/
   |
document loader
   |
chunker
   |
Chroma vector store
   |
retriever
   |
LangGraph workflow
   |
technical analyst
   |
risk analyst
   |
claim extraction
   |
verifier
   |
report writer
   |
decision report

company_docs/
   |
document loader
   |
chunker
   |
deterministic graph extractor
   |
.decision_system/graph/knowledge_graph.json
   |
graph inspection

company_data/
   |
data catalog manifest
   |
CSV profiler
   |
.decision_system/data_profiles/profiles.json
   |
data inspection

web/
   |
static local UI
   |
mock-data JSON fixtures
   |
optional API base URL
```

## Developer Setup

Windows:

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

macOS/Linux:

```bash
git clone <repo-url>
cd <repo-name>
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Demo Dataset Starter Pack

```bash
decision-system init-data-catalog
decision-system seed-demo-data
decision-system profile-data
decision-system inspect-data
```

The demo datasets are synthetic and safe for local development.

## Public Dataset Importer

Raw public datasets should live in the ignored `datasets/` folder. Supported local inputs are `.csv`, `.xlsx`, and `.xls`; SQL Server `.bak` files are skipped with a clear manifest entry.

```bash
decision-system import-datasets --source-dir datasets --max-rows 5000
decision-system inspect-imports
decision-system profile-data
decision-system inspect-data
```

Imported CSVs are written under `company_data/<category>/` as `imported_*.csv` and remain ignored by Git.

## Quick Start With Fake Provider

The fake provider is the default and works without any API key. The repo includes `company_docs/demo_billing.md` for local smoke tests.

```bash
decision-system index
decision-system inspect-index
decision-system ask "Should we migrate billing?"
decision-system ask "Should we migrate billing?" --show-evidence
decision-system ask "Should we migrate billing?" --json
decision-system ask "Should we migrate billing?" --save-run
decision-system extract-graph
decision-system inspect-graph
decision-system init-data-catalog
decision-system profile-data
decision-system inspect-data
decision-system eval
```

## Using NVIDIA NIM

1. Copy `.env.example` to `.env`.
2. Create your own NVIDIA API key in NVIDIA Build.
3. Choose the exact model ID from NVIDIA Build.
4. Set:

```env
DECISION_PROVIDER=nvidia_nim
# NVIDIA_API_KEY — set to your NVIDIA API key below (placeholder only)
# NVIDIA_API_KEY=replace-with-real-key
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_MODEL=deepseek-ai/deepseek-v4-flash
```

Run one question with NIM:

```bash
decision-system ask "Should we migrate billing?" --provider nvidia_nim
```

The NVIDIA provider uses NVIDIA NIM's OpenAI-compatible API through the `openai` Python package and validates model output into Pydantic models before it enters the workflow.

Never commit `.env` or real API keys. The fake provider remains the default for tests and offline runs.

## CLI Commands

- `decision-system index`: index local documents from `company_docs/`
- `decision-system inspect-index`: show collection name, chunk count, and source filenames
- `decision-system ask "..."`: run the decision workflow and print Markdown
- `decision-system ask "..." --show-evidence`: print retrieved evidence before the report
- `decision-system ask "..." --json`: print structured workflow state
- `decision-system ask "..." --save-run`: save full run JSON under `.decision_system/runs/`
- `decision-system ask "..." --provider nvidia_nim`: use NVIDIA NIM for one run
- `decision-system ask "..." --include-insights`: add relevant business/data insights
- `decision-system ask "..." --orchestrated`: include orchestration context
- `decision-system ask "..." --save-context`: save context JSON for inspection
- `decision-system extract-graph`: extract entities and relationships into `.decision_system/graph/knowledge_graph.json`
- `decision-system inspect-graph`: show entity counts, relationship counts, grouped types, and top connected entities
- `decision-system init-data-catalog`: create `company_data/`, category folders, manifest, and fake demo CSVs
- `decision-system seed-demo-data`: write the synthetic 10-category demo CSV starter pack
- `decision-system profile-data`: profile local CSV files and save `.decision_system/data_profiles/profiles.json`
- `decision-system inspect-data`: summarize saved CSV profiles
- `decision-system import-datasets`: convert ignored public CSV/XLSX/XLS datasets into categorized local CSVs
- `decision-system inspect-imports`: inspect the latest import manifest
- `decision-system detect-patterns`: run deterministic pattern and vulnerability detection
- `decision-system inspect-insights`: inspect saved insight summaries
- `decision-system map-ontology`: map dataset columns to ontology business concepts
- `decision-system inspect-ontology`: inspect the local ontology map
- `decision-system analyze-problem "..."`: analyze a business question and print required data, tools, and roles
- `decision-system run-orchestration "..."`: run the full offline orchestration pipeline for a business question
- `decision-system inspect-orchestration`: inspect the latest saved orchestration run
- `decision-system build-context "..."`: build and print decision context for a question
- `decision-system build-context "..." --json`: print context as structured JSON
- `decision-system build-context "..." --save`: save context to `.decision_system/contexts/`
- `decision-system plan-war-room "..."`: preview role dispatch and shared context for a war-room run
- `decision-system run-war-room "..."`: run deterministic specialist artifact generation and judge review
- `decision-system inspect-war-room`: inspect the latest saved war-room run
- `decision-system eval`: run local evaluation cases
- `decision-system eval --json`: print structured evaluation results
- `decision-system eval --save-results`: save evaluation results under `evals/results/`
- `decision-system eval-war-room`: run war-room offline evaluation cases with quality gates
- `decision-system eval-war-room --json`: print structured war-room eval results
- `decision-system eval-war-room --save-results`: save war-room eval results under `.decision_system/evals/`
- `decision-system eval-providers`: run offline/mock provider evaluation cases for fake, NVIDIA NIM, and Ollama
- `decision-system eval-providers --provider X`: evaluate one provider (`fake`, `nvidia_nim`, or `ollama`)
- `decision-system eval-providers --json`: print structured provider evaluation JSON
- `decision-system eval-providers --save-results`: save provider evaluation results under `.decision_system/provider_evals/`
- `decision-system inspect-provider-evals`: inspect saved provider evaluation results
- `decision-system provider-health`: show provider configuration status
- `decision-system provider-smoke --provider X`: run a one-off provider smoke test
- `decision-system eval-provider --provider X`: run provider experiment cases
- `decision-system ask --provider ollama`: use Ollama for memo/claim generation only
- `decision-system serve-api`: run the local FastAPI development API with uvicorn
- `decision-system init-workspace <name>`: create or reuse a local SQLite workspace
- `decision-system list-workspaces`: list all known workspaces
- `decision-system use-workspace <name>`: switch active workspace
- `decision-system workspace-status`: show active workspace and artifact type counts
- `decision-system inspect-workspace [--json]`: inspect workspace metadata and artifacts
- `decision-system export-workspace`: export workspace to JSON bundle
- `decision-system import-workspace <path>`: import workspace from JSON export
- `decision-system connectors list`: list all known connectors
- `decision-system connectors inspect <id>`: show connector details
- `decision-system connectors dry-run <id> --path <dir>`: preview what would import
- `decision-system connectors import <id> --path <dir>`: import files from a local directory
- `decision-system connectors inspect-jobs`: show connector job history
- `decision-system security scan-secrets`: scan local files for credential patterns
- `decision-system security redact-preview <text>`: preview PII/secret redaction
- `decision-system security audit-log`: inspect the local audit log
- `decision-system security policy-check`: run repository governance checks
- `decision-system approval request --reason "..."`: create a local approval record
- `decision-system approval list`: list pending approval requests
- `decision-system approval inspect <id>`: inspect a single approval record
- `decision-system metrics`: show collected observability metrics
- `decision-system eval-history`: show evaluation run history
- `decision-system quality-report`: generate and display a quality report
- `decision-system trace-summary`: show recent workflow trace summaries
- `decision-system enterprise-readiness`: assess enterprise/production readiness
- `decision-system check-hygiene`: verify repository hygiene before releases
- `decision-system check-hygiene --json`: print structured hygiene report

## Project Structure

- `src/decision_system/agents`: bounded technical and risk analyst wrappers
- `src/decision_system/api`: local FastAPI app, Pydantic API models, and route modules
- `src/decision_system/graph`: LangGraph state, nodes, and workflow
- `src/decision_system/rag`: document loading, chunking, embeddings, vector store, retrieval
- `src/decision_system/ledger`: claim ledger and verifier
- `src/decision_system/llm`: fake provider, NVIDIA NIM provider, Ollama provider, provider factory
- `src/decision_system/provider_experiments`: provider experiment models, runner, store, inspector
- `src/decision_system/provider_eval`: provider evaluation models, runner, store, inspector
- `src/decision_system/reports`: decision report renderer
- `src/decision_system/evals`: local evaluation models and runner
- `src/decision_system/graphing`: entity and relationship graph models, extraction, store, and inspection
- `src/decision_system/data_catalog`: local data catalog initialization, CSV profiling, storage, and inspection
- `src/decision_system/insights`: deterministic pattern and vulnerability detection
- `src/decision_system/orchestration`: offline orchestration foundation, problem analysis, planning, dispatch, judge summary
- `src/decision_system/context`: decision context building, selection, persistence, inspection
- `src/decision_system/ontology`: ontology concepts and column mapping
- `src/decision_system/observability`: metrics, eval history, quality reports, trace summaries
- `src/decision_system/security`: secret scanning, redaction preview, policy checks, audit logging, approval workflow
- `src/decision_system/storage`: local SQLite workspace persistence, export, import, inspection (via ``WorkspaceExporter`` / ``WorkspaceImporter``)
- `src/decision_system/connectors`: safe connector framework (local-files real; GitHub/Jira/Slack/Email stubs)
- `src/decision_system/war_room`: war-cabinet protocol, quality gates, and eval runner
- `src/decision_system/web`: packaged web UI files served by the FastAPI API
- `src/decision_system/cli_security.py`: security and approval CLI sub-commands
- `src/decision_system/cli_observability.py`: observability CLI sub-commands and top-level aliases
- `src/decision_system/cli_enterprise.py`: enterprise readiness CLI command
- `src/decision_system/cli_workspaces.py`: workspace CLI commands
- `src/decision_system/cli_connectors.py`: connector CLI commands
- `web`: local static UI prototype and mock JSON fixtures
- `evals/war_room_cases`: offline war-room evaluation cases
- `tests`: offline unit and CLI tests
- `docs`: architecture, setup, development, and troubleshooting docs
- `company_docs`: local docs folder; only demo docs should be committed
- `company_data`: local structured data folder; only manifest, `.gitkeep`, and `demo_*.csv` files should be committed

## Testing

```bash
python -m pytest -q                          # full test suite (1061 tests)
python -m pytest tests/test_security.py -q   # security/audit tests (64 tests)
python -m pytest tests/test_observability.py -q  # observability tests (28 tests)
python -m pytest tests/test_web_ui.py -q     # web UI tests
cd web/workflow-builder && npx vitest run    # frontend tests (35 tests)
decision-system eval                         # bundled evaluation cases
decision-system eval-war-room                # war-room offline evaluation
decision-system eval-providers               # provider evaluation cases
decision-system check-hygiene                # verify repo hygiene
```

## License

This project is licensed under the MIT License. See `LICENSE`.

## Troubleshooting

- **No documents indexed**: make sure `company_docs/` exists and contains `.md` or `.txt` files. The repo includes `company_docs/demo_billing.md`.
- **No graph relationships extracted**: add simple relationship phrases such as `Billing depends on LegacyAuth`, `LegacyAuth owned by Platform Team`, or `CONTRADICTS: ...`.
- **No data profiles found**: run `decision-system init-data-catalog` and then `decision-system profile-data`.
- **Missing NVIDIA key**: set `NVIDIA_API_KEY` in `.env` or use the default fake provider.
- **Chroma warning**: Chroma may emit dependency deprecation warnings during tests; these do not usually block local runs.
- **Wrong provider**: check `DECISION_PROVIDER` in `.env`, or pass `--provider fake` / `--provider nvidia_nim`.
- **Web UI mock data does not load**: run `python -m http.server 8765 --directory web` from the repo root and open `http://localhost:8765`.
- **Windows path with spaces**: quote paths and run commands from the repo root.
- **`.env` not loaded**: run commands from the repo root and confirm the file is named exactly `.env`.

## AI Development Workflow

Claude Code is used as the primary implementer. Codex is used as the independent reviewer/verifier. All Claude work should be test-backed and reviewed before being accepted.

## Repository Hygiene

```bash
decision-system check-hygiene
decision-system check-hygiene --json
```

The hygiene checker verifies that generated state, caches, raw datasets, private env files, and agent instruction files are in a safe repo state before new milestones.

## Roadmap

Completed:
- v0.1: decision brief core
- v0.2: graph/entity extraction
- v0.3: company data intake + profiling
- v0.4: orchestration + ontology + insight engine
- v0.5: insight-aware decision reports
- v0.6: war-cabinet agent context protocol
- v0.7: provider experiment harness for fake, NVIDIA NIM, and Ollama
- v0.7.1: provider evaluation hardening harness
- v0.8: local FastAPI backend
- v0.9: local mock-first web UI prototype
- v1.0: local SQLite workspace persistence, CLI commands, JSON export/import
- v1.1: safe connector framework (local-files real; GitHub/Jira/Slack/Email stubs)
- v1.2: deterministic security, governance, and audit (secret scan, redaction, policy, approval)
- v1.3: observability, metrics, evaluation history, quality reports, trace summaries
- v1.4: Docker packaging, local deployment scripts, release verification
- v1.5: enterprise readiness assessment and gap analysis
- v1.6: final prototype readiness pass (all commands verified, 1061 tests passing)
- v1.7: frontend product UI with 9 sections, mock-first design, API integration
- v1.13: Phase 6 — Bounded Specialist Agent Nodes (Researcher, Critic, Synthesizer)
- v1.14: Phase 7 — Data Analyst Node
- v1.15: Claim Ledger DX, Human Review Gates, Execution History
- v1.16: Backend Connection, 4 New Specialists, Execution UX, Visual Polish
