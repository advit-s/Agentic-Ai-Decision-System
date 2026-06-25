# Local-First Setup — Provider Runtime & AI-Assisted Evidence Synthesis

> **Version:** 1.35.0-dev
> **Last updated:** 2026-06-24

## Overview

v1.33 adds beta packaging — one-command setup, start/stop scripts, diagnostics,
data reset/backup, and Docker Compose hardening.

The project runs fully offline with:

- **Fake provider** — built-in, deterministic, no network needed (default)
- **Local OCR** — Tesseract-based text extraction for scanned PDFs and images
- **Local vector store** — Chroma (in-memory, file-backed)
- **No cloud API keys required**

> **This is a local MVP beta candidate.** It is not production-ready and does not
> yet include enterprise authentication, encryption at rest, or hosted deployment support.

Fake provider is pre-configured for development. No setup required.

---

## Quick start (v1.33)

### Option A: Docker (recommended)

```bash
docker compose up --build
# Open http://localhost:3000
```

### Option B: Local setup script

```bash
# One-command setup:
./scripts/setup-local.sh

# Start everything:
./scripts/start-local.sh --all
# Open http://localhost:5173 (frontend) or http://localhost:8000 (API)
```

### Option C: Manual

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev,doc-parsing,ocr]"
cd web/workflow-builder && npm install && cd ../..
decision-system serve-api --host 0.0.0.0 --port 8000
# Open http://localhost:8000 (API) or http://localhost:5173 (if frontend running)
```

---

## All commands

| Command | Description |
|---------|-------------|
| `./scripts/setup-local.sh` | One-command setup (checks deps, installs, creates .env) |
| `./scripts/start-local.sh --all` | Start backend API + frontend dev server |
| `./scripts/start-local.sh` | Start backend only |
| `./scripts/start-local.sh --frontend` | Start frontend only |
| `./scripts/stop-local.sh` | Stop all local processes |
| `./scripts/doctor-local.sh` | Diagnostics (Python, Node, Docker, health, OCR, deps) |
| `./scripts/validate-local.sh` | CI-ready validation (tests + build + git hygiene) |
| `bash scripts/local-demo-seed.sh` | Seed demo workspace, data, providers, workflow |
| `bash scripts/e2e-local-demo-smoke.sh` | End-to-end demo verification |
| `./scripts/local-smoke-test.sh` | Quick backend/frontend/proxy checks |
| `./scripts/reset-local-data.sh` | Safely delete all local data (with confirmation) |
| `./scripts/backup-local-data.sh` | Backup .decision_system to timestamped archive |
| `decision-system serve-api` | Start the backend API server directly |
| `python -m pytest` | Run all backend tests |
| `cd web/workflow-builder && npm test` | Run frontend tests |

---

## Quick start (no API key needed)

```bash
# Option A: Docker (recommended)
docker compose up --build
# Open http://localhost:3000

# Option B: Manual
python -m venv .venv && source .venv/bin/activate
python -m pip install -e ".[dev,doc-parsing,ocr]"
decision-system serve-api --host 0.0.0.0 --port 8000
# Open http://localhost:8000 (API) or http://localhost:3000 (if frontend running)
```

## Verify it works

```bash
# After starting the backend:
curl http://localhost:8000/health
# → {"status":"ok","version":"1.35.0-dev","provider":"fake"}

# Check system status:
curl http://localhost:8000/system/status

# Run the demo seed:
bash scripts/local-demo-seed.sh

# Run the E2E smoke test:
bash scripts/e2e-local-demo-smoke.sh
```

## Demo Walkthrough

See [DEMO_PATH.md](DEMO_PATH.md) for a complete step-by-step walkthrough.

## Environment Setup

Copy the environment template and edit as needed:

```bash
cp .env.example .env
```

Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DECISION_PROVIDER` | No | `fake` | Provider type: `fake`, `openai`, `anthropic`, `ollama` |
| `DECISION_SYSTEM_DATA_DIR` | No | `.decision_system` | Persistent data directory |
| `DECISION_SYSTEM_SECURITY_MODE` | No | `demo` | Security mode: `demo` or `governed` |
| `DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE` | No | `false` | Enable unsafe code execution node |
| `DECISION_SYSTEM_ENABLE_LOCAL_DEV_CONNECTOR_PATHS` | No | `false` | Allow arbitrary local connector paths |
| `OPENAI_API_KEY` | For OpenAI | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | For Anthropic | — | Anthropic API key |
| `GITHUB_TOKEN` | For GitHub | — | GitHub personal access token |

Never commit `.env` files. The gitignore already covers them.

## OCR Setup

OCR is used for scanned PDFs and image files. It is optional — text-based
documents (`.md`, `.txt`, `.csv`) and text-extractable PDFs work without it.

### How OCR Works

1. **Scanned PDFs**: `pypdf` tries text extraction first. If no text found,
   the `ScannedPdfParser` fallback renders each page as an image and runs
   Tesseract OCR via `tesserocr`.
2. **Images (PNG/JPG/TIFF)**: `ImageOcrParser` runs Tesseract OCR directly.
3. **Output**: OCR-extracted text is chunked and indexed in Chroma alongside
   text-extracted content.

### Dependencies

| Component | Python Package | System Package |
|-----------|---------------|----------------|
| OCR engine | `tesserocr` | `tesseract-ocr`, `tesseract-ocr-eng` |
| PDF rendering | `PyMuPDF` | none |
| Image processing | `Pillow` | none |

### Tesseract Installation

**Debian/Ubuntu:**
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

**macOS:**
```bash
brew install tesseract
```

**Docker:**
The included `Dockerfile` installs Tesseract automatically.

**Verification:**
```bash
tesseract --version
# Should show tesseract 5.x
```

