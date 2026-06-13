# Phase 2: Visual Workflow Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a visual drag-and-drop workflow editor (React Flow) that lets users create, configure, save, load, and execute DAG workflows through a visual interface, plus the WebSocket backend endpoint for real-time execution events.

**Architecture:** Standalone React app at `web/workflow-builder/` (Vite + React 18 + React Flow 11) with mock-first data fallback. Node palette, canvas, and config panel follow the approved three-zone layout. Backend adds a single WebSocket endpoint at `WS /executions/{id}/stream`.

**Tech Stack:** React 18, React Flow 11, Vite 5, Vitest + React Testing Library, CSS Modules, FastAPI WebSocket (Python)

---

## File Structure

```
web/workflow-builder/
├── index.html                  # Entry HTML (minimal, just <div id="root">)
├── package.json                # Deps: react, react-dom, reactflow, vite, vitest
├── vite.config.js              # Dev server config
├── vitest.config.js            # Test config
├── src/
│   ├── main.jsx                # ReactDOM.createRoot
│   ├── App.jsx                 # Root component — canvas + palette + panels + toolbar
│   ├── App.css                 # Global app layout + CSS variables
│   ├── api.js                  # HTTP + WS client with mockData.js fallback
│   ├── mockData.js             # 16 node types, 2 sample workflows, mock events
│   ├── nodeTypes.js            # Node type → color/label/category mapping
│   ├── components/
│   │   ├── WorkflowCanvas.jsx  # React Flow <ReactFlow> wrapper
│   │   ├── WorkflowToolbar.jsx # New | Save | Load ▼ | Execute | Export | Import
│   │   ├── NodePalette.jsx     # Floating draggable palette
│   │   ├── ConfigPanel.jsx     # Right drawer config editor
│   │   ├── ExecutionPanel.jsx  # Execution status sidebar
│   │   ├── SchemaForm.jsx      # JSON Schema → form field renderer
│   │   ├── NodeComponent.jsx   # Custom React Flow node component
│   │   ├── Toast.jsx           # Toast notification component
│   │   └── LoadDropdown.jsx    # Saved workflows dropdown
│   └── styles/
│       ├── toolbar.css
│       ├── palette.css
│       ├── canvas.css
│       ├── config-panel.css
│       ├── execution-panel.css
│       └── toast.css
├── __tests__/
│   ├── api.test.js             # API client tests
│   ├── mockData.test.js        # Mock data structure validation
│   ├── NodePalette.test.jsx    # Palette rendering + drag
│   ├── WorkflowCanvas.test.jsx # Canvas + connections
│   ├── ConfigPanel.test.jsx    # Config panel + schema form
│   ├── SchemaForm.test.jsx     # Schema field rendering
│   ├── ExecutionPanel.test.jsx # Execution status rendering
│   └── integration.test.jsx    # Full create → configure → execute flow
└── public/                     # Static assets (favicon etc., empty for now)
```

**Backend addition:**
```
src/decision_system/workflow_engine/
  ├── stream.py                   # NEW: WebSocket + in-memory event bus
  └── api.py                      # MODIFY: add WebSocket endpoint import
```

**Integration change:**
```
web/index.html                   # MODIFY: add "⚡ Workflows" nav item
web/styles.css                   # MODIFY: if needed for nav item styles
```

---

### Task 1: Scaffold Vite + React Project

**Files:**
- Create: `web/workflow-builder/package.json`
- Create: `web/workflow-builder/vite.config.js`
- Create: `web/workflow-builder/vitest.config.js`
- Create: `web/workflow-builder/index.html`
- Create: `web/workflow-builder/src/main.jsx`
- Create: `web/workflow-builder/public/.gitkeep`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "workflow-builder",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "reactflow": "^11.11.4"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.2",
    "vitest": "^2.0.5",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.8",
    "jsdom": "^24.1.1"
  }
}
```

- [ ] **Step 2: Create vite.config.js**

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls to the Python backend during dev
    proxy: {
      '/workflows': 'http://localhost:8000',
      '/executions': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
```

- [ ] **Step 3: Create vitest.config.js**

```js
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: [],
    include: ['__tests__/**/*.test.{js,jsx}'],
  },
})
```

- [ ] **Step 4: Create index.html**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Workflow Builder</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create src/main.jsx**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 6: Install dependencies and verify**

Run: `cd web/workflow-builder && npm install`

Expected: `package-lock.json` created, node_modules populated.

Run: `npx vite --version`
Expected: prints vite version, no crash.

- [ ] **Step 7: Commit**

```bash
git add web/workflow-builder/package.json web/workflow-builder/vite.config.js web/workflow-builder/vitest.config.js web/workflow-builder/index.html web/workflow-builder/src/main.jsx web/workflow-builder/public/.gitkeep
git commit -m "feat: scaffold Vite + React project for workflow builder"
```

---

### Task 2: API Client with Mock Data Fallback

**Files:**
- Create: `web/workflow-builder/src/mockData.js`
- Create: `web/workflow-builder/src/api.js`
- Create: `web/workflow-builder/__tests__/mockData.test.js`
- Create: `web/workflow-builder/__tests__/api.test.js`

- [ ] **Step 1: Write the mock data file**

```js
// mockData.js — Offline-safe mock data matching Phase 1 API response shapes

const MOCK_NODE_TYPES = [
  {
    type: "decision_system.trigger_manual",
    label: "Manual Trigger",
    description: "Start a workflow manually",
    categories: ["trigger"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { triggered: { type: "boolean" } } },
  },
  {
    type: "decision_system.input_text",
    label: "Input Text",
    description: "Provide text input for the workflow",
    categories: ["trigger"],
    config_schema: {
      type: "object",
      properties: {
        text: { type: "string", title: "Text", default: "" },
        label: { type: "string", title: "Label", default: "Enter text" },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { text: { type: "string" } } },
  },
  {
    type: "decision_system.retrieve",
    label: "Retrieve Evidence",
    description: "Retrieve documents from the vector store",
    categories: ["data"],
    config_schema: {
      type: "object",
      properties: {
        collection: { type: "string", title: "Collection", default: "company_docs" },
        top_k: { type: "integer", title: "Top K", default: 5 },
      },
    },
    input_schema: { type: "object", properties: { query: { type: "string" } } },
    output_schema: { type: "object", properties: { chunks: { type: "array" } } },
  },
  {
    type: "decision_system.technical_analyst",
    label: "Technical Analyst",
    description: "Analyze technical data and system information",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { analysis: { type: "object" } } },
  },
  {
    type: "decision_system.risk_analyst",
    label: "Risk Analyst",
    description: "Analyze risks and vulnerabilities",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { risks: { type: "array" } } },
  },
  {
    type: "decision_system.extract_claims",
    label: "Extract Claims",
    description: "Extract claims from analysis output",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        supported_types: { type: "array", title: "Supported Types", items: { type: "string" } },
      },
    },
    input_schema: { type: "object", properties: { text: { type: "string" } } },
    output_schema: { type: "object", properties: { claims: { type: "array" } } },
  },
  {
    type: "decision_system.verify_claims",
    label: "Verify Claims",
    description: "Verify extracted claims against evidence",
    categories: ["ai"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { claims: { type: "array" } } },
    output_schema: { type: "object", properties: { verified: { type: "array" } } },
  },
  {
    type: "decision_system.write_report",
    label: "Write Report",
    description: "Generate a decision report from verified claims",
    categories: ["output"],
    config_schema: {
      type: "object",
      properties: {
        format: { type: "string", title: "Format", default: "markdown", enum: ["markdown", "json"] },
      },
    },
    input_schema: { type: "object", properties: { claims: { type: "array" } } },
    output_schema: { type: "object", properties: { report: { type: "object" } } },
  },
  {
    type: "decision_system.extract_graph",
    label: "Extract Graph",
    description: "Extract entities and relationships from documents",
    categories: ["data"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { chunks: { type: "array" } } },
    output_schema: { type: "object", properties: { graph: { type: "object" } } },
  },
  {
    type: "decision_system.profile_data",
    label: "Profile Data",
    description: "Profile local CSV data files",
    categories: ["data"],
    config_schema: {
      type: "object",
      properties: {
        catalog_path: { type: "string", title: "Catalog Path", default: "company_data" },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { profiles: { type: "array" } } },
  },
  {
    type: "decision_system.map_ontology",
    label: "Map Ontology",
    description: "Map data profiles to ontology concepts",
    categories: ["output"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { profiles: { type: "array" } } },
    output_schema: { type: "object", properties: { ontology: { type: "object" } } },
  },
  {
    type: "decision_system.detect_patterns",
    label: "Detect Patterns",
    description: "Run pattern and vulnerability detection",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        severity_threshold: {
          type: "string", title: "Severity Threshold", default: "low",
          enum: ["low", "medium", "high", "critical"],
        },
      },
    },
    input_schema: { type: "object", properties: { profiles: { type: "array" } } },
    output_schema: { type: "object", properties: { insights: { type: "array" } } },
  },
  {
    type: "decision_system.war_room",
    label: "Run War Room",
    description: "Run the multi-role analysis protocol",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        question: { type: "string", title: "Question", description: "Business question", default: "" },
      },
    },
    input_schema: { type: "object", properties: { question: { type: "string" } } },
    output_schema: { type: "object", properties: { war_room_run: { type: "object" } } },
  },
  {
    type: "decision_system.filter",
    label: "Filter",
    description: "Filter data based on conditions",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        field: { type: "string", title: "Field to check", default: "" },
        operator: {
          type: "string", title: "Operator", default: "exists",
          enum: ["exists", "equals", "not_equals", "greater_than", "less_than"],
        },
        value: { type: "string", title: "Value", default: "" },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "array" } } },
    output_schema: { type: "object", properties: { filtered: { type: "array" } } },
  },
  {
    type: "decision_system.merge",
    label: "Merge",
    description: "Merge multiple data sources",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        strategy: {
          type: "string", title: "Strategy", default: "merge",
          enum: ["merge", "concat"],
        },
      },
    },
    input_schema: { type: "object", properties: { sources: { type: "array" } } },
    output_schema: { type: "object", properties: { merged: { type: "object" } } },
  },
  {
    type: "decision_system.code",
    label: "Code",
    description: "Execute a Python snippet",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        source: { type: "string", title: "Python Code", default: "# output = ...", format: "textarea" },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { result: { type: "object" } } },
  },
];

const MOCK_WORKFLOWS = [
  {
    id: "wf-sample-1",
    name: "Quarterly Risk Review",
    description: "Analyze company data and generate a risk report",
    nodes: [
      { id: "node-1", type: "decision_system.trigger_manual", label: "Start", config: {}, error_policy: "fail_workflow" },
      { id: "node-2", type: "decision_system.input_text", label: "Business Question", config: { text: "Where are we losing money?" }, error_policy: "fail_workflow" },
      { id: "node-3", type: "decision_system.retrieve", label: "Retrieve Evidence", config: { collection: "company_docs", top_k: 5 }, error_policy: "fail_workflow" },
      { id: "node-4", type: "decision_system.technical_analyst", label: "Tech Analysis", config: { provider: "fake" }, error_policy: "fail_workflow" },
      { id: "node-5", type: "decision_system.risk_analyst", label: "Risk Analysis", config: { provider: "fake" }, error_policy: "fail_workflow" },
      { id: "node-6", type: "decision_system.extract_claims", label: "Extract Claims", config: {}, error_policy: "fail_workflow" },
      { id: "node-7", type: "decision_system.write_report", label: "Generate Report", config: { format: "markdown" }, error_policy: "fail_workflow" },
    ],
    connections: [
      { source_node: "node-1", source_output: "default", target_node: "node-2", target_input: "default" },
      { source_node: "node-2", source_output: "default", target_node: "node-3", target_input: "default" },
      { source_node: "node-3", source_output: "default", target_node: "node-4", target_input: "default" },
      { source_node: "node-3", source_output: "default", target_node: "node-5", target_input: "default" },
      { source_node: "node-4", source_output: "default", target_node: "node-6", target_input: "default" },
      { source_node: "node-5", source_output: "default", target_node: "node-6", target_input: "default" },
      { source_node: "node-6", source_output: "default", target_node: "node-7", target_input: "default" },
    ],
    created_at: "2026-06-12T00:00:00Z",
    updated_at: "2026-06-12T00:00:00Z",
  },
];

const MOCK_EXECUTION_STATE = {
  execution_id: "exec-mock-1",
  workflow_id: "wf-sample-1",
  status: "running",
  node_states: {},
  started_at: "2026-06-12T00:00:00Z",
  completed_at: null,
  error: null,
};

const MOCK_EXECUTION_EVENTS = [
  { event_type: "node_started", node_id: "node-1", data: { node_type: "decision_system.trigger_manual" } },
  { event_type: "node_completed", node_id: "node-1", data: { outputs: { triggered: true } } },
  { event_type: "node_started", node_id: "node-2", data: { node_type: "decision_system.input_text" } },
  { event_type: "node_completed", node_id: "node-2", data: { outputs: { text: "Where are we losing money?" } } },
  { event_type: "node_started", node_id: "node-3", data: { node_type: "decision_system.retrieve" } },
  { event_type: "node_completed", node_id: "node-3", data: { outputs: { chunks: [] } } },
  { event_type: "node_started", node_id: "node-4", data: { node_type: "decision_system.technical_analyst" } },
  { event_type: "node_completed", node_id: "node-4", data: { outputs: { analysis: { summary: "Mock analysis" } } } },
  { event_type: "node_started", node_id: "node-5", data: { node_type: "decision_system.risk_analyst" } },
  { event_type: "node_completed", node_id: "node-5", data: { outputs: { risks: [] } } },
  { event_type: "workflow_completed", node_id: null, data: { status: "completed" } },
];

export { MOCK_NODE_TYPES, MOCK_WORKFLOWS, MOCK_EXECUTION_STATE, MOCK_EXECUTION_EVENTS };
```

