## [1.11.0] - 2026-06-13

### Added
- Phase 4: Scheduling & Triggers — transform workflow engine from manual-execution-only to autonomous automation engine.
- Schedule models (`ScheduleDefinition`, `TriggerType`) with JSON file store (`ScheduleStore`).
- Trigger evaluators: cron (5-field matching with dedup), webhook (path matching with normalization), file-watch (glob-based file diff detection).
- Background scheduler service (`SchedulerService`) with asyncio polling loop and start/stop lifecycle.
- 3 new trigger node types: CronTrigger, WebhookTrigger, FileWatchTrigger (16→19 built-in node types).
- Schedule-aware execution: `schedule_id` propagated through `ExecutionContext` to every node.
- Schedule CRUD API endpoints: POST/GET/PUT/DELETE `/schedules`, POST `/schedules/{id}/toggle`.
- Webhook receiver endpoint: POST `/webhook/{path}` triggers matching workflow execution.
- Scheduler auto-start/stop via FastAPI lifespan context manager.
- CLI schedule commands: `decision-system workflow schedule {list,create,delete,toggle}`.
- Auto-scheduling: workflows with trigger nodes automatically create/update/delete schedules on save.
- Frontend mock API for schedule CRUD and 3 new trigger node types in the node palette.
- ScheduleManager React component for viewing, creating, toggling, and deleting schedules.
- 14 schedule API tests, 9 CLI schedule tests, 6 auto-schedule tests, 8 end-to-end integration tests.

### Changed
- Project version is now 1.11.0.
- `ExecutionContext` now has `schedule_id` field.
- `DAGEngine.execute()` accepts `schedule_id` parameter.
- Node registry now registers 19 built-in node types (up from 16).
- Node count assertions updated in test files.
- FastAPI app now uses lifespan context manager for scheduler lifecycle.

## [1.10.1] - 2026-06-13

### Added
- Phase 3: Real-time workflow execution and data inspection.
- WebSocket event streaming endpoint (`/executions/{id}/stream`) for live node status updates.
- Provider selector per node in the workflow builder UI.
- Node output data inspection panel showing execution results per node.
- Real mode auto-detection: frontend detects when served from FastAPI backend.
- 10 comprehensive test files covering all Phase 3 components.

### Changed
- Phase 3 integration: WebSocket URL construction and event emission optimized.

## [1.10.0] - 2026-06-12

### Added
- Visual workflow builder (Phase 2) — React Flow drag-and-drop editor with 15 implementation tasks.
- 16 custom node types rendered with category-colored headers, status overlays, and config schemas.
- Drag-and-drop node palette with 5 categories: Triggers, Data, AI / Analysis, Output, Flow Control.
- Interactive workflow canvas with snap-to-grid, MiniMap, Controls, and delete-key support.
- Right-side config panel with auto-generated JSON Schema forms (text, number, boolean, enum, array, textarea).
- Execution panel with real-time per-node status badges, elapsed timer, progress bar, and error display.
- Mock-first API client with CRUD workflows, execution, and WebSocket event streaming fallback.
- Backend WebSocket event stream (`GET /workflows/executions/{id}/stream`) bridging DAGEngine events to connected clients.
- Toast notification system with info/success/warning/error types and auto-dismiss.
- 10 comprehensive test files (35 tests) covering all components with localStorage, ResizeObserver, and DataTransfer polyfills.
- Navigation integration: "⚡ Workflows" nav item in the Intelligence Console sidebar.

### Changed
- Project version is now 1.10.0.
- WebSocket endpoint added to workflow engine API router.

## [1.9.0] - 2026-06-12