### TESSDATA_PATH

If Tesseract is installed in a non-standard location, set:
```bash
export TESSDATA_PREFIX=/path/to/tessdata
```

Default locations searched:
- `/usr/share/tesseract-ocr/5/tessdata`
- `/usr/share/tesseract-ocr/4.00/tessdata`
- `/usr/local/share/tessdata`
- `~/.local/share/tessdata`

Check OCR availability:
```bash
./scripts/doctor-local.sh
```

## Providers

### Fake provider (default)

The fake provider is pre-configured for development. No setup required.

```bash
# Verify it's active:
curl http://localhost:8000/providers
# → Should include a provider with type "fake"
```

To add the fake provider from the UI:
1. Open the app
2. Navigate to **Providers**
3. Click **Add Fake Provider**

### Ollama (optional)

1. Install Ollama from https://ollama.com
2. Pull a model:
   ```bash
   ollama pull llama3.2
   ```
3. Add a provider in the UI with:
   - Type: `openai`
   - Base URL: `http://localhost:11434/v1`
   - Model: `llama3.2`

### OpenAI / Anthropic (optional, requires API key)

Configure via the UI or set environment variables:
```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...
```

## Data Persistence

Data is stored in `.decision_system/`:

```text
.decision_system/
├── chroma/              # Vector store
├── workspaces/          # Workspace metadata
│   └── {workspace_id}/
│       ├── meta.json
│       ├── data_sources/
│       └── workflows/
├── providers/           # Provider configurations
├── data_sources/        # Uploaded files
├── reports/             # Generated reports
├── connectors/          # Imported connector data
├── logs/                # Application logs
└── backups/             # Data backups
```

Data survives restarts (including Docker restarts) and is gitignored.

### Reset

Fresh reset (with confirmation prompt):
```bash
./scripts/reset-local-data.sh
```

Quick reset (no confirmation):
```bash
./scripts/reset-local-data.sh --yes
```

Manual reset:
```bash
# Docker:
docker compose down -v

# Native:
rm -rf .decision_system/
```

### Backup

```bash
./scripts/backup-local-data.sh
```

Creates a timestamped archive in `.decision_system/backups/`.
Custom output directory:
```bash
./scripts/backup-local-data.sh /path/to/backup/dir
```

## Validate the install

```bash
./scripts/validate-local.sh
```

Runs git hygiene checks, backend tests, frontend tests, and frontend build.
Use `--summarize` to run all checks even if some fail.

## Docker Compose details

The `docker-compose.yml` starts two services:

- **backend**: FastAPI on port 8000, with persistent data volume and healthcheck
- **frontend**: nginx serving the built React SPA on port 80 (mapped to 3000), with proxy to backend

All API routes, WebSocket streams, and static assets are proxied through nginx.
The frontend build is included in the Docker image — no manual build step needed.

```bash
docker compose up --build
# Open http://localhost:3000
docker compose down     # Stop (data persists)
docker compose down -v  # Stop and delete data volume
```

## System status endpoint

```bash
curl http://localhost:8000/system/status
```

Returns version, data directory, security mode, provider/connector/workspace
counts, OCR availability, and warnings. No secrets leaked.

## Error Handling

Run `./scripts/doctor-local.sh` for automated diagnostics.

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Backend unreachable | Backend not started | `decision-system serve-api` or `./scripts/start-local.sh` |
| "OCR not supported" | Tesseract not installed | Install `tesseract-ocr` |
| "No extractable text" | Scanned PDF without OCR | Install Tesseract and retry |
| Upload fails | File too large | Max upload is 50MB |
| Provider unavailable | No provider configured | Add fake provider |
| Workflow fails | Missing provider | Configure fake provider first |
| Chroma search empty | Documents not indexed | Parse and index files first |

## Known Limitations (v1.33)

1. **OCR quality**: Tesseract accuracy depends on image quality. Low-resolution or highly stylized documents may produce errors.
2. **English only**: Only English (`eng`) language data is bundled.
3. **Single-user**: No multi-user support — RBAC is demo-only.
4. **Sequential workflows**: No parallel node execution in workflow engine.
5. **Chroma in-memory**: Vector store is in-memory (file-based but loaded at startup).
6. **Local MVP beta**: Not production-ready. No enterprise auth, no encryption at rest.
7. **Docker**: Docker smoke may be environment-dependent.
8. **No parallel branches**: Workflow execution is sequential only.

---

## Connector Setup (v1.30+)

Connectors allow you to import data from local folders, GitHub repositories, and URLs as read-only data sources. All connectors are:

- **Read-only**: Data is copied locally; originals are never modified.
- **Workspace-scoped**: Connector configurations and imported data are isolated per workspace.
- **Audited**: All operations are logged to the audit trail.
- **Permission-gated**: Configuring, importing, and syncing require appropriate RBAC permissions.

### Setting up a connector

1. Open the Connectors page in the React SPA.
2. Choose a connector type (Local Folder, GitHub Repository, URL Import).
3. Fill in the configuration fields (folder path, repository URL, or web page URL).
4. For GitHub, optionally set the `GITHUB_TOKEN` environment variable for rate-limit increases.
5. Test the connection to verify it works.
6. List available items and select the ones to import.
7. Import selected items into your workspace as local data sources.

### Troubleshooting credentials

- **GitHub token**: Set `GITHUB_TOKEN` as an environment variable before starting the application. Token values are never stored in configs or returned from API responses.
- **Notion/Google Drive**: These connectors are planned for future milestones. The UI shows disabled connector cards with setup guidance.

### Token safety

- Token values are never exposed in API responses.
- The credential status API returns boolean `token_present` indicators only.
- Tokens are automatically redacted from logs, audit events, and error messages.
