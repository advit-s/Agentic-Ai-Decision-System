## [1.26.1] - 2026-06-24 — Graph UI, Audit Metrics API + Extraction Quality Hardening
### Added
- **Graph audit/metrics API**: GET endpoints for workspace-scoped audit events, metrics, and extraction runs
- **Graph extraction run records**: Persistent run records with status, counts, duration, warnings, errors
- **Graph UI extraction history**: Last extraction time, status, warnings, extract-again action, run inspection
- **Graph evidence preview**: View evidence sources, file types, chunk snippets, confidence from graph UI
- **Extraction quality rules**: Deduplication, stopword filtering, metric/entity separation, idempotent re-runs
- **Confidence/status calibration**: Bounded 0.0-1.0 confidence, consistent statuses (extracted, verified, etc.)
- **AI extraction clarity**: Honest labeling in UI/API for optional/stubbed AI-assisted extraction
- **Graph-to-claim action**: Create pending claims from risks, metrics, entity relationships
- **Graph report section quality**: Top entities, relationships, risks, metrics with evidence/confidence/limitations
- **Risk dashboard quality**: Severity cards, categories, risk-to-claim links, evidence-backed top risks
- **Demo flow graph reliability**: Sample-text extraction works reliably; report includes graph insights
### Changed
- Version bumped from 1.26.0-dev to 1.26.1-dev
- Route registration order: `/reports/` specific paths registered before catch-all to fix shadowing
- Web assets synced: `web/index.html` → `src/decision_system/web/`
- Agent instructions updated to reflect current milestone
### Fixed
- **3 pre-existing test failures resolved**: `test_audit_timeline_api`, `test_provider_safety_api` (route ordering bug), `test_root_and_package_web_assets_match` (asset sync)
- **Extractor v2 regex escaping**: f-string brace escaping for quantifiers in metric extraction
### Known limitations
- Graph extraction is deterministic and evidence-linked but does not prove business truth by itself
- AI-assisted extraction remains optional/stubbed; labeled as such in UI
- Large graphs may have performance implications for full-workspace extraction
### Removed
- No features removed

## [1.26.0] - 2026-06-23 — Knowledge Graph + Entity/Risk Extraction v2
### Added
- **Knowledge graph v2**: Unified workspace graph model with expanded node/edge types
- **Local graph store**: Persistence under `.decision_system/graph/` with CRUD operations
- **Deterministic entity extraction v2**: Company names, vendors, products, money amounts, percentages, dates, risk phrases
- **Relationship extraction v2**: Evidence-linked edges with duplicate merging
- **Risk extraction v2**: Severity-classified, evidence-linked risks with recommended actions
- **Metric extraction v2**: Currency, percentages, counts with evidence references
- **Graph extraction API**: Workspace-scoped endpoints for graph, nodes, edges, risks, metrics
- **Workflow graph nodes**: GraphExtractionNode, RiskExtractionNode, MetricExtractionNode, GraphSummaryNode
- **Graph UI**: Entity/relationship/risk/metric lists with search/filter, evidence links, extract button, and confidence/status display (GraphPage.jsx)
- **Risk dashboard**: Risk count, severity breakdown (cards), top risks, categories, recommended actions, evidence links (RiskDashboard.jsx)
- **Report integration**: Entity Summary, Key Relationships, Extracted Risks, Key Metrics sections in trust reports
- **Audit events**: Graph extraction start/completed/failed, risk/metric extraction completed, graph_fact_created events; duration and count metrics via observability system
- **Demo integration**: Graph extraction step added to DemoFlow; sample text with entities, risks, and metrics
### Changed
- Version bumped from 1.25.0-dev to 1.26.0-dev
- Agent instructions updated to reflect current product direction
- Graph model expanded with workspace-scoped nodes and evidence references
- Existing `graphing/` modules integrated into unified graph system
### Removed
- No features removed
- **Claim-graph integration**: Claims reference graph nodes, edges, risks, metrics via ref fields
- **Observability bug fix**: MetricPoint dataclass serialization fixed in observability API
### Known limitations
- Graph extraction is deterministic and evidence-linked but does not prove business truth by itself
- AI-assisted extraction is optional and remains unverified until evidence-linked
- Workflow node tests added (29 tests); audit tests added (16 tests); total graph coverage: 113 tests
- Large graphs may have performance implications for full-workspace extraction

