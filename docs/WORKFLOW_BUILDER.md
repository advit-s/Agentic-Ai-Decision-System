# Workflow Builder — Architecture & Reference

## Overview

The workflow builder is a **React 18 + React Flow** single-page application at `web/workflow-builder/`. It provides a visual DAG (directed acyclic graph) editor for composing AI decision workflows from 30+ node types.

The builder runs in two modes:
- **Mock mode** (default) — works offline with simulated data, no backend needed
- **Live mode** — connects to the FastAPI backend at a user-configured URL

## Component Tree

```
App (ReactFlowProvider > ToastProvider)
├── WorkflowToolbar          — New, Save, Load, Execute, Export, Templates, History, Schedules, Providers, Theme, Connection badge
├── NodePalette              — Draggable node type sidebar (8 categories)
├── WorkflowCanvas           — React Flow canvas with Background, Controls, MiniMap
│   └── NodeComponent        — Custom React Flow node card (per-type icon, color, status glyphs)
└── ResizablePanel (right sidebar, 280–900px)
    ├── ConfigPanel          — Node configuration (label, schema form, provider badge, error policy)
    ├── ExecutionPanel       — Live execution events, node statuses, structured output views
    ├── ExecutionHistory     — Saved run browser, search, sort, detail drill-down
    ├── ExecutionCompare     — Side-by-side run comparison
    ├── WorkflowDiff         — Version diff between workflow snapshots
    ├── ScheduleManager      — Cron schedule CRUD for workflows
    ├── ProviderManager      — LLM provider config with health checks
    └── TemplateDialog       — Pre-built workflow template selector (modal)
```

## Data Flow

```
User drags node from palette
  → NodePalette sets dataTransfer with nodeType JSON
  → WorkflowCanvas.onDrop creates React Flow node with fresh ID
  → App state (nodes, edges) updated via useWorkflowState hook

User connects nodes
  → onConnect adds edge to edges state
  → hasUnsavedChanges flag set → Save button shows asterisk

User clicks Execute
  → handleSave (if unsaved)
  → executeWorkflow(id) calls POST /workflows/{id}/execute
  → streamExecutionEvents subscribes to WebSocket /executions/{id}/stream
  → Each event updates nodeStatuses (running/completed/failed)
  → NodeComponent shows status glyph (⟳/✓/✕) and animated execution edges
  → ExecutionPanel shows live node progress with structured output previews

User loads a template
  → TemplateDialog.onSelect(template)
  → handleApplyTemplate remaps template IDs → fresh IDs → creates nodes + edges
  → Canvas cleared, template nodes/edges loaded, workflow renamed
```

## State Management

All state lives in `App.jsx` (CanvasInner) via `useState` hooks:

| State | Purpose |
|-------|---------|
| `nodes` / `edges` | React Flow graph state (via useWorkflowState) |
| `nodeTypes` | Fetched node type definitions |
| `currentWorkflowId` | UUID or null for unsaved |
| `currentWorkflowName` | Display name |
| `selectedNode` | Currently selected node for config panel |
| `nodeStatuses` | Per-node execution status + outputs |
| `isExecuting` | Execution in progress flag |
| `workflowStatus` | "running" \| "completed" \| "failed" \| null |
| `hasUnsavedChanges` | Dirty flag for Save button |
| `templateDialogOpen` | Template modal visibility |

## API Layer (`src/api.js`)

All API calls go through `api.js`, which routes to mock or real backend based on `getBaseUrl()`:

| Function | Mock | Real Endpoint |
|----------|------|--------------|
| `fetchNodeTypes()` | `MOCK_NODE_TYPES` | `GET /workflows/nodes` |
| `listWorkflows()` | `_mockWorkflows` | `GET /workflows` |
| `saveWorkflow(wf)` | Mock store | `POST /workflows` or `PUT /workflows/{id}` |
| `getWorkflow(id)` | Mock lookup | `GET /workflows/{id}` |
| `deleteWorkflow(id)` | Mock remove | `DELETE /workflows/{id}` |
| `executeWorkflow(id)` | Mock events | `POST /workflows/{id}/execute` |
| `streamExecutionEvents(id, cb)` | Simulated events | `WS /executions/{id}/stream` |
| `listProviders()` | `MOCK_PROVIDERS` | `GET /providers` |
| `createProvider(p)` | Mock push | `POST /providers` |
| `checkProvider(name)` | Mock ok | `POST /providers/{name}/check` |
| `createSchedule(s)` | Mock push | `POST /schedules` |
| `listSchedules(wfId)` | Mock filter | `GET /schedules` |
| `listExecutionHistory()` | `MOCK_EXECUTION_HISTORY` | `GET /executions/history` |

