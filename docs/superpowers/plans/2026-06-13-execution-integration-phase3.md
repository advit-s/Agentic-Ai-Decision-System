# Phase 3: Real-Time Execution Integration — Implementation Plan

> **Status:** COMPLETED (committed as `cdf8c31`)
> **For reference:** This plan documents what was built in Phase 3. Use the same format for future phases.

**Goal:** Connect the Phase 2 visual workflow editor to the real backend DAG engine, making executions actually run instead of using mock data, and providing real-time status feedback with inspectable node inputs/outputs.

**Architecture:** The SPA is served from FastAPI at `/workflow-builder/`. `api.js` auto-detects backend availability via port inspection. During execution, DAGEngine events flow through `asyncio.Queue` → `ExecutionEventStream` → WebSocket → frontend `streamExecutionEvents()` → React state updates.

**Tech Stack:** Python 3.11+ (FastAPI, asyncio, WebSocket), React 18, React Flow 11, Vitest + React Testing Library

---

## Files Changed

```
src/decision_system/api/app.py                    # MODIFIED: static mount for workflow-builder SPA
web/workflow-builder/src/App.jsx                  # MODIFIED: live WebSocket, input/output capture
web/workflow-builder/src/api.js                   # MODIFIED: auto-detect backend URL
web/workflow-builder/src/components/ExecutionPanel.jsx  # MODIFIED: expandable data inspection
web/workflow-builder/src/mockData.js              # MODIFIED: provider selector on 4 node types
web/workflow-builder/src/styles/execution-panel.css    # MODIFIED: dark code-block styling
.gitignore                                        # MODIFIED: node_modules exclusion
```

**No new source files — all changes were modifications to existing files.**

---

### Task 1: FastAPI Static Mount for Workflow-Builder SPA

**File:** `src/decision_system/api/app.py`

**What changed:** Added a static mount for the built workflow-builder SPA at `/workflow-builder/` before the existing root static mount.

**Resolution logic** (package-level first, repo fallback):
```python
_wf_dir = web_dir / "workflow-builder" / "dist"                # package path
if not _wf_dir.is_dir():
    _repo_wf = Path(__file__).resolve().parents[3] / "web" / "workflow-builder" / "dist"
    if _repo_wf.is_dir():
        _wf_dir = _repo_wf
if _wf_dir.is_dir():
    api.mount("/workflow-builder", StaticFiles(directory=str(_wf_dir), html=True), name="workflow-builder")
```

- [x] **Step 1:** Add import for `Path` at top of file
- [x] **Step 2:** Insert workflow-builder mount block after web_dir resolution but before root static mount
- [x] **Step 3:** Verify: `GET /workflow-builder/` returns the SPA index.html
- [x] **Step 4:** Verify: `GET /workflow-builder/assets/index-*.js` returns JS bundle
- [x] **Step 5:** Backend tests pass (`python -m pytest -q`)

**Test:** `test_root_and_package_web_assets_match` checks both locations have matching `web/` assets. A `web/` source file change requires rebuilding both the root and package copies.

---

### Task 2: API Auto-Detection with Backend Port Check

**File:** `web/workflow-builder/src/api.js`

**What changed:** `getBaseUrl()` now checks `window.location.port` and returns `window.location.origin` when the port is a known backend port (8000/8001/8080). Returns `""` (empty string) otherwise, which triggers mock mode.

- [x] **Step 1:** Add `getBaseUrl()` function with port whitelist
- [x] **Step 2:** Add `isMockMode()` that calls `getBaseUrl()` and checks for empty string
- [x] **Step 3:** All API functions (`fetchNodeTypes`, `listWorkflows`, `getWorkflow`, `saveWorkflow`, `executeWorkflow`, `getExecution`, `streamExecutionEvents`) already had mock/real branching via `isMockMode()` — no changes needed there
- [x] **Step 4:** Add `API_BASE_KEY` constant for optional `localStorage` override
- [x] **Step 5:** Verify: served from FastAPI port 8000 → real mode with WebSocket
- [x] **Step 6:** Verify: served from Vite dev port 5173 → mock mode with simulated events
- [x] **Step 7:** Verify: jsdom test environment port (3000) → mock mode (not in whitelist)

**Key decision:** Positive port matching (whitelist of 8000/8001/8080) instead of negative filtering (anything-not-5173). This prevents false auto-detection from test environments or arbitrary ports.

```javascript
function getBaseUrl() {
  const stored = localStorage.getItem(API_BASE_KEY);
  if (stored) return stored;
  if (typeof window !== "undefined" && window.location) {
    const port = window.location.port;
    if (port && ["8000", "8001", "8080"].includes(port)) {
      return window.location.origin;
    }
  }
  return "";
}
```

---

### Task 3: Live WebSocket Execution in App.jsx

**File:** `web/workflow-builder/src/App.jsx`

**What changed:** `handleExecute()` now processes real WebSocket events from `streamExecutionEvents()`.

- [x] **Step 1:** After calling `executeWorkflow()`, subscribe to events via `streamExecutionEvents(execState.execution_id, callback)`
- [x] **Step 2:** Handle terminal events (`workflow_completed`, `workflow_failed`) that stop the timer, set `workflowStatus`, and return early:

```javascript
if (event.event_type === "workflow_completed") {
  clearInterval(timerRef.current);
  setIsExecuting(false);
  setWorkflowStatus("completed");
  return;
}
```