## [1.25.0] - 2026-06-23 — End-to-End Demo Hardening + Local Beta Release Prep (with OCR support)
### Added
- **OCR support**: Local OCR for scanned PDFs and images via tesserocr
- **Demo sample data**: demo/sample-data/ with scanned contract and invoices
- **Demo seed script**: Hardened scripts/local-demo-seed.sh for repeatable demo setup
- **E2E smoke test**: scripts/e2e-local-demo-smoke.sh for full demo validation
- **Persistence validation**: scripts/test-persistence-restart.sh
- **DEMO_PATH.md**: Complete demo walkthrough documentation

## [1.24.0] - 2026-06-23 — Single App Integration + Data Sources in React Workflow Builder
### Added
- **App shell navigation**: Sidebar with 10 sections (Demo Flow, Workflow Builder, Data Sources, Evidence Search, Execution History, Claim Ledger, Trust Dashboard, Reports, Providers, Settings)
- **Workspace selector**: Create, select, and manage workspaces with stats display
- **Data Sources page**: Upload (drag-drop + browse), parse, index, preview chunks, view CSV/XLSX profiles, delete sources
- **Evidence Search page**: Query with file type filter, result limit, evidence metadata display
- **Claim Ledger page**: Claim status summary, verify all claims, scan contradictions
- **Reports section**: View and export trust reports
- **Provider Manager section**: Reachable from main navigation
- **Execution History section**: View past workflow runs from main nav
- **Trust Dashboard section**: Full verification dashboard from main nav
- **Demo Flow**: Guided 6-step local demo (workspace → data → provider → workflow → run → report)
- **Workspace isolation fix**: Added workspace_id to EvidenceChunk model, Chroma metadata, and retriever filtering so evidence queries respect workspace boundaries
### Changed
- Version bumped from 1.23.1-dev to 1.24.0-dev
- React Workflow Builder is now the clear main product UI with app-wide navigation
- Legacy static `web/` UI labeled as deprecated prototype
- Updated docs reflecting single-app integration
- Frontend test suite expanded with new imports and navigation coverage
### Fixed
- Chroma vector search now filters by workspace_id when provided
- Verification tests no longer fail due to cross-workspace Chroma data leakage
- Test suite isolation: Chroma query respects workspace boundaries
### Removed
- No features removed
### Known limitations
- Legacy static `web/` UI is preserved as historical reference only
- Some backend API endpoints require workspace context (no anonymous queries)
- Demo flow uses mock data emulation when backend is unavailable
- Chroma re-indexing required for existing data to have workspace_id metadata

---

## [1.22.1] - 2026-06-23 — Provider API Route Fix + Release Stabilization
### Fixed
- **Provider API route conflict**: Removed duplicate old provider CRUD routes from workflow_engine/api.py
- **Route ordering**: Moved static `/providers/default` routes before dynamic `/{provider_id}` routes
- **Name uniqueness**: Added check in store creating HTTP 409 for duplicate provider names
- **Backward compat**: Added model_validator converting api_base to base_url; added backward-compat routes
- **Frontend compat**: Updated mockData.js and ProviderManager.jsx from api_base to base_url
- **20 TestProviderAPI tests**: Rewrote test class with deterministic setup/cleanup, route ordering coverage
- **3 syntax/assertion bugs**: Fixed indentation error, undefined variable, incorrect field check in tests
### Changed
- Version bumped from 1.22.0-dev to 1.22.1-dev
- Docs updated to reflect v1.22.1 stabilization
### Removed
- Duplicate provider CRUD routes from workflow_engine/api.py (150 lines)
- v1.22 known-failure note about 7 provider API test failures

---

## [1.23.0] - 2026-06-23 — Document Parsing Expansion + PDF/DOCX/XLSX Support
### Added
- **Parser registry**: `BaseParser` ABC with `TextParser`, `JsonParser`, `PdfParser`, `DocxParser`, `XlsxParser`
- **PDF text parsing**: Local text extraction via pypdf with page-level chunks and metadata
- **DOCX parsing**: Local paragraph/heading/table extraction via python-docx with block-type metadata
- **XLSX parsing**: Sheet detection, profiling, searchable text via openpyxl with per-row chunks
- **CSV profiling**: Column type detection, missing value analysis, numeric/categorical summaries
- **ParseResult model**: Structured parse output with text, pages, tables, metadata, warnings
- **DataSourceStatus**: Added PARSING, PARSED_WITH_WARNINGS, INDEXING, UNSUPPORTED, DELETED statuses
- **Chunks/preview endpoints**: GET /workspaces/{ws}/data-sources/{id}/chunks and /preview
- **File safety checks**: Allowed extension validation, path traversal protection, 100 MB size limit
- **Audit events**: document_parse_started, document_parse_completed, document_parse_failed
- **Dependencies**: Added pypdf, python-docx, openpyxl as optional doc-parsing extras
### Changed
- Version bumped from 1.22.1-dev to 1.23.0-dev
- Parser module rewritten with class-based architecture and parser registry
- Parse endpoint handles PDF/DOCX/XLSX files through local parsers
- Data source statuses expanded to cover full parse/index lifecycle
- Evidence chunk metadata includes page_number, sheet_name, block_type where available
- Docs updated to reflect new file type support and limitations
### Removed
- No features removed
### Fixed
- CSV parse now correctly saves profile and updates status without overwriting
### Known limitations
- PDF support is text-extraction only. Scanned image PDFs require OCR (intentionally excluded)
- XLSX formulas are read as values only (data_only=True), no formula execution
- No HTML parser yet (available via lxml but not integrated)
- DOCX embedded images are not extracted

