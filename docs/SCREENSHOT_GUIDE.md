# Screenshot Capture Guide — v1.35.0-dev

> **Version:** 1.35.0-dev
> **Milestone:** Public Beta Release Candidate + Demo Video Script
> **Date:** 2026-06-24

## How to Seed Demo Data

```bash
# If starting fresh:
./scripts/reset-local-data.sh
./scripts/start-local.sh

# Upload sample files from demo/sample-data/ via the Data Sources page
# Or use the CLI:
decision-system index --docs-dir demo/sample-data/
```

## Before Taking Screenshots

- [ ] Close all browser tabs except the app
- [ ] Clear any personal/private data from the workspace
- [ ] Use the "Default Workspace" or create a "Demo Workspace"
- [ ] Ensure no real API keys or tokens are visible
- [ ] Use a consistent browser window size (1280x720 recommended)
- [ ] Disable any browser extensions that might appear in screenshots

## No Secrets Rule

**Before sharing screenshots, verify:**
- No API keys visible in UI, URL bar, or terminal output
- No local file paths that reveal your username/home directory
- No uploaded documents with real sensitive data
- No provider tokens or secrets visible

If in doubt, blur sensitive areas or use demo/sample-data files only.

## Screenshot Checklist

### 1. App Shell with Beta Status
- Sidebar visible with all navigation items
- Beta label visible (top of sidebar)
- Version number visible (1.35.0-dev)
- Backend connection status visible
- **File:** `screenshot-app-shell.png`

### 2. Workspace Dashboard
- Workspace name and description
- Stats/overview cards
- **File:** `screenshot-workspace.png`

### 3. Data Sources Page
- File list with uploaded documents
- File types visible (PDF, DOCX, MD, etc.)
- Parse/index status indicators
- **File:** `screenshot-data-sources.png`

### 4. Evidence Search
- Search bar with query entered
- Search results with source references
- Relevance scores visible
- **File:** `screenshot-evidence-search.png`

### 5. Connector Setup Wizard
- Connector type selection
- Local folder connector configuration
- Path field with demo path filled in
- **File:** `screenshot-connector.png`

### 6. Workflow Builder
- Workflow canvas with nodes visible
- Node palette open
- Demo workflow loaded
- **File:** `screenshot-workflow-builder.png`

### 7. Execution Details
- Execution timeline or node states
- Node inputs/outputs expandable
- Completion status visible
- **File:** `screenshot-execution.png`

### 8. Claim Ledger
- Claim list with status badges
- Verified/unsupported/contradicted visible
- Evidence references shown
- **File:** `screenshot-claim-ledger.png`

### 9. Knowledge Graph
- Graph visualization with nodes and edges
- Entity details panel
- Risk panel visible
- **File:** `screenshot-knowledge-graph.png`

### 10. Risk Dashboard
- Risk items with severity levels
- Metric displays
- **File:** `screenshot-risk-dashboard.png`

### 11. Trust Report
- Report sections visible (executive summary, evidence, claims)
- Citations linked to evidence
- Markdown export button visible
- **File:** `screenshot-trust-report.png`

### 12. Audit Log
- Event list with timestamps
- Action types visible
- **File:** `screenshot-audit-log.png`

### 13. Settings / Security Mode
- Demo/Governed mode indicator
- Provider configuration
- **File:** `screenshot-settings.png`

## Recommended Image Naming

```text
screenshot-01-app-shell.png
screenshot-02-workspace.png
screenshot-03-data-sources.png
screenshot-04-evidence-search.png
screenshot-05-connector.png
screenshot-06-workflow-builder.png
screenshot-07-execution.png
screenshot-08-claim-ledger.png
screenshot-09-knowledge-graph.png
screenshot-10-risk-dashboard.png
screenshot-11-trust-report.png
screenshot-12-audit-log.png
screenshot-13-settings.png
```

## Where Screenshots Should Live

If committed to the repo:
- `docs/screenshots/` directory
- Referenced from README via relative links
- Max 500KB per image
- PNG format preferred

If not committed (e.g., for a video or blog post):
- Keep organized in a local folder
- Include naming convention above
- Blur any sensitive information

## Quick Verification

After capturing, do a final scan:
- [ ] No secrets or tokens visible
- [ ] No personal file paths exposed
- [ ] Images are under 500KB each
- [ ] Numbering is sequential
- [ ] README links reference the correct filenames
