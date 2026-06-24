# Demo Path — End-to-End Walkthrough

> **Version:** 1.25.0-dev
> **Last updated:** 2026-06-23

This document describes the complete demo path a reviewer follows to understand
the product in 10 minutes without reading source code.

---

## Quick Start (Docker)

```bash
# From a fresh clone:
docker compose up --build
```

Then open **http://localhost:3000**

---

## Demo Flow Steps

### 1. Create or Use Demo Workspace

**UI:** Workspace selector in sidebar

**What happens:**
- User clicks "Workspaces" or uses the workspace dropdown
- Clicks "Create Workspace" or selects existing "Demo Workspace"
- Backend: `POST /workspaces` creates workspace in `.decision_system/workspaces/`
- Data stored: `{workspace_id}/meta.json`

**Can fail if:** Backend unavailable, disk full

---

### 2. Load Sample Business Documents

**UI:** Data Sources → Upload

**What happens:**
- User navigates to Data Sources page
- Uploads files from `demo/sample-data/`:
  - `company_overview.md` — plain text (no OCR needed)
  - `risk_register.csv` — structured data (no OCR needed)
  - `scanned_contract.pdf` — image-based PDF **(requires OCR)**
  - `image_invoice.png` — scanned invoice image **(requires OCR)**
- Backend: `POST /data-sources/upload` accepts multipart file upload

**Can fail if:** File too large, unsupported type

---

### 3. Parse, OCR (if needed), and Index Files

**UI:** Data Sources → Click file → Parse → Index

**What happens:**
1. File is saved to `.decision_system/data_sources/{source_id}/`
2. **Parse step:**
   - For `.md`/`.txt`: `TextParser` reads content directly
   - For `.csv`: `TextParser` reads as text
   - For `.pdf`: `PdfParser` tries text extraction via `pypdf`
     - If no text extracted → **OCR fallback** (`ScannedPdfParser`):
       - Renders each page via PyMuPDF
       - Runs tesserocr on each page image
       - Returns OCR-extracted text
   - For `.png`/`.jpg`: `ImageOcrParser` runs tesserocr directly
3. **Index step:** Text is chunked and stored in Chroma vector store
4. Backend: `POST /data-sources/{id}/parse` → `POST /data-sources/{id}/index`

**OCR trigger conditions:**
- PDF with no extractable text → automatic fallback to OCR
- Image files (png/jpg/tiff/bmp) → direct OCR parsing
- PDF with some text + some images → text pages parsed, OCR pages warned

**Can fail if:** Tesseract not installed, tessdata missing, corrupt file

---

### 4. Run Evidence Search

**UI:** Evidence Search

**What happens:**
- User types a query like "billing system migration risks"
- Backend: `POST /evidence/search`
- Chroma vector search returns relevant chunks
- Results show source file, page number, text excerpt, relevance score

**Can fail if:** No documents indexed, Chroma unavailable

---

### 5. Configure Fake Provider

**UI:** Providers → Add Fake Provider

**What happens:**
- User can click "Add Fake Provider" button
- Backend: `POST /providers` creates a fake provider
- Fake provider returns deterministic responses (no API key needed)
- Becomes default provider if none exists

**Can fail if:** Provider already exists (idempotent — shows success)

---

### 6. Load Demo Workflow

**UI:** Workflow Builder → Templates → "Local Trust Report Demo"

**What happens:**
- User opens Workflow Builder
- Clicks "Templates" and selects "Local Trust Report Demo"
- Workflow loads with pre-configured nodes:
  1. Evidence Search (uses current workspace)
  2. Evidence Synthesis (uses fake provider)
  3. Claim Verification
  4. Contradiction Scan
  5. Review Gate (optional)
  6. Trust Report (generates Markdown report)

**Can fail if:** Template missing, workflow validation fails

---

### 7. Run Workflow

**UI:** Workflow Builder → Execute

**What happens:**
- User clicks "Execute"
- Backend creates workflow execution
- Each node runs in sequence:
  1. **Evidence Search** — queries Chroma for relevant evidence
  2. **Evidence Synthesis** — analyzes evidence via fake provider
  3. **Claim Verification** — checks claims against evidence
  4. **Contradiction Scan** — detects conflicting statements
  5. **Review Gate** — optionally pauses for human review
  6. **Trust Report** — generates final report with citations

**Can fail if:** No evidence indexed, provider offline, workflow invalid

---

### 8. Verify Claims

**UI:** Claim Ledger

**What happens:**
- User navigates to Claim Ledger
- Sees claims with statuses:
  - ✅ **Supported** — evidence found and matches
  - ❌ **Contradicted** — evidence contradicts claim
  - ⚠️ **Unsupported** — no evidence found
  - ❓ **Uncertain** — insufficient evidence
  - 🔍 **Needs Review** — requires human judgment
- User can click "Verify All" to run verification

**Can fail if:** No claims generated yet

---

### 9. Scan Contradictions

**UI:** Claim Ledger → Scan Contradictions

**What happens:**
- Backend scans all claims for logical contradictions
- Contradictions detected:
  - Metric mismatch (e.g., "2% error rate" vs "0.5% error rate")
  - Status conflicts (e.g., "migration complete" vs "migration pending")
  - Risk assessment differences
- Results show paired contradictory claims with evidence

**Can fail if:** No claims exist

---

### 10. Generate Trust Report

**UI:** Trust Dashboard → Generate Report

**What happens:**
- User clicks "Generate Trust Report"
- Backend creates a Markdown report including:
  - Executive summary
  - Evidence quality score
  - Claim verification summary
  - Contradictions found
  - Recommendations
  - Confidence assessment
- Report is stored and displayed in UI

**Can fail if:** No verification data

---

### 11. Export Markdown Report

**UI:** Reports → Export

**What happens:**
- User views the trust report
- Clicks "Export" → downloads as `.md` file
- File includes full citations and evidence references

**Can fail if:** Report not generated yet

---

### 12. Restart and Persist

**What happens:**
- User stops the Docker containers
- Restarts: `docker compose up`
- All data remains in `.decision_system/` (Docker volume)
- Workspaces, data sources, providers, workflows, reports survive restart

**Reset:** `docker compose down -v` removes all data

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

## Known Limitations (v1.25)

1. **OCR quality**: Tesseract accuracy depends on image quality. Low-resolution
   or highly stylized documents may produce errors.
2. **Non-English text**: Only English (`eng`) language data is bundled.
3. **Large PDFs**: OCR of large multi-page PDFs is slow (2-5 seconds per page).
4. **No document images**: Formats like `.docx` with embedded images are not OCR'd.
5. **Chroma in-memory**: Vector store is in-memory (file-based but loaded at startup).
6. **Single-user**: No multi-user support.
7. **No production readiness**: This is a local MVP beta candidate.
8. **Workflow execution**: Sequential node execution only (no parallel branches).
