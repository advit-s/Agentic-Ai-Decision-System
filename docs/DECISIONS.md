# Architecture Decisions

## ADR-001: Use Backend-First CLI Before Frontend

Status: Accepted

The first version uses a CLI because the critical risk is the reasoning and evidence workflow, not UI. This keeps v0.1 small, testable, and easy to run locally.

## ADR-002: Use a Linear LangGraph Workflow

Status: Accepted

The system uses LangGraph because the decision process has explicit state and ordered steps. v0.1 is intentionally linear to avoid agent loops and uncontrolled conversations.

## ADR-003: Use Local Chroma for v0.1

Status: Accepted

Local Chroma gives persistent vector search without adding a database or hosted service. It is suitable for local prototype indexing and smoke tests.

## ADR-004: Use Fake Provider by Default

Status: Accepted

The fake provider keeps the project runnable without API keys. It also makes tests deterministic and protects the early architecture from provider-specific behavior.

## ADR-005: Use Claim Ledger Before Final Report

Status: Accepted

The report must consume verified, unsupported, and contradicted claims from the ledger. This prevents raw agent prose from becoming final truth without verification.

## ADR-006: Keep OpenAI/Ollama as Stubs in v0.1

Status: Accepted

Real providers are useful later, but v0.1 proves the workflow shape first. Provider stubs preserve extension points without making external execution required.

## ADR-007: Do Not Add Database/Auth/Extra Agents Yet

Status: Accepted

Database, auth, and more agents would add complexity before the retrieval, verification, and reporting loop is proven. They remain future milestones after evaluation.

## ADR-008: Add NVIDIA NIM as Optional Hosted Provider

Status: Accepted

The fake provider remains the default for tests and offline use. NVIDIA NIM is available only when explicitly selected through `DECISION_PROVIDER=nvidia_nim` or `decision-system ask --provider nvidia_nim`, and credentials must come from `.env` or environment variables.

## ADR-017: Add Decision Context Builder Before LLM-Based Synthesis

Status: Accepted

v0.5 adds a `DecisionContextBuilder` that assembles structured context from local stores (ontology map, insights, orchestration sessions, knowledge graph) without calling external APIs. The context supports optional rendering in decision reports while keeping the default output unchanged for backward compatibility.

Key principles:
- All stores are loaded defensively: missing files return empty defaults.
- Insight selection always includes high and critical severity regardless of keyword match.
- Contradiction and missing_data insights create human review items automatically.
- Context is persistable under `.decision_system/contexts/` and ignored by Git.

## ADR-018: Keep Insight-Aware Sections Opt-In

Status: Accepted

Default `decision-system ask` output does not include insight-aware sections. Section inclusion is controlled by CLI flags (`--include-insights`, `--orchestrated`, `--save-context`). This preserves backward compatibility and keeps offline smoke tests stable.

## ADR-009: Add a Local JSON Knowledge Graph Before a Database

Status: Accepted

The Company Intelligence Engine needs entity and relationship structure, but v0.2 should not add a database. A local `.decision_system/graph/knowledge_graph.json` file keeps the graph inspectable, easy to test, and safe for offline use.

## ADR-010: Use Deterministic Graph Extraction in v0.2

Status: Accepted

Entity and relationship extraction starts with rule-based patterns for phrases such as `depends on`, `owned by`, `caused`, `affects`, `blocks`, `mitigates`, `related to`, and `CONTRADICTS:`. This keeps tests deterministic and avoids adding a real LLM, extra agents, or free-form extraction loops before the storage and inspection contracts are proven.

## ADR-011: Add Local CSV Data Catalog Before Connectors

Status: Accepted

v0.3 introduces `company_data/` as a local structured data intake area. It supports category folders, a manifest, and fake demo CSV files only. This gives the Company Intelligence Engine a place to inspect structured company data without adding enterprise connectors, auth, scheduled ingestion, or a database.

## ADR-012: Persist CSV Profiles as Generated Local JSON

Status: Accepted

CSV profiling writes summaries to `.decision_system/data_profiles/profiles.json`. The profile store is generated local state and should not be committed. Profiles contain shape and quality signals, not semantic decisions: row counts, column counts, missing values, numeric summaries, categorical top values, date-like columns, and warnings.

## ADR-014: Add Deterministic Insight Engine Before Real LLM Analysis

Status: Accepted

