# Demo Path — End-to-End Walkthrough

> **Version:** 1.33.0-dev
> **Last updated:** 2026-06-24

This document describes the complete demo path a reviewer follows to understand
the product without reading source code. Each step details the user action,
expected UI state, backend API involved, artifact created, failure modes, and
recovery guidance.

---

## Demo Flow: 18-Step Walkthrough

### Step 1 — Open App and Confirm Backend Status

| Item | Details |
|------|---------|
| **User action** | Open `http://localhost:3000` in browser |
| **Expected UI state** | App loads with sidebar showing version (`1.33.0-dev`), `LOCAL BETA` label, backend status (green/connected), security mode badge |
| **Backend API** | `GET /health` → `{"status":"ok","version":"1.33.0-dev"}` |
| **Artifact created** | None |
| **What can fail** | Backend not started, port conflict, frontend build missing |
| **How to recover** | Run `./scripts/doctor-local.sh` to check; start backend with `./scripts/start-local.sh`; rebuild frontend with `cd web/workflow-builder && npm run build` |

---

### Step 2 — Create or Use Demo Workspace

| Item | Details |
|------|---------|
| **User action** | Click "Workspaces" in sidebar → Create Workspace or select existing "Demo Workspace" |
| **Expected UI state** | Workspace list visible; create form accepts name and description; selected workspace appears in header |
| **Backend API** | `GET /workspaces` — list workspaces; `POST /workspaces` — create with `{"name":"Demo","description":"..."}` |
| **Artifact created** | `{data_dir}/workspaces/{workspace_id}/meta.json` |
| **What can fail** | Backend unavailable, disk full, workspace name conflict |
| **How to recover** | Check backend is running; use a different workspace name |

---

### Step 3 — Load Sample Data

| Item | Details |
|------|---------|
| **User action** | Navigate to Data Sources → Upload files from `demo/sample-data/` (e.g. `company_overview.md`, `risk_register.csv`) |
| **Expected UI state** | File upload progress shown; after completion, file appears in data source list with name, type, size, status |
| **Backend API** | `POST /workspaces/{wid}/data-sources/upload` — multipart file upload |
| **Artifact created** | `{data_dir}/data_sources/{source_id}/original_file` + `meta.json` |
| **What can fail** | File too large, unsupported type, path traversal in filename |
| **How to recover** | Check supported types (md, txt, csv, json, pdf, docx, xlsx); rename file with allowed extension |

---

### Step 4 — Parse / OCR / Index Files

| Item | Details |
|------|---------|
| **User action** | Click on a data source → click "Parse" → wait for completion → click "Index" |
| **Expected UI state** | Parse button triggers processing; status changes from "uploaded" → "parsed" → "indexed"; chunks count visible |
| **Backend API** | `POST /data-sources/{id}/parse` → `POST /data-sources/{id}/index` |
| **Artifact created** | Parsed text in `{data_dir}/chunks/{source_id}/`; Chroma vector index entries |
| **What can fail** | Corrupt file, parser missing dependency, Tesseract unavailable (for scanned PDFs), disk full |
| **How to recover** | Use text-based files (md/txt) if OCR unavailable; check Tesseract with `tesseract --version` |

**OCR details:**
- Text-based PDFs → `pypdf` extracts text directly
- Scanned PDFs (no extractable text) → `ScannedPdfParser` via PyMuPDF + tesserocr
- Images (png/jpg) → `ImageOcrParser` via tesserocr
- If Tesseract is unavailable: text-based files still work; scanned PDFs show OCR-unavailable warning

---

### Step 5 — Search Evidence

| Item | Details |
|------|---------|
| **User action** | Navigate to Evidence Search → type query (e.g. "billing system") → press Enter |
| **Expected UI state** | Results list shows matching chunks with source document name, text excerpt, relevance score |
| **Backend API** | `POST /evidence/search` — Chroma vector search |
| **Artifact created** | Search result set (ephemeral) |
| **What can fail** | No documents indexed, Chroma unavailable, empty query |
| **How to recover** | Ensure Step 3 and 4 completed; index at least one file before searching |

---

### Step 6 — Configure Fake Provider

