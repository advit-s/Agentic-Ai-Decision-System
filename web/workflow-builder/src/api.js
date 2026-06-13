// api.js — HTTP + WebSocket client with mock data fallback

import {
  MOCK_NODE_TYPES,
  MOCK_WORKFLOWS,
  MOCK_EXECUTION_STATE,
  MOCK_EXECUTION_EVENTS,
  MOCK_SCHEDULES,
} from "./mockData";

const API_BASE_KEY = "wfBuilderApiBaseUrl";

function getBaseUrl() {
  const stored = localStorage.getItem(API_BASE_KEY);
  if (stored) return stored;
  // Auto-detect: when SPA is served from FastAPI backend, the API is at
  // the same origin. Only trigger for known backend ports.
  if (typeof window !== "undefined" && window.location) {
    const port = window.location.port;
    if (port && ["8000", "8001", "8080"].includes(port)) {
      return window.location.origin;
    }
  }
  return "";
}

function isMockMode() {
  return !getBaseUrl();
}

async function apiFetch(path, options = {}) {
  const base = getBaseUrl();
  if (!base) throw new Error("No API base URL configured");
  const url = `${base.replace(/\/+$/, "")}${path}`;
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  return response.json();
}

// --- Node Types ---
async function fetchNodeTypes() {
  if (isMockMode()) return [...MOCK_NODE_TYPES];
  return apiFetch("/workflows/nodes");
}

// --- Workflows ---
let _mockWorkflows = [...MOCK_WORKFLOWS];

function listWorkflows() {
  if (isMockMode())
    return Promise.resolve(
      _mockWorkflows.map(({ id, name, description, updated_at }) => ({ id, name, description, updated_at }))
    );
  return apiFetch("/workflows");
}

function getWorkflow(id) {
  if (isMockMode()) {
    const wf = _mockWorkflows.find((w) => w.id === id);
    if (!wf) throw new Error("Workflow not found");
    return Promise.resolve(JSON.parse(JSON.stringify(wf)));
  }
  return apiFetch(`/workflows/${id}`);
}

function saveWorkflow(workflow) {
  if (isMockMode()) {
    const idx = _mockWorkflows.findIndex((w) => w.id === workflow.id);
    if (idx >= 0) _mockWorkflows[idx] = workflow;
    else _mockWorkflows.push(workflow);
    return Promise.resolve(workflow);
  }
  if (workflow.id && workflow.id.startsWith("wf-")) {
    return apiFetch(`/workflows/${workflow.id}`, {
      method: "PUT",
      body: JSON.stringify(workflow),
    });
  }
  return apiFetch("/workflows", {
    method: "POST",
    body: JSON.stringify(workflow),
  });
}

function deleteWorkflow(id) {
  if (isMockMode()) {
    _mockWorkflows = _mockWorkflows.filter((w) => w.id !== id);
    return Promise.resolve({ success: true });
  }
  return apiFetch(`/workflows/${id}`, { method: "DELETE" });
}

// --- Execution ---
function executeWorkflow(id) {
  if (isMockMode()) {
    const state = {
      ...MOCK_EXECUTION_STATE,
      execution_id: `exec-mock-${Date.now()}`,
      workflow_id: id,
      started_at: new Date().toISOString(),
      status: "running",
    };
    return Promise.resolve(state);
  }
  return apiFetch(`/workflows/${id}/execute`, { method: "POST" });
}

function getExecution(id) {
  if (isMockMode()) {
    return Promise.resolve({ ...MOCK_EXECUTION_STATE, execution_id: id, status: "completed" });
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
      onEvent({
        ...MOCK_EXECUTION_EVENTS[idx],
        execution_id: executionId,
        timestamp: new Date().toISOString(),
      });
      idx++;
    }, 500);
    return () => clearInterval(interval);
  }

  const base = getBaseUrl().replace(/^http/, "ws");
  const ws = new WebSocket(`${base}/executions/${executionId}/stream`);
  ws.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data));
    } catch {
      // ignore parse errors
    }
  };
  ws.onerror = () => {
    // WS error — caller handles via timeout
  };
  return () => ws.close();
}

// --- Schedules ---
let _mockSchedules = [...MOCK_SCHEDULES];

function createSchedule(schedule) {
  if (isMockMode()) {
    const s = {
      ...schedule,
      id: `sch-mock-${Date.now()}`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      last_fired: null,
    };
    _mockSchedules.push(s);
    return Promise.resolve(s);
  }
  return apiFetch("/schedules", { method: "POST", body: JSON.stringify(schedule) });
}

function listSchedules(workflowId) {
  if (isMockMode()) {
    let list = _mockSchedules;
    if (workflowId) list = list.filter((s) => s.workflow_id === workflowId);
    return Promise.resolve({ schedules: list });
  }
  const query = workflowId ? `?workflow_id=${workflowId}` : "";
  return apiFetch(`/schedules${query}`);
}

function getSchedule(id) {
  if (isMockMode()) {
    const s = _mockSchedules.find((s) => s.id === id);
    if (!s) return Promise.reject(new Error("Schedule not found"));
    return Promise.resolve({ ...s });
  }
  return apiFetch(`/schedules/${id}`);
}

function updateSchedule(id, updates) {
  if (isMockMode()) {
    const idx = _mockSchedules.findIndex((s) => s.id === id);
    if (idx < 0) return Promise.reject(new Error("Schedule not found"));
    _mockSchedules[idx] = { ..._mockSchedules[idx], ...updates, updated_at: new Date().toISOString() };
    return Promise.resolve({ ..._mockSchedules[idx] });
  }
  return apiFetch(`/schedules/${id}`, { method: "PUT", body: JSON.stringify(updates) });
}

function deleteSchedule(id) {
  if (isMockMode()) {
    _mockSchedules = _mockSchedules.filter((s) => s.id !== id);
    return Promise.resolve({ status: "deleted", id });
  }
  return apiFetch(`/schedules/${id}`, { method: "DELETE" });
}

function toggleSchedule(id) {
  if (isMockMode()) {
    const idx = _mockSchedules.findIndex((s) => s.id === id);
    if (idx < 0) return Promise.reject(new Error("Schedule not found"));
    _mockSchedules[idx].enabled = !_mockSchedules[idx].enabled;
    _mockSchedules[idx].updated_at = new Date().toISOString();
    return Promise.resolve({ ..._mockSchedules[idx] });
  }
  return apiFetch(`/schedules/${id}/toggle`, { method: "POST" });
}

export {
  getBaseUrl,
  isMockMode,
  fetchNodeTypes,
  listWorkflows,
  getWorkflow,
  saveWorkflow,
  deleteWorkflow,
  executeWorkflow,
  getExecution,
  streamExecutionEvents,
  createSchedule,
  listSchedules,
  getSchedule,
  updateSchedule,
  deleteSchedule,
  toggleSchedule,
};