v0.4 introduces a rule-based insight engine that reads existing data profiles, local knowledge graph relationships, and raw CSV files to produce deterministic offline insights. No real LLM is called during detection. This keeps the Company Intelligence Engine testable, auditable, and runnable without API keys while providing visible value from existing data layers.

The engine is intentionally conservative: thresholds are set to minimise false positives, and detectors gracefully skip when upstream data is absent. Insights are persisted to ``.decision_system/insights/insights.json`` and inspected via CLI commands.

## ADR-015: Keep Insight Detection Offline and Testable

Status: Accepted

All v0.4 detectors are rule-based and deterministic. They run against cached data profiles and local files. No agent call, no free-form analysis, and no new LangGraph nodes are introduced. The insight engine is a standalone analysis layer that reads the output of existing subsystems (profiler, graph, CSV loader) without modifying their contracts.

## ADR-019: Add War-Cabinet Agent Context Protocol (v0.6)

Status: Accepted

v0.6 introduces a bounded multi-role analysis layer over the existing company intelligence stores. It is not free-form agent chat; it is a structured protocol with immutable context, role-scoped personal contexts, an append-only shared workspace, deterministic artifact generation, and a deterministic judge.

Key principles:
- **HigherContext is deep-frozen.** No agent can mutate the global problem framing or nested context values.
- **Personal contexts are role-scoped.** Each specialist gets a bounded task, perspective, allowed tools, and focus areas; not a full conversation history.
- **Common workspace is append-only.** `WorkspaceArtifact` records are written by agents; no agent can delete or overwrite another's artifacts.
- **Judge is deterministic.** Four rules: unsupported artifacts (medium), high/critical insight links (high + human review), contradiction links (critical + human review), low confidence (low warning).
- **Sandbox is an allow-list.** Validated tool calls: `read_profiles`, `read_graph`, `read_insights`, `read_context`, `save_artifact`. Destructive patterns are blocked.
- **No LLM calls.** All agent simulations are deterministic artifact generators reading local stores via sandboxed reads.
- **Structured storage, not chat.** Coordination uses typed Pydantic artifacts, not free-form agent transcripts.
- **War-room runs are persisted locally.** JSON files under `.decision_system/war_room/runs/` and ignored by Git.

This layer is a direct precursor to Phase 2 of the product vision: bounded orchestration over the company intelligence layer. It proves the context-sharing, role-dispatch, and judge-review contracts before adding real LLM-backed specialists.

## ADR-020: Add Offline War-Room Quality Gates Before Real Specialist Agents

Status: Accepted

v0.6.1 adds `decision-system eval-war-room` so the war-cabinet protocol can be measured before any real LLM-backed specialists are introduced.

Key principles:
- **Eval cases are local JSON.** Cases live under `evals/war_room_cases/` and encode expected roles, tools, data categories, artifact counts, and judge requirements.
- **Cases run the actual war-room pipeline.** The eval runner calls the deterministic `run_war_room` flow instead of scoring static fixtures.
- **Quality gates are structured.** Gates check higher context presence and immutability, personal context references, append-only workspace behavior, judge execution, human-review behavior, offline boundaries, and no unbounded chat transcript shape.
- **Results are inspectable.** `--json` prints structured suite state and `--save-results` writes `.decision_system/evals/war_room_results.json`.
- **Offline default remains mandatory.** No real provider, external API, database, auth, connector, or frontend is introduced.

This keeps v0.6 focused on protocol discipline and gives future specialist-agent work a repeatable regression harness.

## ADR-021: Add Repository Hygiene Checks Before Releases

Status: Accepted

v0.6.2 adds `decision-system check-hygiene` and `docs/RELEASE_CHECKLIST.md` as
release-readiness guardrails. This is intentionally a local inspection layer,
not a new product workflow.

Key principles:
- **Generated state remains local.** `.decision_system/`, caches, raw
  `datasets/`, and imported CSV outputs are checked as ignored local artifacts.
- **Fake provider remains the default.** The hygiene check fails if
  `.env.example` no longer declares `DECISION_PROVIDER=fake`.
- **Agent instructions are explicit.** Root `AGENTS.md` and `CLAUDE.md` give
  Codex and Claude Code shared scope rules and review expectations.
- **No behavior expansion.** The hygiene layer adds no frontend, database,
  auth, connectors, providers, external API calls, or new agents.
