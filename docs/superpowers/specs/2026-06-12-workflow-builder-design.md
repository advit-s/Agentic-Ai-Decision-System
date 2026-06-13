# Phase 2: Visual Drag-and-Drop Workflow Builder

> **Goal:** Build a visual node-based workflow editor (React Flow) that lets users create, configure, save, load, and execute DAG workflows through a drag-and-drop interface. Connects to the Phase 1 REST API with offline mock data fallback.

**Architecture:** Standalone React app (`web/workflow-builder/`) built with Vite + React + React Flow. Served independently of the existing vanilla JS web UI. Linked from the main app sidebar via an "⚡ Workflows" nav item that loads the builder in place of the current view.

**Tech Stack:** React 18, React Flow 11, Vite 5, Vitest + React Testing Library, CSS Modules

---

## 1. Navigation Integration

The existing sidebar nav gains a **Workflows** entry between "War Room" and "Workspaces":

| Existing Nav | New Nav |
|---|---|
| War Room | War Room |
| — | **⚡ Workflows** (new) |
| Workspaces | Workspaces |

Clicking "⚡ Workflows" navigates to the workflow builder view. The builder replaces the current main content area — it's a full-page editor, not a constrained widget. The sidebar, topbar, and API URL config remain visible.

The builder can optionally be accessed at its own URL path (e.g. `/workflow-builder/`) for direct access during development.

## 2. Layout

The editor uses a three-zone layout:

```
┌──────────────────────────────────────────────────────┐
│  Workflow Toolbar  [New] [Save] [Load ▼] [▶ Execute] │
├────────┬─────────────────────────────┬────────────────┤
│        │                             │                │
│ Float  │                             │  Config Panel  │
│ Node   │    React Flow Canvas         │  (right drawer │
│ Palette│    (zoom, pan, minimap)      │   when node    │
│        │                             │   selected)    │
│ (drag- │                             │                │
│ gable) │                             │                │
│        │                             │  Execution     │
│        │                             │  Panel (during │
│        │                             │  execution)    │
└────────┴─────────────────────────────┴────────────────┘
```

- **Floating Node Palette** — draggable, can be hidden via toggle (hotkey: `P`). Categorized node list fetched from API. Dragging a node onto the canvas creates an instance.
- **React Flow Canvas** — full editor area with zoom, pan, minimap, grid background. Custom node types for each of the 16 built-in node types.
- **Config Panel** — right drawer that opens when a node is selected. Auto-renders from each node's `get_config_schema()` JSON Schema. Closes on canvas click.
- **Execution Panel** — replaces the config panel during execution. Shows all nodes with real-time status updates via WebSocket. Collapsible.

## 3. Component Tree

```
App
├── WorkflowToolbar        — New, Save, Load dropdown, Execute, Export
│   └── LoadDropdown       — List of saved workflows from API
├── NodePalette            — Floating draggable palette
│   └── NodeCategory       — Color-coded group (triggers, data, flow, output)
│       └── PaletteItem    — Individual draggable node type
├── WorkflowCanvas         — React Flow canvas wrapper
│   ├── CustomNode         — React Flow custom node component
│   │   ├── NodeHeader     — Icon + label + status badge
│   │   ├── PortHandles    — Input/output connection points
│   │   └── StatusOverlay  — Running/completed/failed indicator
│   ├── CustomEdge         — Animated connection edge
│   ├── Minimap            — React Flow minimap
│   └── Controls           — Zoom controls
├── ConfigPanel            — Right drawer, visible when node selected
│   ├── SectionHeader      — Node type + label + delete button
│   └── SchemaForm         — Auto-rendered from JSON Schema
│       ├── StringField
│       ├── NumberField
│       ├── EnumField
│       ├── BooleanField
│       └── ArrayField
└── ExecutionPanel         — Right panel during execution
    ├── ExecutionStatus     — Overall workflow status + timing
    └── NodeStatusList     — Per-node status + timing + I/O
```

## 4. Data Flow

### API Client Layer (`api.js`)

```
React App ──▶ api.js ──▶ Phase 1 REST API (preferred)
                        └──▶ Mock data (fallback, offline-safe)
```

