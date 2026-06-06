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