- **Structured output is available.** `check-hygiene --json` emits a Pydantic
  `HygieneReport` for auditability.

## ADR-022: Add Provider Experiment Harness Before Deep Provider Integration

Status: Accepted

v0.7 adds optional provider experiments for fake, NVIDIA NIM, and Ollama. The
goal is to compare structured provider behavior without changing the bounded
decision workflow or adding unbounded agents.

Key principles:
- **Fake remains default.** Tests and normal offline use still require no API
  key or local model.
- **NVIDIA NIM is hosted and optional.** It runs only when explicitly selected
  and configured with environment variables.
- **Ollama is local and optional.** It calls only the configured local
  `OLLAMA_BASE_URL`, normally `http://localhost:11434`.
- **Tests are mocked/offline.** No test calls NIM, Ollama, or the internet.
- **Provider output is structured.** Provider JSON is validated into Pydantic
  `AgentMemo` and `Claim` models.
- **The ledger still governs reports.** Retrieval, verification, claim ledger,
  and local report rendering remain responsible for final decision reports.
- **No deep war-room integration yet.** Provider experiments do not add new
  specialist agents, database storage, frontend, auth, or connectors.

## ADR-023: Add Offline Provider Evaluation Hardening

Status: Accepted

v0.7.1 adds `decision-system eval-providers` and
`decision-system inspect-provider-evals` to compare fake, NVIDIA NIM, and
Ollama behavior without making optional providers part of the default runtime.

Key principles:
- **Fake remains default.** The harness does not mutate `DECISION_PROVIDER`.
- **Optional providers are mocked by default.** NVIDIA NIM and Ollama evaluation
  runs do not require API keys, local daemons, or network access.
- **Real provider runs are manual.** A caller must pass
  `--manual-real-provider` before NIM or Ollama provider objects are initialized.
- **Automated tests stay offline.** Tests never contact NVIDIA NIM, Ollama, the
  internet, or a local Ollama daemon.
- **Scoring is structured.** Results record schema validity, JSON validity,
  citation grounding, hallucination risk, contradiction handling,
  unsupported-claim handling, errors, and notes.
- **Generated results remain local.** Saved results live under
  `.decision_system/provider_evals/` and are ignored by Git.

## ADR-024: Add Local FastAPI Backend Without Auth or Database

Status: Accepted

v0.8 adds a FastAPI application as a local-development API surface over the
existing backend services. It is an adapter layer, not a second implementation
of the decision system.

Key principles:
- **Wrap existing services.** Routes call the same document indexing, workflow,
  context, orchestration, war-room, ontology, insight, and eval modules used by
  the CLI.
- **No auth or database yet.** The API is for local development clients only in
  v0.8.
- **No frontend.** This milestone exposes JSON endpoints but does not build UI.
- **Offline tests.** API tests use FastAPI `TestClient`, the fake provider, and
  temporary local stores. They do not start uvicorn or call external APIs.
- **Structured errors.** API failures use a consistent `{ "error": ... }`
  shape and do not expose stack traces.
- **Generated state remains local.** Indexes, runs, ontology maps, insights,
  contexts, and eval outputs remain under ignored generated folders.

## ADR-025: Add a Mock-First Local Web UI Prototype

Status: Accepted

v0.9 adds a local static UI under `web/` so users can inspect reports, insights,
ontology mappings, war-room runs, provider evals, data profiles, and graph
relationships without waiting for a backend API milestone.

Key principles:
- **Mock-first by default.** The UI loads lightweight JSON fixtures from
  `web/mock-data/` and remains usable without an API server.
- **Optional API integration only.** Users can configure an API base URL in the
  browser. Failed API calls fall back to mock data instead of hard-failing.
- **No frontend-owned core logic.** The browser renders artifacts and mock ask
  responses; decision workflow, claim verification, report truth, and provider
  behavior remain backend concerns.
- **No auth or database.** The prototype adds no login, permission model,
  server-side persistence, or saved workspace store.
- **No raw datasets in UI assets.** Mock fixtures are small representative JSON
  summaries, not copied private or public datasets.
- **Tests stay offline.** UI tests validate static files and mock contracts
  without starting an API server or calling real providers.

## ADR-016: Import Public Datasets as Local CSV Copies

Status: Accepted