---

## [1.22.0] - 2026-06-23 — Visual Workflow Builder Productization
### Added
- **Version identity**: Updated to 1.22.0-dev for the v1.22 milestone.
- **Workflow builder UX audit**: Documented current UI state, gaps, and fixes.
- **Node catalog cleanup**: Categorized node palette with clear labels and safety warnings.
- **Node configuration panels**: Dedicated config UI for evidence search, synthesis, claim verification, review gate, and trust report nodes.
- **Workflow validation**: Pre-run validation for missing fields, disconnected nodes, unsafe CodeNode.
- **Execution run experience**: Live node status, elapsed time, logs.
- **Execution debugger panel**: Node inputs/outputs, errors, collapsible payloads.
- **Guided demo templates**: Local Evidence Search, Evidence→AI Synthesis→Verify, Risk Review, Trust Report, Data Profile templates.
- **First-run onboarding**: Guided steps for workspace creation, data upload, demo workflow.
- **Provider selection UX**: Dropdown, model dropdown, status indicator, fake provider quick-select.
- **Report actions from workflow result**: Verify claims, scan contradictions, generate trust report, export.
- **Workflow import/export**: JSON export and import workflows.
- **Autosave and version visibility**: Saved state, last saved time, version history.
- **Error and empty state polish**: Helpful messages across workspace, workflow, data sources, execution, and reports.
- **Accessibility and usability pass**: Button labels, form labels, keyboard focus, aria labels, status text.
- **Frontend tests**: Updated and expanded coverage.
- **Backend tests**: Updated where needed.
- **Local demo script**: Seed script for workspace, data, fake provider, and demo workflow.
- **Documentation**: Updated CURRENT_STATE, IMPLEMENTATION_REPORT, WORKFLOW_BUILDER, LOCAL_FIRST_SETUP, README, CHANGELOG.
### Changed
- Version bumped from 1.21.0-dev to 1.22.0-dev.
- Workflow builder now has categorized node palette, config panels, validation, execution debugger, demo templates, onboarding, import/export, autosave, error/empty states, accessibility.
- Frontend test count expanded.
- Backend targeted tests remain passing.

---

