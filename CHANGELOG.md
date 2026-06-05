# Changelog

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
- `decision-system analyze-problem` — classifies a business question into a decision type and returns required data categories, tools, roles, ontology concepts, and storage tiers.
- `decision-system run-orchestration` — end-to-end pipeline: analyze → plan → dispatch → sandbox → detect → judge.
- `decision-system inspect-orchestration` — loads and renders the latest orchestration run.
- Problem analyzer: deterministic keyword → `DecisionType` mapping for 13 domain types (financial, customer, sales, marketing, feedback, product, competitor, operations, analytics, strategic, technical, risk, general).
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