v0.3.2 imports local public `.csv`, `.xlsx`, and `.xls` files from ignored `datasets/` into categorized CSV files under `company_data/<category>/`. Imported files are named `imported_*.csv` and remain ignored by Git. This keeps raw public downloads and generated conversions out of commits while allowing the existing CSV profiler to inspect them.

SQL Server `.bak` files are skipped with a clear manifest record instead of adding native database restore support.

## ADR-026: Version Reporting Single Source of Truth

Status: Accepted

v0.9.1 establishes `decision_system.__version__` as the single source of truth for the project version. The FastAPI app reads this value for its app version and `/health` response, and it is updated consistently with `pyproject.toml`.

## ADR-027: Provider Eval Endpoint Uses Canonical Harness

Status: Accepted

The API endpoint `POST /evals/providers` routes to the v0.7.1 `provider_eval` harness (`decision_system.provider_eval.runner.run_provider_eval_suite`), not the older `provider_experiments` module. This ensures API callers get the full 8-case evaluation coverage with schema validity, citation grounding, hallucination risk, contradiction handling, and error probes.

## ADR-028: Friendly Missing-Index Errors for Chroma

Status: Accepted

When the Chroma vector store has not been populated, `chromadb.errors.NotFoundError` is caught at both the CLI `ask` command and the API `POST /ask` endpoint. The CLI and API both return a friendly message (`"Collection not found. Run decision-system index first."`) instead of an unhandled traceback. The API returns a structured 400 response with `code: "missing_index"`.

## ADR-029: Web UI Static Assets Available From Package and Repo Root

Status: Accepted

The web UI static files are always accessible from two locations: the original `web/` directory at the repo root (for standalone static-server use) and `src/decision_system/web/` inside the package (for FastAPI static mounts). The package-relative path ensures the API can serve the web UI correctly regardless of where the installed package is located.

## ADR-030: Use Local SQLite Workspaces Before Cloud/Database Complexity

Status: Accepted

v1.0 introduces a local SQLite-backed workspace layer that stores typed artifacts for query, inspection, export, and import without forcing any existing workflow onto a database.

Key principles:

- **SQLite is local-only persistence.** The workspace DB lives at `.decision_system/workspaces/workspaces.sqlite` and is ignored by Git. No PostgreSQL, cloud database, auth, or enterprise connectors.
- **Existing JSON outputs remain canonical.** `ask`, `index`, `profile-data`, `map-ontology`, `detect-patterns`, `run-war-room`, and `eval-providers` continue writing/looking at their `.decision_system/` JSON outputs unchanged. The workspace DB is an optional import/query layer only.
- **No mandatory workspace.** The CLI and API work without a workspace initialized. SQLite is never required.
- **Idempotent migrations.** Tables use `IF NOT EXISTS` and repeated initialization never drops data. Tests verify this.
- **Typed artifacts, not chat transcripts.** Workspaces store curated structured artifacts with `ArtifactType` enum values. Raw datasets are excluded from exports.
- **Future versions can write directly to workspace.** v1.0 imports from JSON. Future versions may write directly to SQLite, but this does not change existing JSON outputs.

This keeps company data local and auditable while staying safe for offline testing. A full database moves barriers too high for the v1.0 scope.

## ADR-031: Add Connector Registry With Local-Files First And External Stubs

Status: Accepted

v1.1 introduces a safe connector framework for controlled data intake. The first real connector is `local-files`, which copies supported files into `.decision_system/connectors/`. GitHub, Jira, Slack, and Email are offline stubs that do not make network calls and do not store credentials.

Key principles:

- **Local-files first.** Only `local-files` is a real connector. It supports dry-run and copy-based import.
- **External connectors are stubs.** GitHub, Jira, Slack, and Email connectors report `is_stub=True` and produce safe errors for dry-run/import/API calls.
- **No OAuth or secrets.** Connectors do not store API tokens, cookies, or session state.
- **Source files are never modified.** The local-files connector only copies; existing destination files get a numeric suffix.
- **Protected files are skipped.** `.env`, `.gitignore`, key files, Python cache, virtual environment folders, and raw dataset directories are skipped with reasons.
- **Jobs are persisted locally.** Import jobs live under `.decision_system/connectors/jobs.json` and are ignored by Git.
- **Workspace integration is best-effort.** Connectors do not write to the workspace SQLite database directly; workspace integration is handled separately by the import-artifacts command.

This is the safest expansion path: real connector logic exists for one data source while the four common enterprise targets are represented as stubs. Adding live GitHub/Jira/Slack/Email integrations requires an explicit future ADR with OAuth/scoping design.