- [ ] **Step 2: Write the API client**

```js
// api.js — HTTP + WebSocket client with mock data fallback

import {
  MOCK_NODE_TYPES,
  MOCK_WORKFLOWS,
  MOCK_EXECUTION_STATE,
  MOCK_EXECUTION_EVENTS,
} from './mockData';

const API_BASE_KEY = 'wfBuilderApiBaseUrl';

function getBaseUrl() {
  return localStorage.getItem(API_BASE_KEY) || '';
}

function isMockMode() {
  return !getBaseUrl();
}

async function apiFetch(path, options = {}) {
  const base = getBaseUrl();
  if (!base) throw new Error('No API base URL configured');
  const url = `${base.replace(/\/+$/, '')}${path}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  return response.json();
}

// --- Node Types ---
async function fetchNodeTypes() {
  if (isMockMode()) return [...MOCK_NODE_TYPES];
  return apiFetch('/workflows/nodes');
}

// --- Workflows ---
let _mockWorkflows = [...MOCK_WORKFLOWS];

async function listWorkflows() {
  if (isMockMode()) return _mockWorkflows.map(({ id, name, description, updated_at }) => ({ id, name, description, updated_at }));
  return apiFetch('/workflows');
}

async function getWorkflow(id) {
  if (isMockMode()) {
    const wf = _mockWorkflows.find(w => w.id === id);
    if (!wf) throw new Error('Workflow not found');
    return JSON.parse(JSON.stringify(wf));
  }
  return apiFetch(`/workflows/${id}`);
}

async function saveWorkflow(workflow) {
  if (isMockMode()) {
    const idx = _mockWorkflows.findIndex(w => w.id === workflow.id);
    if (idx >= 0) _mockWorkflows[idx] = workflow;
    else _mockWorkflows.push(workflow);
    return workflow;
  }
  if (workflow.id && workflow.id.startsWith('wf-')) {
    return apiFetch(`/workflows/${workflow.id}`, {
      method: 'PUT',
      body: JSON.stringify(workflow),
    });
  }
  return apiFetch('/workflows', {
    method: 'POST',
    body: JSON.stringify(workflow),
  });
}

async function deleteWorkflow(id) {
  if (isMockMode()) {
    _mockWorkflows = _mockWorkflows.filter(w => w.id !== id);
    return { success: true };
  }
  return apiFetch(`/workflows/${id}`, { method: 'DELETE' });
}

// --- Execution ---
async function executeWorkflow(id) {
  if (isMockMode()) {
    const state = {
      ...MOCK_EXECUTION_STATE,
      execution_id: `exec-mock-${Date.now()}`,
      workflow_id: id,
      started_at: new Date().toISOString(),
      status: 'running',
    };
    return state;
  }
  return apiFetch(`/workflows/${id}/execute`, { method: 'POST' });
}

async function getExecution(id) {
  if (isMockMode()) {
    return { ...MOCK_EXECUTION_STATE, execution_id: id, status: 'completed' };
  }
  return apiFetch(`/executions/${id}`);
}

// --- WebSocket Stream ---
function streamExecutionEvents(executionId, onEvent) {
  if (isMockMode()) {
    // Simulate events with delays
    let idx = 0;
    const interval = setInterval(() => {
      if (idx >= MOCK_EXECUTION_EVENTS.length) {
        clearInterval(interval);
        return;
      }
      onEvent({ ...MOCK_EXECUTION_EVENTS[idx], execution_id: executionId, timestamp: new Date().toISOString() });
      idx++;
    }, 500);
    return () => clearInterval(interval);
  }

  const base = getBaseUrl().replace(/^http/, 'ws');
  const ws = new WebSocket(`${base}/executions/${executionId}/stream`);
  ws.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data));
    } catch { /* ignore parse errors */ }
  };
  ws.onerror = () => { /* WS error — caller handles via timeout */ };
  return () => ws.close();
}

export {
  getBaseUrl, isMockMode,
  fetchNodeTypes,
  listWorkflows, getWorkflow, saveWorkflow, deleteWorkflow,
  executeWorkflow, getExecution, streamExecutionEvents,
};
```

- [ ] **Step 3: Write mock data tests**

```js
// __tests__/mockData.test.js
import { describe, it, expect } from 'vitest';
import { MOCK_NODE_TYPES, MOCK_WORKFLOWS, MOCK_EXECUTION_STATE, MOCK_EXECUTION_EVENTS } from '../src/mockData';

describe('mockData', () => {
  it('has 16 node types matching Phase 1 built-in nodes', () => {
    expect(MOCK_NODE_TYPES.length).toBe(16);
    const types = MOCK_NODE_TYPES.map(n => n.type);
    expect(types).toContain('decision_system.trigger_manual');
    expect(types).toContain('decision_system.retrieve');
    expect(types).toContain('decision_system.technical_analyst');
    expect(types).toContain('decision_system.risk_analyst');
    expect(types).toContain('decision_system.extract_claims');
    expect(types).toContain('decision_system.verify_claims');
    expect(types).toContain('decision_system.write_report');
    expect(types).toContain('decision_system.extract_graph');
    expect(types).toContain('decision_system.profile_data');
    expect(types).toContain('decision_system.map_ontology');
    expect(types).toContain('decision_system.detect_patterns');
    expect(types).toContain('decision_system.war_room');
    expect(types).toContain('decision_system.input_text');
    expect(types).toContain('decision_system.filter');
    expect(types).toContain('decision_system.merge');
    expect(types).toContain('decision_system.code');
  });

  it('has config_schema for every node type', () => {
    for (const node of MOCK_NODE_TYPES) {
      expect(node.config_schema).toBeDefined();
      expect(node.config_schema.type).toBe('object');
    }
  });

  it('has input_schema and output_schema for every node type', () => {
    for (const node of MOCK_NODE_TYPES) {
      expect(node.input_schema).toBeDefined();
      expect(node.output_schema).toBeDefined();
    }
  });

  it('has at least one sample workflow', () => {
    expect(MOCK_WORKFLOWS.length).toBeGreaterThanOrEqual(1);
    const wf = MOCK_WORKFLOWS[0];
    expect(wf.nodes.length).toBeGreaterThan(0);
    expect(wf.connections.length).toBeGreaterThan(0);
  });

  it('has execution state and events', () => {
    expect(MOCK_EXECUTION_STATE.execution_id).toBeDefined();
    expect(MOCK_EXECUTION_EVENTS.length).toBeGreaterThan(0);
    expect(MOCK_EXECUTION_EVENTS[0].event_type).toBeDefined();
  });
});
```

- [ ] **Step 4: Write API client tests**

```js
// __tests__/api.test.js
import { describe, it, expect, beforeEach } from 'vitest';
import {
  fetchNodeTypes, listWorkflows, getWorkflow, saveWorkflow, deleteWorkflow,
  executeWorkflow, getExecution, isMockMode,
} from '../src/api';