| Item | Details |
|------|---------|
| **User action** | Navigate to Providers → click "Add Fake Provider" |
| **Expected UI state** | Provider added; status shows "configured"; no API key required |
| **Backend API** | `POST /providers` — creates fake provider |
| **Artifact created** | Provider config stored in `{data_dir}/providers/` |
| **What can fail** | Provider already exists (idempotent — reports success) |
| **How to recover** | Re-run; fake provider is idempotent |

---

### Step 7 — Import Sample Data Through Local Folder Connector

| Item | Details |
|------|---------|
| **User action** | Navigate to Connectors → Add "Local Folder" connector → point to `demo/sample-data/` → run import |
| **Expected UI state** | Connector setup wizard completes; import job starts with progress bar; items appear in connector view |
| **Backend API** | `POST /connectors` — create; `POST /connectors/{id}/import` — start import job |
| **Artifact created** | Connector config in `{data_dir}/connectors/`; imported items in data sources |
| **What can fail** | Invalid folder path, folder does not exist, permission denied, large folder timeouts |
| **How to recover** | Use absolute path to `demo/sample-data/`; ensure folder is readable |

---

### Step 8 — Run Connector Sync Twice and See Unchanged Items Skipped

| Item | Details |
|------|---------|
| **User action** | Click "Sync" on the connector → after completion, click "Sync" again |
| **Expected UI state** | First sync: imports items with progress. Second sync: shows "all items unchanged" or "0 new items" |
| **Backend API** | `POST /connectors/{id}/sync` — incremental sync with hash-based duplicate detection |
| **Artifact created** | Sync job record; duplicate detection marks unchanged items via `content_hash` comparison |
| **What can fail** | Rate limiting, folder deleted between syncs, permission changes |
| **How to recover** | Check folder still exists; retry sync |

---

### Step 9 — Run Demo Workflow

| Item | Details |
|------|---------|
| **User action** | Navigate to Workflow Builder → Templates → "Local Trust Report Demo" → Execute |
| **Expected UI state** | Workflow loads with nodes; execution progress bar advances through nodes; final report appears |
| **Backend API** | `GET /workflows/templates` — load template; `POST /workflows/{id}/execute` — run |
| **Artifact created** | Execution record; generated claims; report markdown |
| **What can fail** | No evidence indexed, provider not configured, workflow validation error, missing workspace default |
| **How to recover** | Ensure Steps 3-6 completed (data indexed, fake provider set); check workflow node configuration |

**Demo workflow node sequence:**
1. Evidence Search — queries Chroma
2. Evidence Synthesis — analyzes via fake provider
3. Claim Verification — checks claims
4. Contradiction Scan — detects conflicts
5. Review Gate — optional human pause
6. Trust Report — generates Markdown

---

### Step 10 — Generate Claims

| Item | Details |
|------|---------|
| **User action** | After workflow execution → navigate to Claim Ledger |
| **Expected UI state** | Claims listed with status labels (pending, verified, unsupported, contradicted) |
| **Backend API** | Claims are created during workflow execution; `GET /claims` to list |
| **Artifact created** | Claim records in `{data_dir}/claims/` |
| **What can fail** | No claims generated (workflow did not complete), empty evidence set |
| **How to recover** | Re-run workflow; ensure evidence was indexed |

---

### Step 11 — Verify Claims

| Item | Details |
|------|---------|
| **User action** | Click "Verify All" or verify individual claims |
| **Expected UI state** | Claim statuses update; each shows evidence references; unsupported/contradicted claims are visible (not hidden) |
| **Backend API** | `POST /claims/{id}/verify` — verify single claim; `POST /claims/verify-all` — batch verify |
| **Artifact created** | Verification results attached to claims |
| **What can fail** | Provider not responding, no evidence for comparison |
| **How to recover** | Ensure fake provider is configured; ensure evidence is indexed |

---

### Step 12 — Extract Graph Facts / Risks / Metrics

| Item | Details |
|------|---------|
| **User action** | Navigate to Knowledge Graph → run extraction → view entities and relationships |
| **Expected UI state** | Graph shows entity nodes with relationship edges; detail panel shows evidence references |
| **Backend API** | `POST /graph/extract` — run graph extraction from indexed data |
| **Artifact created** | Graph nodes/edges in `{data_dir}/graph/` |
| **What can fail** | No data indexed, extraction timeout, empty result set |
| **How to recover** | Ensure data sources are indexed; check graph extraction config |

