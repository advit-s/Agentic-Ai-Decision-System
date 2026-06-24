# Local-First Setup — Provider Runtime & AI-Assisted Evidence Synthesis

## Overview

v1.25 adds OCR capability and a hardened end-to-end demo flow. The project
runs fully offline with:

- **Fake provider** — built-in, deterministic, no network needed (default)
- **Local OCR** — Tesseract-based text extraction for scanned PDFs and images
- **Local vector store** — Chroma (in-memory, file-backed)
- **No cloud API keys required**

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
# → {"status":"ok","version":"1.26.1-dev","provider":"fake"}

# Run the demo seed:
bash scripts/local-demo-seed.sh

# Run the E2E smoke test:
bash scripts/e2e-local-demo-smoke.sh
```

## Demo Walkthrough

See [DEMO_PATH.md](DEMO_PATH.md) for a complete step-by-step walkthrough.

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
└── reports/             # Generated reports
```

Data survives restarts (including Docker restarts).

To reset:
```bash
# Docker:
docker compose down -v

# Native:
rm -rf .decision_system/
```

## Error Handling

Common issues and their solutions:

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| Backend unreachable | Backend not started | `decision-system serve-api` |
| "OCR not supported" | Tesseract not installed | Install `tesseract-ocr` |
| "No extractable text" | Scanned PDF without OCR | Install Tesseract and retry |
| Upload fails | File too large | Max upload is 50MB |
| Provider unavailable | No provider configured | Add fake provider |
| Workflow fails | Missing provider | Configure fake provider first |
| Chroma search empty | Documents not indexed | Parse and index files first |

## Known Limitations (v1.25)

1. **OCR quality**: Tesseract accuracy depends on image quality.
2. **English only**: Only English language data is bundled.
3. **Single-user**: No multi-user support.
4. **Sequential workflows**: No parallel node execution.
5. **Chroma in-memory**: Vector store loaded at startup from disk.
6. **Local MVP**: Not production-ready.

## Reset instructions

```bash
# Remove all local data
rm -rf .decision_system/

# For Docker:
docker compose down -v

# Re-seed demo data
bash scripts/local-demo-seed.sh
```
