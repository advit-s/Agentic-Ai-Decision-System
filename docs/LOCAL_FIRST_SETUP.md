# Local-First Setup Guide

This guide explains how to run the **Agentic Decision System** entirely locally,
with no cloud accounts, no API keys, and all data stored on your machine.

---

## Quick Start (Docker Compose — Recommended)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v24+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.21+)

### Start the app

```bash
# Clone the repository (if not already cloned)
git clone https://github.com/your-org/Agentic-Ai-Decision-System.git
cd Agentic-Ai-Decision-System

# Start backend and frontend
docker compose up
```

### Open the app

```text
Frontend:  http://localhost:3000
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs
```

### Stop the app

```bash
docker compose down
```

Your data remains in `.decision_system/`.

### Reset all local data

```bash
docker compose down
rm -rf .decision_system/
```

> ⚠️ **Warning:** This permanently deletes all local workflows, executions,
> reviews, claims, documents, and reports.

---

## Manual Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- npm 9+

### Backend setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install with dev dependencies
python -m pip install -e ".[dev]"

# Start the API server
decision-system serve-api --host 0.0.0.0 --port 8000
```

### Frontend setup

```bash
cd web/workflow-builder
npm install

# Development mode (with hot reload)
npm run dev

# Production build
npm run build
```

### Open the app

```text
Frontend (dev): http://localhost:5173
Backend:        http://localhost:8000
```

The Vite dev server proxies API calls (`/workflows`, `/executions`, etc.)
to the backend at `http://localhost:8000`.

---

## Data Storage

All persistent data is stored under `.decision_system/` in the project root:

```text
.decision_system/
├── app.db              # Workspace metadata (SQLite)
├── workflow_engine/    # Workflow definitions, executions, versions
│   ├── workflows/      # Workflow JSON definitions
│   ├── executions/     # Execution states
│   ├── versions/       # Workflow version snapshots
│   └── schedules/      # Schedule definitions
├── files/              # Uploaded documents (future)
├── datasets/           # Imported datasets (future)
├── reports/            # Generated reports (future)
├── vector_store/       # Chroma vector database (future)
├── audits/             # Audit event logs (future)
├── reviews/            # Review gate records
├── providers/          # Provider configurations (future)
└── workspaces/         # Workspace records
```

### Storage is configurable

Set the `DECISION_SYSTEM_DATA_DIR` environment variable to change the
data directory:

```bash
export DECISION_SYSTEM_DATA_DIR=/path/to/my/data
docker compose up
```

### Data persistence guarantees

- Workflow definitions survive restarts ✅
- Workflow versions survive restarts ✅
- Execution history survives restarts ✅
- Schedule definitions survive restarts ✅
- Review records survive restarts ✅
- Provider configurations survive restarts ✅

---

## AI Provider Setup

The app starts with **fake/offline provider** by default — no API keys needed.

### Configure a local AI provider

#### Option 1: Ollama (Recommended)

```bash
# Install Ollama: https://ollama.com
ollama pull llama3.2
```

Then add a provider in the UI:

1. Open the Provider Manager (gear icon in toolbar)
2. Click "Add Provider"
3. Set:
   - **Name:** `ollama`
   - **API Base:** `http://localhost:11434/v1`
   - **Default Model:** `llama3.2`
4. Click "Check Connection" to verify
5. Set as default

#### Option 2: OpenAI-compatible local endpoint

```bash
# e.g., LocalAI, vLLM, Text Generation Inference
```

Add a provider in the UI with your local endpoint URL.

#### Option 3: OpenAI API (requires key)

Add a provider with:

- **API Base:** `https://api.openai.com/v1`
- **API Key Env:** `OPENAI_API_KEY`
- **Default Model:** `gpt-4o-mini`

Then set the environment variable when starting:

```bash
export OPENAI_API_KEY=sk-...
docker compose up
```

### No provider configured?

If no AI provider is configured, the app still starts and functions for:

- Workflow creation and editing
- Manual workflow execution (with fake provider)
- Schedule management
- Document browsing
- Report viewing

The UI will show a "No AI provider configured" message with setup options.

---

## Testing

### Backend tests

```bash
# All tests (requires venv activated)
python -m pytest -q

# Specific test files
python -m pytest tests/test_workflow_engine/test_api.py -q
python -m pytest tests/test_config.py tests/test_claim_ledger.py -q
```

### Frontend tests

```bash
cd web/workflow-builder
npm test
npm run build  # Verify production build
```

---

## CLI Commands

```bash
# Index local documents
decision-system index

# Run a decision question
decision-system ask "Should we migrate billing?"

# Extract knowledge graph
decision-system extract-graph

# Profile data
decision-system profile-data

# Detect patterns
decision-system detect-patterns

# Run orchestration
decision-system run-orchestration "Where are we losing money?"

# Run war room
decision-system run-war-room "Where are we losing money?"
```

---

## Architecture

```text
Browser UI (React + React Flow)
    ↓ HTTP/WebSocket
FastAPI Backend
    ↓
Local Workflow Engine (DAG executor)
    ↓
Local Stores (JSON/SQLite)
    ↓
.decision_system/  ← All data lives here
```

---

## Known Limitations (MVP)

- **Claim ledger** is in-memory per run; durable storage planned
- **Reports** are generated in-memory; local file export planned
- **Code node** is disabled by default (set `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=true` to enable)
- **Vector store** (Chroma) data not yet stored under `.decision_system/`
- **Audit logs** are partially wired; more events planned
- **Workspace export/import** is in development

---

## Troubleshooting

### "Port already in use"

```bash
# Check what's using port 8000 or 3000
lsof -i :8000
lsof -i :3000

# Kill the process or use a different port
```

### Docker build fails

```bash
# Rebuild without cache
docker compose build --no-cache

# Check Docker logs
docker compose logs backend
docker compose logs frontend
```

### Frontend shows blank page

```bash
# Clear browser cache and reload
# Check browser console for errors
# Ensure backend is running on port 8000
```

---

## Next Steps

- [ ] Try the quick start with Docker Compose
- [ ] Create your first workspace
- [ ] Build a workflow in the visual editor
- [ ] Run a workflow and inspect execution history
- [ ] Configure a local Ollama provider
- [ ] Upload documents and run the indexing pipeline
- [ ] Export a report
