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

## Why This Exists

The goal is to prototype safer multi-agent decision support and grow toward a Company Intelligence Engine: software that uses past and present company data to surface hidden patterns, vulnerabilities, relationships, contradictions, and risks that are hard for humans to see.

Final reports come from verified claim ledger state, not uncontrolled agent chat. Contradictions, unsupported assumptions, citations, confidence, and human review needs are kept visible instead of being smoothed away.

See [Product Vision](docs/PRODUCT_VISION.md) for the longer two-phase vision: company data understanding first, then bounded orchestration over that intelligence layer.

## Current Features

- CLI commands
- local `.md` / `.txt` documents
- Chroma vector store
- deterministic fake provider
- optional NVIDIA NIM provider
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
```

The v0.6.1 evaluation layer runs the actual war-room pipeline for known business questions and checks expected roles, tools, data categories, artifacts, and judge summaries. Quality gates verify higher context deep immutability, personal context references, append-only workspace semantics, judge execution, offline boundaries, and no chat-transcript-shaped artifacts. Saved results go to `.decision_system/evals/war_room_results.json`.

## What Is Not Included Yet

- frontend
- database
- auth
- enterprise connectors
- Slack/Jira/email/GitHub integrations
- autonomous external actions

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
NVIDIA_API_KEY=your_key_here
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
- `decision-system provider-health`: show provider configuration status
- `decision-system provider-smoke --provider X`: run a one-off provider smoke test
- `decision-system eval-provider --provider X`: run provider experiment cases
- `decision-system ask --provider ollama`: use Ollama for memo/claim generation only

## Project Structure

- `src/decision_system/agents`: bounded technical and risk analyst wrappers
- `src/decision_system/graph`: LangGraph state, nodes, and workflow
- `src/decision_system/rag`: document loading, chunking, embeddings, vector store, retrieval
- `src/decision_system/ledger`: claim ledger and verifier
- `src/decision_system/llm`: fake provider, NVIDIA NIM provider, Ollama provider, provider factory
- `src/decision_system/provider_experiments`: provider experiment models, runner, store, inspector
- `src/decision_system/reports`: decision report renderer
- `src/decision_system/evals`: local evaluation models and runner
- `src/decision_system/graphing`: entity and relationship graph models, extraction, store, and inspection
- `src/decision_system/data_catalog`: local data catalog initialization, CSV profiling, storage, and inspection
- `src/decision_system/insights`: deterministic pattern and vulnerability detection
- `src/decision_system/war_room`: war-cabinet protocol, quality gates, and eval runner
- `evals/war_room_cases`: offline war-room evaluation cases
- `tests`: offline unit and CLI tests
- `docs`: architecture, setup, development, and troubleshooting docs
- `company_docs`: local docs folder; only demo docs should be committed
- `company_data`: local structured data folder; only manifest, `.gitkeep`, and `demo_*.csv` files should be committed

## Testing

```bash
python -m pytest -q
decision-system eval
decision-system eval-war-room
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

Upcoming:
- v0.8: richer retrieval and bounded specialist tools
- v0.9: FastAPI backend
- v1.0: frontend, database, auth, and saved workspaces
