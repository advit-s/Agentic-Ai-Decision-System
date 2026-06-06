# Architecture

## System Purpose

The Agentic AI Decision System is evolving into a Company Intelligence Engine. It creates evidence-backed decision reports from local documents and now starts extracting local entity and relationship structure for future hidden-pattern detection.

It is backend-first and CLI-first: users place documents in `company_docs/`, index them locally, extract graph structure locally, then ask a decision question.

The system is not an autonomous decision-maker. It produces a decision brief that separates cited evidence, verified claims, contradicted claims, unsupported assumptions, risk notes, confidence, and human review needs.

The broader product direction is captured in [Product Vision](PRODUCT_VISION.md): Phase 1 builds a company-specific intelligence layer from data, ontology, graph structure, and insights; Phase 2 adds bounded orchestration over that layer.

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
  -> Problem Analyzer: keyword -> DecisionType + required data/tools/roles/tiers
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
- **Decision types** map to domain-specific tool chains: financial -> profile + detect; strategic -> profile + graph + detect; technical -> graph only; general -> profile only.
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
- `decision-system check-hygiene`
- `decision-system eval-providers`
- `decision-system inspect-provider-evals`

These commands make retrieved evidence, workflow state, claim verification, insight detection, and final report output inspectable.

## FastAPI Backend (v0.8)

v0.8 adds a local-development FastAPI backend over the existing CLI/backend services:

```text
API client
  -> FastAPI route
  -> existing document, workflow, context, orchestration, war-room, ontology,
     insight, or eval service
  -> structured JSON response
```

The API does not add a frontend, auth, database, new provider, or new agent loop.
Routes call the same bounded services used by the CLI and return structured JSON
with consistent error envelopes. Stack traces are not exposed to clients.

The v0.8 route surface is:

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

`decision-system serve-api` runs uvicorn for local development. Tests use
FastAPI `TestClient` directly and do not require a live server or real API keys.

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
- `ollama`: optional local provider using Ollama's local HTTP API

The fake provider remains the default for tests, evals, and offline runs.

## NVIDIA NIM Provider

`NvidiaNimProvider` uses NVIDIA NIM's OpenAI-compatible API through the `openai` Python package. It reads credentials, base URL, model, and generation settings from `.env` or environment variables only. It asks the model for strict JSON and validates responses into Pydantic models before they enter workflow state.

The local report renderer still owns final report writing.

## Ollama Provider (v0.7)

