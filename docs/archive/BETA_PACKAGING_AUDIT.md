# Beta Packaging Audit — v1.32

> **Version:** 1.32.0-dev
> **Status:** Baseline audit before packaging improvements
> **Date:** 2026-06-24

## Purpose

This document captures the current install/startup/validation baseline before
implementing the v1.32 beta packaging improvements. Every gap identified here
is addressed by a later phase in this milestone.

## MCP / Code Index Availability

The codebase-memory MCP server is available and the repository is indexed
(`home-kali-Desktop-Agentic-Ai-Decision-System`, 10726 nodes, 35705 edges).

## Current Install Path

| Step | Status | Notes |
|------|--------|-------|
| `git clone` | ✅ Documented | README shows clone URL |
| Python venv | ✅ Documented | README shows `python -m venv .venv` |
| `pip install -e ".[dev]"` | ✅ Working | Dev extras install test deps |
| `.env` creation | ⚠️ Manual | `.env.example` exists but sparse; no documented `cp .env.example .env` |
| OCR deps install | ⚠️ Manual | Documented in LOCAL_FIRST_SETUP.md but no script does it |
| Node/npm install | ⚠️ Manual | No setup script handles it |
| `decision-system serve-api` | ✅ Working | Backend starts on port 8000 |

### Gaps

- No single `setup-local.sh` script exists.
- No automated OCR dependency check.
- `.env.example` is outdated (NVIDIA-focused, missing modern vars).

## Current Docker Path

| Step | Status | Notes |
|------|--------|-------|
| `docker compose up --build` | ✅ Working | Builds backend + frontend |
| Backend healthcheck | ✅ Working | Uses `python -c "from decision_system import __version__; print(__version__)"` |
| Frontend healthcheck | ❌ Missing | Only backend has a healthcheck |
| Persistent data volume | ✅ Working | `decision_data` volume at `/app/.decision_system` |
| OCR dependencies | ✅ Working | Dockerfile installs tesseract-ocr |
| Proxy routes | ✅ Working | nginx proxies `/api/`, SPA routes, WebSocket |
| Frontend build as part of Docker | ✅ Working | Multi-stage build in `web/workflow-builder/Dockerfile` |

### Gaps

- No frontend healthcheck.
- No `/system/status` endpoint.
- Environment variables in compose are sparse (only `DECISION_PROVIDER`, `DECISION_SYSTEM_DATA_DIR`).

## Current Scripts

| Script | Status | Notes |
|--------|--------|-------|
| `scripts/validate-local.sh` | ✅ Good | Runs git check + backend tests + frontend tests + build |
| `scripts/local-demo-seed.sh` | ✅ Good | Seeds demo workspace, data, providers, workflows |
| `scripts/e2e-local-demo-smoke.sh` | ✅ Good | End-to-end demo verification |
| `scripts/local-smoke-test.sh` | ✅ Good | Quick backend/frontend/proxy checks |
| `scripts/dev.sh` | ✅ Exists | Manual development start |
| `scripts/clean-generated.sh` | ✅ Exists | Cleans generated files |
| `scripts/release-check.sh` | ✅ Exists | Pre-release verification |

### Gaps

- No `scripts/setup-local.sh` (one-command local setup).
- No `scripts/start-local.sh` (start backend + frontend).
- No `scripts/stop-local.sh` (stop local dev processes).
- No `scripts/doctor-local.sh` (diagnostics and troubleshooting).
- No `scripts/reset-local-data.sh` (safe data reset).
- No `scripts/backup-local-data.sh` (data backup).

## Current Environment Variables

### Documented in `.env.example`

```
DECISION_DOCS_DIR=company_docs
DECISION_STORE_DIR=.decision_system/chroma
DECISION_COLLECTION=decision_chunks
DECISION_PROVIDER=fake
NVIDIA_API_KEY=
NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_NIM_MODEL=
NVIDIA_TEMPERATURE=0
NVIDIA_TOP_P=0.95
NVIDIA_MAX_TOKENS=4096
NVIDIA_REASONING_ENABLED=false
NVIDIA_REASONING_EFFORT=medium
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=
OLLAMA_TEMPERATURE=0
OLLAMA_MAX_TOKENS=2048
OLLAMA_TIMEOUT_SECONDS=60
```

### Missing from `.env.example`

```
DECISION_SYSTEM_DATA_DIR=.decision_system
DECISION_SYSTEM_SECURITY_MODE=demo
DECISION_SYSTEM_ENABLE_UNSAFE_CODE_NODE=false
DECISION_SYSTEM_ENABLE_LOCAL_DEV_CONNECTOR_PATHS=false
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
LOCAL_OPENAI_API_KEY=
GITHUB_TOKEN=
NOTION_API_KEY=
GOOGLE_DRIVE_TOKEN=
```

### Gaps

- `.env.example` is NVIDIA-focused; missing new security mode, data dir, and connector vars.
- No required vs optional documentation.
- No explicit note about not committing `.env`.

## Current Data Directory Behavior

