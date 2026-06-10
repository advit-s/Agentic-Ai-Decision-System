# Deployment Guide

This document describes how to run the Agentic Decision System locally.
No cloud deployment is supported at this prototype stage.

## Requirements

- Python 3.11+
- pip
- (Optional) Docker and Docker Compose for containerized runs

## Local Install

```bash
python -m pip install -e ".[dev]"
```

This installs the `decision-system` CLI and all dependencies.
The **fake/offline provider** is the default; no API keys are needed.

## Local CLI

```bash
decision-system --help
decision-system serve-api
```

## Docker (Development Only)

Build and run the API in a container:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000`.

### Docker Notes

- No secrets are baked into the image.
- `DECISION_PROVIDER=fake` is the default in the container.
- `.decision_system/` state is stored in a Docker volume.
- Source documents (`company_docs/`, `company_data/`) are mounted read-only.
- No auth, database, ingress, or cloud services are included.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DECISION_PROVIDER` | `fake` | LLM provider (fake, nvidia_nim, ollama) |
| `NVIDIA_NIM_BASE_URL` | (none) | NVIDIA NIM OpenAI-compatible endpoint |
| `NVIDIA_API_KEY` | (none) | NVIDIA NIM API key (optional, for real provider) |
| `OLLAMA_BASE_URL` | (none) | Ollama endpoint (optional, for local Ollama) |
| `DECISION_DOCS_DIR` | `company_docs` | Directory for source documents |
| `DECISION_OBSERVABILITY_ROOT` | `.decision_system/observability` | Observability data root |

## Release Check

Before any release, run:

```bash
# Linux/macOS
./scripts/release-check.sh

# Windows PowerShell
.\scripts\release-check.ps1
```

This verifies:
- No `__pycache__` or `.pyc` in tracked files
- No generated `.decision_system/` tracked
- No raw datasets or `.env` committed
- Package installs cleanly
- Tests pass
- CLI import is fast (<3s)
- Hygiene check passes

## Security Notes for Deployment

- **No auth** is implemented yet. The API is intended for local prototype use only.
- **No database** is used. Chroma + local JSON files are sufficient for the prototype.
- **No cloud services** are required or used by default.
- **No secrets** should be baked into Docker images or committed to the repo.
- The `security scan-secrets` and `security policy-check` commands help verify repository hygiene.
- Connector stubs for GitHub, Jira, Slack, and Email are offline placeholders.

## What This Is Not

- Not production-ready
- Not a hosted SaaS product
- Not suitable for processing real PII without additional controls
- Not hardened for internet-facing deployment