describe('api client (mock mode)', () => {
  beforeEach(() => {
    localStorage.removeItem('wfBuilderApiBaseUrl');
  });

  it('is in mock mode when no base URL configured', () => {
    expect(isMockMode()).toBe(true);
  });

  it('fetches node types', async () => {
    const types = await fetchNodeTypes();
    expect(types.length).toBe(16);
  });

  it('lists workflows', async () => {
    const list = await listWorkflows();
    expect(Array.isArray(list)).toBe(true);
  });

  it('gets a specific workflow by id', async () => {
    const list = await listWorkflows();
    const wf = await getWorkflow(list[0].id);
    expect(wf.name).toBeDefined();
    expect(wf.nodes).toBeDefined();
    expect(wf.connections).toBeDefined();
  });

  it('saves a new workflow', async () => {
    const wf = {
      id: 'wf-test-1',
      name: 'Test Workflow',
      description: 'A test',
      nodes: [],
      connections: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    const saved = await saveWorkflow(wf);
    expect(saved.id).toBe('wf-test-1');

    const list = await listWorkflows();
    expect(list.find(w => w.id === 'wf-test-1')).toBeDefined();
  });

  it('deletes a workflow', async () => {
    const result = await deleteWorkflow('wf-test-1');
    expect(result.success).toBe(true);
  });

  it('executes a workflow', async () => {
    const state = await executeWorkflow('wf-sample-1');
    expect(state.execution_id).toBeDefined();
    expect(state.status).toBe('running');
  });

  it('gets execution state', async () => {
    const state = await getExecution('exec-mock-1');
    expect(state.status).toBe('completed');
  });
});
```

- [ ] **Step 5: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/api.test.js __tests__/mockData.test.js`

Expected: All tests pass.

- [ ] **Step 6: Commit**

```bash
git add web/workflow-builder/src/mockData.js web/workflow-builder/src/api.js web/workflow-builder/__tests__/mockData.test.js web/workflow-builder/__tests__/api.test.js
git commit -m "feat: add API client with mock data fallback for workflow builder"
```

---

### Task 3: Node Type Mapping and App CSS

**Files:**
- Create: `web/workflow-builder/src/nodeTypes.js`
- Create: `web/workflow-builder/src/App.css`

- [ ] **Step 1: Write node type mapping**

```js
// nodeTypes.js — Converts API node types to visual configs

const CATEGORY_CONFIG = {
  trigger: { color: '#3b82f6', bg: '#eff6ff', label: 'Triggers', icon: '⚡' },
  data: { color: '#f59e0b', bg: '#fffbeb', label: 'Data', icon: '📊' },
  ai: { color: '#8b5cf6', bg: '#f5f3ff', label: 'AI / Analysis', icon: '🤖' },
  output: { color: '#22c55e', bg: '#f0fdf4', label: 'Output', icon: '📄' },
  flow: { color: '#6b7280', bg: '#f9fafb', label: 'Flow Control', icon: '🔀' },
};

function getNodeCategoryConfig(type) {
  const entry = CATEGORY_CONFIG[type];
  return entry || CATEGORY_CONFIG.flow;
}

function getCategories() {
  return Object.entries(CATEGORY_CONFIG).map(([key, cfg]) => ({
    id: key,
    ...cfg,
  }));
}

export { CATEGORY_CONFIG, getNodeCategoryConfig, getCategories };
```

- [ ] **Step 2: Write App.css**

```css
/* App.css — Global app layout */

:root {
  --toolbar-height: 48px;
  --panel-width: 300px;
  --color-bg: #f8f9fa;
  --color-surface: #ffffff;
  --color-border: #e5e7eb;
  --color-text: #1f2937;
  --color-text-muted: #6b7280;
  --color-primary: #3b82f6;
  --color-success: #22c55e;
  --color-warning: #eab308;
  --color-danger: #ef4444;
  --radius: 6px;
  --shadow: 0 1px 3px rgba(0,0,0,0.1);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--color-bg);
  color: var(--color-text);
  overflow: hidden;
  height: 100vh;
}

#root {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.app-main {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* React Flow canvas area */
.canvas-wrapper {
  flex: 1;
  height: 100%;
}

/* Scrollbar styling */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }
```

- [ ] **Step 3: Verify**

No test needed for these static files.

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/nodeTypes.js web/workflow-builder/src/App.css
git commit -m "feat: add node type mapping and app layout CSS"
```

---

### Task 4: Toast Component

**Files:**
- Create: `web/workflow-builder/src/components/Toast.jsx`
- Create: `web/workflow-builder/src/styles/toast.css`

- [ ] **Step 1: Write tests**

```js
// __tests__/Toast.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ToastProvider, useToast } from '../src/components/Toast';
import React from 'react';

function TestConsumer() {
  const { showToast } = useToast();
  return <button onClick={() => showToast('Test message', 'info')}>Show Toast</button>;
}

describe('Toast', () => {
  it('renders children', () => {
    render(<ToastProvider><div>Content</div></ToastProvider>);
    expect(screen.getByText('Content')).toBeDefined();
  });

  it('provides showToast via context', () => {
    render(<ToastProvider><TestConsumer /></ToastProvider>);
    expect(screen.getByText('Show Toast')).toBeDefined();
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/Toast.test.jsx`
Expected: FAIL (component/missing)

- [ ] **Step 2: Write implementation**

```jsx
// components/Toast.jsx
import React, { createContext, useContext, useState, useCallback } from 'react';
import '../styles/toast.css';

const ToastContext = createContext(null);

function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const showToast = useCallback((message, type = 'info', duration = 4000) => {
    const id = Date.now() + Math.random();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, duration);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="toast-container">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast-${t.type}`} onClick={() => dismissToast(t.id)}>
            <span className="toast-message">{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export { ToastProvider, useToast };
```

```css
/* styles/toast.css */
.toast-container {
  position: fixed;
  bottom: 16px;
  right: 16px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 360px;
}

.toast {
  padding: 10px 16px;
  border-radius: var(--radius);
  background: var(--color-surface);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  cursor: pointer;
  animation: toast-in 0.2s ease-out;
  font-size: 14px;
  border-left: 4px solid var(--color-primary);
}

.toast-info { border-left-color: var(--color-primary); }
.toast-success { border-left-color: var(--color-success); }
.toast-warning { border-left-color: var(--color-warning); }
.toast-error { border-left-color: var(--color-danger); }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/Toast.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/Toast.jsx web/workflow-builder/src/styles/toast.css web/workflow-builder/__tests__/Toast.test.jsx
git commit -m "feat: add Toast notification component"
```

---

### Task 5: SchemaForm Component

**Files:**
- Create: `web/workflow-builder/src/components/SchemaForm.jsx`
- Create: `web/workflow-builder/__tests__/SchemaForm.test.jsx`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/SchemaForm.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import SchemaForm from '../src/components/SchemaForm';
import React from 'react';

describe('SchemaForm', () => {
  const basicSchema = {
    type: 'object',
    properties: {
      name: { type: 'string', title: 'Name', default: 'hello' },
      count: { type: 'integer', title: 'Count', default: 5 },
      enabled: { type: 'boolean', title: 'Enabled', default: true },
      severity: { type: 'string', title: 'Severity', default: 'low', enum: ['low', 'high'] },
      tags: { type: 'array', title: 'Tags', items: { type: 'string' } },
    },
  };

  it('renders all field types from schema', () => {
    const values = {};
    render(<SchemaForm schema={basicSchema} values={values} onChange={v => Object.assign(values, v)} />);
    expect(screen.getByDisplayValue('hello')).toBeDefined();
    expect(screen.getByDisplayValue('5')).toBeDefined();
    expect(screen.getByText('low')).toBeDefined();
  });

  it('calls onChange when text input changes', () => {
    const onChange = [];
    render(<SchemaForm schema={basicSchema} values={{}} onChange={v => onChange.push(v)} />);
    const input = screen.getByDisplayValue('hello');
    fireEvent.change(input, { target: { value: 'world' } });
    // onChange should have been called
    expect(onChange.length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty form for empty schema', () => {
    const { container } = render(<SchemaForm schema={{ type: 'object', properties: {} }} values={{}} onChange={() => {}} />);
    expect(container.textContent).toBe('');
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/SchemaForm.test.jsx`
Expected: FAIL (component not found)

- [ ] **Step 2: Write implementation**

```jsx
// components/SchemaForm.jsx
import React from 'react';

function SchemaForm({ schema, values, onChange }) {
  if (!schema || !schema.properties) return null;

  const props = schema.properties || {};

  function handleChange(key, newValue) {
    onChange({ [key]: newValue });
  }

  return (
    <div className="schema-form">
      {Object.entries(props).map(([key, prop]) => (
        <Field key={key} name={key} prop={prop} value={values?.[key] ?? prop.default ?? ''} onChange={handleChange} />
      ))}
    </div>
  );
}

function Field({ name, prop, value, onChange }) {
  const label = prop.title || name;
  const desc = prop.description;

  if (prop.enum) {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <select value={value} onChange={e => onChange(name, e.target.value)}>
          {prop.enum.map(opt => <option key={opt} value={opt}>{opt}</option>)}
        </select>
      </div>
    );
  }

  if (prop.type === 'boolean') {
    return (
      <div className="schema-field schema-field-checkbox">
        <label>
          <input type="checkbox" checked={!!value} onChange={e => onChange(name, e.target.checked)} />
          {label}
        </label>
        {desc && <span className="field-desc">{desc}</span>}
      </div>
    );
  }

  if (prop.type === 'integer' || prop.type === 'number') {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <input
          type="number"
          step={prop.type === 'number' ? 'any' : '1'}
          value={value}
          onChange={e => onChange(name, prop.type === 'integer' ? parseInt(e.target.value, 10) : parseFloat(e.target.value))}
        />
      </div>
    );
  }

  if (prop.type === 'array') {
    return (
      <div className="schema-field">
        <label>{label}</label>
        {desc && <span className="field-desc">{desc}</span>}
        <input
          type="text"
          value={Array.isArray(value) ? value.join(', ') : String(value)}
          onChange={e => onChange(name, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
          placeholder="Comma-separated values"
        />
      </div>
    );
  }

  // Default: string / text
  return (
    <div className="schema-field">
      <label>{label}</label>
      {desc && <span className="field-desc">{desc}</span>}
      {prop.format === 'textarea' ? (
        <textarea
          rows={4}
          value={value}
          onChange={e => onChange(name, e.target.value)}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={e => onChange(name, e.target.value)}
        />
      )}
    </div>
  );
}

export default SchemaForm;
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/SchemaForm.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/SchemaForm.jsx web/workflow-builder/__tests__/SchemaForm.test.jsx
git commit -m "feat: add SchemaForm component for JSON Schema rendering"
```

---

### Task 6: NodePalette Component

**Files:**
- Create: `web/workflow-builder/src/components/NodePalette.jsx`
- Create: `web/workflow-builder/src/styles/palette.css`
- Create: `web/workflow-builder/__tests__/NodePalette.test.jsx`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/NodePalette.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import NodePalette from '../src/components/NodePalette';
import { MOCK_NODE_TYPES } from '../src/mockData';
import React from 'react';

describe('NodePalette', () => {
  it('renders all 16 node types', () => {
    render(<NodePalette nodeTypes={MOCK_NODE_TYPES} onDragStart={() => {}} />);
    // Check for a few known node labels
    expect(screen.getByText('Manual Trigger')).toBeDefined();
    expect(screen.getByText('Retrieve Evidence')).toBeDefined();
    expect(screen.getByText('Write Report')).toBeDefined();
  });

  it('renders category headers (Triggers, Data, AI / Analysis, Output, Flow Control)', () => {
    render(<NodePalette nodeTypes={MOCK_NODE_TYPES} onDragStart={() => {}} />);
    expect(screen.getByText('Triggers')).toBeDefined();
    expect(screen.getByText('Data')).toBeDefined();
    expect(screen.getByText('AI / Analysis')).toBeDefined();
    expect(screen.getByText('Output')).toBeDefined();
    expect(screen.getByText('Flow Control')).toBeDefined();
  });

  it('fires onDragStart when dragging a node type', () => {
    const onDragStart = [];
    render(<NodePalette nodeTypes={MOCK_NODE_TYPES} onDragStart={e => onDragStart.push(e)} />);
    const item = screen.getByText('Manual Trigger');
    fireEvent.dragStart(item);
    expect(onDragStart.length).toBeGreaterThanOrEqual(1);
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/NodePalette.test.jsx`
Expected: FAIL (component not found)

- [ ] **Step 2: Write implementation**

```jsx
// components/NodePalette.jsx
import React, { useState } from 'react';
import { getNodeCategoryConfig, getCategories } from '../nodeTypes';
import '../styles/palette.css';

function NodePalette({ nodeTypes, onDragStart }) {
  const [collapsed, setCollapsed] = useState(false);

  // Group node types by category
  const grouped = {};
  for (const nt of nodeTypes) {
    const cat = nt.categories?.[0] || 'flow';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(nt);
  }

  if (collapsed) {
    return (
      <button className="palette-toggle" onClick={() => setCollapsed(false)} title="Show palette">
        📋
      </button>
    );
  }

  return (
    <div className="node-palette">
      <div className="palette-header">
        <span className="palette-title">Nodes</span>
        <button className="palette-close" onClick={() => setCollapsed(true)} title="Hide palette">✕</button>
      </div>
      <div className="palette-scroll">
        {getCategories().map(cat => {
          const items = grouped[cat.id] || [];
          if (!items.length) return null;
          return (
            <div key={cat.id} className="palette-category">
              <div className="palette-category-title" style={{ color: cat.color }}>
                {cat.icon} {cat.label}
              </div>
              {items.map(nt => (
                <div
                  key={nt.type}
                  className="palette-item"
                  style={{ borderLeftColor: cat.color }}
                  draggable
                  onDragStart={e => {
                    e.dataTransfer.setData('application/json', JSON.stringify(nt));
                    if (onDragStart) onDragStart(nt);
                  }}
                >
                  <span className="palette-item-label">{nt.label}</span>
                  <span className="palette-item-desc">{nt.description}</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default NodePalette;
```

```css
/* styles/palette.css */
.node-palette {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  width: 220px;
  max-height: calc(100% - 16px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.palette-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
  font-weight: 600;
}

.palette-close {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
}
.palette-close:hover { background: var(--color-bg); }

.palette-toggle {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  padding: 8px 10px;
  cursor: pointer;
  box-shadow: var(--shadow);
  font-size: 18px;
}

.palette-scroll {
  overflow-y: auto;
  flex: 1;
  padding: 8px;
}

.palette-category { margin-bottom: 12px; }

.palette-category-title {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}

.palette-item {
  padding: 6px 8px;
  margin-bottom: 3px;
  border-left: 3px solid;
  border-radius: 4px;
  cursor: grab;
  background: var(--color-surface);
  transition: background 0.15s;
  font-size: 12px;
}
.palette-item:hover { background: var(--color-bg); }
.palette-item:active { cursor: grabbing; }

.palette-item-label { font-weight: 500; display: block; }
.palette-item-desc { font-size: 11px; color: var(--color-text-muted); display: block; }
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/NodePalette.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/NodePalette.jsx web/workflow-builder/src/styles/palette.css web/workflow-builder/__tests__/NodePalette.test.jsx
git commit -m "feat: add NodePalette component with drag-to-create"
```

---

### Task 7: NodeComponent (Custom React Flow Node)

**Files:**
- Create: `web/workflow-builder/src/components/NodeComponent.jsx`
- Create: `web/workflow-builder/src/styles/canvas.css` (partial — canvas styles)

- [ ] **Step 1: Write implementation** (NodeComponent is visual — testing requires React Flow context, done in Task 8)

```jsx
// components/NodeComponent.jsx
import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { getNodeCategoryConfig } from '../nodeTypes';

const NodeComponent = memo(({ id, data, selected }) => {
  const catConfig = getNodeCategoryConfig(data.category);
  const status = data.status || 'idle';

  const statusColors = {
    idle: '',
    running: 'node-status-running',
    completed: 'node-status-completed',
    failed: 'node-status-failed',
    skipped: 'node-status-skipped',
  };

  const hasInputs = data.inputPorts && data.inputPorts.length > 0;
  const hasOutputs = data.outputPorts && data.outputPorts.length > 0;

  return (
    <div
      className={`custom-node ${selected ? 'selected' : ''} ${statusColors[status] || ''}`}
      style={{ borderColor: catConfig.color }}
    >
      {/* Input handles */}
      {hasInputs && data.inputPorts.map((port, i) => (
        <Handle
          key={`in-${port}`}
          type="target"
          position={Position.Left}
          id={port}
          style={{ top: `${((i + 1) / (data.inputPorts.length + 1)) * 100}%` }}
          title={port}
        />
      ))}
      {!hasInputs && (
        <Handle type="target" position={Position.Left} id="default" style={{ top: '50%' }} />
      )}

      {/* Node body */}
      <div className="node-header" style={{ background: catConfig.color }}>
        <span className="node-icon">{catConfig.icon}</span>
        <span className="node-type-label">{data.label || data.typeLabel}</span>
      </div>
      <div className="node-body">
        {status === 'running' && <span className="node-spinner">⟳</span>}
      </div>

      {/* Output handles */}
      {hasOutputs && data.outputPorts.map((port, i) => (
        <Handle
          key={`out-${port}`}
          type="source"
          position={Position.Right}
          id={port}
          style={{ top: `${((i + 1) / (data.outputPorts.length + 1)) * 100}%` }}
          title={port}
        />
      ))}
      {!hasOutputs && (
        <Handle type="source" position={Position.Right} id="default" style={{ top: '50%' }} />
      )}
    </div>
  );
});

NodeComponent.displayName = 'NodeComponent';

export default NodeComponent;
```

```css
/* styles/canvas.css (append to existing or create initial) */
.custom-node {
  background: var(--color-surface);
  border: 2px solid;
  border-radius: 8px;
  min-width: 150px;
  box-shadow: var(--shadow);
  font-size: 12px;
  transition: box-shadow 0.15s;
}
.custom-node.selected {
  box-shadow: 0 0 0 2px var(--color-primary), 0 4px 12px rgba(0,0,0,0.15);
}

.node-header {
  padding: 6px 12px;
  color: #fff;
  border-radius: 6px 6px 0 0;
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 12px;
}
.node-icon { font-size: 14px; }

.node-body {
  padding: 8px 12px;
  min-height: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-spinner {
  animation: spin 1s linear infinite;
  font-size: 16px;
}
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

/* Status overlays */
.node-status-completed { border-color: var(--color-success) !important; }
.node-status-running { border-color: var(--color-warning) !important; animation: pulse-border 1.5s ease-in-out infinite; }
.node-status-failed { border-color: var(--color-danger) !important; }
.node-status-skipped { border-color: #9ca3af !important; opacity: 0.6; }

@keyframes pulse-border {
  0%, 100% { box-shadow: 0 0 0 0 rgba(234, 179, 8, 0.4); }
  50% { box-shadow: 0 0 0 4px rgba(234, 179, 8, 0); }
}
```

- [ ] **Step 2: Commit**

```bash
git add web/workflow-builder/src/components/NodeComponent.jsx web/workflow-builder/src/styles/canvas.css
git commit -m "feat: add custom React Flow NodeComponent with status overlays"
```

---

### Task 8: WorkflowCanvas Component

**Files:**
- Create: `web/workflow-builder/src/components/WorkflowCanvas.jsx`
- Create: `web/workflow-builder/__tests__/WorkflowCanvas.test.jsx`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/WorkflowCanvas.test.jsx
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import WorkflowCanvas from '../src/components/WorkflowCanvas';
import React from 'react';

describe('WorkflowCanvas', () => {
  it('renders the canvas area', () => {
    const { container } = render(
      <WorkflowCanvas
        nodes={[]}
        edges={[]}
        onNodesChange={() => {}}
        onEdgesChange={() => {}}
        onConnect={() => {}}
        onNodeClick={() => {}}
        onPaneClick={() => {}}
        onDrop={() => {}}
        nodeTypes={{}}
      />
    );
    expect(container.querySelector('.react-flow')).toBeDefined();
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/WorkflowCanvas.test.jsx`
Expected: FAIL (component not found)

- [ ] **Step 2: Write implementation**

```jsx
// components/WorkflowCanvas.jsx
import React from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import '../styles/canvas.css';

function WorkflowCanvas({ nodes, edges, onNodesChange, onEdgesChange, onConnect, onNodeClick, onPaneClick, onDrop, onDragOver, nodeTypes }) {
  return (
    <div className="canvas-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={nodeTypes}
        fitView
        deleteKeyCode={['Backspace', 'Delete']}
        snapToGrid
        snapGrid={[20, 20]}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
        <Controls />
        <MiniMap
          nodeStrokeColor="#6b7280"
          nodeColor="#f3f4f6"
          maskColor="rgba(0,0,0,0.1)"
          style={{ border: '1px solid #e5e7eb', borderRadius: '6px' }}
        />
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/WorkflowCanvas.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/WorkflowCanvas.jsx web/workflow-builder/__tests__/WorkflowCanvas.test.jsx
git commit -m "feat: add WorkflowCanvas component with React Flow wrapper"
```

---

### Task 9: WorkflowToolbar Component

**Files:**
- Create: `web/workflow-builder/src/components/WorkflowToolbar.jsx`
- Create: `web/workflow-builder/src/components/LoadDropdown.jsx`
- Create: `web/workflow-builder/src/styles/toolbar.css`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/WorkflowToolbar.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import WorkflowToolbar from '../src/components/WorkflowToolbar';
import React from 'react';

describe('WorkflowToolbar', () => {
  it('renders all toolbar buttons', () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="My Workflow"
        isExecuting={false}
      />
    );
    expect(screen.getByText('+ New')).toBeDefined();
    expect(screen.getByText('Save')).toBeDefined();
    expect(screen.getByText('Load')).toBeDefined();
    expect(screen.getByText('Execute')).toBeDefined();
    expect(screen.getByText('Export')).toBeDefined();
  });

  it('shows current workflow name', () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="Test Workflow"
        isExecuting={false}
      />
    );
    expect(screen.getByText('Test Workflow')).toBeDefined();
  });

  it('disables execute button when isExecuting is true', () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="Test"
        isExecuting={true}
      />
    );
    const executeBtn = screen.getByText('Running...');
    expect(executeBtn.disabled).toBe(true);
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/WorkflowToolbar.test.jsx`
Expected: FAIL

- [ ] **Step 2: Write implementation**

```jsx
// components/LoadDropdown.jsx
import React, { useState } from 'react';

function LoadDropdown({ workflows, onSelect }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="load-dropdown" onMouseLeave={() => setOpen(false)}>
      <button className="toolbar-btn" onClick={() => setOpen(!open)}>
        Load ▾
      </button>
      {open && (
        <div className="dropdown-menu">
          {workflows.length === 0 && <div className="dropdown-empty">No saved workflows</div>}
          {workflows.map(wf => (
            <button
              key={wf.id}
              className="dropdown-item"
              onClick={() => { onSelect(wf.id); setOpen(false); }}
            >
              {wf.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default LoadDropdown;
```

```jsx
// components/WorkflowToolbar.jsx
import React from 'react';
import LoadDropdown from './LoadDropdown';
import '../styles/toolbar.css';

function WorkflowToolbar({ onNew, onSave, onLoad, onExecute, onExport, workflows, currentWorkflowName, isExecuting, hasUnsavedChanges }) {
  return (
    <div className="workflow-toolbar">
      <div className="toolbar-left">
        <button className="toolbar-btn" onClick={onNew} title="Create new workflow">+ New</button>
        <button className="toolbar-btn" onClick={onSave} title="Save workflow">
          {hasUnsavedChanges ? '💾 Save *' : '💾 Save'}
        </button>
        <LoadDropdown workflows={workflows} onSelect={onLoad} />
        <button className="toolbar-btn toolbar-btn-primary" onClick={onExecute} disabled={isExecuting}>
          {isExecuting ? '⏳ Running...' : '▶ Execute'}
        </button>
        <button className="toolbar-btn" onClick={onExport} title="Export as JSON">📋 Export</button>
      </div>
      <div className="toolbar-center">
        <span className="toolbar-workflow-name">{currentWorkflowName || 'Untitled Workflow'}</span>
      </div>
      <div className="toolbar-right">
        <span className="toolbar-mode">⚡ Workflow Builder</span>
      </div>
    </div>
  );
}

export default WorkflowToolbar;
```

```css
/* styles/toolbar.css */
.workflow-toolbar {
  height: var(--toolbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 4px;
  flex-shrink: 0;
}

.toolbar-left { display: flex; gap: 4px; align-items: center; }
.toolbar-center { flex: 1; text-align: center; }
.toolbar-right { display: flex; align-items: center; }

.toolbar-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
  white-space: nowrap;
  transition: background 0.15s;
}
.toolbar-btn:hover { background: var(--color-bg); }
.toolbar-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.toolbar-btn-primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}
.toolbar-btn-primary:hover { filter: brightness(1.1); }

.toolbar-workflow-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
}

.toolbar-mode {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg);
  padding: 3px 8px;
  border-radius: 4px;
}

.load-dropdown { position: relative; }
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 100;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  min-width: 200px;
  max-height: 300px;
  overflow-y: auto;
  margin-top: 2px;
}
.dropdown-item {
  display: block;
  width: 100%;
  padding: 8px 12px;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text);
}
.dropdown-item:hover { background: var(--color-bg); }
.dropdown-empty { padding: 12px; color: var(--color-text-muted); font-size: 12px; text-align: center; }
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/WorkflowToolbar.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/WorkflowToolbar.jsx web/workflow-builder/src/components/LoadDropdown.jsx web/workflow-builder/src/styles/toolbar.css web/workflow-builder/__tests__/WorkflowToolbar.test.jsx
git commit -m "feat: add WorkflowToolbar and LoadDropdown components"
```

---

### Task 10: ConfigPanel Component

**Files:**
- Create: `web/workflow-builder/src/components/ConfigPanel.jsx`
- Create: `web/workflow-builder/src/styles/config-panel.css`
- Create: `web/workflow-builder/__tests__/ConfigPanel.test.jsx`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/ConfigPanel.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ConfigPanel from '../src/components/ConfigPanel';
import { MOCK_NODE_TYPES } from '../src/mockData';
import React from 'react';

describe('ConfigPanel', () => {
  const retrieveNodeType = MOCK_NODE_TYPES.find(n => n.type === 'decision_system.retrieve');

  it('renders nothing when no node selected', () => {
    const { container } = render(
      <ConfigPanel selectedNode={null} nodeType={null} onUpdateConfig={() => {}} onDelete={() => {}} />
    );
    expect(container.textContent).toBe('');
  });

  it('shows node label and type when a node is selected', () => {
    const node = { id: 'n1', type: 'decision_system.retrieve', data: { label: 'My Retrieve', config: {} } };
    render(
      <ConfigPanel selectedNode={node} nodeType={retrieveNodeType} onUpdateConfig={() => {}} onDelete={() => {}} />
    );
    expect(screen.getByDisplayValue('My Retrieve')).toBeDefined();
    expect(screen.getByText('decision_system.retrieve')).toBeDefined();
  });

  it('renders config fields from the node type schema', () => {
    const node = { id: 'n1', type: 'decision_system.retrieve', data: { label: 'My Retrieve', config: {} } };
    render(
      <ConfigPanel selectedNode={node} nodeType={retrieveNodeType} onUpdateConfig={() => {}} onDelete={() => {}} />
    );
    expect(screen.getByText('Collection')).toBeDefined();
    expect(screen.getByText('Top K')).toBeDefined();
  });

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = [];
    const node = { id: 'n1', type: 'decision_system.retrieve', data: { label: 'My Retrieve', config: {} } };
    render(
      <ConfigPanel selectedNode={node} nodeType={retrieveNodeType} onUpdateConfig={() => {}} onDelete={() => onDelete.push('deleted')} />
    );
    const deleteBtn = screen.getByText('Delete Node');
    fireEvent.click(deleteBtn);
    expect(onDelete.length).toBe(1);
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/ConfigPanel.test.jsx`
Expected: FAIL

- [ ] **Step 2: Write implementation**

```jsx
// components/ConfigPanel.jsx
import React from 'react';
import SchemaForm from './SchemaForm';
import { getNodeCategoryConfig } from '../nodeTypes';
import '../styles/config-panel.css';

function ConfigPanel({ selectedNode, nodeType, onUpdateConfig, onUpdateLabel, onDelete, errorPolicies }) {
  if (!selectedNode || !nodeType) return null;

  const catConfig = getNodeCategoryConfig(nodeType.categories?.[0]);

  function handleConfigChange(changes) {
    onUpdateConfig(selectedNode.id, { ...selectedNode.data.config, ...changes });
  }

  function handleLabelChange(e) {
    onUpdateLabel(selectedNode.id, e.target.value);
  }

  function handleErrorPolicyChange(e) {
    onUpdateConfig(selectedNode.id, { ...selectedNode.data.config, error_policy: e.target.value });
  }

  return (
    <div className="config-panel">
      <div className="config-panel-header" style={{ borderLeftColor: catConfig.color }}>
        <div className="config-node-type">
          <span className="config-cat-icon">{catConfig.icon}</span>
          <span>{nodeType.type}</span>
        </div>
      </div>

      <div className="config-panel-body">
        <div className="config-section">
          <label className="config-label">Label</label>
          <input
            className="config-input"
            type="text"
            value={selectedNode.data.label || ''}
            onChange={handleLabelChange}
          />
        </div>

        <div className="config-section">
          <label className="config-label">Description</label>
          <p className="config-desc">{nodeType.description}</p>
        </div>

        <div className="config-section">
          <div className="config-section-title">Configuration</div>
          <SchemaForm
            schema={nodeType.config_schema}
            values={selectedNode.data.config || {}}
            onChange={handleConfigChange}
          />
        </div>

        {(errorPolicies && errorPolicies.length > 0) && (
          <div className="config-section">
            <label className="config-label">Error Policy</label>
            <select className="config-input" value={selectedNode.data.config?.error_policy || 'fail_workflow'} onChange={handleErrorPolicyChange}>
              {errorPolicies.map(ep => <option key={ep} value={ep}>{ep}</option>)}
            </select>
          </div>
        )}

        <div className="config-section">
          <div className="config-section-title">Inputs</div>
          <div className="config-schema-view">
            {Object.keys(nodeType.input_schema?.properties || {}).length === 0
              ? <span className="config-muted">No inputs expected</span>
              : Object.entries(nodeType.input_schema.properties).map(([key, prop]) => (
                  <div key={key} className="config-port-item config-input-port">
                    <span className="config-port-name">{key}</span>
                    <span className="config-port-type">{prop.type || 'any'}</span>
                  </div>
                ))
            }
          </div>
        </div>

        <div className="config-section">
          <div className="config-section-title">Outputs</div>
          <div className="config-schema-view">
            {Object.keys(nodeType.output_schema?.properties || {}).length === 0
              ? <span className="config-muted">No outputs</span>
              : Object.entries(nodeType.output_schema.properties).map(([key, prop]) => (
                  <div key={key} className="config-port-item config-output-port">
                    <span className="config-port-name">{key}</span>
                    <span className="config-port-type">{prop.type || 'any'}</span>
                  </div>
                ))
            }
          </div>
        </div>

        <div className="config-section">
          <button className="config-delete-btn" onClick={() => onDelete(selectedNode.id)}>
            🗑 Delete Node
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfigPanel;
```

```css
/* styles/config-panel.css */
.config-panel {
  width: var(--panel-width);
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.config-panel-header {
  padding: 12px;
  border-left: 4px solid;
  border-bottom: 1px solid var(--color-border);
}

.config-node-type {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: monospace;
}

.config-cat-icon { font-size: 14px; }

.config-panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.config-section { margin-bottom: 16px; }
.config-section-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin-bottom: 8px;
  letter-spacing: 0.5px;
}

.config-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  color: var(--color-text);
}

.config-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 13px;
  background: var(--color-surface);
  color: var(--color-text);
}
.config-input:focus { outline: none; border-color: var(--color-primary); }

.config-desc {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.config-muted {
  font-size: 12px;
  color: var(--color-text-muted);
  font-style: italic;
}

.config-schema-view { display: flex; flex-direction: column; gap: 4px; }

.config-port-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 8px;
  background: var(--color-bg);
  border-radius: 4px;
  font-size: 12px;
}
.config-port-name { font-weight: 500; }
.config-port-type {
  font-size: 10px;
  color: var(--color-text-muted);
  font-family: monospace;
  background: var(--color-surface);
  padding: 1px 5px;
  border-radius: 3px;
}
.config-input-port { border-left: 3px solid var(--color-primary); }
.config-output-port { border-left: 3px solid var(--color-success); }

.config-delete-btn {
  width: 100%;
  padding: 8px;
  background: #fef2f2;
  color: var(--color-danger);
  border: 1px solid #fecaca;
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 13px;
  transition: background 0.15s;
}
.config-delete-btn:hover { background: #fee2e2; }

/* Inline schema form styles */
.schema-form { display: flex; flex-direction: column; gap: 12px; }
.schema-field { display: flex; flex-direction: column; gap: 2px; }
.schema-field label { font-size: 12px; font-weight: 500; color: var(--color-text); }
.schema-field select,
.schema-field input[type="text"],
.schema-field input[type="number"],
.schema-field textarea {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 13px;
  background: var(--color-surface);
  color: var(--color-text);
}
.schema-field select:focus,
.schema-field input:focus,
.schema-field textarea:focus { outline: none; border-color: var(--color-primary); }
.schema-field textarea { resize: vertical; font-family: monospace; font-size: 12px; }
.schema-field-checkbox { flex-direction: row; gap: 8px; align-items: center; }
.schema-field-checkbox input { width: auto; }
.field-desc { font-size: 11px; color: var(--color-text-muted); }
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/ConfigPanel.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/ConfigPanel.jsx web/workflow-builder/src/styles/config-panel.css web/workflow-builder/__tests__/ConfigPanel.test.jsx
git commit -m "feat: add ConfigPanel component with auto-rendered schema form"
```

---

### Task 11: ExecutionPanel Component

**Files:**
- Create: `web/workflow-builder/src/components/ExecutionPanel.jsx`
- Create: `web/workflow-builder/src/styles/execution-panel.css`
- Create: `web/workflow-builder/__tests__/ExecutionPanel.test.jsx`

- [ ] **Step 1: Write tests**

```jsx
// __tests__/ExecutionPanel.test.jsx
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ExecutionPanel from '../src/components/ExecutionPanel';
import React from 'react';

describe('ExecutionPanel', () => {
  const nodeStatuses = [
    { nodeId: 'n1', label: 'Manual Trigger', status: 'completed', duration: 0.02 },
    { nodeId: 'n2', label: 'Retrieve Evidence', status: 'running', duration: 1.5 },
    { nodeId: 'n3', label: 'Tech Analyst', status: 'pending' },
    { nodeId: 'n4', label: 'Write Report', status: 'failed', duration: 0.5, error: 'Timeout error' },
  ];

  it('renders execution status header', () => {
    render(<ExecutionPanel nodeStatuses={nodeStatuses} workflowStatus="running" elapsed={2.3} onClose={() => {}} />);
    expect(screen.getByText(/Running/)).toBeDefined();
  });

  it('renders all node statuses', () => {
    render(<ExecutionPanel nodeStatuses={nodeStatuses} workflowStatus="running" elapsed={2.3} onClose={() => {}} />);
    expect(screen.getByText('Manual Trigger')).toBeDefined();
    expect(screen.getByText('Retrieve Evidence')).toBeDefined();
    expect(screen.getByText('Tech Analyst')).toBeDefined();
  });

  it('shows error text for failed nodes', () => {
    render(<ExecutionPanel nodeStatuses={nodeStatuses} workflowStatus="failed" elapsed={3.0} onClose={() => {}} />);
    expect(screen.getByText(/Timeout error/)).toBeDefined();
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/ExecutionPanel.test.jsx`
Expected: FAIL

- [ ] **Step 2: Write implementation**

```jsx
// components/ExecutionPanel.jsx
import React from 'react';
import '../styles/execution-panel.css';

function ExecutionPanel({ nodeStatuses, workflowStatus, elapsed, onClose }) {
  const statusIcons = {
    pending: '○',
    running: '⟳',
    completed: '✅',
    failed: '❌',
    skipped: '⏭',
  };

  const statusColors = {
    pending: '#9ca3af',
    running: '#eab308',
    completed: '#22c55e',
    failed: '#ef4444',
    skipped: '#6b7280',
  };

  const completedCount = nodeStatuses.filter(n => n.status === 'completed' || n.status === 'skipped').length;

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Execution</div>
        <button className="execution-close" onClick={onClose}>✕</button>
      </div>

      <div className="execution-summary">
        <span className="execution-status-badge" style={{ background: statusColors[workflowStatus] || '#6b7280' }}>
          {workflowStatus}
        </span>
        <span className="execution-progress">{completedCount}/{nodeStatuses.length} nodes</span>
        {elapsed > 0 && <span className="execution-elapsed">{elapsed.toFixed(1)}s</span>}
      </div>

      <div className="execution-node-list">
        {nodeStatuses.map(ns => (
          <div key={ns.nodeId} className="execution-node-item" style={{ borderLeftColor: statusColors[ns.status] || '#d1d5db' }}>
            <div className="execution-node-header">
              <span className="execution-node-icon" style={{ color: statusColors[ns.status] }}>
                {statusIcons[ns.status] || '○'}
              </span>
              <span className="execution-node-label">{ns.label}</span>
              {ns.duration !== undefined && <span className="execution-node-duration">{ns.duration.toFixed(2)}s</span>}
            </div>
            {ns.error && <div className="execution-node-error">{ns.error}</div>}
            {ns.status === 'running' && (
              <div className="execution-progress-bar">
                <div className="execution-progress-fill" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExecutionPanel;
```

```css
/* styles/execution-panel.css */
.execution-panel {
  width: var(--panel-width);
  background: var(--color-surface);
  border-left: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.execution-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid var(--color-border);
}

.execution-panel-title {
  font-weight: 600;
  font-size: 13px;
}

.execution-close {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
}
.execution-close:hover { background: var(--color-bg); }

.execution-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  font-size: 12px;
}

.execution-status-badge {
  padding: 2px 8px;
  border-radius: 10px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.execution-progress { color: var(--color-text-muted); }
.execution-elapsed { color: var(--color-text-muted); margin-left: auto; }

.execution-node-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.execution-node-item {
  padding: 8px 10px;
  margin-bottom: 4px;
  border-left: 3px solid;
  border-radius: 4px;
  background: var(--color-bg);
}

.execution-node-header {
  display: flex;
  align-items: center;
  gap: 6px;
}

.execution-node-icon { font-size: 14px; width: 18px; text-align: center; }

.execution-node-label {
  font-size: 12px;
  font-weight: 500;
  flex: 1;
}

.execution-node-duration {
  font-size: 10px;
  color: var(--color-text-muted);
  font-family: monospace;
}

.execution-node-error {
  margin-top: 4px;
  font-size: 11px;
  color: var(--color-danger);
  word-break: break-all;
}

.execution-progress-bar {
  margin-top: 6px;
  height: 3px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.execution-progress-fill {
  height: 100%;
  width: 60%;
  background: var(--color-warning);
  border-radius: 2px;
  animation: progress-indeterminate 1.5s ease-in-out infinite;
}

@keyframes progress-indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(200%); }
}
```

- [ ] **Step 3: Run tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/ExecutionPanel.test.jsx`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web/workflow-builder/src/components/ExecutionPanel.jsx web/workflow-builder/src/styles/execution-panel.css web/workflow-builder/__tests__/ExecutionPanel.test.jsx
git commit -m "feat: add ExecutionPanel component with real-time status display"
```

---

### Task 12: App Assembly + Full Integration Tests

**Files:**
- Create: `web/workflow-builder/src/App.jsx`
- Create: `web/workflow-builder/__tests__/integration.test.jsx`

- [ ] **Step 1: Write integration tests**

```jsx
// __tests__/integration.test.jsx
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import App from '../src/App';
import React from 'react';

describe('App integration', () => {
  beforeEach(() => {
    localStorage.removeItem('wfBuilderApiBaseUrl');
  });

  it('renders the toolbar', () => {
    render(<App />);
    expect(screen.getByText('+ New')).toBeDefined();
    expect(screen.getByText('Save')).toBeDefined();
  });

  it('renders the node palette', () => {
    render(<App />);
    expect(screen.getByText('Manual Trigger')).toBeDefined();
    expect(screen.getByText('Triggers')).toBeDefined();
  });

  it('shows Untitled Workflow initially', () => {
    render(<App />);
    expect(screen.getByText('Untitled Workflow')).toBeDefined();
  });
});
```

Run: `cd web/workflow-builder && npx vitest run __tests__/integration.test.jsx`
Expected: FAIL (App not built yet)

- [ ] **Step 2: Write App.jsx**

```jsx
// App.jsx — Root component
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ReactFlowProvider, useReactFlow } from 'reactflow';
import WorkflowCanvas from './components/WorkflowCanvas';
import WorkflowToolbar from './components/WorkflowToolbar';
import NodePalette from './components/NodePalette';
import ConfigPanel from './components/ConfigPanel';
import ExecutionPanel from './components/ExecutionPanel';
import NodeComponent from './components/NodeComponent';
import { ToastProvider, useToast } from './components/Toast';
import {
  fetchNodeTypes,
  listWorkflows,
  getWorkflow,
  saveWorkflow,
  executeWorkflow,
  getExecution,
  streamExecutionEvents,
} from './api';
import { getNodeCategoryConfig } from './nodeTypes';
import './App.css';

const ERROR_POLICIES = ['fail_workflow', 'fail_node', 'retry', 'skip'];

const initialNodes = [];
const initialEdges = [];

function idGen() {
  return `node-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function CanvasInner() {
  const reactFlow = useReactFlow();
  const {
    nodes, setNodes, edges, setEdges,
    onNodesChange, onEdgesChange,
  } = useWorkflowState();

  const [nodeTypes, setNodeTypes] = useState([]);
  const [workflows, setWorkflows] = useState([]);
  const [currentWorkflowId, setCurrentWorkflowId] = useState(null);
  const [currentWorkflowName, setCurrentWorkflowName] = useState('Untitled Workflow');
  const [selectedNode, setSelectedNode] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [executionPanel, setExecutionPanel] = useState(null);
  const [nodeStatuses, setNodeStatuses] = useState([]);
  const [elapsed, setElapsed] = useState(0);
  const [workflowStatus, setWorkflowStatus] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const { showToast } = useToast();
  const timerRef = useRef(null);

  // Load node types on mount
  useEffect(() => {
    fetchNodeTypes().then(setNodeTypes).catch(() => {});
    listWorkflows().then(setWorkflows).catch(() => {});
  }, []);

  // Build custom node type map for React Flow
  const nodeTypeMap = {
    custom: NodeComponent,
  };

  // Find node type info for a given type string
  function getNodeTypeInfo(type) {
    return nodeTypes.find(nt => nt.type === type);
  }

  // Convert workflow nodes to React Flow nodes
  function workflowToReactNodes(wf) {
    return wf.nodes.map((n, i) => {
      const nt = getNodeTypeInfo(n.type);
      const cat = nt?.categories?.[0] || 'flow';
      const inputPorts = nt ? Object.keys(nt.input_schema?.properties || {}) : [];
      const outputPorts = nt ? Object.keys(nt.output_schema?.properties || {}) : [];
      return {
        id: n.id,
        type: 'custom',
        position: { x: n.position_x || 200, y: n.position_y || 100 + i * 120 },
        data: {
          label: n.label,
          typeLabel: nt?.label || n.type,
          category: cat,
          config: n.config || {},
          inputPorts,
          outputPorts,
          status: 'idle',
        },
      };
    });
  }

  // Convert React Flow edges to Connection objects
  function reactEdgesToConnections(es) {
    return es.map(e => ({
      source_node: e.source,
      source_output: e.sourceHandle || 'default',
      target_node: e.target,
      target_input: e.targetHandle || 'default',
    }));
  }

  // New workflow
  function handleNew() {
    setNodes([]);
    setEdges([]);
    setCurrentWorkflowId(null);
    setCurrentWorkflowName('Untitled Workflow');
    setSelectedNode(null);
    setExecutionPanel(null);
    setHasUnsavedChanges(false);
  }

  // Save
  async function handleSave() {
    try {
      const wf = {
        id: currentWorkflowId || `wf-${Date.now()}`,
        name: currentWorkflowName,
        description: '',
        nodes: nodes.map(n => ({
          id: n.id,
          type: n.data.typeLabel ? nodeTypes.find(nt => nt.label === n.data.typeLabel)?.type || 'decision_system.trigger_manual' : 'decision_system.trigger_manual',
          label: n.data.label,
          config: n.data.config || {},
          error_policy: n.data.config?.error_policy || 'fail_workflow',
          position_x: n.position?.x || 0,
          position_y: n.position?.y || 0,
          _reactFlowType: n.type,
          _reactFlowPosition: n.position,
        })),
        connections: reactEdgesToConnections(edges),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      const saved = await saveWorkflow(wf);
      setCurrentWorkflowId(saved.id);
      setHasUnsavedChanges(false);
      showToast('Workflow saved', 'success');
      listWorkflows().then(setWorkflows);
    } catch (err) {
      showToast(`Save failed: ${err.message}`, 'error');
    }
  }

  // Load workflow
  async function handleLoad(id) {
    try {
      const wf = await getWorkflow(id);
      setCurrentWorkflowId(wf.id);
      setCurrentWorkflowName(wf.name);
      setSelectedNode(null);
      setExecutionPanel(null);

      const rn = workflowToReactNodes(wf);
      const re = wf.connections.map(c => ({
        id: `${c.source_node}-${c.target_node}`,
        source: c.source_node,
        target: c.target_node,
        sourceHandle: c.source_output,
        targetHandle: c.target_input,
      }));

      // Use setNodes/setEdges from ReactFlow
      setNodes(rn);
      setEdges(re);
      setHasUnsavedChanges(false);
      showToast(`Loaded: ${wf.name}`, 'info');
    } catch (err) {
      showToast(`Load failed: ${err.message}`, 'error');
    }
  }

  // Execute
  async function handleExecute() {
    if (nodes.length === 0) {
      showToast('Add at least one node to the workflow', 'warning');
      return;
    }
    if (!currentWorkflowId) {
      // Auto-save first
      await handleSave();
    }

    setIsExecuting(true);
    setExecutionPanel('active');
    setWorkflowStatus('running');
    setElapsed(0);

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed((Date.now() - startTime) / 1000);
    }, 100);

    // Set all nodes to pending initially
    const initialStatuses = nodes.map(n => ({
      nodeId: n.id,
      label: n.data.label,
      status: 'pending',
    }));
    setNodeStatuses(initialStatuses);

    try {
      const execState = await executeWorkflow(currentWorkflowId);

      // Subscribe to events
      const unsub = streamExecutionEvents(execState.execution_id, (event) => {
        setNodeStatuses(prev => {
          const updated = [...prev];
          const idx = updated.findIndex(n => n.nodeId === event.node_id);
          if (idx >= 0) {
            const newStatus = {
              node_started: 'running',
              node_completed: 'completed',
              node_failed: 'failed',
            }[event.event_type] || updated[idx].status;

            updated[idx] = {
              ...updated[idx],
              status: newStatus,
              duration: event.event_type === 'node_completed' ? (Date.now() - startTime) / 1000 : updated[idx].duration,
              error: event.data?.error,
            };
          }

          // Update node status on canvas
          setNodes(nds => nds.map(n => {
            if (n.id === event.node_id) {
              const canvasStatus = {
                node_started: 'running',
                node_completed: 'completed',
                node_failed: 'failed',
              }[event.event_type] || n.data.status;
              return { ...n, data: { ...n.data, status: canvasStatus } };
            }
            return n;
          }));

          return updated;
        });

        if (event.event_type === 'workflow_completed') {
          setWorkflowStatus('completed');
          clearInterval(timerRef.current);
          setIsExecuting(false);
          showToast('Workflow completed', 'success');
        } else if (event.event_type === 'workflow_failed') {
          setWorkflowStatus('failed');
          clearInterval(timerRef.current);
          setIsExecuting(false);
          showToast(`Workflow failed: ${event.data?.error || 'Unknown error'}`, 'error');
        }
      });

      // Fallback: stop checking after 60s
      setTimeout(() => {
        if (isExecuting) {
          clearInterval(timerRef.current);
          setIsExecuting(false);
          setWorkflowStatus('completed');
          unsub();
        }
      }, 60000);

    } catch (err) {
      clearInterval(timerRef.current);
      setIsExecuting(false);
      setWorkflowStatus('failed');
      showToast(`Execution failed: ${err.message}`, 'error');
    }
  }

  // Export
  function handleExport() {
    const data = {
      name: currentWorkflowName,
      nodes: nodes.map(n => ({
        id: n.id,
        type: n.data.typeLabel ? nodeTypes.find(nt => nt.label === n.data.typeLabel)?.type || 'unknown' : 'unknown',
        label: n.data.label,
        config: n.data.config,
      })),
      connections: reactEdgesToConnections(edges),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentWorkflowName.replace(/\s+/g, '-').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Drop handler
  const onDrop = useCallback((event) => {
    event.preventDefault();
    const data = event.dataTransfer.getData('application/json');
    if (!data) return;

    try {
      const nt = JSON.parse(data);
      const cat = nt.categories?.[0] || 'flow';
      const position = reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
      const newNode = {
        id: idGen(),
        type: 'custom',
        position,
        data: {
          label: nt.label,
          typeLabel: nt.label,
          category: cat,
          config: {},
          inputPorts: Object.keys(nt.input_schema?.properties || {}),
          outputPorts: Object.keys(nt.output_schema?.properties || {}),
          status: 'idle',
        },
      };
      setNodes(nds => [...nds, newNode]);
      setHasUnsavedChanges(true);
    } catch { /* ignore invalid drops */ }
  }, [reactFlow, setNodes]);

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  // Node selection
  function handleNodeClick(_, node) {
    setSelectedNode(node);
  }

  function handlePaneClick() {
    setSelectedNode(null);
  }

  // Config updates
  function handleUpdateConfig(nodeId, config) {
    setNodes(nds => nds.map(n => {
      if (n.id === nodeId) return { ...n, data: { ...n.data, config } };
      return n;
    }));
    setHasUnsavedChanges(true);
  }

  function handleUpdateLabel(nodeId, label) {
    setNodes(nds => nds.map(n => {
      if (n.id === nodeId) return { ...n, data: { ...n.data, label } };
      return n;
    }));
    setHasUnsavedChanges(true);
  }

  function handleDeleteNode(nodeId) {
    setNodes(nds => nds.filter(n => n.id !== nodeId));
    setEdges(eds => eds.filter(e => e.source !== nodeId && e.target !== nodeId));
    setSelectedNode(null);
    setHasUnsavedChanges(true);
  }

  // Derive selected node type info
  const selectedNodeTypeInfo = selectedNode
    ? nodeTypes.find(nt => nt.label === selectedNode.data.typeLabel) || null
    : null;

  // Connection handler
  const onConnect = useCallback((params) => {
    setEdges(eds => [...eds, { ...params, id: `${params.source}-${params.target}` }]);
    setHasUnsavedChanges(true);
  }, [setEdges]);

  // Track changes
  useEffect(() => {
    if (currentWorkflowId && !hasUnsavedChanges) setHasUnsavedChanges(true);
  }, [nodes, edges]);

  return (
    <div className="app-layout">
      <WorkflowToolbar
        onNew={handleNew}
        onSave={handleSave}
        onLoad={handleLoad}
        onExecute={handleExecute}
        onExport={handleExport}
        workflows={workflows}
        currentWorkflowName={currentWorkflowName}
        isExecuting={isExecuting}
        hasUnsavedChanges={hasUnsavedChanges}
      />
      <div className="app-main">
        <NodePalette nodeTypes={nodeTypes} onDragStart={() => {}} />
        <WorkflowCanvas
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={handleNodeClick}
          onPaneClick={handlePaneClick}
          onDrop={onDrop}
          onDragOver={onDragOver}
          nodeTypes={nodeTypeMap}
        />
        {executionPanel ? (
          <ExecutionPanel
            nodeStatuses={nodeStatuses}
            workflowStatus={workflowStatus}
            elapsed={elapsed}
            onClose={() => { setExecutionPanel(null); setWorkflowStatus(null); }}
          />
        ) : (
          <ConfigPanel
            selectedNode={selectedNode}
            nodeType={selectedNodeTypeInfo}
            onUpdateConfig={handleUpdateConfig}
            onUpdateLabel={handleUpdateLabel}
            onDelete={handleDeleteNode}
            errorPolicies={ERROR_POLICIES}
          />
        )}
      </div>
    </div>
  );
}

// Workflow state hook (separated to work inside ReactFlowProvider)
function useWorkflowState() {
  const reactFlow = useReactFlow();
  const [nodes, setNodes] = useState(initialNodes);
  const [edges, setEdges] = useState(initialEdges);

  const onNodesChange = useCallback((changes) => {
    setNodes(nds => {
      let updated = [...nds];
      for (const change of changes) {
        if (change.type === 'position' && change.dragging === false) {
          // Position change finalized
        }
        if (change.type === 'remove') {
          updated = updated.filter(n => n.id !== change.id);
        }
        // React Flow handles position changes internally via reactFlow
      }
      return reactFlow.applyNodeChanges(changes, updated);
    });
  }, [reactFlow]);

  const onEdgesChange = useCallback((changes) => {
    setEdges(eds => reactFlow.applyEdgeChanges(changes, eds));
  }, [reactFlow]);

  return { nodes, setNodes, edges, setEdges, onNodesChange, onEdgesChange };
}

function App() {
  return (
    <ReactFlowProvider>
      <ToastProvider>
        <CanvasInner />
      </ToastProvider>
    </ReactFlowProvider>
  );
}

export default App;
```

- [ ] **Step 3: Run integration tests**

Run: `cd web/workflow-builder && npx vitest run __tests__/integration.test.jsx`
Expected: PASS

- [ ] **Step 4: Start dev server and verify visually**

Run: `cd web/workflow-builder && npx vite --port 5173`
Open `http://localhost:5173` in browser. Expected: toolbar visible, palette visible, empty canvas in center.

- [ ] **Step 5: Commit**

```bash
git add web/workflow-builder/src/App.jsx web/workflow-builder/__tests__/integration.test.jsx
git commit -m "feat: add main App component with full workflow builder assembly"
```

---

### Task 13: Backend WebSocket Event Stream

**Files:**
- Create: `src/decision_system/workflow_engine/stream.py`
- Create: `tests/test_workflow_engine/test_stream.py`
- Modify: `src/decision_system/workflow_engine/api.py` (add WebSocket route)

- [ ] **Step 1: Write tests**

```python
# tests/test_workflow_engine/test_stream.py
"""Tests for the execution event stream / WebSocket module."""

from __future__ import annotations

import pytest
from decision_system.workflow_engine.engine.events import ExecutionEvent
from decision_system.workflow_engine.stream import (
    get_execution_queue, emit_event, ExecutionEventStream,
)


@pytest.mark.asyncio
async def test_get_execution_queue_creates_queue():
    queue = get_execution_queue("test-exec-1")
    assert queue is not None


@pytest.mark.asyncio
async def test_emit_event_puts_into_queue():
    queue = get_execution_queue("test-exec-2")
    event = ExecutionEvent(
        execution_id="test-exec-2",
        event_type="node_started",
        node_id="n1",
        data={},
    )
    emit_event(event)
    # Read from queue with small timeout
    import asyncio
    result = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert result["event_type"] == "node_started"
    assert result["node_id"] == "n1"


@pytest.mark.asyncio
async def test_event_stream_yields_events():
    import asyncio
    exec_id = "test-exec-3"
    stream = ExecutionEventStream(exec_id)

    # Emit a couple events
    emit_event(ExecutionEvent(execution_id=exec_id, event_type="node_started", node_id="n1", data={}))
    emit_event(ExecutionEvent(execution_id=exec_id, event_type="node_completed", node_id="n1", data={"outputs": {}}))
    emit_event(ExecutionEvent(execution_id=exec_id, event_type="workflow_completed", node_id=None, data={"status": "completed"}))

    events = []
    async for event in stream:
        events.append(event)
        if event["event_type"] in ("workflow_completed", "workflow_failed"):
            break

    assert len(events) >= 2
    assert events[0]["event_type"] == "node_started"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest tests/test_workflow_engine/test_stream.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Write stream.py**

```python
"""Execution event streaming — bridges DAGEngine events to WebSocket consumers.

Uses an in-memory dict of asyncio.Queue objects, one per execution ID.
The DAGEngine's on_event handler calls emit_event(), which puts the event
into the execution's queue. The WebSocket endpoint reads from the queue
via ExecutionEventStream.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator

from decision_system.workflow_engine.engine.events import ExecutionEvent

# In-memory event queues: execution_id -> asyncio.Queue
_execution_queues: dict[str, asyncio.Queue] = {}


def get_execution_queue(execution_id: str) -> asyncio.Queue:
    """Get or create an event queue for the given execution ID."""
    if execution_id not in _execution_queues:
        _execution_queues[execution_id] = asyncio.Queue()
    return _execution_queues[execution_id]


def emit_event(event: ExecutionEvent) -> None:
    """Emit an event into the execution's queue (non-blocking).
    
    Called by DAGEngine's on_event handler.
    """
    queue = _execution_queues.get(event.execution_id)
    if queue is not None:
        queue.put_nowait(event.model_dump(mode="json"))


def cleanup_queue(execution_id: str) -> None:
    """Remove an execution's queue after the stream ends."""
    _execution_queues.pop(execution_id, None)


class ExecutionEventStream:
    """Async iterator that yields events for a given execution.
    
    Stops yielding when a terminal event (workflow_completed,
    workflow_failed) is received.
    """

    def __init__(self, execution_id: str, timeout: float = 1.0) -> None:
        self.execution_id = execution_id
        self.queue = get_execution_queue(execution_id)
        self.timeout = timeout

    async def __aiter__(self) -> AsyncIterator[dict]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[dict]:
        try:
            while True:
                try:
                    event = await asyncio.wait_for(self.queue.get(), timeout=self.timeout)
                    yield event
                    if event.get("event_type") in ("workflow_completed", "workflow_failed"):
                        return
                except asyncio.TimeoutError:
                    # No event yet — yield a heartbeat so WS doesn't timeout
                    yield {"event_type": "heartbeat", "execution_id": self.execution_id, "data": {}}
        finally:
            cleanup_queue(self.execution_id)
```

- [ ] **Step 4: Run tests**

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest tests/test_workflow_engine/test_stream.py -v`
Expected: PASS

- [ ] **Step 5: Add WebSocket route to api.py**

Modify: `src/decision_system/workflow_engine/api.py` — add WebSocket endpoint.

Find where the router is created and add the WebSocket endpoint.

```python
# Add to the imports at the top of api.py:
from fastapi import WebSocket, WebSocketDisconnect

# Add inside the router definition file — after the existing routes but before the return:

@router.websocket("/executions/{execution_id}/stream")
async def execution_event_stream(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint streaming execution events in real-time."""
    from decision_system.workflow_engine.stream import ExecutionEventStream
    
    await websocket.accept()
    try:
        stream = ExecutionEventStream(execution_id)
        async for event in stream:
            try:
                await websocket.send_json(event)
            except WebSocketDisconnect:
                break
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

- [ ] **Step 6: Run all existing tests to verify no regression**

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest -q`
Expected: All tests pass (796+)

- [ ] **Step 7: Commit**

```bash
git add src/decision_system/workflow_engine/stream.py src/decision_system/workflow_engine/api.py tests/test_workflow_engine/test_stream.py
git commit -m "feat: add WebSocket execution event stream endpoint"
```

---

### Task 14: Navigation Integration in Existing Web UI

**Files:**
- Modify: `web/index.html` — add "⚡ Workflows" nav item
- Modify: `web/app.js` — add workflows navigation handler

- [ ] **Step 1: Add nav item to index.html**

Find the sidebar nav list (around line 21-28 in index.html) and add a "⚡ Workflows" entry between War Room and Workspaces:

```html
<!-- After the War Room nav item, before Workspaces: -->
<button class="nav-item" type="button" data-view="workflows">⚡ Workflows</button>
```

The modified nav section should look like:
```html
<button class="nav-item active" type="button" data-view="dashboard">Dashboard</button>
<button class="nav-item" type="button" data-view="ask">Decision Brief</button>
<button class="nav-item" type="button" data-view="data">Data &amp; Ontology</button>
<button class="nav-item" type="button" data-view="war-room">War Room</button>
<button class="nav-item" type="button" data-view="workflows">⚡ Workflows</button>
<button class="nav-item" type="button" data-view="workspaces">Workspaces</button>
```

- [ ] **Step 2: Add navigation handler in app.js**

In the `navigateTo` function's `sectionNames` map (around line 490 in app.js), add:
```js
"workflows": "Workflow Builder",
```

And in the navigation handler, redirect to the workflow builder app:
```js
if (sectionId === "workflows") {
  // Open workflow builder — either by redirect or in-place iframe
  // For standalone mode, redirect:
  window.location.href = '/workflow-builder/';
  return;
}
```

- [ ] **Step 3: Verify the nav item renders**

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest tests/ -q -k "test_web" 2>/dev/null || echo "Web UI tests may not exist — manual verification needed"`

Also verify visually: Start the API server with `decision-system serve-api` and navigate to `http://localhost:8000` — the nav item should appear.

- [ ] **Step 4: Commit**

```bash
git add web/index.html web/app.js
git commit -m "feat: add Workflows nav item in existing web UI sidebar"
```

---

### Task 15: Version Bump and Final Checks

**Files:**
- Modify: `src/decision_system/__init__.py`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Bump version to 1.10.0**

In `src/decision_system/__init__.py`:
```python
__version__ = "1.10.0"
```

In `pyproject.toml`:
```toml
version = "1.10.0"
```

- [ ] **Step 2: Update CHANGELOG.md**

Add a new section:
```markdown
## v1.10.0 (2026-06-12) — Visual Workflow Builder (Phase 2)

### Added
- Visual drag-and-drop workflow builder at `web/workflow-builder/` (React + React Flow)
- Floating NodePalette with 16 color-coded node types, drag-to-create
- WorkflowCanvas with React Flow (zoom, pan, minimap, connection validation)
- NodeComponent with status overlays (running, completed, failed, skipped)
- ConfigPanel auto-rendered from JSON Schema per node type
- SchemaForm component for all field types (string, number, boolean, enum, array)
- ExecutionPanel with real-time node status via WebSocket
- WorkflowToolbar: New, Save, Load (dropdown), Execute, Export, Import
- Toast notification system for success/error/warning feedback
- API client with mock data fallback (16 node types, 2 sample workflows)
- WebSocket endpoint at `WS /executions/{id}/stream` for live events
- "⚡ Workflows" nav item in existing web UI sidebar

### Changed
- Bumped version to 1.10.0

### Backward Compatibility
- All existing 796+ tests pass unchanged
- Existing LangGraph workflow, CLI commands, FastAPI routes, web UI all untouched
```

- [ ] **Step 3: Run full test suite**

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System && python -m pytest -q`
Expected: All tests pass.

Run: `cd /home/kali/Desktop/Agentic-Ai-Decision-System/web/workflow-builder && npx vitest run`
Expected: All frontend tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/decision_system/__init__.py pyproject.toml CHANGELOG.md
git commit -m "v1.10.0: Phase 2 — Visual drag-and-drop workflow builder (React Flow)"
```

---

## Self-Review

**1. Spec coverage:**
- Task 1-12: All frontend components (palette, canvas, config panel, schema form, node component, toolbar, execution panel, toast, app assembly)
- Task 13: WebSocket backend endpoint
- Task 14: Nav integration in existing sidebar
- Task 15: Version bump + changelog
- Missing: The API proxy config in vite.config.js (Task 1) — covers the dev server routing
- Missing: The `nodeTypes.js` mapping (Task 3) — covers color coding
- All spec sections are covered

**2. Placeholder scan:**
- No TBD, TODO, or placeholder patterns found
- All code is complete — no "add appropriate error handling" or "similar to Task N"
- All function signatures are consistent across tasks

**3. Type consistency:**
- `api.js` uses consistent function names: `fetchNodeTypes`, `listWorkflows`, `getWorkflow`, `saveWorkflow`, `deleteWorkflow`, `executeWorkflow`, `getExecution`, `streamExecutionEvents`
- `mockData.js` exports: `MOCK_NODE_TYPES`, `MOCK_WORKFLOWS`, `MOCK_EXECUTION_STATE`, `MOCK_EXECUTION_EVENTS`
- `App.jsx` uses the same function names from `api.js`
- React Flow node shape: `{ id, type: 'custom', position, data: { label, typeLabel, category, config, ... } }`
- Connection shape: `{ source, target, sourceHandle, targetHandle }`

---

**Plan complete and saved to `docs/superpowers/plans/2026-06-12-workflow-builder-phase2.md`.** Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

2. **Inline Execution** — Execute tasks in this session, batch execution with checkpoints

**Which approach?**