`OllamaProvider` uses Ollama's local `/api/chat` endpoint through Python's
standard library HTTP client. It reads `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
generation settings from `.env` or environment variables. The provider asks for
strict JSON and validates responses into Pydantic models before the workflow
uses them.

Ollama is local testing only. It is not contacted unless selected with
`DECISION_PROVIDER=ollama` or `decision-system ask --provider ollama`.

## Provider Experiment Harness (v0.7)

v0.7 adds a provider comparison harness without changing the bounded workflow:

```text
evals/provider_cases/*.json
-> ProviderExperimentCase
-> selected provider: fake | nvidia_nim | ollama
-> technical_memo
-> risk_memo
-> extract_claims
-> validate AgentMemo / Claim objects
-> ProviderExperimentSuiteResult
-> optional .decision_system/evals/provider_results_<provider>_<timestamp>.json
```

Provider experiments measure whether a provider can produce valid structured
memos and claims for fixed cases. They do not judge model quality deeply, do
not bypass the claim ledger, and do not let provider prose become the final
report. `provider-health` exits successfully even when real providers are not
configured. `eval-provider` skips unconfigured NIM/Ollama providers unless
`--require-configured` is used.

## Provider Evaluation Harness (v0.7.1)

v0.7.1 adds a safer comparison harness for fake, NVIDIA NIM, and Ollama provider
behavior:

```text
built-in ProviderEvalCase list
-> fake provider or mocked optional provider
-> structured memo / claim probes
-> contradiction, unsupported-claim, and citation scoring
-> malformed JSON, refusal, and timeout safe-failure probes
-> ProviderEvalSuiteResult
-> optional .decision_system/provider_evals/provider_eval_results.json
```

The default mode never contacts NVIDIA NIM or Ollama. NIM and Ollama are mocked
unless `--manual-real-provider` is explicitly passed. Manual mode is for local
experiments only and is not used by automated tests. The harness records
schema validity, JSON validity, citation grounding, hallucination risk,
contradiction handling, unsupported-claim handling, errors, and notes. It does
not change `DECISION_PROVIDER`, does not write reports, does not bypass the
claim ledger, and stores saved results under ignored generated local state.

## Decision Context and Insight-Aware Reports (v0.5)

v0.5 adds a decision context layer that assembles relevant signals from local stores before the report is written:

```text
question -> DecisionContextBuilder
  -> problem analysis
  -> load ontology map (.decision_system/ontology/ontology_map.json)
  -> load insights (.decision_system/insights/insights.json)
  -> load latest orchestration run (.decision_system/orchestration/runs/)
  -> select relevant ontology concepts (required from analysis + keyword match)
  -> select relevant insights (high/critical always-include + data category + keyword + ontology overlap)
  -> extract graph signals (top connected entities + contradictions)
  -> build human review items (high/critical insights + contradictions + low-confidence judge + missing data)
  -> DecisionContext
  -> .decision_system/contexts/<run_id>.json
```

The `ask` command accepts three new optional flags for v0.5:
- `--include-insights`: adds selected insights under a "Business/Data Insights" section.
- `--orchestrated`: includes orchestration summary and judge findings.
- `--save-context`: writes full context JSON for inspection.

The `build-context` command runs the context builder standalone and prints the assembled context without invoking the LangGraph workflow. `--json` outputs structured JSON. `--save` writes to disk.

All insight-aware sections are conditionally rendered so the default `ask` output remains unchanged. Insights are always phrased as detected signals with severity and confidence. Features are defined by detecting concrete patterns and signals in the data, not by comparing insights to each other.

## War-Cabinet Agent Context Protocol (v0.6)

v0.6 introduces a bounded agent context protocol for structured multi-role analysis:

```text
business question
-> build_higher_context (frozen, immutable)
-> build_dispatch_spec (role selection + personal contexts)
-> CommonWorkspace (append-only, structured artifacts)
-> simulate specialist agents (deterministic, reads local stores via sandbox)
-> run_judge (4 deterministic intervention rules)
-> persist WarRoomRun to .decision_system/war_room/runs/<run_id>.json
```

- **HigherContext is deep-frozen.** All agents read it, but none mutate it or nested context values.
- **Personal contexts are role-scoped.** Each specialist gets a bounded task, perspective, allowed tools, and focus areas.
- **Common workspace is append-only.** Agents write `WorkspaceArtifact` records; no agent can delete or overwrite another's artifacts.
- **Judge is deterministic.** Four rules: unsupported artifacts (medium), high/critical insight links (high + human review), contradiction links (critical + human review), low confidence (low warning).
- **Sandbox is an allow-list.** Agents can only call `read_profiles`, `read_graph`, `read_insights`, `read_context`, `save_artifact`. Destructive operations are blocked.
- **No LLM calls.** All agent simulations are deterministic artifact generators that read local stores.
- **Structured storage, not chat.** Coordination happens through typed Pydantic artifacts, not free-form agent transcripts.

Three new CLI commands:
- `decision-system plan-war-room "question"`: dispatches roles without executing agents.
- `decision-system run-war-room "question"`: full pipeline execution.
- `decision-system inspect-war-room`: renders the latest run summary.

## War-Room Evaluation (v0.6.1)

v0.6.1 adds an offline evaluation layer for the war-cabinet protocol:

```text
evals/war_room_cases/*.json
-> run actual war-room pipeline
-> evaluate role/tool/category expectations
-> run quality gates
-> print structured suite result
-> optionally save .decision_system/evals/war_room_results.json
```

Quality gates check:
- higher context exists
- higher context rejects top-level and nested mutation
- personal contexts reference the higher context
- common workspace remains append-only
- judge output exists
- high/critical judge interventions require human review
- artifacts avoid external API markers
- artifacts remain bounded and do not look like chat transcripts

The eval layer is deterministic and offline. It does not add new agents, call real providers, or create free-form agent-to-agent chat.

## Repository Hygiene and Release Readiness (v0.6.2)

v0.6.2 adds a repository hygiene layer for release review. It does not change
application decision behavior, provider behavior, storage architecture, or the
bounded war-room protocol.

```text
repo root
-> check generated/local paths
-> check ignored raw datasets and imported CSVs
-> check AGENTS.md and CLAUDE.md presence
-> check fake provider default
-> check CLI entry point
-> HygieneReport
```

`decision-system check-hygiene` emits a human-readable report. `--json` emits
the same structured `HygieneReport` state for automation. Existing local
generated state such as `.decision_system/`, `__pycache__/`, `.pytest_cache/`,
`datasets/`, and `company_data/**/imported_*.csv` is reported as a warning when
the files are ignored, not as a failure. Missing agent instructions, missing
critical config, or a non-fake default provider are failures.

The release checklist in `docs/RELEASE_CHECKLIST.md` complements the hygiene
command by documenting install, test, smoke, eval, git hygiene, and skills
directory checks.

## Current Limits

- No frontend.
- No database.
- No auth or permission model.
- API is local-development only.
- No enterprise connectors.
- No autonomous external actions.
- No PDF parsing.
- No hybrid keyword search.
- No semantic contradiction verifier.
- No long-term persisted claim ledger.
- No database-backed graph store.
- No semantic entity resolution beyond deterministic v0.2 rules.
- Context selection is rule-based: no real LLM re-ranks insights.
- Human review items are coarsely heuristically derived (high severity + contradiction + low judge confidence + missing data).
- No database-backed structured data catalog.
- No connector-backed data intake.
- No semantic analysis of CSV profiles yet.
- No native SQL Server `.bak` import.
- Hash embeddings are for local testing, not production retrieval quality.
- Provider experiments do not integrate with war-room specialist artifacts yet.
