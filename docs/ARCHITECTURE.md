# Architecture

## System Purpose

The Agentic AI Decision System is evolving into a Company Intelligence Engine. It creates evidence-backed decision reports from local documents and now starts extracting local entity and relationship structure for future hidden-pattern detection.

It is backend-first and CLI-first: users place documents in `company_docs/`, index them locally, extract graph structure locally, then ask a decision question.

The system is not an autonomous decision-maker. It produces a decision brief that separates cited evidence, verified claims, contradicted claims, unsupported assumptions, risk notes, confidence, and human review needs.

## Bounded Workflow

The workflow is a linear LangGraph state machine:

```text
START
  -> retrieve_evidence
  -> technical_analyst
  -> risk_analyst
  -> claim_extraction
  -> verifier
  -> report_writer
  -> END
```

There are no back edges, free-form debate loops, or agent-to-agent chat edges. Each node has a narrow responsibility and passes structured state to the next node.

## Evidence Pipeline

```text
company_docs/
  -> document loader
  -> chunker
  -> hash embeddings
  -> local Chroma collection
  -> retriever
  -> EvidenceChunk objects
```

Retrieval returns `EvidenceChunk` objects, not answers. Each chunk includes an evidence ID, source filename, chunk ID, text, and retrieval score.

## Local Knowledge Graph

v0.2 adds a graph-like JSON store without introducing a database:

```text
company_docs/
  -> document loader
  -> chunker
  -> deterministic graph extractor
  -> .decision_system/graph/knowledge_graph.json
  -> graph inspector
```

The graph contains `Entity`, `Relationship`, and `KnowledgeGraph` Pydantic models. Entities and relationships keep source evidence IDs and source filenames so every extracted connection remains auditable.

The first extractor is deliberately rule-based and offline. It recognizes phrases such as `depends on`, `owned by`, `caused`, `affects`, `blocks`, `mitigates`, explicit `related to`, and `CONTRADICTS:` markers. It does not call a real LLM and does not add new agents.

## Local Structured Data Catalog

v0.3 adds local CSV intake and profiling without adding a database:

```text
company_data/
  -> manifest.json
  -> category folders
  -> fake demo CSV files or local private CSV files
  -> CSV profiler
  -> .decision_system/data_profiles/profiles.json
  -> data inspector
```

The data catalog is intentionally descriptive. It profiles CSV shape and quality signals: row count, column count, missing values, numeric summaries, categorical top values, date-like columns, and warnings. It does not ingest data into Chroma, join it with the claim ledger, train models, call hosted providers, or run autonomous analysis.

Only fake `demo_*.csv` files should be committed. Private company CSV files remain local.

v0.3.2 adds a local public dataset importer. Raw files stay in ignored `datasets/`; supported `.csv`, `.xlsx`, and `.xls` files are converted to ignored `company_data/<category>/imported_*.csv` files. SQL Server `.bak` files are explicitly skipped. Import results are recorded in `.decision_system/imports/import_manifest.json`.

## Analysts

The technical analyst and risk analyst produce structured `AgentMemo` objects. They do not own final truth. Their claims must pass through the claim ledger and verifier before the report writer can use them as evidence-backed statements.

## Claim Ledger

Claim extraction converts memos into `Claim` records. The ledger keeps claim IDs, source agent, claim text, evidence IDs, status, confidence, and verification notes.

Claim statuses are:

- `pending`
- `verified`
- `unsupported`
- `contradicted`

Contradicted and unsupported claims are preserved for auditability.

## Verifier

The verifier checks whether cited evidence exists and whether a deterministic `CONTRADICTS:` marker is present. This is intentionally simple and testable. It is not a semantic truth engine yet.

## Report Writer

The report writer renders from claim ledger state, not raw model prose. Reports include recommendation, options, evidence citations, risks, contradictions, unsupported assumptions, confidence level, human review requirements, and the original question.

## Ontology Layer (v0.4)

The ontology layer maps CSV columns to standardized business concepts:

```text
data_profiles/profiles.json
  -> column-to-concept matcher (38 concepts, deterministic rules)
  -> OntologyMap (concepts, column_mappings)
  -> .decision_system/ontology/ontology_map.json
  -> decision-system map-ontology
  -> decision-system inspect-ontology
```

Concepts are typed (entity, metric, relationship, risk) so downstream analysis can reason about what kind of data exists without parsing column names.

## Orchestration Layer (v0.4)

