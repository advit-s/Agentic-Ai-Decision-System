# Workflow Builder — Architecture & Reference

## Overview

The workflow builder is a **React 18 + React Flow** single-page application at `web/workflow-builder/`. It provides a visual DAG (directed acyclic graph) editor for composing AI decision workflows from 28 node types.

The builder runs in two modes:
- **Mock mode** (default) — works offline with simulated data, no backend needed
- **Live mode** — connects to the FastAPI backend at a user-configured URL

## Component Tree

```
App (ReactFlowProvider > ToastProvider)
├── WorkflowToolbar          — New, Save, Load, Execute, Export, Templates, History, Schedules, Providers, Theme, Connection badge
├── NodePalette              — Draggable node type sidebar (5 categories)
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

28 node types across 5 categories:

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