## [1.21.0] - 2026-06-23 — Local Provider Runtime + AI-Assisted Evidence Synthesis
### Added
- **Version identity**: Updated to 1.21.0-dev for the v1.21 milestone.
- **Local provider runtime**: Provider model, store, and runtime interface supporting fake/dev, Ollama, and OpenAI-compatible local endpoints.
- **Provider APIs**: Full CRUD endpoints for provider configuration, health checks, model listing, and connection testing.
- **Fake provider**: Deterministic offline provider for development and testing.
- **Ollama provider**: Support for Ollama local LLM with model listing, chat/generate, and health checks.
- **OpenAI-compatible provider**: Support for LM Studio, vLLM, LocalAI, and similar local endpoints.
- **Provider Manager UI**: Frontend provider configuration, health checks, model selection, and default provider setup.
- **Evidence synthesis service**: AI-assisted summary, risk detection, opportunity detection, claim extraction, and report outlining from workspace evidence.
- **Prompt templates**: Grounded prompt templates with anti-hallucination instructions for synthesis modes.
- **Structured output parser**: Robust parser for AI output handling JSON, markdown-fenced JSON, and plain text fallback.
- **EvidenceSynthesisNode**: Workflow node for AI-assisted evidence synthesis with optional auto-verification.
- **AI-assisted report drafting**: Trust-preserving report generation where AI drafts prose but trust data remains authoritative.
- **Demo workflow template**: Evidence Search → Synthesis → Verification → Contradiction Scan → Trust Report workflow.
- **Provider/synthesis audit and observability**: Audit events and metrics for provider calls and synthesis operations.
- **Security and privacy documentation**: Clear explanation of local vs cloud provider data handling.
### Changed
- Version bumped from 1.20.1-dev to 1.21.0-dev.
- Frontend fetch test environment fixed with proper fetch mocking.
- Backend test collection errors categorized and documented.
- Frontend workflow builder updated with Evidence Synthesis node type.
- Documentation updated for provider setup, synthesis service, and AI-assisted reports.
---
## [1.20.0] - 2026-06-23 — Intelligence Quality + Claim Verification v2
## [1.20.1] - 2026-06-23 — Trust UI + Audit Wiring + Release Hardening
### Added
- **Version identity**: Updated to 1.20.1-dev for the v1.20.1 milestone.
- **Verification API client**: Frontend API client methods for all verification and trust report endpoints.
- **Claim Ledger verification UI**: Claim status badges (supported/contradicted/unsupported/uncertain/needs_review), evidence quality indicators, verify button, filter-by-status.
- **Execution verification UI**: Verification summary panel with total/supported/contradicted/unsupported claims, average confidence, evidence coverage.
- **Workspace trust dashboard**: Trust health metrics, recommended next actions, workspace-wide verification triggers.
- **Trust report viewer**: Sectioned trust report display with export to Markdown and JSON.
- **Contradiction UI**: Contradiction scanning from UI, contradiction list with severity/type/description, linked claims.
- **Audit event wiring**: Dedicated audit events for claim_verified, execution_claims_verified, workspace_claims_verified, contradiction_scan_run, trust_report_generated, trust_report_exported.
- **Observability metrics**: verification_duration_ms, claims_verified_count, contradictions_found_count, unsupported_claims_count, average_confidence, and more.
- **Backend audit tests**: Tests cover audit event creation for verification and report actions.
- **Documentation**: Updated CURRENT_STATE.md, CHANGELOG.md, and IMPLEMENTATION_REPORT.md.
### Changed
- Version bumped from 1.20.0-dev to 1.20.1-dev.
- Frontend components enhanced with verification/trust/report sections.
- docs/CURRENT_STATE.md updated to reflect v1.20.1 completion.
### Fixed
- No backend logic changes; all changes are UI/audit/observability additions.
---
### Added
- **Version identity**: Updated to 1.20.0-dev for the v1.20 milestone.
- **Claim verification v2**: Deterministic local claim verifier with supported/contradicted/unsupported/uncertain/needs_review statuses.
- **Evidence resolver**: Resolves evidence references to local snippets with workspace isolation.
- **Contradiction detection**: Local pattern-based contradiction detection for metrics, status, dates, and risk claims.
- **Evidence quality scoring**: Each verified claim gets strong/moderate/weak/missing/contradicted quality labels.
- **Verification APIs**: Claim-level, execution-level, and workspace-level verification with persistent results.
- **Verification workflow nodes**: ClaimVerifierNode, ContradictionScanNode, VerificationSummaryNode.
- **Trust report format**: Reports include verification summary, evidence table, contradictions, and trust scoring.
- **Verification UI**: Frontend panels show claim status, evidence quality, contradictions, and verification summaries.
- **Local trust evaluation suite**: Deterministic eval scenarios for claim verification quality.
- **Audit events**: Verification actions and contradiction scans create audit records.
### Changed
- Claim model expanded with new statuses and evidence quality fields.
- Report renderer upgraded to produce trust-aware reports with full verification sections.
- Documentation updated to explain verification capabilities and limitations.
- Node registry test count updated (28→29) to match new evidence_search node.
### Fixed
- WorkflowToolbar.jsx JSX syntax issue (let declarations inside JSX expressions).
- Pre-existing test count assertion (28→29).
## [1.19.0] - 2026-06-23 — Local Data Sources + Evidence Intelligence Layer
### Added
- **Version identity**: Updated to 1.19.0-dev for the v1.19 milestone.
## [1.16.2] - 2026-06-13 — Backend Hardening & Deprecation Cleanup
### Fixed
- **Pydantic V2 deprecation**: Replaced class-based `Config` with `model_config = ConfigDict(...)` in workflow engine models.
- **Starlette/httpx deprecation**: Installed `httpx2` to resolve `StarletteDeprecationWarning` about httpx TestClient.
- **Version sync**: `pyproject.toml` bumped from 1.14.0 to 1.16.1 to match feature progress in CHANGELOG.
### Removed
- **Skill artifacts**: Cleaned up skills-lock.json and related skill-generated files from the project root.
## [1.16.1] - 2026-06-13 — Frontend Modernization & Design System
### Added
- **Signal-Intelligence Design System**: Refined color palette with richer primary (#2563eb), ember accent (#d97706), emerald success (#059669); deeper dark theme background (#0a0f1c); increased border-radius from 6px to 8px throughout.
- **Animation System**: Shared CSS animation tokens with consistent easing/timing variables; loading skeleton shimmer keyframes with reusable `.skeleton` classes; view fade-in animations for panel transitions.
- **Animated Execution Edges**: Traveling dot effect on connection edges during active workflow runs — communicates "evidence flowing through this path."
- **Node Status Glyphs**: Visual ✓ / ✕ / — indicators for completed/failed/skipped node states.
- **Canvas Polish**: Enhanced node card hover/selected effects with `color-mix()` shadows; improved React Flow handle, minimap, and controls styling.
- **Toolbar Dividers**: Subtle dividers between primary and secondary button groups.
- **Card Hover Lift**: Consistent translateY(-1px) + shadow on claim cards, execution items, and review cards.
- **Unified Status Badges**: Reusable `.status-badge` component classes with subtle backgrounds for verified/unsupported/contradicted/pending states.
- **Gradient Progress Bars**: Updated to match refined palette.
### Changed
- Glass-morphism backdrop blur increased from 12px to 16px in dark mode.
- Card hover effects consistently use `var(--color-primary)` for border highlighting.
- Font rendering with `-webkit-font-smoothing: antialiased` for sharper text.
## [1.16.0] - 2026-06-13 — Backend Connection, 4 New Nodes, Execution UX, Visual Polish
### Added
- **Backend Connection**: Async execute endpoint (removed asyncio.run wrapper); fix saveWorkflow POST/PUT routing for new vs existing workflows; fix execute payload format for real backend mode; list workflows response format handling.
- **4 New Specialist Nodes**: Planner (step-by-step plans), Auditor (quality/completeness audits), Compliance Checker (rule/policy checks), Code Runner (simulated code execution with I/O).
- **Execution UX Depth**: Inline execution preview badges; live streaming indicator with pulse animation; auto-expand completed nodes; execution timeline view with horizontal bar chart; edit-and-replay (modify configs post-execution); WorkflowDiff component for side-by-side definition comparison.
- **Visual Polish**: Dark/light theme toggle; minimap; keyboard shortcuts (Ctrl+S, Delete, Escape, Space, Ctrl+Shift+E, Ctrl+D, Ctrl+C/V); shortcuts help dialog; resizable panels (280-900px); zoom-to-fit; themed React Flow Controls + MiniMap.
## [1.15.0] - 2026-06-13 — Claim Ledger DX, Human Review Gates, Execution History
### Added
- Phase 8: Claim Ledger DX, Human Review Gates, and Execution History — three major workflow builder features.
- **Claim Ledger Report (Phase 1)**: Claim-centric post-execution view is now the default display mode; "Export Decision Report" button generating downloadable JSON reports with full claim details, evidence, and issue trail; search/filter for claims by text content; enhanced claim card expansion with full verification trail (finding → critic issue → evidence link); claim path indicator ("Researcher → Critic → Ledger").
- **Human Review Gates (Phase 2)**: New `decision_system.review_gate` backend node for pausing execution at review points; review queue UI with approve, reject, and request-changes actions; configurable require-notes and allow-edit parameters per gate node; review history with resolved and pending views, full audit trail; real and mock API endpoints for review management.
- **Execution History & Comparison (Phase 3)**: Execution history browser with search, sort, and detail drill-down; side-by-side execution comparison with node and claim diffing; status pill summaries showing claim state evolution across runs; historical run persistence (mock mode) with detail expansion.
- Rich sample workflow mock data with full Researcher → Critic → Synthesizer pipeline.
- Frontend tests passing (35+), build clean.
### Changed
- Project version is now 1.15.0.
## [1.14.0] - 2026-06-12
### Added
- Phase 7: Data Analyst Node — structured data analysis capabilities for the workflow builder.
- **DataAnalystNode** (`decision_system.data_analyst`): Analyzes structured data with 5 analysis types — profile, summary, trend, anomaly, and correlation. Deterministic fake fallback for each analysis type with schema-matching mock data. LLM path samples data (50 rows max) to avoid token limits and injects analysis instructions via system prompt.
- Config: `analysis_type` (5 enums, default "summary"), `max_rows` (1-100000, default 1000), `include_charts` (boolean, default false).
- Input: `data` (array of objects, required), `analysis_type` (string override), `columns` (string array for column focus).
- Output: `analysis` (object), `summary` (string), `charts` (object), `fallback_reason` (string).
- 21 new tests: DataAnalystNode with 10 async tests covering empty data, dict normalization, all 5 analysis types, LLM path, provider error, schema compliance, input override; plus 11 helper tests.
- Frontend mock data entry for DataAnalystNode in the AI Analysis category.
### Changed
- Project version is now 1.14.0.
- Node registry now registers 23 built-in node types (up from 22).
## [1.13.0] - 2026-06-13
### Added
- Phase 6: Bounded Specialist Agent Nodes — 3 new AI-powered drag-and-drop workflow node types for composable war-cabinet architecture.
- **ResearcherNode** (`decision_system.researcher`): Retrieves and synthesizes information from connected data sources. Produces structured findings with citations and confidence scores. Keyword-matched fake fallback (`revenue`, `risk`, `growth` keyword sets).
- **CriticNode** (`decision_system.critic`): Reviews outputs from other nodes for contradictions, unsupported claims, logical fallacies, and confidence calibration. Deterministic rule-based checks as fake fallback with negation-pair matching, trigger-phrase detection, and strictness levels (lenient/balanced/strict).
- **SynthesizerNode** (`decision_system.synthesizer`): Takes multiple evidence/analysis streams and synthesizes them into weighted decision options with trade-off analysis and a recommended course of action. Deterministic keyword-matched fake option generation (`invest`, `expand`, `default` option sets).
- All 3 nodes registered in `create_default_registry()` alongside existing 19 node types (22 total).
- Frontend mock data entries for all 3 node types in the AI Analysis category.
- Integration tests for node chaining: Researcher→Critic, multi-stream→Synthesizer, Synthesizer→Critic validation gate.
- 60 new tests: 6 researcher, 21 critic, 14 synthesizer, 11 helper unit tests, 4 integration tests, 4 chaining integration tests.
### Changed
- Project version is now 1.13.0.
- Node registry now registers 22 built-in node types (up from 19).
## [1.12.0] - 2026-06-13
### Added
- Phase 5: Real LLM Provider Integration — transform AI analysis nodes from fake-only to real LLM-powered.
- Provider configuration system: JSON file-backed ProviderStore with named provider instances.
- Unified `openai_compat` API type: works with any OpenAI-compatible `/chat/completions` endpoint (opencode, OpenAI, OpenRouter, NVIDIA NIM, Groq, Cerebras, Gemini, Ollama, etc.).
- `ProviderConfig` model with `name`, `api_base`, `api_key_env`, `default_model` and built-in validators.
- `LLMClient` — async HTTP client using httpx with SSE streaming, token accumulation, and error mapping.
- Exception hierarchy: `ProviderError`, `AuthenticationError`, `RateLimitError`, `ModelNotFoundError`, `TimeoutError`.
- Provider resolution order: per-node override → system default (first in list) → None (fake fallback).
- 5 AI nodes wired for real LLM calls: TechAnalystNode, RiskAnalystNode, ExtractClaimsNode, VerifyClaimsNode, WriteReportNode.
- Provider CRUD API routes: GET/POST/PUT/DELETE `/providers/{name}`, POST `/providers/{name}/check`, POST `/providers/system/default`.
- CLI provider commands: `decision-system workflow provider {list,add,remove,set-default,check}`.
- ProviderManager React component with provider cards, add form, test connection, and set-default controls.
- Frontend mock API + mock data for providers in mock mode.
- 10 AI node integration tests (fake fallback + LLM path for each node).
- 16 provider API route tests (CRUD, validation, error handling).
- First-is-default semantics: first provider in config is the system default.
### Changed
- Project version is now 1.12.0.
- `DAGEngine` constructor accepts optional `provider_store` parameter.
- `ExecutionContext.resolve_provider()` for provider resolution in nodes.
- Built-in node config schemas updated with provider/model fields.
- httpx added as core dependency; pytest-httpx as dev dependency.
- Cleaned up fallback paths in decision_nodes.py to correctly call legacy fake functions.
- Removed `nvidia` optional dependency.
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
## [1.18.0-dev] - 2026-06-23 — Local product-loop hardening (in development)
### Planned
- Consistent version metadata across all components
- Docker/nginx port alignment
- Frontend auto-detects local backend on port 3000
- Nginx proxy routes for all backend APIs
- Workspace scoping for workflows, executions, reviews
- Persistent execution event timelines
- Multiple review-gate resume correctness
- Claim API validation hardening
- Workspace overview claim summary
- Frontend live-mode hardening and status indicators
- One-command Docker build
- Smoke test script
- Code cleanup and whitespace fixes
## [1.17.0] - 2026-06-23 — Local-first foundation
### Added
- **Persistent workflow stores**: JSON-file-backed stores for workflows, executions, schedules, and reviews
- **Workspace routes**: `GET /workspaces/{workspace_id}/workflows` and workspace-scoped API endpoints
- **Docker Compose setup**: Self-contained backend + frontend deployment via `docker compose up`
- **Claim store foundation**: Persistent claim storage for workflow executions
- **Review-gate pause/resume**: Human-in-the-loop review gates with approve/reject/request-changes
- **CodeNode safety**: Code execution node disabled by default for security
- **Cron parser improvements**: Better schedule parsing and validation
- **Audit endpoints**: Execution detail and history API routes
### Changed
- Version bumped from 1.16.2 to 1.17.0 to reflect local-first milestone
## [1.16.2] - 2026-06-13 — Backend Hardening & Deprecation Cleanup


## [1.23.1] - 2026-06-23 — Finish Document Ingestion Wiring + Test Reliability
### Fixed
- **DataSourceStore local data directory**: Default construction now honors `DECISION_SYSTEM_DATA_DIR` environment variable instead of hardcoding `.decision_system`
- **Upload source_id consistency**: `store.create()` accepts optional `source_id` parameter so the upload endpoint uses the same ID for file storage and the data source record
- **Upload endpoint file type support**: Added `pdf`, `docx`, `xlsx` to supported upload types using shared `SUPPORTED_UPLOAD_EXTENSIONS` constant
- **Raw upload robustness**: Upload endpoint accepts raw bytes body (no JSON wrapper required)
- **XLSX profile bug**: Fixed `NameError: name 'sheets' is not defined` by saving sheet metadata before closing the workbook
- **Indexing with warnings**: Index endpoint now allows files with `parsed_with_warnings` status when chunks exist
- **Evidence source names**: Evidence search results use the DataSource's `original_filename` instead of internal stored filenames
- **File safety hardening**: Added filename sanitization, path traversal protection, and 100 MB max file size limit
- **Docker install**: Backend Dockerfile now installs doc-parsing extras (`pypdf`, `python-docx`, `openpyxl`)
- **Frontend text**: Data Sources page in legacy web app correctly lists PDF, DOCX, XLSX as supported
- **Test collection**: Renamed duplicate `test_ollama_provider.py` to `test_ollama_provider_legacy.py` to fix module name collision
- **pytest-asyncio**: Added to dev dependencies so async tests work by default
### Changed
- Version bumped from 1.23.0-dev to 1.23.1-dev
- Evidence search in routes now passes `source.original_filename` to Chroma indexing
- Docs updated to reflect correct file type support and known limitations
### Removed
- No features removed
### Known limitations
- PDF support is text-extraction only (pypdf). Scanned image PDFs require OCR (intentionally excluded)
- XLSX formulas are read as values only (data_only=True), no formula execution
- DOCX embedded images are not extracted
- Data Sources UI is in the legacy static web app (`web/index.html`), not yet in the React workflow builder
- API-level upload tests using ASGITransport may hang on Python 3.13 (environmental compatibility issue)
## [1.27.1] - 2026-06-24 — Frontend Security UI + Permission-Aware Components
### Added
- **Permission context hook**: usePermission() provides current user, role, permissions, security mode, and can() permission check throughout the React app
- **PermissionGuard component**: Wraps UI sections behind permission checks with fallback UI for unauthorized access
- **ForbiddenPage component**: Shared 403 permission error page with role info and required permission display
- **AuditLogPage component**: Workspace audit event viewer with event type/actor filters, summary stats, and sorted event list
- **AppNav security status**: Sidebar displays current user, role label, and demo/governed mode indicator
- **SettingsPage security tab**: Security mode toggle (demo vs governed), governance rule checkboxes, audit retention setting
- **SettingsPage users tab**: User CRUD table with create/delete, workspace membership management with role assignment
- **SettingsPage audit tab**: Full audit log viewer with summary cards and filterable event list
- **ProviderManager key display**: Shows env-var name (api_key_env) and redaction notice for provider API keys
- **Mock identity data**: MOCK_IDENTITY, MOCK_USERS, MOCK_MEMBERSHIPS, MOCK_SECURITY_SETTINGS, MOCK_PERMISSION_MATRIX, MOCK_AUDIT_EVENTS
- **API client identity methods**: getCurrentIdentity, listUsers, createUser, updateUser, deleteUser, workspace membership CRUD, security settings, permission matrix, audit events
### Changed
- Version bumped from 1.27.0-dev to 1.27.1-dev
- App root wrapped with PermissionProvider context
- SettingsPage receives onNavigate prop and has full tab-based UI
- AppNav shows security status (user, role, mode) in sidebar footer
### Fixed
- mockData.js duplicate export block removed to fix frontend build
- SettingsPage now properly loads security settings and users from API
### Known limitations
- Frontend permission UI requires the identity API backend to be running in governed mode for real enforcement
- In demo mode, all permissions are granted (can() returns true)
## [1.27.0] - 2026-06-24 — Security, Auth, RBAC + Governance Foundation
### Added
- **Local identity model**: User model with roles (owner, admin, analyst, reviewer, viewer)
- **Workspace membership**: Role-based workspace membership with scoped access
- **Permission system**: 14+ permissions mapped to roles with a permission-checking layer
- **API route permission enforcement**: Permission checks on workspaces, data sources, evidence, workflows, providers, reports, audit, settings
- **Frontend permission states**: Role-aware UI that hides/disables restricted actions and handles 403 gracefully
- **Governance-aware review gates**: Role enforcement for approve/reject, actor recording, audit
- **Secure export governance**: Permission checks on report export, audit events for exports
- **Provider secret safety**: Redacted API keys in responses, audit on config changes, secrets excluded from exports
- **Audit log viewer**: GET /workspaces/{id}/audit/events with filters, frontend Audit Log page
- **Workspace isolation enforcement**: Verified cross-workspace blocking for all major artifact types
- **Security mode settings**: demo | governed mode, default_role, exports_require_admin, review_requires_reviewer_role
- **Security docs**: SECURITY_MODEL.md and THREAT_MODEL.md with honest local-first assumptions
### Changed
- Version bumped from 1.26.1-dev to 1.27.0-dev
- Audit events now include real actor identity
- Provider API responses redact secrets (api_key_present boolean only)
- Review gate resolution checks user role
- Frontend API client handles 403 responses
### Fixed
- Provider secrets no longer exposed in API responses, exports, or logs
- Cross-workspace data leakage prevented for all artifact types
- Review gates can no longer be resolved by unauthorized users
### Known limitations
- No cloud auth or SSO — this is a local governance foundation
- No password-based authentication — identity is local/system
- No encryption at rest for stored data
- No audit webhook or SIEM integration
- No ABAC/ReBAC — role-based only
- No session management — intended for local single-user/small-team use
### Removed
- No features removed

## [1.27.2] - 2026-06-24 — Test Harness + Docker Smoke + Release Baseline
### Changed
- Version bumped from 1.27.1-dev to 1.27.2-dev
- **Test infrastructure migration**: All API tests migrated from Starlette's synchronous TestClient to httpx.AsyncClient with ASGITransport to fix Python 3.13 + anyio 4.14 hang issues
- **conftest.py**: Strengthened monkey-patches for anyio.to_thread.run_sync; added async_client fixture with isolated temp dirs and env setup
### Fixed
- **Starlette/httpx compatibility**: async route tests now execute correctly with pytest-asyncio 0.26.0
- **Test dependency hygiene**: pytest-asyncio correctly declared as dev dependency in pyproject.toml
### Added
- **scripts/validate-local.sh**: CI-ready validation script (git diff --check, backend tests, frontend tests, frontend build)
- **Validation documentation**: Exact commands documented in CURRENT_STATE.md, README.md, and IMPLEMENTATION_REPORT.md
- **Route regression tests**: GET /health, /identity/me, /identity/permissions, /identity/settings, /workspaces/{id}/audit/events, /workspaces/{id}/audit/summary, /providers, /providers/default, /workspaces/{id}/data-sources, /workspaces/{id}/graph, /workspaces/{id}/reports all tested
### Security
- Local validation baseline established for contributors
### Known limitations
- Docker not available in sandbox environment — Docker smoke cannot be verified here
- E2E demo smoke cannot be run without Docker or running backend
- No password authentication — identity is header-based in governed mode
- No encryption at rest — data is stored as plain JSON/SQLite files
- Demo mode is default — permission enforcement requires governed mode
- This is a local governance foundation, not enterprise auth
### Removed
- No features removed
