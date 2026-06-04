# Agentic AI Decision System

Backend-first agentic decision brief system for local evidence, bounded analysis, claim verification, and cited decision reports.

## What This Project Does

This project turns local documents into auditable decision briefs. It:

- loads local `.md` and `.txt` documents
- chunks and indexes evidence in a local Chroma vector store
- runs a bounded LangGraph workflow
- creates technical and risk memos
- extracts material claims
- verifies claims against retrieved evidence
- produces a cited decision report from claim ledger state

## Why This Exists

The goal is to prototype safer multi-agent decision support. Final reports come from verified claim ledger state, not uncontrolled agent chat. Contradictions, unsupported assumptions, citations, confidence, and human review needs are kept visible instead of being smoothed away.

## Current Features

- CLI commands
- local `.md` / `.txt` documents
- Chroma vector store
- deterministic fake provider
- optional NVIDIA NIM provider
- claim ledger
- verifier
- report writer
- inspectability commands
- evaluation command

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
   ↓
document loader
   ↓
chunker
   ↓
Chroma vector store
   ↓
retriever
   ↓
LangGraph workflow
   ↓
technical analyst
   ↓
risk analyst
   ↓
claim extraction
   ↓
verifier
   ↓
report writer
   ↓
decision report
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

## Quick Start With Fake Provider

The fake provider is the default and works without any API key. The repo includes `company_docs/demo_billing.md` for local smoke tests.

```bash
decision-system index
decision-system inspect-index
decision-system ask "Should we migrate billing?"
decision-system ask "Should we migrate billing?" --show-evidence
decision-system ask "Should we migrate billing?" --json
decision-system ask "Should we migrate billing?" --save-run
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
NVIDIA_NIM_MODEL=deepseek-ai/deepseek-v4-flash
```

Run one question with NIM:

```bash
decision-system ask "Should we migrate billing?" --provider nvidia_nim
```

The NVIDIA provider uses LangChain's `ChatNVIDIA` integration and validates model output into Pydantic models before it enters the workflow.

Never commit `.env` or real API keys. The fake provider remains the default for tests and offline runs.

## CLI Commands

- `decision-system index`: index local documents from `company_docs/`
- `decision-system inspect-index`: show collection name, chunk count, and source filenames
- `decision-system ask "..."`: run the decision workflow and print Markdown
- `decision-system ask "..." --show-evidence`: print retrieved evidence before the report
- `decision-system ask "..." --json`: print structured workflow state
- `decision-system ask "..." --save-run`: save full run JSON under `.decision_system/runs/`
- `decision-system ask "..." --provider nvidia_nim`: use NVIDIA NIM for one run
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
- `tests`: offline unit and CLI tests
- `docs`: architecture, setup, development, and troubleshooting docs
- `company_docs`: local docs folder; only demo docs should be committed

## Testing

```bash
python -m pytest -q
decision-system eval
```

## Troubleshooting

- **No documents indexed**: make sure `company_docs/` exists and contains `.md` or `.txt` files. The repo includes `company_docs/demo_billing.md`.
- **Missing NVIDIA key**: set `NVIDIA_API_KEY` in `.env` or use the default fake provider.
- **Chroma warning**: Chroma may emit dependency deprecation warnings during tests; these do not usually block local runs.
- **Wrong provider**: check `DECISION_PROVIDER` in `.env`, or pass `--provider fake` / `--provider nvidia_nim`.
- **Windows path with spaces**: quote paths and run commands from the repo root.
- **`.env` not loaded**: run commands from the repo root and confirm the file is named exactly `.env`.

## Roadmap

- v0.2: real provider comparison
- v0.3: better retrieval
- v0.4: FastAPI backend
- v0.5: frontend
- v0.6: database and saved decision history