## Workflow Templates

5 pre-built templates in `src/templates.js`:

| Template | Nodes | Description |
|----------|-------|-------------|
| **Blank Canvas** | 0 | Empty canvas |
| **Research Pipeline** | 5 | Trigger → Researcher → Critic → Synthesizer → Report |
| **Data Analysis** | 5 | Trigger + Query → Retrieve → Data Analyst → Report |
| **Compliance Audit** | 7 | Trigger → Tech Analyst + Risk Analyst → Extract → Verify → Review Gate → Report |
| **Full Pipeline** | 10 | Trigger → Researcher + Retrieve + Data Analyst → Critic → Synthesizer → Verify + War Room → Review Gate → Report |

## Node Types

30+ node types across 8 categories:

- **⚡ Triggers** (5): Manual, Input Text, Cron, Webhook, File Watch
- **📊 Data** (4): Retrieve, Extract Graph, Profile Data, Data Analyst
- **🤖 AI / Analysis** (9): Technical Analyst, Risk Analyst, Extract Claims, Verify Claims, Researcher, Critic, Synthesizer, Detect Patterns, War Room
- **📄 Output** (2): Write Report, Map Ontology
- **🔀 Flow Control** (5): Filter, Merge, Code, Review Gate, decision_system.claim_ledger

Each node type has:
- `config_schema` — JSON Schema for the configuration panel
- `input_schema` / `output_schema` — port definitions
- `icon` / `color` — visual identity
- `categories` — category membership

## Provider System

Providers manage LLM connections for AI nodes. Each node's config_schema may include a `provider` enum field (fake / nvidia_nim / ollama) for per-node overrides.

- **ProviderManager** component: CRUD for providers, test connection, set default
- **Health indicators**: Green/yellow/gray dots in ProviderManager cards and toolbar badge
- **Backend**: `POST /providers/{name}/check` tests with a simple completion

## Styles & Design System

The frontend uses CSS custom properties for theming:

```css
--color-primary: #2563eb;
--color-ember: #d97706;
--color-success: #059669;
--color-bg: #f8fafc;       /* light */
--color-bg: #0a0f1c;       /* dark */
--color-surface: #ffffff;  /* light */
--color-surface: #111827;  /* dark */
--radius: 8px;
--shadow-sm/md/lg: ...;
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
```

Key CSS files:

| File | Purpose |
|------|---------|
| `src/App.css` | Design tokens, layout, loading skeletons, status badges |
| `src/styles/canvas.css` | React Flow background, minimap, controls, animated edges |
| `src/styles/toolbar.css` | Toolbar buttons, dropdown, dividers, connection badge |
| `src/styles/execution-panel.css` | Execution result cards, node status bars, timeline view |
| `src/styles/config-panel.css` | Node config form, provider badge, port lists |
| `src/styles/provider-manager.css` | Provider cards, add form, health indicators |
| `src/styles/template-dialog.css` | Template dialog overlay, grid cards |

## Running Tests