### Added
- Workflow Engine (Phase 1) — node SDK, DAG runtime, CLI, and API for visual workflow automation.
- Core models: WorkflowNode (ABC), WorkflowDefinition, ExecutionState, Connection, ErrorPolicy, RetryConfig.
- DAG validator (cycle detection, missing connection checks) and topological sort (Kahn's algorithm).
- DAG executor with async parallel layer dispatch via `asyncio.gather()` and 4 error policies (fail_workflow, fail_node, retry with exponential backoff, skip).
- ExecutionEvent streaming model for real-time execution progress (Phase 2 UI).
- NodeRegistry with type registration, lookup, entry-point hooks, and instantiation.
- 16 built-in node types: ManualTrigger, InputText, Filter, Merge, Code, Retrieve, TechAnalyst, RiskAnalyst, ExtractClaims, VerifyClaims, WriteReport, ExtractGraph, ProfileData, MapOntology, DetectPatterns, WarRoom.
- WorkflowStore + ExecutionStore ABCs with JSON file persistence.
- CLI commands: `decision-system workflow create|validate|run|list|list-nodes`, `decision-system execution list|inspect`.
- REST API: CRUD workflows, execute workflow, get execution state, list node types with JSON schemas.
- 93 new tests covering all components with no API keys required.
- All 16 node types accessible via `create_default_registry()`.

### Changed
- Project version is now 1.9.0.
- All 700+ existing tests remain unchanged and passing.

## [1.8.0] - 2026-06-10

### Added
- Decision Report Export CLI + API (`decision-system export-report --format markdown|json|html`) for exporting latest decision/war-room report with claims, risks, assumptions, evidence, and audit metadata.
- Evidence Coverage Score CLI + API (`decision-system coverage`) showing total/verified/unsupported/contradicted claims and evidence coverage percentage.
- Workspace Snapshot Diff CLI (`decision-system diff-workspaces`) for comparing two workspace exports with added/removed/changed items across documents, ontology, insights, metrics, and security posture.
- Audit Timeline CLI + API (`decision-system audit-timeline`) summarizing recent local audit events from war-room, security, connectors, and index sources.
- Demo Data Validator CLI (`decision-system validate-demo-data`) verifying demo docs and mock data contain no real secrets or large raw datasets.
- Provider Safety Status CLI + API (`decision-system provider-safety`) showing current provider mode with external provider warnings. Default is always fake/offline (`safe`).
- Path validation utility (`decision_system.path_util`) for safe canonicalization and traversal protection.
- API endpoints: `POST /reports/export`, `GET /reports/coverage`, `GET /reports/audit-timeline`, `GET /reports/provider-safety`.
- 49 new tests covering all v1.8 features and path validation.

### Changed
- Project version is now 1.8.0.
- API web asset discovery fixed: uses `importlib.resources.files()` for correct wheel-installed mode serving (previously looked at wrong directory).
- Security redaction improved: `original_text` is masked when findings exist, `matched_preview` always shows truncated preview (never full secret), and overlapping findings are deduplicated (longer patterns take precedence over shorter fragments).
- Release check script hardened for `set -euo pipefail` fallback mode; final summary always printed.
- Dockerfile removed `COPY docs/` to match `.dockerignore` exclusion.
- Release check now includes `validate-demo-data` gate (11 total checks).
- CLI help includes 6 new commands.

### Fixed
- API web serving path: now uses `importlib.resources.files("decision_system").joinpath("web")` with repo-root fallback.
- Security redaction: overlapping patterns fixed (secret_token patterns now take precedence over phone fragments inside them).
- Security redaction API: `original_text` no longer exposes raw secrets when findings exist.
- Release check final summary now reliably printed even in non-Git fallback mode.

## [1.7.0] - 2026-06-09

### Added
- Frontend product UI with 9 navigation sections: Dashboard, Decision Brief, Data & Ontology, War Room, Workspaces, Connectors, Security & Governance, Observability, and Enterprise Readiness.
- Dashboard with system readiness status, provider info, document index state, workspace state, metrics (profiles, insights, graph entities/links, connectors, war-room runs), and quick links.
- Decision Brief section with offline mode notice, Ask form, claim status summary, and API-backed or mock-first responses.
- Data & Ontology section with tabbed sub-views for data profiles, ontology mapping, insights (severity-grouped), and knowledge graph entities/relationships.
- War Room section with HigherContext/PersonalAgentContext/CommonWorkspace explanation, roles, judge interventions, and artifacts.
- Connectors section showing local-files (real) and GitHub/Jira/Slack/Email (stub) connectors with clear stub labeling and no token input fields.
- Security & Governance section with policy check status, audit log events, and approval requests.
- Observability section with metrics, eval history, quality reports, and trace summaries (standalone scaffolding notice).
- Enterprise Readiness section with readiness level badge, working vs gap counts, and detailed gap list with severity.
- `GET /enterprise-readiness` API endpoint returning static readiness assessment.
- `GET /observability/metrics`, `GET /observability/eval-history`, `GET /observability/quality-report`, `GET /observability/traces` API endpoints for observability data.
- Mock data fixtures for all 9 sections under `web/mock-data/` and package `src/decision_system/web/mock-data/`.

### Changed
- Project version is now 1.7.0.
- Web UI completely rebuilt: `web/index.html`, `web/app.js`, `web/styles.css` rewritten with 9-section architecture.
- Mock data contracts expanded: dashboard, connectors, observability, enterprise-readiness mock fixtures added.
- Navigation uses sidebar with compact dark theme and section-specific page titles.
- All existing API endpoints preserved; new endpoints added for enterprise-readiness and observability.
- Web UI tests expanded to cover all 9 sections and new API endpoints.

### Fixed
- Security view no longer crashes: `FALLBACK_DATA.security` added to prevent `TypeError` on undefined data.
- Web UI tests updated to reference new section IDs and mock data contracts.

### Security
- All 651 tests pass offline with no API keys.
- No real secrets, tokens, or credentials in mock data fixtures.
- Security scanner continues to mask full secret values.

## [1.6.0] - 2026-06-09
### Added
- Final prototype hardening pass completed.
- `clean-generated.sh` and `clean-generated.ps1` for safe generated-state cleanup (dry-run by default).
- All 49 CLI commands verified working offline with fake provider.
- CLI import verified fast (~0.2s) with lazy imports preserved.

### Changed
- Project version is now 1.6.0.
- CLI refactored: monolithic `cli.py` (2018 lines) split into `cli_security.py`, `cli_observability.py`, `cli_enterprise.py` (~1574 lines remaining).
- README.md: security command paths corrected, v1.3–v1.6 sections added, roadmap completed, "What Is Not Included" expanded with production gaps.
- ARCHITECTURE.md: v1.3 (observability), v1.4 (Docker), v1.5 (enterprise readiness), v1.6 (final hardening) sections added; inspectability list and current limits updated.
- DECISIONS.md: ADR-033 (observability), ADR-034 (Docker), ADR-035 (enterprise readiness), ADR-036 (final hardening) added.
- RELEASE_CHECKLIST.md: v1.3 (observability), v1.4 (Docker), v1.5 (enterprise readiness), v1.6 (final hardening) checklist sections added.
- Shallow implementations documented: observability module has working tests and CLI plumbing but is not populated by the core workflow.

### Fixed
- Policy check now skips synthetic test secret fixtures to avoid false positives.
- Storage paths now accept optional `root` parameter throughout observability.
- CLI command duplication eliminated: observability commands were defined twice (sub-app + top-level aliases), now shared from a single implementation.
- README documented wrong CLI paths for security commands (`scan-secrets` → `security scan-secrets`, etc.).

### Security
- All 651 tests pass offline with no API keys.
- No tracked generated state in the repository.
- Security scanner never prints full secret values (masked preview only).
- Audit log and security stores under `.decision_system/` are in `.gitignore`.

## [1.5.0] - 2026-06-09
### Added
- Enterprise readiness checklist command (`decision-system enterprise-readiness`).
- Honest readiness assessment distinguishing prototype-ready, enterprise-ready, production-ready.
- `docs/ENTERPRISE_READINESS.md` with gap analysis (auth, RBAC, tenant isolation, secrets vault, compliance, etc.).
- `docs/SECURITY_MODEL.md` describing current security posture and planned improvements.
- `docs/HUMAN_APPROVAL_WORKFLOW.md` documenting the approval record-keeping mechanism.
- CLI test for enterprise-readiness command (text and JSON output).

### Changed
- Project version is now 1.5.0.

## [1.4.0] - 2026-06-09
### Added
- `Dockerfile` for containerized local development (fake/offline default, no secrets baked in).
- `docker-compose.yml` for single-service local deployment.
- `.dockerignore` to exclude secrets, generated state, and dev files from Docker builds.
- `scripts/dev.sh` and `scripts/dev.ps1` local development helpers (install, test, api, smoke, hygiene).
- `scripts/release-check.sh` and `scripts/release-check.ps1` release verification scripts.
- `docs/DEPLOYMENT.md` with local deployment instructions and security notes.
- Release check verifies: no pycache/pyc in tracked files, no generated DBs, no raw datasets, no secrets, package installs, tests pass, CLI import fast, hygiene passes.

### Changed
- Project version is now 1.4.0.

## [1.3.0] - 2026-06-09
### Added
- Observability and evaluation history package (`src/decision_system/observability/`).
- Metrics collection with JSONL persistence and summary aggregation.
- Evaluation run history with load/save/inspect.
- Quality report generator from evaluation run data.
- Trace summary storage for workflow runs.
- CLI commands: `metrics`, `eval-history`, `quality-report`, `trace-summary` (each with `--json`).
- Observability sub-command group: `observability metrics/eval-history/quality-report/trace-summary`.
- Deterministic persistence under `.decision_system/observability/` (metrics, eval_history, quality_reports, traces).
- 28 observability tests with tempfile isolation.

### Changed
- Project version is now 1.3.0.
- `.gitignore` includes `.decision_system/observability/`.

## [1.2.0] - 2026-06-09
### Added
- Deterministic local secret scanning (`decision-system scan-secrets`).
- Redaction preview for PII-like values and secret-like tokens (`decision-system redact-preview`).
- Local audit log under `.decision_system/security/audit/audit_log.jsonl`.
- Policy checks for repo hygiene and governance (`decision-system policy-check`).
- Local approval request workflow (`decision-system approval request/list/inspect`).
- 9 security module package: models, secret_scan, redaction, audit, policy, approvals, store, inspector.
- 64 security tests with synthetic data only.

### Changed
- Project version is now 1.2.0.

## [1.1.0] - 2026-06-08
### Added
- Safe connector framework with connector registry, job manifests, and inspection.
- Real `local-files` connector with dry-run and copy-based import.
- Offline connector stubs for GitHub, Jira, Slack, and Email.
- Connector CLI commands: `connectors list`, `connectors inspect`, `connectors dry-run`, `connectors import`, `connectors inspect-jobs`.
- Connector API endpoints under `/connectors`.
- Optional workspace artifact integration for connector import jobs.
- Connector job persistence under `.decision_system/connectors/`.

## [1.0.1] - 2026-06-08
### Fixed
- Synced root and packaged web UI assets.
- Added top-level workspace CLI command aliases.
- Fixed workspace API activation so only one workspace is active.
- Tightened workspace CLI/API integration tests.

## [1.0.0] - 2026-06-07
### Added
- Local SQLite workspace store under `src/decision_system/storage/` with idempotent migrations.
- Workspace CLI commands: `init-workspace`, `list-workspaces`, `use-workspace`, `workspace-status`, `inspect-workspace`, `export-workspace`, `import-workspace`.
- Workspace artifact repository with typed artifact tracking (document, dataset, profile, ontology, insight, report, orchestration, war-room, provider eval, audit).
- JSON export/import support for local workspace bundles with controlled artifact type allowlist.
- Workspace inspection with Rich tables and optional `--json` output.
- Offline tests for storage layer and workspace CLI integration (49 new tests).
### Fixed
- Aligned v0.9.2 package/API version metadata before v1.0 implementation.
- Fixed `Settings` backward compatibility so existing `Settings(...)` calls that omit `workspace_db_path` still work.

# Changelog

## [0.9.2] - 2026-06-07
### Fixed
- Made generated-file cleanup scripts safe by default (dry-run, requires --force).
- Added protection against root/package web asset drift via tests.
- Reduced CLI import/startup fragility by deferring heavy imports from module scope into heavy commands.
- Tightened missing-index API test (requires status 400 and error.code == "missing_index").
- Tightened missing-index CLI test (requires no traceback and the "decision-system index" hint).
- Fixed provider eval documentation typo (renamed `runer` to `runner`).

## [0.9.1] - 2026-06-06

### Fixed
- Aligned API version reporting with project version (0.9.1).
- Routed API provider evaluation endpoint to the canonical provider-eval harness.
- Added friendly missing-index errors for CLI and API ask flows.
- Hardened web UI static asset packaging (package-relative path).
- Clarified provider evaluation command naming in documentation.
- Improved release cleanup guidance for generated files and caches.

## [0.9.0] - 2026-06-06

### Added
- Local web UI prototype.
- Mock-first views for reports, insights, ontology, war-room, provider evals, and data profiles.
- Static Graph and Ask views with optional API base URL configuration.
- Lightweight mock JSON fixtures under `web/mock-data/`.

## [0.8.0] - 2026-06-06

### Added
- FastAPI application.
- Local API endpoints for documents, reports, ontology, insights, orchestration, war-room, and evals.
- `decision-system serve-api`.
- Offline API tests with TestClient.

## [0.7.1] - 2026-06-06

### Added
- Provider evaluation harness.
- `decision-system eval-providers`.
- `decision-system inspect-provider-evals`.
- Offline/mock evaluation for fake, NVIDIA NIM, and Ollama providers.
- Saved provider evaluation results.

## [0.7.0] - 2026-06-05

### Added
- Provider experiment harness (new `decision_system.provider_experiments` package).
- `decision-system provider-health` - prints configured provider, NIM/Ollama status.
- `decision-system provider-smoke --provider X` - one-shot provider smoke test.
- `decision-system eval-provider --provider X` - run provider eval cases.
- Optional Ollama provider for local model testing via stdlib HTTP.
- `evals/provider_cases/` - billing_migration, contradiction_case, empty_context eval cases.
- `tests/test_provider_experiments.py` and `tests/test_ollama_provider.py` - offline tests.
- `docs/OLLAMA.md` - Ollama setup and usage guide.

### Changed
- `Settings` now includes `ollama_*` fields from `.env`.
- Provider factory now supports `fake`, `nvidia_nim`, and `ollama`.
- `decision-system ask --provider` accepts `ollama` in addition to `nvidia_nim`.

## [0.6.2] - 2026-06-05

### Added
- `AGENTS.md` for Codex and coding-agent repository instructions.
- Repository hygiene checker via `src/decision_system/devtools/hygiene.py`.
- `decision-system check-hygiene` and `decision-system check-hygiene --json` CLI commands.
- `tests/test_hygiene.py` - tests covering clean repo layout, missing files, and CLI output.
- `docs/RELEASE_CHECKLIST.md` - install, test, smoke, eval, git hygiene, skills audit checklist.

### Fixed
- `human_review_required_allowed` is now enforced in war-room eval quality gates.
  If a case disallows human review but judge interventions require it, the case fails.
- War-room eval quality gate suite now includes `human_review_not_blocked` gate.
- Added `human_review_not_blocked` gate tests in `tests/test_war_room_evals.py`.

## [0.6.1] - 2026-06-05

### Added
- War-room evaluation cases under `evals/war_room_cases/`.
- War-room quality gates: higher context existence, deep immutability, personal context reference, artifact count, append-only workspace, judge summary, human review flag, no external APIs, no unbounded chat.
- `decision-system eval-war-room` with `--json` and `--save-results` flags.
- War-room eval persistence at `.decision_system/evals/war_room_results.json`.
- Structured models: `WarRoomEvalCase`, `WarRoomEvalResult`, `WarRoomEvalSuiteResult`.

## [0.6.0] - 2026-06-05

### Added - War-Cabinet Agent Context Protocol
- `decision_system.war_room` package with 9 modules: `models`, `context_builder`, `dispatcher`, `sandbox`, `judge`, `runner`, `store`, `inspector`, `workspace`.
- Deep-frozen `HigherContext` shared by all war-room agents.
- Role-specific `PersonalAgentContext` for specialist agents with bounded tool access.
- Append-only `CommonWorkspace` for structured artifact sharing (no deletion of others' artifacts).
- Deterministic role dispatch: keyword-based selection of specialist roles (financial, marketing, technical, risk, and 7 others).
- Deterministic simulated specialist agents that read local stores (profiles, insights, graph) via sandboxed reads.
- Judge intervention system with 4 deterministic rules: unsupported artifacts, high/critical insight links, contradiction links, low confidence warnings.
- Sandboxed tool execution with explicit allow-list (`read_profiles`, `read_graph`, `read_insights`, `read_context`, `save_artifact`) and destructive-action blocking.
- Local JSON persistence for war-room runs under `.decision_system/war_room/runs/<run_id>.json`.
- Three new CLI commands: `plan-war-room`, `run-war-room`, `inspect-war-room`.
- 30 unit tests covering dispatch, immutability, workspace append-only semantics, sandbox validation, judge interventions, and runner integration.

## [0.5.0] - 2026-06-05

### Added
- Decision context builder (`DecisionContextBuilder`) assembling structured context from local stores.
- `decision-system build-context "..."` with `--json` and `--save` flags.
- Insight-aware decision reports via `--include-insights` on `ask`.
- `--orchestrated` flag on `ask` to include orchestration context in reports.
- `--save-context` flag on `ask` to persist context under `.decision_system/contexts/`.
- Optional report sections for Business/Data Insights, Ontology Concepts Used, Graph and Relationship Signals, and Orchestration Summary.
- Decision context models: `InsightEvidence` and `DecisionContext`.
- Context package with selector logic (relevance by keywords, ontology concepts, severity), store (persist/load JSON), and inspect/render helpers.
- Context builder unit tests covering missing stores, financial/customer/marketing insight selection, high-severity always-include, and contradiction human review items.

## [0.4.1] - 2026-06-05

### Fixed
- Fixed editable install dependency resolution for `python -m pip install -e ".[dev]"`.
- Removed the direct `langchain-nvidia-ai-endpoints` dependency conflict.
- Reworked `NvidiaNimProvider` to use NVIDIA NIM's OpenAI-compatible API through the `openai` Python package.
- Added `NVIDIA_NIM_BASE_URL` environment configuration.
- Corrected stale README roadmap and added missing v0.4 CLI command docs.
- Improved ontology mappings so columns such as `signup_month`, `page`, and `sessions` map to appropriate concepts.
- Added ontology concept IDs to deterministic insights.
- Updated NVIDIA provider documentation to describe the current OpenAI-compatible client path.

## [0.4.0] - 2026-06-05

### Added - Orchestration Layer
- `decision_system.orchestration` package with Pydantic v2 models: `StorageTier`, `DecisionSession`, `DecisionType`, `ProblemAnalysis`, `DispatchPlan`, `JudgeSummary`.
- `decision-system analyze-problem`: classifies a business question into a decision type and returns required data categories, tools, roles, ontology concepts, and storage tiers.
- `decision-system run-orchestration`: end-to-end pipeline: analyze -> plan -> dispatch -> sandbox -> detect -> judge.
- `decision-system inspect-orchestration`: loads and renders the latest orchestration run.
- Problem analyzer: deterministic keyword -> `DecisionType` mapping for 13 domain types (financial, customer, sales, marketing, feedback, product, competitor, operations, analytics, strategic, technical, risk, general).
- Dispatch planner: selects tools, roles, and artifacts based on required data categories; enforces execution ordering.
- Sandbox executor: explicit function-call allow-list; blocks destructive operations (delete, shell exec, HTTP, external messaging).
- Judge summary: confidence scoring (low/medium/high), key findings, risks, missing data, recommended next actions, and human-review flags.
- Persistence layer: save/load orchestration runs under `.decision_system/orchestration/runs/`.
- Inspector renderers for problem analysis and dispatch plan output.

### Added - Ontology Layer
- 31 business concepts across entity, metric, relationship, and risk types.
- Deterministic column-to-concept mapper with ~200 rules.
- `decision-system map-ontology` and `decision-system inspect-ontology`.

### Added - Pattern / Vulnerability Detection
- Local insight models and insight store.
- Deterministic pattern and vulnerability detectors (offline, no LLM).
- Detection from data profiles, local CSV datasets, and knowledge graph relationships.
- `decision-system detect-patterns`.
- `decision-system inspect-insights`.
- 16 detector categories: revenue risk, profit margin, customer concentration, sales channel concentration, marketing ROI, feedback risk, product risk, competitor risk, operations bottleneck, analytics conversion, strategic gaps, missing data, data quality, dependency risk, contradiction, and ownership gap.

## [Unreleased]

### Added
- Claude Code project memory and workflow commands.

## [0.3.2] - 2026-06-05

### Added
- Local public dataset importer for ignored `datasets/` files.
- `decision-system import-datasets` and `decision-system inspect-imports`.
- CSV and XLSX import paths plus optional XLS support through `xlrd`.
- Clear `.bak` skipping with an auditable import manifest under `.decision_system/imports/import_manifest.json`.
- Offline importer tests for classification, dry runs, overwrite safety, row limits, `.bak` skipping, and CLI commands.

## [0.3.1] - 2026-06-05

### Added
- Synthetic demo dataset starter pack.
- `decision-system seed-demo-data` with `--force` flag.
- Demo CSVs for financial, customer, sales, marketing, feedback, product, competitor, operations, analytics, and strategic data.
- `docs/DATASETS.md` with synthetic data guidance and recommended public datasets.

## [0.3.0] - 2026-06-04

### Added
- Local `company_data/` folder structure for structured company data intake.
- Data catalog manifest with supported categories and fake demo CSV metadata.
- Fake demo CSV files for financial and customer profiling smoke tests.
- CSV profiling for row count, column count, missing values, numeric summaries, categorical top values, date-like columns, and warnings.
- Profile persistence under `.decision_system/data_profiles/profiles.json`.
- `decision-system init-data-catalog`, `decision-system profile-data`, and `decision-system inspect-data`.
- Offline tests for catalog initialization, CSV profiling, profile persistence, and CLI commands.

## [0.2.0] - 2026-06-04

### Added
- Local entity and relationship extraction for the Company Intelligence Engine direction.
- `Entity`, `Relationship`, and `KnowledgeGraph` Pydantic models.
- Rule-based graph extraction for `depends on`, `owned by`, `caused`, `affects`, `blocks`, `mitigates`, `CONTRADICTS:`, and explicit related-to statements.
- Local graph JSON persistence at `.decision_system/graph/knowledge_graph.json`.
- `decision-system extract-graph` and `decision-system inspect-graph`.
- Graph inspection summaries for entity counts, relationship counts, grouped types, and top connected entities.
- Optional NVIDIA NIM provider, later hardened in v0.4.1 to avoid dependency conflicts.
- Provider factory with `fake` default and `nvidia_nim` selection.
- `decision-system ask --provider`.
- Environment-based NVIDIA NIM configuration for API key, model, temperature, top-p, max tokens, and optional reasoning settings.
- Mocked provider tests for structured NIM JSON parsing and malformed-output failures.
- GitHub readiness documentation for setup, architecture, development, NVIDIA NIM, troubleshooting, and contributing.
- Secret hygiene guidance; fake provider remains default and no real secrets should be committed.

## [0.1.2] - 2026-06-04

### Added
- `decision-system eval` for repeatable local evaluation cases.
- Evaluation case models and structured suite results.
- Offline eval runner that indexes temporary case documents and runs the normal workflow.
- Bundled billing, empty-context, and contradiction eval cases.
- `decision-system eval --json` and `decision-system eval --save-results`.

## [0.1.1] - 2026-06-04

### Added
- `decision-system inspect-index` for Chroma collection count and source filename inspection.
- `decision-system ask --show-evidence` for retrieved evidence previews.
- `decision-system ask --json` for structured workflow state output.
- `decision-system ask --save-run` for saving full workflow results under `.decision_system/runs/`.

## [0.1.0] - 2026-06-04

### Added
- Backend-first CLI prototype.
- `decision-system index`.
- `decision-system ask`.
- Local `.md` and `.txt` document loading.
- Deterministic chunking with stable chunk IDs and evidence IDs.
- Persistent local Chroma indexing.
- Fake offline provider by default.
- Bounded LangGraph workflow.
- Claim ledger with `verified`, `unsupported`, and `contradicted` statuses.
- Markdown decision report generation.
- Test suite that passes without real API keys.

### Not Included
- Frontend.
- Database.
- Auth.
- Enterprise connectors.
- Real OpenAI/Ollama execution.
- Extra agents.
