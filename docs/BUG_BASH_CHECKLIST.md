# Bug Bash Checklist — v1.34.0-dev

> **Version:** 1.34.0-dev
> **Milestone:** Local Beta Feedback Loop + Issue Templates
> **Date:** 2026-06-24

Use this checklist to guide structured bug bashes. Check each item after testing.
Report bugs using the GitHub issue templates.

---

## Install / Setup

- [ ] `git clone` from origin
- [ ] `cp .env.example .env`
- [ ] `./scripts/setup-local.sh` completes without errors
- [ ] Virtual environment created
- [ ] Backend dependencies installed
- [ ] Frontend dependencies installed
- [ ] `.decision_system/` data directory created
- [ ] `./scripts/doctor-local.sh` reports healthy state
- [ ] `./scripts/validate-local.sh` passes

## Startup / Shutdown

- [ ] `./scripts/start-local.sh` starts backend
- [ ] Backend responds at `http://localhost:8000/health`
- [ ] `./scripts/start-local.sh --all` starts both backend and frontend
- [ ] Frontend loads at `http://localhost:5173` (dev) or `http://localhost:3000` (Docker)
- [ ] `./scripts/stop-local.sh` stops processes cleanly
- [ ] No orphaned processes after stop

## Workspace

- [ ] Default workspace created on first load
- [ ] Create new workspace
- [ ] Switch between workspaces
- [ ] Delete workspace (with confirmation)
- [ ] Workspace isolation: data from workspace A does not appear in workspace B

## Data Upload

- [ ] Upload TXT file
- [ ] Upload MD file
- [ ] Upload CSV file
- [ ] Upload JSON file
- [ ] Upload PDF (text-based)
- [ ] Upload DOCX file
- [ ] Upload XLSX file
- [ ] Unsupported file type shows clear error
- [ ] Delete source
- [ ] Path traversal filenames rejected

## OCR / Parsing / Indexing

- [ ] Text-based PDF parses correctly
- [ ] DOCX parses correctly
- [ ] XLSX parses correctly
- [ ] Chunks created after indexing
- [ ] Parsing errors reported per-file (not silent)

## Evidence Search

- [ ] Search by keyword returns results
- [ ] Results show source document reference
- [ ] Workspace-scoped search works
- [ ] Empty/non-match search returns guidance

## Connectors

- [ ] Local folder connector configurable
- [ ] Import job shows progress
- [ ] Imported items visible in item list
- [ ] Pagination works for large results
- [ ] No connector writes to external systems
- [ ] Secrets not exposed in UI or logs

## Connector Sync

- [ ] Manual sync triggers
- [ ] Duplicate detection prevents re-import
- [ ] Sync can be cancelled
- [ ] Cancel leaves imported items intact

## Provider / Fake Provider

- [ ] Fake provider available and selectable
- [ ] Fake provider works without API keys
- [ ] Provider status shown
- [ ] Switching provider updates behavior

## Workflow Builder

- [ ] Workflow Builder page loads
- [ ] Demo workflows available
- [ ] Workflow can be selected/loaded
- [ ] Workflow execution starts
- [ ] Execution shows progress
- [ ] Failed executions show understandable errors

## Claim Verification

- [ ] Claims created from workflow output
- [ ] Claim verification runs
- [ ] Verified/unsupported/contradicted/pending statuses correct
- [ ] Evidence references link back to sources

## Knowledge Graph

- [ ] Graph extraction generates entities/relationships
- [ ] Graph nodes visible
- [ ] Graph facts include evidence IDs
- [ ] Workspace isolation respected

## Reports / Export

- [ ] Report generation starts
- [ ] Completed report readable
- [ ] Markdown export produces valid .md
- [ ] Unsupported/contradicted claims not hidden

## RBAC / Governance

- [ ] Demo mode: all features accessible
- [ ] Governed mode: roles enforced
- [ ] 403 displayed nicely (not stack trace)
- [ ] Secrets redacted in all UI

## Audit Logs

- [ ] Events recorded for key actions
- [ ] Timestamp, action, details visible
- [ ] Audit log filterable

## Backup / Reset

- [ ] `./scripts/backup-local-data.sh` creates timestamped archive
- [ ] `./scripts/reset-local-data.sh` requires explicit confirmation
- [ ] After reset, `.decision_system/` recreated empty

## Error Handling

- [ ] No raw stack traces in normal UI
- [ ] Backend-unavailable state shows helpful message
- [ ] Empty states show guidance (not errors)
- [ ] File upload shows progress indicator

## Docs Clarity

- [ ] README points to docs
- [ ] Known limitations accurate
- [ ] Setup instructions complete
- [ ] Demo path walkthrough complete

---

*Update this checklist as areas change or new features are added.*