```bash
# Frontend (Vitest)
cd web/workflow-builder
npx vitest run                    # 35+ tests
npx vite build                    # Production build

# Backend (Pytest)
cd /project
python -m pytest -q               # 1061+ tests
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save workflow |
| `Delete` / `Backspace` | Delete selected node |
| `Escape` | Close all panels |
| `Space` | Execute workflow |
| `Ctrl+Shift+E` | Export as JSON |
| `Shift+?` | Show shortcuts help |

## v1.22 — Productized Workflow Builder

### Node Catalog (v1.22)

Categories: **Core**, **Data**, **Evidence**, **AI**, **Verification**, **Review**, **Report**, **Utility**

| Node Type | Category | Provider Required | Safety Warning |
|-----------|----------|-------------------|----------------|
| Start | Core | No | — |
| Manual Input | Core | No | — |
| Cron Trigger | Core | No | — |
| Webhook Trigger | Core | No | — |
| File Watch Trigger | Core | No | — |
| Retrieve Evidence | Evidence | No | — |
| Evidence Search | Evidence | No | — |
| Evidence Synthesis | AI | **Yes** | Claims are draft-quality until verified |
| Technical Analyst | AI | No | — |
| Risk Analyst | AI | No | — |
| Researcher | AI | No | — |
| Critic / Judge | AI | No | — |
| Decision Synthesizer | AI | No | — |
| Data Analyst | AI | No | — |
| Extract Claims | AI | No | — |
| Planner | AI | No | — |
| Auditor | AI | No | — |
| Compliance Checker | AI | No | — |
| War Room | AI | No | — |
| Verify Claims | Verification | No | Verification is against available evidence only |
| Claim Verifier v2 | Verification | No | Verification is against available evidence only |
| Contradiction Scan | Verification | No | — |
| Verification Summary | Verification | No | — |
| Review Gate | Review | No | Pauses workflow for human approval |
| Write Report | Report | No | Report quality depends on claim verification |
| Filter | Utility | No | — |
| Merge | Utility | No | — |
| Code Node | Utility | No | **DISABLED by default** |
| Code Runner | Utility | No | **Unsafe** |

### Configuration Panels

Each node shows:
- Human-readable label and description
- Required fields list
- Provider requirement warning (if applicable)
- Safety warning (if applicable)
- Auto-generated form for config_schema fields
- Input/output port definitions

### Workflow Validation

Before running a workflow, click **Validate** to check:
1. At least one Start/trigger node exists
2. No disconnected nodes
3. All required fields are filled
4. Provider-required nodes have a provider configured
5. Unsafe Code nodes are flagged
6. Workspace ID is set for evidence/verification nodes

Validation results are shown in a dialog with errors and warnings. Workflows with errors cannot be executed.

### Execution Experience

When a workflow runs:
- Node status updates live on the canvas
- Elapsed timer shows run duration
- Each node shows running/completed/failed status
- Execution panel shows event timeline
- Verification and trust report actions appear after completion

### Demo Templates

Built-in templates (no cloud keys required):

| Template | Nodes | Description |
|----------|-------|-------------|
| Local Evidence Search | Start → Evidence Search → Verification Summary | Search local evidence |
| Evidence → AI Synthesis → Verify | Start → Search → Synthesize → Contradiction Scan → Verify → Report | Full AI pipeline |
| Risk Review Workflow | Start → Search → Risk Analyst → Extract → Verify → Review Gate → Report | Risk analysis with human review |
| Trust Report Generator | Start → Search → Extract → Verify → Contradiction Scan → Report | Generate verified trust report |
| Data Profile Summary | Start → Profile → Detect Patterns → Summary | Profile CSV data |

### Import/Export

- **Export**: Click the Export button to download the current workflow as JSON
- **Import**: Click the Import button to load a workflow from a JSON file
- Import validates the JSON structure before loading

### Provider Integration

- Provider selector available in node config panels
- Evidence Synthesis node shows a required provider warning
- Provider Manager accessible from toolbar
- Fake provider works offline with no API keys

### Key Files

| File | Purpose |
|------|---------|
| `src/nodeTypes.js` | Node catalog and category definitions |
| `src/workflowValidation.js` | Pre-run validation logic |
| `src/templates.js` | Demo workflow templates |
| `src/mockData.js` | Mock data with categorized node types |
| `src/components/ConfigPanel.jsx` | Enhanced config panel with catalog hints |
| `src/components/ValidationDialog.jsx` | Validation results display |
| `src/components/OnboardingPanel.jsx` | First-run onboarding |
| `src/components/WorkflowToolbar.jsx` | Toolbar with validate/import/export |
| `src/styles/config-panel.css` | Config panel and catalog hint styles |
| `scripts/local-demo-seed.sh` | Demo seed script |

---

## Connector Setup UI

The Connectors page (available from the main navigation) provides a wizard-style
setup experience:

1. **Choose connector type** — Select from Local Folder, GitHub Repository, or URL Import.
   Notion and Google Drive are shown as disabled/planned with setup guidance.
2. **Review capabilities** — Each connector shows what data it can read (all read-only).
3. **Configure fields** — Schema-driven forms adapt to the selected connector type.
4. **Configure credentials** — Token/env-var fields show guidance on environment variable setup.
5. **Test connection** — Test results include structured diagnostics (reachable, auth status, warnings).
6. **Preview items** — Before import, you can see item titles, types, sizes, and source URLs.
7. **Create connector** — Save the configuration to your workspace.
8. **Import selected items** — Select items to import as local data sources.

### Permission requirements
- **Viewer**: Can view connectors and setup schemas only.
- **Analyst**: Can import and sync if permission allows.
- **Admin/Owner**: Full connector management including create, update, delete, and scheduling.