Endpoints called by the workflow builder:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/workflows/nodes` | List available node types + JSON schemas |
| `POST` | `/workflows` | Create new workflow |
| `GET` | `/workflows` | List saved workflows |
| `GET` | `/workflows/{id}` | Load workflow definition |
| `PUT` | `/workflows/{id}` | Save/update workflow |
| `DELETE` | `/workflows/{id}` | Delete workflow |
| `POST` | `/workflows/{id}/execute` | Execute workflow |
| `GET` | `/executions/{id}` | Get execution state |
| `WS` | `/executions/{id}/stream` | Live execution events |

### Mock Data (Offline)

The builder follows the same pattern as the existing vanilla JS UI:

1. Try API first (if `apiBaseUrl` is configured and reachable)
2. Fall back to embedded mock data in `src/mockData.js`
3. Provide a "Using mock data" indicator

Mock data includes:
- `mockNodeTypes` — all 16 node types with full JSON schemas
- `mockWorkflows` — 2-3 pre-built example workflows (e.g. "Quarterly Risk Review", "Data Pipeline")
- `mockExecutionState` — sample execution with all node statuses
- `mockEvents` — sample WebSocket event stream for demo

### WebSocket Stream

During execution, the builder connects to `WS /executions/{id}/stream` to receive real-time `ExecutionEvent` objects:

```typescript
interface ExecutionEvent {
  execution_id: string;
  event_type: "node_started" | "node_completed" | "node_failed"
                | "workflow_completed" | "workflow_failed" | "log";
  node_id: string | null;
  data: Record<string, unknown>;
  timestamp: string;  // ISO 8601
}
```

For mock/offline mode, the events are simulated with a `setInterval`-based progression through the DAG layers.

## 5. Custom React Flow Node Types

Each built-in node type gets a custom React Flow node renderer. The renderer is determined by the `type` prefix:

| Category | Color | Prefix Examples |
|----------|-------|----------------|
| Triggers | Blue (`#3b82f6`) | `decision_system.trigger_manual`, `decision_system.input_text` |
| Data/Analysis | Orange (`#f59e0b`) | `decision_system.retrieve`, `decision_system.profile_data`, `decision_system.extract_graph` |
| AI/Processing | Purple (`#8b5cf6`) | `decision_system.technical_analyst`, `decision_system.risk_analyst`, `decision_system.extract_claims`, `decision_system.verify_claims`, `decision_system.detect_patterns`, `decision_system.war_room` |
| Output | Green (`#22c55e`) | `decision_system.write_report`, `decision_system.map_ontology` |
| Flow Control | Gray (`#6b7280`) | `decision_system.filter`, `decision_system.merge`, `decision_system.code` |

Each node displays:
- Category-colored header bar with icon
- Node label (editable inline or via config panel)
- Input port handles (left side) — one per named input
- Output port handles (right side) — one per named output
- Status border overlay during execution (green for completed, red for failed, yellow for running)

## 6. Config Panel (Auto-Rendered from JSON Schema)

When a node is selected on the canvas, the config panel opens on the right side. The panel reads the node's `config_schema` (from `get_config_schema()`) and renders appropriate form fields:

```json
{
  "type": "object",
  "properties": {
    "top_k": {
      "type": "integer",
      "default": 5,
      "title": "Top K"
    },
    "severity_threshold": {
      "type": "string",
      "default": "low",
      "enum": ["low", "medium", "high", "critical"],
      "title": "Severity Threshold"
    }
  }
}
```

Schema-to-component mapping:
- `"string"` → `<input type="text">`
- `"integer"` → `<input type="number">`
- `"number"` → `<input type="number" step="any">`
- `"boolean"` → `<input type="checkbox">`
- `string + enum` → `<select>` dropdown
- `"array"` → list editor with add/remove
- `"object"` → nested form section

All properties include their `title`, `description`, and `default` from the schema. The config panel also shows:
- The node's `input_schema` (read-only, documents what inputs the node expects)
- The node's `output_schema` (read-only, shows what outputs it produces)
- Error policy selector (fail_workflow, fail_node, retry, skip)
- Retry configuration (if policy is "retry")
- A "Delete Node" button

## 7. Execution Panel

When the user clicks Execute:
1. The config panel collapses; the execution panel opens on the right
2. The workflow is POSTed to `/workflows/{id}/execute`
3. The builder connects to `WS /executions/{id}/stream` for live updates
4. Each node's status updates in real-time as events arrive

The execution panel shows:

```
Workflow: Quarterly Risk Review
Status: Running (3/8 nodes completed)
Duration: 2.3s

✅ Manual Trigger       0.02s
✅ Input Text           0.01s
✅ Retrieve Evidence    0.15s (5 chunks)
⟳ Technical Analyst    2.1s  [████████░░░░]
○ Risk Analyst         (pending)
○ Extract Claims       (pending)
○ Verify Claims        (pending)
○ Write Report         (pending)
```

Clicking a completed/failed node expands it to show its inputs and outputs as collapsible JSON views.

## 8. WorkflowToolbar

