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

## Pattern and Vulnerability Detection

```bash
decision-system detect-patterns
decision-system inspect-insights
```

The v0.4 insight engine uses saved data profiles, local CSV datasets, and the local knowledge graph to surface deterministic offline insights such as revenue risk, customer concentration, marketing ROI risk, competitor risk, operations bottlenecks, dependency risks, contradictions, missing data, and data quality issues.

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
- `decision-system eval`: run local evaluation cases
- `decision-system eval --json`: print structured evaluation results
- `decision-system eval --save-results`: save evaluation results under `evals/results/`

## Project Structure

- `src/decision_system/agents`: bounded technical and risk analyst wrappers
- `src/decision_system/graph`: LangGraph state, nodes, and workflow
- `src/decision_system/rag`: document loading, chunking, embeddings, vector store, retrieval
- `src/decision_system/ledger`: claim ledger and verifier
- `src/decision_system/llm`: fake provider, NVIDIA NIM provider, provider factory
- `src/decision_system/reports`: decision report renderer
- `src/decision_system/evals`: local evaluation models and runner
- `src/decision_system/graphing`: entity and relationship graph models, extraction, store, and inspection
- `src/decision_system/data_catalog`: local data catalog initialization, CSV profiling, storage, and inspection
- `src/decision_system/insights`: deterministic pattern and vulnerability detection
- `tests`: offline unit and CLI tests
- `docs`: architecture, setup, development, and troubleshooting docs
- `company_docs`: local docs folder; only demo docs should be committed
- `company_data`: local structured data folder; only manifest, `.gitkeep`, and `demo_*.csv` files should be committed

## Testing

```bash
python -m pytest -q
decision-system eval
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

## Roadmap

- v0.1: decision brief core
- v0.2: graph/entity extraction
- v0.3: company data intake + profiling
- v0.4: orchestration + ontology + insight engine
- v0.5: insight-aware decision reports
- v0.6: real provider experiments
- v0.7: FastAPI backend
- v0.8: frontend
- v0.9: database + auth + saved workspaces
