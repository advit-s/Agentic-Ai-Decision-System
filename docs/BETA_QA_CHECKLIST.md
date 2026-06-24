# Beta QA Checklist — v1.33.0-dev

> **Version:** 1.33.0-dev
> **Milestone:** End-to-End Beta QA + Bug Bash
> **Date:** 2026-06-24

Use this checklist to verify the local beta experience from a fresh clone.
Check each item after confirming the expected behavior.

---

## Table of Contents

1. [Fresh Clone Setup](#1-fresh-clone-setup)
2. [Non-Docker Startup](#2-non-docker-startup)
3. [Docker Startup](#3-docker-startup)
4. [Frontend Navigation](#4-frontend-navigation)
5. [Workspace Flow](#5-workspace-flow)
6. [Data-Source Flow](#6-data-source-flow)
7. [OCR / Parsing / Indexing](#7-ocr--parsing--indexing)
8. [Evidence Search](#8-evidence-search)
9. [Connector Import](#9-connector-import)
10. [Connector Sync](#10-connector-sync)
11. [Provider Setup](#11-provider-setup)
12. [Workflow Execution](#12-workflow-execution)
13. [Claim Verification](#13-claim-verification)
14. [Knowledge Graph](#14-knowledge-graph)
15. [Risk Dashboard](#15-risk-dashboard)
16. [Trust Reports](#16-trust-reports)
17. [Audit Logs](#17-audit-logs)
18. [Backup / Reset](#18-backup--reset)
19. [Security / Governance States](#19-security--governance-states)
20. [Known Limitations](#20-known-limitations)

---

## 1. Fresh Clone Setup

- [ ] `git clone` from origin completes without errors
- [ ] `.env.example` exists and is complete
- [ ] `cp .env.example .env` creates a valid `.env` file
- [ ] `scripts/setup-local.sh` runs without errors
- [ ] Setup detects missing Python and errors clearly
- [ ] Setup detects missing Node.js and errors clearly
- [ ] Setup creates Python virtual environment
- [ ] Setup installs backend `pip install -e ".[dev]"`
- [ ] Setup installs frontend `npm install`
- [ ] Setup creates `.decision_system/` data directory
- [ ] `scripts/doctor-local.sh` reports healthy state after setup
- [ ] `scripts/doctor-local.sh` reports clear messages for missing dependencies (Docker, Tesseract)
- [ ] `scripts/doctor-local.sh` exits with non-zero on real failures

---

## 2. Non-Docker Startup

- [ ] `scripts/start-local.sh` starts backend server
- [ ] Backend starts on `http://localhost:8000` (or configured port)
- [ ] `GET /health` returns 200 with version and status
- [ ] `GET /system/status` returns version, data_dir, security_mode, counts
- [ ] `scripts/start-local.sh --all` starts both backend and frontend
- [ ] `scripts/stop-local.sh` stops all running processes
- [ ] PID files are cleaned up on stop
- [ ] Starting twice does not create duplicate processes
- [ ] `scripts/doctor-local.sh` reports backend and frontend as running after start

---

## 3. Docker Startup

> ⚠️ Docker validation is environment-dependent. If Docker is unavailable, skip this section and note it.

- [ ] `docker compose up --build` completes without errors
- [ ] Backend container starts and becomes healthy
- [ ] Frontend container starts and becomes healthy
- [ ] `http://localhost:3000` loads the React SPA
- [ ] `http://localhost:8000/health` returns 200
- [ ] `docker compose down` stops all containers cleanly

---

## 4. Frontend Navigation

- [ ] App loads without console errors
- [ ] AppNav sidebar shows:
  - [ ] Version number (`1.33.0-dev`)
  - [ ] `LOCAL BETA` label
  - [ ] Backend connection status
  - [ ] Security mode badge
- [ ] Each main section loads without blank pages:
  - [ ] Workspace
  - [ ] Data Sources
  - [ ] Evidence Search
  - [ ] Connectors
  - [ ] Knowledge Graph
  - [ ] Risk Dashboard
  - [ ] Workflow Builder
  - [ ] Execution History
  - [ ] Claim Ledger
  - [ ] Trust Dashboard
  - [ ] Reports
  - [ ] Providers
  - [ ] Settings
  - [ ] Audit Log
- [ ] Navigation highlights active section
- [ ] Backend-unavailable state shows helpful message (not stack trace)
- [ ] Empty states show helpful guidance (not blank or error)
- [ ] Back button and browser history work correctly
- [ ] No raw stack traces appear in normal UI
- [ ] Page titles are descriptive

---

## 5. Workspace Flow

- [ ] Default workspace exists on first load
- [ ] Create new workspace with name and description
- [ ] Switch between workspaces
- [ ] Workspace name appears in UI headers
- [ ] Delete workspace shows confirmation dialog
- [ ] Workspace isolation: data from workspace A does not appear in workspace B
- [ ] Workspace settings are persisted across page reload
- [ ] Workspace list shows all created workspaces

---

## 6. Data-Source Flow

- [ ] Data Sources page lists existing sources
- [ ] Upload TXT file succeeds
- [ ] Upload MD file succeeds
- [ ] Upload CSV file succeeds
- [ ] Upload JSON file succeeds
- [ ] Upload PDF (text) succeeds
- [ ] Upload DOCX succeeds
- [ ] Upload XLSX succeeds
- [ ] Unsupported file type shows clear error
- [ ] File upload shows progress indicator
- [ ] Uploaded file appears in source list
- [ ] Source preview shows file content
- [ ] Profile data generates column/field stats
- [ ] Delete source removes it from list
- [ ] Source metadata includes name, type, size, date, status
- [ ] Path traversal filenames are rejected or sanitized

---

## 7. OCR / Parsing / Indexing

- [ ] Text-based PDF parses and indexes correctly
- [ ] DOCX parses and indexes correctly
- [ ] XLSX parses and indexes correctly
- [ ] Chunks are created after indexing
- [ ] Chunk count and status are visible in UI
- [ ] If Tesseract is available:
  - [ ] Scanned PDF runs OCR pipeline
  - [ ] OCR status is reported in UI
  - [ ] OCR text is indexed
- [ ] If Tesseract is unavailable:
  - [ ] OCR-unavailable state is clear (no false claims of OCR support)
  - [ ] No attempt to OCR fails silently
- [ ] Parsing errors are reported per-file (not silent)
- [ ] Large files (e.g. >10MB) are handled gracefully

---

## 8. Evidence Search

- [ ] Search bar is visible and responsive
- [ ] Searching by keyword returns matching results
- [ ] Results show source document reference
- [ ] Results show relevance score or ranking
- [ ] Search within a specific workspace returns workspace-scoped results
- [ ] Empty search returns guidance
- [ ] Search with no matching results shows empty state
- [ ] Search result metadata is visible (source, chunk, date)
- [ ] Clicking a result shows evidence detail

---

## 9. Connector Import

- [ ] Connectors page lists available connector types
- [ ] Local folder connector can be configured
- [ ] Folder path is validated (exists, readable)
- [ ] Connector setup wizard completes without errors
- [ ] Import job starts and shows progress
- [ ] Imported items appear in item list
- [ ] Item preview shows content
- [ ] Pagination works for large import results
- [ ] Large folder import (100+ files) completes within reasonable time
- [ ] Import respects file size limits
- [ ] Directories are not imported as items
- [ ] Read-only guarantee: no connector writes to external systems
- [ ] Secrets/tokens are never exposed in UI or logs
- [ ] Sensitive local paths are not leaked in error messages

---

## 10. Connector Sync

- [ ] Manual sync can be triggered
- [ ] First sync imports all items
- [ ] Second sync (no changes) shows unchanged/duplicate detection
- [ ] Sync progress is displayed
- [ ] Sync shows counts: processed, changed, unchanged, errors
- [ ] Duplicate detection prevents re-importing identical content
- [ ] Sync can be cancelled
- [ ] Cancel leaves already-imported items intact
- [ ] Pagination works for large sync results
- [ ] Rate-limit handling works (for GitHub/URL connectors)

---

## 11. Provider Setup

- [ ] Providers page lists available providers
- [ ] Fake provider is available and selectable
- [ ] Fake provider works without API keys
- [ ] Provider can be configured with environment variables
- [ ] Provider status is shown (configured/unconfigured)
- [ ] OpenAI / Anthropic provider can be configured (if key available)
- [ ] Provider secrets are redacted after save
- [ ] Provider test/check function works
- [ ] Switching provider updates downstream behavior

---

## 12. Workflow Execution

- [ ] Workflow Builder page loads
- [ ] Demo workflows are available:
  - [ ] Local Trust Report Demo
  - [ ] Evidence Search workflow
  - [ ] Evidence Synthesis workflow
  - [ ] Claim Verification workflow
  - [ ] Graph Extraction workflow
  - [ ] Trust Report workflow
  - [ ] Review Gate workflow
- [ ] Workflow can be selected/loaded
- [ ] Workflow execution starts
- [ ] Execution shows progress / current node
- [ ] Execution timeline shows node sequence
- [ ] Node output is displayed after execution
- [ ] Review Gate pausing/resuming works
- [ ] Failed executions show understandable error messages
- [ ] Execution history stores past runs
- [ ] Execution details are inspectable after completion
- [ ] Demo workflow runs end-to-end with fake provider

---

## 13. Claim Verification

- [ ] Claims are created from workflow output
- [ ] Claims list shows all claims with status
- [ ] Claim verification runs
- [ ] Verified claims show evidence references
- [ ] Unsupported claims display clearly (not hidden)
- [ ] Contradicted claims display clearly (not hidden)
- [ ] Claim status labels are correct:
  - [ ] `verified`
  - [ ] `unsupported`
  - [ ] `contradicted`
  - [ ] `pending`
- [ ] Evidence references link back to source documents
- [ ] Claim details show supporting and contradicting evidence

---

## 14. Knowledge Graph

- [ ] Graph extraction generates entities and relationships
- [ ] Graph nodes are visible in Knowledge Graph view
- [ ] Graph edges show relationships
- [ ] Entity detail shows connected entities
- [ ] Graph visualization is interactive (pan, zoom, click)
- [ ] Graph facts include evidence IDs
- [ ] Graph-to-claim linking works
- [ ] Graph extraction respects workspace isolation

---

## 15. Risk Dashboard

- [ ] Risk dashboard loads
- [ ] Risks are extracted from data
- [ ] Risk severity levels are shown
- [ ] Risk descriptions include evidence references
- [ ] Mitigation suggestions are shown (if applicable)
- [ ] Metrics are displayed (if applicable)
- [ ] Pattern/vulnerability detection results are shown

---

## 16. Trust Reports

- [ ] Trust report generation starts
- [ ] Report generation shows progress
- [ ] Completed report is readable
- [ ] Report includes sections:
  - [ ] Executive summary
  - [ ] Evidence summary
  - [ ] Claim analysis
  - [ ] Risk assessment
  - [ ] Graph analysis
- [ ] Report citations include source evidence IDs
- [ ] Markdown export produces valid `.md` file
- [ ] Exported report includes all sections
- [ ] Unsupported/contradicted claims are not hidden in report
- [ ] Report permissions (view/export) respect user role

---

## 17. Audit Logs

- [ ] Audit log page loads
- [ ] Events are recorded for key actions:
  - [ ] Workspace create/delete
  - [ ] Data source upload/delete
  - [ ] Connector import/sync
  - [ ] Provider change
  - [ ] Workflow run
  - [ ] Report export
  - [ ] Backup/reset
- [ ] Audit events show timestamp, user, action, details
- [ ] Audit log is visible only when user has permission
- [ ] Audit log can be filtered or searched

---

## 18. Backup / Reset

- [ ] `scripts/backup-local-data.sh` creates a timestamped tar.gz
- [ ] Backup includes `.decision_system/` contents
- [ ] Backup file is written to current directory
- [ ] `scripts/reset-local-data.sh` shows confirmation prompt
- [ ] Reset confirmation requires explicit `yes` (not just Enter)
- [ ] Reset without confirmation does not delete data
- [ ] After reset, `.decision_system/` is recreated empty
- [ ] Backup can be restored manually (tar -xzf)
- [ ] After restart, data is persisted (before reset)
- [ ] After reset, fresh start is possible

---

## 19. Security / Governance States

### Demo Mode (default)

- [ ] All features are accessible
- [ ] No authentication required
- [ ] Audit log records actions

### Governed Mode

- [ ] DECISION_SYSTEM_SECURITY_MODE=governed can be configured
- [ ] Login/identity page appears
- [ ] Roles are enforced:
  - [ ] `owner` — full access
  - [ ] `admin` — manage users, settings
  - [ ] `analyst` — run workflows, view data
  - [ ] `reviewer` — approve reviews, view reports
  - [ ] `viewer` — read-only access
- [ ] Restricted buttons are disabled for low-privilege roles
- [ ] 403 forbidden is displayed nicely (not stack trace)
- [ ] Viewer cannot mutate data (create, edit, delete)
- [ ] Reviewer can resolve reviews
- [ ] Report export respects role permissions
- [ ] Secrets remain redacted in all UI
- [ ] Cross-workspace data does not leak
- [ ] Audit log visibility respects role

---

## 20. Known Limitations

- [ ] All documented limitations are accurate
- [ ] No feature is claimed as supported when it is not
- [ ] OCR availability is clearly documented as Tesseract-dependent
- [ ] Notion/Drive connectors are documented as disabled/planned (not active)
- [ ] External database is not required (SQLite/JSON only)
- [ ] No auth system is claimed (demo mode is default)
- [ ] Not production-ready is stated clearly
- [ ] Docker smoke results are honest about environment constraints
- [ ] Test gaps are documented where they exist
- [ ] Enterprise features (SSO, encryption at rest, audit stream) are not claimed

---

## Summary

| Section | Status | Notes |
|---------|--------|-------|
| 1. Fresh Clone Setup | ⬜ | |
| 2. Non-Docker Startup | ⬜ | |
| 3. Docker Startup | ⬜ | |
| 4. Frontend Navigation | ⬜ | |
| 5. Workspace Flow | ⬜ | |
| 6. Data-Source Flow | ⬜ | |
| 7. OCR / Parsing / Indexing | ⬜ | |
| 8. Evidence Search | ⬜ | |
| 9. Connector Import | ⬜ | |
| 10. Connector Sync | ⬜ | |
| 11. Provider Setup | ⬜ | |
| 12. Workflow Execution | ⬜ | |
| 13. Claim Verification | ⬜ | |
| 14. Knowledge Graph | ⬜ | |
| 15. Risk Dashboard | ⬜ | |
| 16. Trust Reports | ⬜ | |
| 17. Audit Logs | ⬜ | |
| 18. Backup / Reset | ⬜ | |
| 19. Security / Governance States | ⬜ | |
| 20. Known Limitations | ⬜ | |

---

*Checklist generated for v1.33.0-dev — End-to-End Beta QA + Bug Bash.*
*Update this checklist as bugs are found, fixed, and verified.*