Toolbar across the top of the editor:

| Button | Action |
|--------|--------|
| **+ New** | Clear canvas, prompt for workflow name |
| **💾 Save** | Create or update workflow via API |
| **📂 Load ▼** | Dropdown listing saved workflows from API |
| **▶ Execute** | Validate and execute workflow (confirms if unsaved) |
| **📋 Export** | Download workflow definition as JSON file |
| **📥 Import** | Upload JSON file to load as workflow |

Save/Load state is managed via React context and synced to the API.

## 9. Error Handling States

| State | Behavior |
|-------|----------|
| **API unreachable** | Mock data fallback, toast notification "API unreachable — using mock data" |
| **Invalid workflow** | Execute button shows validation errors via toast, highlights problematic nodes on canvas |
| **Node execution failure** | Node turns red on canvas, execution panel shows error details. Other nodes continue based on their error policy |
| **WebSocket disconnect** | Falls back to polling `GET /executions/{id}` every 1 second |
| **Workflow with no trigger** | Validation error: "Workflow must have at least one trigger node" |
| **DAG has cycle** | Validation error from backend, shown as toast |
| **Empty canvas** | Show placeholder text: "Drag nodes from the palette to build your workflow" |

## 10. Testing

- **Component tests** via Vitest + React Testing Library for each component
- **Mock API client** for offline testing (no API keys)
- **Flow integration tests** — simulate drag, connect, configure, execute flow
- **Existing 796 tests** remain untouched
- **CI check** — `npm test` in `web/workflow-builder/` must pass

Test categories:
1. **NodePalette** — renders all 16 node types, drag initiates create
2. **WorkflowCanvas** — drops node, connects nodes, validates connections
3. **ConfigPanel** — renders schema fields, updates node config
4. **ExecutionPanel** — renders status list, processes events
5. **API client** — CRUD operations, mock fallback
6. **Integration** — full create→configure→save→load cycle

## 11. Non-Goals (Phase 2)

- No credential management or OAuth (Phase 3)
- No plugin/node marketplace (Phase 3)
- No user accounts or RBAC (Phase 4)
- No WebSocket reconnection beyond simple retry
- No undo/redo stack (post-MVP)
- No workflow versioning
- No multi-tenant workspaces

## 12. File Structure

```
web/workflow-builder/
├── index.html
├── package.json
├── vite.config.js
├── src/
│   ├── main.jsx                 # React entry point
│   ├── App.jsx                  # Layout + state management
│   ├── components/
│   │   ├── WorkflowCanvas.jsx   # React Flow wrapper
│   │   ├── WorkflowToolbar.jsx  # Save/Load/Execute buttons
│   │   ├── NodePalette.jsx      # Floating draggable palette
│   │   ├── ConfigPanel.jsx      # Right drawer config editor
│   │   ├── ExecutionPanel.jsx   # Execution status panel
│   │   ├── SchemaForm.jsx       # JSON Schema → Form renderer
│   │   └── NodeType.jsx         # Custom React Flow node component
│   ├── api.js                   # REST + WS client
│   ├── mockData.js              # Offline fallback
│   ├── nodeTypes.js             # Node type → renderer mapping
│   └── styles/
│       ├── canvas.css
│       ├── palette.css
│       ├── config-panel.css
│       ├── toolbar.css
│       └── execution-panel.css
├── __tests__/
│   ├── WorkflowCanvas.test.jsx
│   ├── NodePalette.test.jsx
│   ├── ConfigPanel.test.jsx
│   ├── ExecutionPanel.test.jsx
│   └── api.test.js
└── vitest.config.js
```

## 13. Backend Additions

The Phase 1 API already provides all needed REST endpoints. Phase 2 adds:

1. **WebSocket endpoint** — `WS /executions/{id}/stream` using FastAPI's `WebSocket` support
   - Accepts execution ID
   - Streams `ExecutionEvent` objects from the `DAGEngine` event bus
   - In-memory event queue per execution
   - Falls back to empty stream if execution doesn't exist

2. **CORS configuration** — Add `localhost:5173` (Vite dev server) to allowed origins for development

3. **Static file serving** — In production, the React build output is served from the FastAPI app

## 14. Future Phases

| Phase | Focus | Depends On |
|-------|-------|------------|
| **Phase 2 (this)** | Visual drag-and-drop workflow builder (React Flow) | Phase 1 |
| **Phase 3** | Node SDK, plugin entry points, credential management, triggers (webhook, cron) | Phase 1-2 |
| **Phase 4** | Auth, RBAC, multi-tenant, execution history viewer, workflow templates | Phase 1-3 |
