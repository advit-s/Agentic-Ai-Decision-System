# Changelog

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
- Optional NVIDIA NIM provider using LangChain's `ChatNVIDIA` integration.
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