---

### Step 13 — Generate Trust Report

| Item | Details |
|------|---------|
| **User action** | Navigate to Trust Dashboard → select workspace → click "Generate Trust Report" |
| **Expected UI state** | Report generation progress shown; completed report displayed with sections (summary, evidence, claims, risks, graph) |
| **Backend API** | `POST /reports/generate` — generate trust report |
| **Artifact created** | Report markdown in `{data_dir}/reports/{report_id}/` |
| **What can fail** | No claims/evidence data, provider unavailable, report generation timeout |
| **How to recover** | Complete Steps 9-11 first; check provider configuration |

---

### Step 14 — Export Markdown Report

| Item | Details |
|------|---------|
| **User action** | View generated report → click "Export" |
| **Expected UI state** | Browser downloads a `.md` file with full report including citations |
| **Backend API** | `GET /reports/{id}/export` — returns markdown file |
| **Artifact created** | Downloaded `*.md` file on user's machine |
| **What can fail** | Report not generated yet, permission denied (governed mode), disk full |
| **How to recover** | Generate report first (Step 13); ensure user has export permission |

---

### Step 15 — Backup Data

| Item | Details |
|------|---------|
| **User action** | Run `./scripts/backup-local-data.sh` from terminal |
| **Expected UI state** | Terminal shows backup progress; timestamped `.tar.gz` file created |
| **Backend API** | None (script-based) |
| **Artifact created** | `decision-system-backup-{timestamp}.tar.gz` in current directory |
| **What can fail** | Data directory missing, disk full, permission denied |
| **How to recover** | Ensure `.decision_system/` exists; check disk space |

---

### Step 16 — Reset Data (with Confirmation)

| Item | Details |
|------|---------|
| **User action** | Run `./scripts/reset-local-data.sh` from terminal → type `yes` when prompted |
| **Expected UI state** | Terminal prompts for confirmation; after `yes`, data directory is cleared and recreated |
| **Backend API** | None (script-based) |
| **Artifact created** | Empty `.decision_system/` directory |
| **What can fail** | Confirmation not provided (script exits safely), permission denied, directory locked |
| **How to recover** | Stop backend first; run script again and type `yes` |

---

### Step 17 — Restart and Confirm Persistence

| Item | Details |
|------|---------|
| **User action** | Stop app → restart → verify data is still present (before reset) |
| **Expected UI state** | After restart, workspaces, data sources, providers, workflows, and reports are all preserved |
| **Backend API** | `GET /workspaces`, `GET /data-sources`, `GET /providers` — all return previous data |
| **Artifact created** | None (verification step) |
| **What can fail** | Data directory moved/deleted, volume not mounted (Docker), permissions changed |
| **How to recover** | Check `.decision_system/` exists and has content; restore from backup |

---

### Step 18 — Run Doctor / Validate Scripts

| Item | Details |
|------|---------|
| **User action** | Run `./scripts/doctor-local.sh` and `./scripts/validate-local.sh` |
| **Expected UI state** | Doctor shows green checks for healthy components; validate runs test suite |
| **Backend API** | None (script-based, but `GET /health` is checked by doctor) |
| **Artifact created** | Test results; doctor report |
| **What can fail** | Environment dependencies missing (Docker, Tesseract), backend not running |
| **How to recover** | Follow script output instructions; install missing dependencies |

---

## OCR Flow Details

### Architecture

```text
Upload (PDF/Image)
  │
  ├── PDF → PdfParser (pypdf text extraction)
  │         ├── Text found → return text
  │         └── No text → ScannedPdfParser (fallback)
  │                       ├── PyMuPDF render page → PIL Image
  │                       └── tesserocr OCR → text
  │
  └── Image (png/jpg/tiff) → ImageOcrParser
                              └── tesserocr OCR → text
```

### Dependencies