## ADR-032: Add Deterministic Local Security, Governance, and Audit

Status: Accepted

v1.2 adds offline security primitives: secret scanning, PII redaction preview, audit logging, policy checks, and local approval requests. All features are deterministic, require no external services, and do not add auth, cloud scanning, or secret vaults.

Key principles:

- **Security is local and deterministic.** Every check runs against local files and state. No external scanner, no cloud API, no telemetry.
- **Fake provider remains default.** No security check requires a real LLM or API key.
- **Audit log is local JSONL.** Events append to `.decision_system/security/audit/audit_log.jsonl`. The writer is reusable by future modules and does not require a workspace.
- **Secret scanning never prints full values.** Matched text is masked to first+last 4 characters before display. Only file path, line number, severity, and masked preview appear in output.
- **Redaction is preview-only.** `redact-preview` returns a `RedactionPreviewResult` with replacements and redacted text. It never writes to disk.
- **Policy checks are offline rules.** Seven checks validate repo hygiene: fake provider default in `.env.example`, required `.gitignore` entries, untracked `.env` files, no network patterns in connector stubs, no leaked secrets in source, agent instruction files present, and release checklist present.
- **Approval requests are local JSON files.** `approval request` creates a file under `.decision_system/security/approvals/` with `pending`/`approved`/`rejected`/`cancelled` status. No notifications, no external services, no auth.
- **All generated security paths are in `.gitignore`.** `.decision_system/security/` is ignored. Hygiene checks pass with the directory present.
- **API exposes a minimal surface.** `GET /security/policy`, `POST /security/redact-preview`, and `GET /security/audit` are added. No auth header, no secret body fields.
- **Web UI shows a mock-first security section.** Policy status, audit log summary, and approval requests render from mock fixtures when no API is configured.

This keeps security tooling accessible for a local prototype without forcing cloud dependencies, secret vaults, or RBAC.

## ADR-033: Add Local Observability, Metrics, and Evaluation History

Status: Accepted

v1.3 adds a local observability package for tracking metrics, evaluation runs, quality reports, and workflow traces. All data is stored as JSONL/JSON under `.decision_system/observability/` with no remote telemetry.

Key principles:

- **Local-only telemetry.** Metrics, eval runs, and traces are appended to local JSONL files. No cloud monitoring, no external observability backend, no telemetry export.
- **JSONL append-only storage.** New fields can be added to the tail without schema migrations. Each record is self-describing with timestamps and types.
- **CLI commands mirror sub-app access pattern.** Both `decision-system metrics` (top-level alias) and `decision-system observability metrics` (sub-group) access the same underlying store.
- **No automatic integration with core workflow.** The observability package has standalone tests and working CLI commands, but the core workflow (`ask`, `run-war-room`, `eval`, etc.) does not automatically record metrics or traces. This is a standalone foundation that requires future integration work.
- **No remote dependencies.** The module uses only Python standard library JSON and pathlib operations.
- **Generated paths are ignored.** `.decision_system/observability/` is in `.gitignore`.

This is noted as a **shallow implementation**: the module is correctly scaffolded and tested in isolation, but nothing populates it during normal system operation.

## ADR-034: Add Docker Packaging for Local Development

Status: Accepted

v1.4 adds Docker packaging for containerized local development. The packaging is for development and testing convenience, not production deployment.

Key principles:

- **Fake/offline defaults in the container.** The Dockerfile sets `DECISION_PROVIDER=fake` and does not bake in `.env` files or credentials.
- **Generated state lives in a Docker volume.** `.decision_system/` is mounted as a volume so generated state persists across restarts but is never part of the image.
- **Cross-platform dev scripts.** Both `scripts/dev.sh` (Bash) and `scripts/dev.ps1` (PowerShell) provide install, test, api, smoke, and hygiene commands.
- **Release check scripts are dry-run by default.** `scripts/release-check.sh` and `scripts/release-check.ps1` require `--force` to clean generated state, preventing accidental data loss.
- **No production Docker Compose.** The `docker-compose.yml` is single-service with no TLS, reverse proxy, secrets injection, or health checks.
- **No expansion of architecture rules.** Docker packaging does not add auth, database, enterprise connectors, new agents, or real provider requirements.