- [x] **Step 3:** Capture `inputs` and `outputs` from `event.data` on each `node_completed` event
- [x] **Step 4:** Update `nodeStatuses` state with status, duration, inputs, outputs, error
- [x] **Step 5:** Propagate status changes back to canvas node data so node components show running/completed/failed overlays
- [x] **Step 6:** Add 60-second safety timeout that stops execution if WebSocket doesn't deliver terminal event
- [x] **Step 7:** Error handling: clear timer, set workflow to failed, show toast on exception

**Event → state mapping:**

| Event Type | nodeStatuses.status | Canvas node status | Timer |
|---|---|---|---|
| `node_started` | `running` | `running` | active |
| `node_completed` | `completed` | `completed` | active |
| `node_failed` | `failed` | `failed` | active |
| `workflow_completed` | (terminal) | — | stopped |
| `workflow_failed` | (terminal) | — | stopped |

---

### Task 4: Provider Selector on Node Config Schemas

**File:** `web/workflow-builder/src/mockData.js`

**What changed:** Added `provider` field to `config_schema.properties` for 4 AI node types:

- `extract_claims` — `{ type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] }`
- `verify_claims` — same
- `write_report` — same
- `war_room` — same

- [x] **Step 1:** Add provider field to each node type's `config_schema.properties`
- [x] **Step 2:** The field is picked up automatically by `SchemaForm.jsx` which renders an `<select>` dropdown for enum-type fields
- [x] **Step 3:** On save, the provider value is propagated to `node.config.provider` which is passed to the backend node's `config` dict

**Key insight:** No UI component changes needed — `SchemaForm` auto-renders enum fields as dropdowns. The provider selector appears in the ConfigPanel for these node types without additional code.

---

### Task 5: Expandable Node Data Inspection in ExecutionPanel

**Files:**
- `web/workflow-builder/src/components/ExecutionPanel.jsx`
- `web/workflow-builder/src/styles/execution-panel.css`

**What changed:** ExecutionPanel now shows per-node input/output data in expandable rows.

- [x] **Step 1:** Add `expandedNode` state to track which node is expanded (null = none)
- [x] **Step 2:** Make node header clickable with `role="button", tabIndex={0}, onKeyDown` for accessibility
- [x] **Step 3:** Show expand/collapse indicator (▸/▾) when node has inputs or outputs
- [x] **Step 4:** When expanded, render formatted JSON of inputs and outputs in a dark code block
- [x] **Step 5:** Add `formatData()` function that serializes objects to JSON with 2000-char truncation
- [x] **Step 6:** CSS: dark background (`#1a1a2e`), monospace font, section labels (Inputs/Outputs), pre-wrap for long content

**CSS classes added:**
- `.execution-node-data` — dark code-block container
- `.execution-data-section` — subsection wrapper
- `.execution-data-label` — "Inputs" / "Outputs" label
- `.execution-data-json` — `<pre>` element for formatted JSON
- `.execution-node-header:hover` — cursor pointer, opacity change

---

### Task 6: .gitignore and Test Infrastructure Fixes

**Files:**
- `.gitignore`
- `web/workflow-builder/__tests__/setup.js`
- `web/workflow-builder/vitest.config.js`

**What changed:**

- [x] **Step 1:** Add `node_modules/`, `.webpack/`, `yarn-error.log` to `.gitignore`
- [x] **Step 2:** Add test polyfills for jsdom:
  - `localStorage` — in-memory store with get/set/remove/clear
  - `ResizeObserver` — no-op class (required by React Flow MiniMap/Controls)
  - `DataTransfer` — full implementation (required by drag-and-drop events)
  - `EventTarget.dispatchEvent` override — attaches `dataTransfer` to drag events since jsdom's implementation is incomplete
- [x] **Step 3:** Wire setup file in `vitest.config.js` via `setupFiles: ['./__tests__/setup.js']`
- [x] **Step 4:** Fix text matchers to use regex for emoji-prefixed button text (`/Save/` instead of `"Save"`)
- [x] **Step 5:** Fix async-loaded content to use `findByText` instead of `getByText`

---

### Task 7: Integration Testing

**Files:**
- `web/workflow-builder/__tests__/integration.test.jsx`

**What changed:** Full create → configure → execute integration test covering the real app assembly.

- [x] **Step 1:** Render `<App />` with `ReactFlowProvider` and `ToastProvider`
- [x] **Step 2:** Verify node palette renders (async — waits for mock data load)
- [x] **Step 3:** Verify toolbar shows "Untitled Workflow" initially
- [x] **Step 4**–[x] **Step 12:** Additional tests for palette items, config panel, canvas rendering

---

## Task Dependency Graph

```
Task 1 (FastAPI mount)          Task 2 (API auto-detect)    Task 6 (test infra)
         │                             │                            │
         └─────────────┬───────────────┘                            │
                       │                                            │
                  Task 3 (WS execution)           Task 4 (provider)  │
                       │                             │              │
                  Task 5 (data inspection) ◄─────────┘              │
                       │                                            │
                  Task 7 (integration test) ◄───────────────────────┘
```

## Test Results

- **Backend:** 801 passed (no regressions — all existing + Phase 1 workflow engine tests)
- **Frontend:** 35 passed across 10 test files (new: ExecutionPanel, integration; existing: api, mockData, NodePalette, WorkflowCanvas, WorkflowToolbar, ConfigPanel, SchemaForm, Toast)

## Verification Checklist

- [x] `python -m pytest -q` — 801 passed
- [x] `cd web/workflow-builder && npx vitest run` — 35 passed
- [x] `git status` — clean (no staged/unstaged changes)
- [x] SPA builds: `cd web/workflow-builder && npx vite build` — produces `dist/index.html` + `dist/assets/`
- [x] `git log --oneline` — clean history, no merge commits