The orchestration layer is a bounded, deterministic pipeline that ties all subsystems together for end-to-end decision support:

```text
user question
  -> Problem Analyzer: keyword → DecisionType + required data/tools/roles/tiers
  -> Planner: enrich artifact paths and analysis notes
  -> Dispatcher: select tools, roles, execution order, skip irrelevant tools
  -> Sandbox: validate and execute allowed actions (read profiles, graph, detectors, save)
  -> Detect: run pattern/vulnerability detectors
  -> Judge: confidence scoring, key findings, risks, human review flags
  -> Persistence: save session to .decision_system/orchestration/runs/
  -> Output: structured result dict for CLI / downstream consumption
```

Key design principles:
- **All steps are deterministic.** No LLM calls in the orchestration layer itself.
- **Sandbox is an allow-list, not a security boundary.** It validates function names and rejects destructive patterns.
- **Decision types** map to domain-specific tool chains: financial → profile + detect; strategic → profile + graph + detect; technical → graph only; general → profile only.
- **Storage tiers** (4 tiers) describe which data artifacts each decision type needs.
- **Judge summary** downgrades confidence when data is missing and flags high-severity insights for human review.

## Insight Engine (v0.4)

The deterministic insight engine reads saved data profiles, the local knowledge graph, and raw CSV files under ``company_data/`` to surface patterns and vulnerabilities without requiring a real LLM.

```text
.company_data/          <- local CSV datasets
  |
  v
.csv profiler           <- row shape, missing values, numeric summaries
  |
  v
.data_profiles/profiles.json   <- cached profile summaries
  |
  v
profile-based detectors        <- missing data, data quality, sales
                                 channel concentration, customer
                                 concentration
  |
  v
.csv loader                    <- raw CSV rows (only when profile
                                 data is insufficient)
  |
  v
business CSV detectors         <- revenue/expense risk, marketing ROI,
                                 feedback risk, product risk,
                                 competitor risk, operations bottleneck,
                                 analytics conversion risk, strategic gaps
  |
  v
knowledge_graph                <- dependency risk, contradiction,
  |                                 ownership gap
  v
.insights/insights.json        <- ranked insight records
  |
  v
decision-system detect-patterns   (offline, testable, deterministic)
decision-system inspect-insights  (human-readable summary)
```

All detection logic is rule-based and offline. No real LLM execution is required. Thresholds are intentionally conservative to minimise false positives.

## Inspectability

The CLI exposes debug surfaces:

- `decision-system inspect-index`
- `decision-system extract-graph`
- `decision-system inspect-graph`
- `decision-system init-data-catalog`
- `decision-system profile-data`
- `decision-system inspect-data`
- `decision-system import-datasets`
- `decision-system inspect-imports`
- `decision-system detect-patterns`
- `decision-system inspect-insights`
- `decision-system ask "..." --show-evidence`
- `decision-system ask "..." --json`
- `decision-system ask "..." --save-run`

These commands make retrieved evidence, workflow state, claim verification, insight detection, and final report output inspectable.

## Evaluation Harness

`decision-system eval` runs local cases from `evals/cases/`. Each case writes temporary documents, indexes a temporary Chroma store, runs the normal workflow with the fake provider, and checks expectations.

Eval cases cover:

- useful billing evidence
- empty context
- explicit contradiction markers

Eval results are printed by default and are only saved under `evals/results/` when `--save-results` is passed.

## Optional Providers

The provider factory supports:

- `fake`: deterministic offline provider and default
- `nvidia_nim`: optional hosted provider using NVIDIA NIM

The fake provider remains the default for tests, evals, and offline runs.

## NVIDIA NIM Provider

`NvidiaNimProvider` uses NVIDIA NIM's OpenAI-compatible API through the `openai` Python package. It reads credentials, base URL, model, and generation settings from `.env` or environment variables only. It asks the model for strict JSON and validates responses into Pydantic models before they enter workflow state.

The local report renderer still owns final report writing.

## Current Limits

- No frontend.
- No database.
- No auth or permission model.
- No enterprise connectors.
- No autonomous external actions.
- No PDF parsing.
- No hybrid keyword search.
- No semantic contradiction verifier.
- No long-term persisted claim ledger.
- No database-backed graph store.
- No semantic entity resolution beyond deterministic v0.2 rules.
- No database-backed structured data catalog.
- No connector-backed data intake.
- No semantic analysis of CSV profiles yet.
- No native SQL Server `.bak` import.
- Hash embeddings are for local testing, not production retrieval quality.