## ADR-035: Add Enterprise Readiness Assessment as an Honest Static Gap Analysis

Status: Accepted

v1.5 adds `decision-system enterprise-readiness` as a hardcoded CLI assessment distinguishing prototype-ready, enterprise-ready, and production-ready. It is intentionally static and does not probe the live system.

Key principles:

- **Honest assessment.** The command checks 13 prototype capabilities (`True`) and 11 enterprise gaps (`False`) with severity and notes. The result is always `prototype-ready`, never higher.
- **No external calls.** The assessment is a hardcoded checklist. No network probes, no configuration scanning, no dependency version checks.
- **JSON output for automation.** `--json` emits structured payload with version, readiness level, pass/fail counts, and missing items with severity.
- **Not a dynamic probe.** The assessment does not verify whether the system actually has implemented each capability — it is a documentation-driven checklist. This is intentional to avoid requiring live system state for every invocation.
- **No behavior change.** Enterprise readiness does not add auth, database, connectors, compliance controls, or deployment hardening. It only reports what is missing.
- **Gap analysis documented separately.** See [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md) for the full gap analysis.

## ADR-036: Final Prototype Hardening Pass — Consolidate, Do Not Add

Status: Accepted

v1.6 is the final hardening pass before the prototype can be declared safe to commit. It does not add new features — it audits, consolidates, and verifies.

Key principles:

- **No new features.** v1.6 strictly audits existing code, fixes documentation, runs all commands, and verifies the architecture. No v1.7 is planned.
- **CLI monolith is broken up.** The 2018-line `cli.py` is refactored into separate modules (`cli_security.py`, `cli_observability.py`, `cli_enterprise.py`) following the established pattern from `cli_workspaces.py` and `cli_connectors.py`.
- **Duplicate code is eliminated.** The observability commands were defined twice — once as a sub-app and once as top-level aliases — with identical command bodies. The refactoring shares a single implementation and eliminates 340+ lines of duplication.
- **Documentation is comprehensively updated.** README, ARCHITECTURE.md, DECISIONS.md, RELEASE_CHECKLIST.md, and CHANGELOG.md are all updated for v1.3–v1.6.
- **All commands are verified.** All 49 CLI commands are confirmed working with the fake provider. All 650 tests pass offline.
- **Shallow implementations are documented.** The observability module works in isolation but is never populated by the workflow. This is noted, not silently accepted.
- **Architectural rules are preserved.** All 15 rules from CLAUDE.md are audited and confirmed intact: fake provider default, no database, no auth, no enterprise connectors, bounded agents, claim-ledger-driven reports.

## ADR-037: Add Frontend Product UI as a Mock-First Vanilla Web Application

Status: Accepted

v1.7 adds a full local web product UI with 9 navigation sections, transforming
the project from "CLI/backend with a prototype UI" to "usable local web app
for the Company Intelligence Engine." The UI is built in clean vanilla
HTML/CSS/JS with no build system, no framework, and no npm dependency.

Key principles:

- **Mock-first by default.** Every section works when the API backend is
  unavailable. Mock JSON fixtures cover all 9 sections under `web/mock-data/`.
- **API integration when available.** When the API backend is running (via
  `decision-system serve-api`), the UI fetches live data. Failed calls fall
  back to mock data.
- **No build system.** The UI uses vanilla HTML, CSS, and JavaScript. No
  bundler, no framework, no npm install step required.
- **Existing APIs preserved.** All existing v0.8–v1.6 API endpoints work
  unchanged. New endpoints are additive and minimal.
- **Phase 1 + Phase 2 alignment.** The UI is organized around the two-phase
  product model: Data & Ontology (Phase 1: company data understanding) and
  War Room + Decision Brief (Phase 2: war cabinet analysis).
- **Security view crash fixed.** The v0.9 `renderSecurity()` function crashed
  because `FALLBACK_DATA` lacked a `security` key. This is fixed in v1.7 by
  adding `FALLBACK_DATA.security`.
- **Package assets stay synced.** Root `web/` and package
  `src/decision_system/web/` remain byte-for-byte identical. Drift tests
  enforce this.
- **Offline-safe.** No API keys required. The fake provider remains the
  default. The UI works loaded from the filesystem or the FastAPI static mount.
- **No auth added.** The UI makes no authenticated API calls, stores no tokens,
  and has no login screen.
- **651 tests passing.** One new test validates the v1.7 API endpoints.