| Aspect | Status | Notes |
|--------|--------|-------|
| Location | `.decision_system/` | Configurable via `DECISION_SYSTEM_DATA_DIR` |
| Survival across restarts | ✅ Yes | Files on disk persist |
| Docker persistence | ✅ Yes | Named volume `decision_data` |
| Git ignored | ✅ Yes | In `.gitignore` |
| Reset instructions | ✅ Documented | `rm -rf .decision_system/` |

### Gaps

- No `reset-local-data.sh` with confirmation prompt.
- No `backup-local-data.sh`.

## Current OCR Dependency Behavior

| Dep | Status | Notes |
|-----|--------|-------|
| `tesseract-ocr` | ✅ Docker | Installed in Dockerfile |
| `tesseract-ocr-eng` | ✅ Docker | English language data |
| `tesserocr` | ✅ pip dep | Optional `[ocr]` extra |
| `PyMuPDF` | ✅ pip dep | PDF rendering |
| `pdf2image` | ✅ pip dep | Alternative PDF renderer |
| `pytesseract` | ✅ pip dep | Alternative OCR |
| `TESSDATA_PREFIX` | ✅ Set | `/usr/share/tesseract-ocr/5/tessdata` in Docker |

### Gaps

- No script checks OCR availability at setup time.
- No graceful degradation info when OCR deps are missing.

## Current Demo Path

| Step | Status | Notes |
|------|--------|-------|
| Workspace creation | ✅ Working | Via API/UI |
| Data upload | ✅ Working | File upload API |
| Parse/index | ✅ Working | With OCR fallback |
| Evidence search | ✅ Working | Chroma vector search |
| Provider config | ✅ Working | Fake provider works offline |
| Workflow execution | ✅ Working | Sequential nodes |
| Claim verification | ✅ Working | Claim ledger |
| Report generation | ✅ Working | Markdown export |
| Demo seed script | ✅ Working | `scripts/local-demo-seed.sh` |
| E2E smoke script | ✅ Working | `scripts/e2e-local-demo-smoke.sh` |

### Gaps

- Demo seed script doesn't print version/beta status.
- E2E smoke doesn't validate `/system/status` endpoint (doesn't exist yet).

## Current Validation Commands

| Command | Status | Notes |
|---------|--------|-------|
| `python -m pytest -q` | ✅ Passing | 1644 passed, 3 failed, 2 skipped |
| `python -m pytest tests/test_connectors -q` | ✅ Passing | |
| `python -m pytest tests/test_connector_sync -q` | ✅ Passing | |
| `python -m pytest tests/test_connector_setup -q` | ✅ Passing | |
| `python -m pytest tests/test_connector_reliability -q` | ✅ Passing | |
| `cd web/workflow-builder && npm test` | ✅ Working | Frontend tests |
| `cd web/workflow-builder && npm run build` | ✅ Working | Frontend build |
| `git diff --check` | ✅ Clean | No whitespace errors |
| `scripts/validate-local.sh` | ✅ Working | CI-ready validation |

### Gaps

- 3 pre-existing test failures in `test_connector_cli.py` (being fixed in v1.32).
- No Docker smoke test in validate script.
- No doctor check in validate script.

## Known Packaging Gaps (Summary)

1. **No setup-local.sh** — New users must manually run venv, pip install, npm install, .env setup.
2. **No start-local.sh / stop-local.sh** — No simple non-Docker start/stop.
3. **No doctor-local.sh** — No diagnostic script for troubleshooting.
4. **No reset-local-data.sh** — Data reset is manual `rm -rf`.
5. **No backup-local-data.sh** — No backup mechanism.
6. **Outdated .env.example** — Missing security mode, connector token vars.
7. **No /system/status endpoint** — No unified health/status endpoint.
8. **No frontend healthcheck in Docker** — Only backend has healthcheck.
9. **3 pre-existing test failures** — Connector CLI tests need updating.
10. **Version needs bumping** — Currently 1.31.0-dev.
11. **Frontend lacks beta/version/status UI** — No visible version or backend status.

## v1.32 Plan

```
Phase 0: ✅ This document
Phase 1: Bump version to 1.32.0-dev
Phase 2: Fix 3 pre-existing test failures (connector CLI tests)
Phase 3: Harden .env.example with all vars and docs
Phase 4: Create scripts/setup-local.sh
Phase 5: Create scripts/start-local.sh, scripts/stop-local.sh
Phase 6: Harden Docker Compose (frontend healthcheck, env vars)
Phase 7: Add /system/status endpoint
Phase 8: Create scripts/doctor-local.sh
Phase 9: Polish demo seed and smoke scripts
Phase 10: Create scripts/reset-local-data.sh, scripts/backup-local-data.sh
Phase 11: Upgrade scripts/validate-local.sh
Phase 12: Frontend beta polish (version, status, beta label)
Phase 13: Update README and packaging docs
Phase 14: Frontend tests for new UI elements
Phase 15: Backend tests for /system/status and diagnostics
Phase 16: Docker validation (if Docker available)
Phase 17: Final validation
Phase 18: Final implementation report
```