| Component | Package | System Dep |
|-----------|---------|------------|
| OCR engine | `tesserocr` | `tesseract-ocr` + `tesseract-ocr-eng` |
| PDF rendering | `PyMuPDF` | none (pure Python) |
| PDF alternative | `pdf2image` | `poppler-utils` |
| Image processing | `Pillow` | none |

### Fallback Behavior

- If OCR dependencies are missing, parsers return a warning
- Demo path still works with text-only files
- OCR status is reported per source in the Data Sources UI

---

## Non-Docker Equivalent

Every step above works without Docker:

```bash
# Terminal 1: Start backend
./scripts/start-local.sh

# Terminal 2: Start frontend (optional, API works via curl too)
./scripts/start-local.sh --all

# Or use the all-in-one
./scripts/start-local.sh --all
```

The SPA frontend at `http://localhost:3000` uses Vite dev server by default.
For production-like build: `cd web/workflow-builder && npm run build && npx serve dist`

---

## Known Limitations (v1.33)

1. **OCR quality**: Tesseract accuracy depends on image quality. Low-resolution
   or highly stylized documents may produce errors. OCR is only available when
   Tesseract is installed on the system.
2. **Non-English text**: Only English (`eng`) language data is bundled.
3. **Large PDFs**: OCR of large multi-page PDFs is slow (2-5 seconds per page).
4. **No document images**: Formats like `.docx` with embedded images are not OCR'd.
5. **Chroma in-memory**: Vector store is file-based but loaded at startup.
6. **Single-user**: No multi-user support. Demo mode is default.
7. **Not production-ready**: This is a local MVP beta candidate.
8. **Workflow execution**: Sequential node execution only (no parallel branches).
9. **Docker smoke not run**: Docker validation is environment-dependent.
10. **Notion/Drive connectors**: Disabled/planned, not active.
11. **No enterprise auth**: No SSO, no encryption at rest, no audit stream.
12. **External connectors**: Read-only only. No write connectors.

---

*Demo path verified for v1.33.0-dev — End-to-End Beta QA + Bug Bash.*
*Update this document when API endpoints, UI flows, or dependencies change.*


## Validation Transcript (2026-06-26)

The following transcript was captured from a clean run of the CLI data pipeline using the fake (offline) provider. All 8 steps pass.

```
============================================================
CLI Pipeline Validation Transcript
============================================================

  [PASS] Seed demo data
    Seeded demo data: 0 created, 10 overwritten, 0 skipped

  [PASS] Init data catalog
    Initialized data catalog at company_data/manifest.json

  [PASS] Index documents
    Indexed 1 documents into 1 chunks.

  [PASS] Inspect index
    Collection name: decision_chunks
    Chunk count: 42
    Unique source filenames: demo_billing.md, warn.txt

  [PASS] Extract knowledge graph
    Entity count: 2
    Relationship count: 1

  [PASS] Profile data
    Profiled datasets: 11
    Saved profiles at .decision_system/data_profiles/

  [PASS] Detect patterns
    Insights detected: 2
    By severity: high: 1, low: 1
    By category: contradiction: 1, strategic_gap: 1

  [PASS] Ask offline question (fake provider)
    Full decision report generated with claims, contradictions,
    confidence assessment, and human review guidance.

Steps: 8 | Pass: 8 | Fail: 0
============================================================
```


## API Server Validation (2026-06-26)

The following transcript was captured from a clean start of the API server
with the fake (offline) provider. All 12 endpoint groups respond correctly
(200 success or 404 for empty/unseeded data). No 500 errors.

```
Version: 1.35.0-dev | Provider: fake | Mode: demo
============================================================
✅ GET /health: 200
✅ GET /system/status: 200
✅ GET /providers: 200
✅ GET /providers/default: 200
✅ GET /providers/types/list: 200
✅ GET /workspaces: 200
✅ GET /connectors/schemas: 200
✅ GET /data-sources/status?workspace_id=demo: 404 (expected - no data seeded)
✅ GET /evidence/search?workspace_id=demo&q=test: 404 (expected - no data)
✅ GET /graph/summary/demo: 404 (expected - no data)
✅ GET /executions?workspace_id=demo: 404 (expected - no executions)
```

All endpoints return 2xx or 4xx codes — no 5xx server errors.
