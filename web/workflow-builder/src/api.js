// api.js — HTTP + WebSocket client with mock data fallback

import {
  MOCK_NODE_TYPES,
  MOCK_WORKFLOWS,
  MOCK_EXECUTION_STATE,
  MOCK_EXECUTION_EVENTS,
  MOCK_SCHEDULES,
  MOCK_PROVIDERS,
  MOCK_REVIEWS,
  MOCK_EXECUTION_HISTORY,
  MOCK_EXECUTION_DETAILS,
  MOCK_WORKFLOW_VERSIONS,
  MOCK_CLAIM_VERIFICATION,
  MOCK_VERIFICATION_SUMMARY,
  MOCK_CONTRADICTIONS,
  MOCK_TRUST_REPORT,
} from "./mockData";

const API_BASE_KEY = "wfBuilderApiBaseUrl";
let _testMockOverride = false;

function getBaseUrl() {
  if (_testMockOverride) return "";
  const stored = localStorage.getItem(API_BASE_KEY);
  if (stored) return stored;
  // Auto-detect: when SPA is served from FastAPI backend, the API is at
  // the same origin. Trigger for known backend ports and Docker frontend port 3000.
  if (typeof window !== "undefined" && window.location) {
    const port = window.location.port;
    if (port && ["3000", "8000", "8001", "8080"].includes(port)) {
      return window.location.origin;
    }
  }
  return "";
}

function isMockMode() {
  return !getBaseUrl();
}

/**
 * Returns the current backend mode for UI status display.
 * - "live" when auto-detected or user-configured base URL is set
 * - "mock" when no base URL is configured
 * - "unavailable" when live mode is configured but backend is unreachable
 */
export function getBackendMode() {
  const base = getBaseUrl();
  if (!base) return "mock";
  // Initial optimistic return; caller can update after health check
  return "live";
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

async function listWorkflows() {
  if (isMockMode())
    return _mockWorkflows.map(({ id, name, description, updated_at }) => ({ id, name, description, updated_at }));
  const data = await apiFetch("/workflows");
  // Backend returns { workflows: [...] } — unwrap for consistency with mock path
  return data.workflows || data;
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
  // "wf-" prefix means this is a locally-generated id for a new unsaved workflow — use POST
  if (workflow.id && !workflow.id.startsWith("wf-")) {
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
function executeWorkflow(id, inputs = {}) {
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
  return apiFetch(`/workflows/${id}/execute`, {
    method: "POST",
    body: JSON.stringify({ inputs }),
  });
}

function getExecution(id) {
  if (isMockMode()) {
    return Promise.resolve({ ...MOCK_EXECUTION_STATE, execution_id: id, status: "completed" });
  }
  return apiFetch(`/executions/${id}`);
}

// --- Execution History ---
let _mockHistory = [...MOCK_EXECUTION_HISTORY];

function listExecutionHistory() {
  if (isMockMode()) {
    return Promise.resolve([..._mockHistory]);
  }
  return apiFetch("/executions/history").then(data => data.executions || data);
}

function getExecutionDetail(id) {
  if (isMockMode()) {
    const detail = MOCK_EXECUTION_DETAILS[id];
    if (!detail) return Promise.reject(new Error("Execution detail not found"));
    return Promise.resolve(JSON.parse(JSON.stringify(detail)));
  }
  return apiFetch(`/executions/${id}/detail`);
}

function deleteExecutionHistory(id) {
  if (isMockMode()) {
    _mockHistory = _mockHistory.filter(h => h.id !== id);
    return Promise.resolve({ success: true });
  }
  return apiFetch(`/executions/history/${id}`, { method: "DELETE" });
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

// --- Providers ---
let _mockProviders = [...MOCK_PROVIDERS];

function listProviders() {
  if (isMockMode()) return Promise.resolve({ providers: [..._mockProviders] });
  return apiFetch("/providers");
}

function createProvider(provider) {
  if (isMockMode()) {
    const p = { ...provider, api_key_configured: false };
    _mockProviders.push(p);
    return Promise.resolve(p);
  }
  return apiFetch("/providers", { method: "POST", body: JSON.stringify(provider) });
}

function deleteProvider(name) {
  if (isMockMode()) {
    _mockProviders = _mockProviders.filter((p) => p.name !== name);
    return Promise.resolve({ status: "deleted", name });
  }
  return apiFetch(`/providers/${name}`, { method: "DELETE" });
}

function checkProvider(name) {
  if (isMockMode()) {
    return Promise.resolve({ status: "ok", provider: name, model: "mock-model", response: "ok" });
  }
  return apiFetch(`/providers/${name}/check`, { method: "POST" });
}

function setDefaultProvider(name) {
  if (isMockMode()) {
    const idx = _mockProviders.findIndex((p) => p.name === name);
    if (idx < 0) return Promise.reject(new Error("Provider not found"));
    const [provider] = _mockProviders.splice(idx, 1);
    _mockProviders.unshift(provider);
    return Promise.resolve({ status: "ok", default_provider: provider });
  }
  return apiFetch("/providers/system/default", { method: "POST", body: JSON.stringify({ name }) });
}

function updateProvider(name, updates) {
  if (isMockMode()) {
    const idx = _mockProviders.findIndex((p) => p.name === name);
    if (idx < 0) return Promise.reject(new Error("Provider not found"));
    _mockProviders[idx] = { ..._mockProviders[idx], ...updates };
    return Promise.resolve({ ..._mockProviders[idx] });
  }
  return apiFetch(`/providers/${name}`, { method: "PUT", body: JSON.stringify(updates) });
}

// --- Reviews ---
let _mockReviews = [...MOCK_REVIEWS];

function listReviews() {
  if (isMockMode()) {
    return Promise.resolve({ reviews: [..._mockReviews] });
  }
  return apiFetch("/reviews");
}

function resolveReview(reviewId, action, notes, modifiedData, reviewedBy) {
  if (isMockMode()) {
    const idx = _mockReviews.findIndex((r) => (r.review_id || r.id) === reviewId);
    if (idx < 0) return Promise.reject(new Error("Review not found"));

    const review = _mockReviews[idx];
    if (review.status !== "pending_review") {
      return Promise.reject(new Error("Review is already resolved"));
    }

    const now = new Date().toISOString();
    if (action === "approve") {
      review.status = "approved";
      review.approved = true;
    } else if (action === "reject") {
      review.status = "rejected";
      review.approved = false;
    } else {
      review.status = "changes_requested";
      review.approved = false;
    }

    review.action = action;
    review.review_notes = notes || "";
    review.modified_data = modifiedData || null;
    review.reviewed_by = reviewedBy || "system";
    review.resolved_at = now;

    _mockReviews[idx] = { ...review };
    return Promise.resolve({ ..._mockReviews[idx] });
  }
  return apiFetch(`/reviews/${reviewId}/resolve`, {
    method: "POST",
    body: JSON.stringify({ action, notes, modified_data: modifiedData, reviewed_by: reviewedBy }),
  });
}

// --- Workflow Versions ---
let _mockWorkflowVersions = [...MOCK_WORKFLOW_VERSIONS];

function listWorkflowVersions(workflowId) {
  if (isMockMode()) {
    return Promise.resolve(
      _mockWorkflowVersions.filter(v => v.workflow_id === workflowId || !workflowId)
    );
  }
  return apiFetch(`/workflows/${workflowId}/versions`).then(data => data.versions || data);
}

function getWorkflowVersion(workflowId, versionId) {
  if (isMockMode()) {
    const v = _mockWorkflowVersions.find(v => v.id === versionId);
    if (!v) return Promise.reject(new Error("Version not found"));
    return Promise.resolve(JSON.parse(JSON.stringify(v)));
  }
  return apiFetch(`/workflows/${workflowId}/versions/${versionId}`);
}

// --- Replay execution ---
function streamReplayEvents(executionId, nodeIds, onEvent) {
  if (isMockMode()) {
    const targetSet = new Set(nodeIds);
    let idx = 0;
    const filteredEvents = MOCK_EXECUTION_EVENTS.filter(
      e => !e.node_id || targetSet.has(e.node_id)
    );
    const interval = setInterval(() => {
      if (idx >= filteredEvents.length) {
        clearInterval(interval);
        return;
      }
      onEvent({
        ...filteredEvents[idx],
        execution_id: executionId,
        timestamp: new Date().toISOString(),
      });
      idx++;
    }, 500);
    return () => clearInterval(interval);
  }
  // Real mode: same WebSocket subscription
  return streamExecutionEvents(executionId, onEvent);
}

// --- Verification & Trust Report ---

function verifyClaim(claimId, workspaceId) {
  if (isMockMode()) {
    const result = MOCK_CLAIM_VERIFICATION[claimId];
    if (!result) return Promise.reject(new Error("Claim not found"));
    return Promise.resolve({ ...result, status: result.status, verified_at: new Date().toISOString() });
  }
  return apiFetch(`/claims/${claimId}/verify`, {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId || null }),
  });
}

function verifyExecutionClaims(executionId, workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({
      execution_id: executionId,
      verified: true,
      summary: { ...MOCK_VERIFICATION_SUMMARY, verified_at: new Date().toISOString() },
    });
  }
  return apiFetch(`/executions/${executionId}/claims/verify`, {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId || null }),
  });
}

function verifyWorkspaceClaims(workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({
      workspace_id: workspaceId,
      verified: true,
      summary: { ...MOCK_VERIFICATION_SUMMARY, verified_at: new Date().toISOString() },
    });
  }
  return apiFetch(`/workspaces/${workspaceId}/claims/verify`, {
    method: "POST",
  });
}

function getClaimVerification(claimId) {
  if (isMockMode()) {
    const result = MOCK_CLAIM_VERIFICATION[claimId];
    if (!result) return Promise.resolve(null);
    return Promise.resolve({ ...result });
  }
  return apiFetch(`/claims/${claimId}/verification`);
}

function getExecutionVerificationSummary(executionId) {
  if (isMockMode()) {
    return Promise.resolve({ ...MOCK_VERIFICATION_SUMMARY });
  }
  return apiFetch(`/executions/${executionId}/verification-summary`);
}

function getWorkspaceVerificationSummary(workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({ ...MOCK_VERIFICATION_SUMMARY });
  }
  return apiFetch(`/workspaces/${workspaceId}/verification-summary`);
}

function scanWorkspaceContradictions(workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({
      contradictions: [...MOCK_CONTRADICTIONS],
      count: MOCK_CONTRADICTIONS.length,
    });
  }
  return apiFetch(`/workspaces/${workspaceId}/contradictions/scan`, {
    method: "POST",
  });
}

function listWorkspaceContradictions(workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({
      contradictions: [...MOCK_CONTRADICTIONS],
      count: MOCK_CONTRADICTIONS.length,
    });
  }
  return apiFetch(`/workspaces/${workspaceId}/contradictions`);
}

function listClaimContradictions(claimId) {
  if (isMockMode()) {
    const claimCons = MOCK_CONTRADICTIONS.filter(c => c.claim_id === claimId);
    return Promise.resolve({
      contradictions: [...claimCons],
      count: claimCons.length,
    });
  }
  return apiFetch(`/claims/${claimId}/contradictions`);
}

function generateTrustReport(executionId, workspaceId) {
  if (isMockMode()) {
    return Promise.resolve({
      ...MOCK_TRUST_REPORT,
      report_id: `rpt-mock-${Date.now()}`,
      execution_id: executionId,
      workspace_id: workspaceId || "ws-1",
      generated_at: new Date().toISOString(),
    });
  }
  return apiFetch(`/executions/${executionId}/report`, {
    method: "POST",
    body: JSON.stringify({ workspace_id: workspaceId || null }),
  });
}

function getReport(reportId) {
  if (isMockMode()) {
    return Promise.resolve({ ...MOCK_TRUST_REPORT, report_id: reportId });
  }
  return apiFetch(`/reports/${reportId}`);
}

function exportReport(reportId, format = "md") {
  if (isMockMode()) {
    const md = `# Trust Report — Revenue Analysis Q2\n\n## Verification Summary\n\nTotal claims: 5\nSupported: 1\nContradicted: 1\nUnsupported: 1\nUncertain: 1\nNeeds review: 1\n\n## Warnings and Limitations\n\nThis verification is deterministic and conservative.`;
    return Promise.resolve({
      report_id: reportId,
      format,
      content: md,
      filename: `trust-report-${reportId}.${format}`,
    });
  }
  return apiFetch(`/reports/${reportId}/export?format=${format}`);
}

function getReportMarkdown(reportId) {
  return exportReport(reportId, "md").then(r => r.content || r);
}



// --- Workspaces ---
let _mockWorkspaces = [
  { workspace_id: "ws-1", name: "Demo Workspace", description: "Sample workspace with demo data", active: true },
];
let _mockActiveWs = "ws-1";

async function listWorkspaces() {
  if (isMockMode()) {
    return { status: "ok", workspaces: [..._mockWorkspaces], active_workspace_id: _mockActiveWs };
  }
  return apiFetch("/workspaces");
}

async function getWorkspaceStatus() {
  if (isMockMode()) {
    const ws = _mockWorkspaces.find(w => w.workspace_id === _mockActiveWs);
    if (!ws) return { status: "no_active_workspace", workspace: null, artifact_counts: {} };
    return {
      status: "ok",
      workspace: { ...ws },
      data_source_count: 0,
      document_count: 0,
      dataset_count: 0,
      indexed_document_count: 0,
      chunk_count: 0,
      claim_count: 0,
      report_count: 0,
      database_path: ".decision_system/workspaces/workspaces.sqlite",
    };
  }
  return apiFetch("/workspaces/status");
}

async function createWorkspace(name, description = "", activate = true) {
  if (isMockMode()) {
    const wsId = name.toLowerCase().replace(/\s+/g, "-").replace(/_/g, "-");
    const existing = _mockWorkspaces.find(w => w.workspace_id === wsId);
    if (existing) {
      if (activate) { _mockActiveWs = wsId; existing.active = true; }
      return { status: "exists", workspace: existing };
    }
    const ws = { workspace_id: wsId, name, description, active: activate };
    _mockWorkspaces.push(ws);
    if (activate) _mockActiveWs = wsId;
    _mockWorkspaces.forEach(w => w.active = w.workspace_id === wsId);
    return { status: "created", workspace: ws };
  }
  return apiFetch("/workspaces", {
    method: "POST",
    body: JSON.stringify({ name, description, activate }),
  });
}

async function activateWorkspace(name) {
  if (isMockMode()) {
    const ws = _mockWorkspaces.find(w => w.name === name);
    if (!ws) throw new Error("Workspace not found");
    _mockActiveWs = ws.workspace_id;
    _mockWorkspaces.forEach(w => w.active = w.workspace_id === ws.workspace_id);
    return { status: "ok", workspace: ws };
  }
  return apiFetch(`/workspaces/${encodeURIComponent(name)}/activate`, { method: "POST" });
}

async function getActiveWorkspaceId() {
  if (isMockMode()) return _mockActiveWs;
  try {
    const data = await getWorkspaceStatus();
    return data.workspace?.workspace_id || null;
  } catch { return null; }
}



// --- Data Sources ---
let _mockDataSources = {};

function _getMockSources(wsId) {
  if (!_mockDataSources[wsId]) _mockDataSources[wsId] = [];
  return _mockDataSources[wsId];
}

async function listDataSources(workspaceId) {
  if (isMockMode()) {
    return { data_sources: [..._getMockSources(workspaceId)] };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources`);
}

async function uploadDataSource(workspaceId, filename, content, fileType) {
  if (isMockMode()) {
    const sourceId = `ds-mock-${Date.now()}`;
    const ds = {
      source_id: sourceId,
      workspace_id: workspaceId,
      name: filename,
      file_type: fileType || "unknown",
      source_type: "document",
      status: "uploaded",
      original_filename: filename,
      size_bytes: content.length || 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    _getMockSources(workspaceId).push(ds);
    return { status: "uploaded", data_source: ds };
  }
  // Multipart or direct content upload
  const resp = await fetch(`${getBaseUrl().replace(/\/+$/, "")}/workspaces/${workspaceId}/data-sources/upload?filename=${encodeURIComponent(filename)}`, {
    method: "POST",
    body: content,
  });
  if (!resp.ok) throw new Error(`Upload failed: HTTP ${resp.status}`);
  return resp.json();
}

async function getDataSource(workspaceId, sourceId) {
  if (isMockMode()) {
    const ds = _getMockSources(workspaceId).find(s => s.source_id === sourceId);
    if (!ds) throw new Error("Data source not found");
    return { data_source: { ...ds } };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}`);
}

async function deleteDataSource(workspaceId, sourceId) {
  if (isMockMode()) {
    _mockDataSources[workspaceId] = _getMockSources(workspaceId).filter(s => s.source_id !== sourceId);
    return { status: "deleted" };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}`, { method: "DELETE" });
}

async function parseDataSource(workspaceId, sourceId) {
  if (isMockMode()) {
    const sources = _getMockSources(workspaceId);
    const ds = sources.find(s => s.source_id === sourceId);
    if (!ds) throw new Error("Data source not found");
    ds.status = "parsed";
    ds.chunks = [{ chunk_id: "mock-chunk-1", text: "Mock parsed content for " + ds.name, chunk_index: 0 }];
    return { status: "parsed", source_id: sourceId, chunk_count: 1 };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/parse`, { method: "POST" });
}

async function indexDataSource(workspaceId, sourceId) {
  if (isMockMode()) {
    const sources = _getMockSources(workspaceId);
    const ds = sources.find(s => s.source_id === sourceId);
    if (!ds) throw new Error("Data source not found");
    ds.status = "indexed";
    return { status: "indexed", source_id: sourceId, chunk_count: 1, retrieval_mode: "keyword" };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/index`, { method: "POST" });
}

async function getDataSourceStatus(workspaceId, sourceId) {
  if (isMockMode()) {
    const ds = _getMockSources(workspaceId).find(s => s.source_id === sourceId);
    if (!ds) throw new Error("Data source not found");
    return { status: ds.status, source_id: sourceId, workspace_id: workspaceId };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/status`);
}

async function getDataSourceProfile(workspaceId, sourceId) {
  if (isMockMode()) {
    return { profile: null, source_id: sourceId };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/profile`);
}

async function getDataSourceChunks(workspaceId, sourceId) {
  if (isMockMode()) {
    const ds = _getMockSources(workspaceId).find(s => s.source_id === sourceId);
    return { chunks: ds?.chunks || [], source_id: sourceId };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/chunks`);
}

async function getDataSourcePreview(workspaceId, sourceId) {
  if (isMockMode()) {
    const ds = _getMockSources(workspaceId).find(s => s.source_id === sourceId);
    return { chunks: ds?.chunks || [], source_id: sourceId };
  }
  return apiFetch(`/workspaces/${workspaceId}/data-sources/${sourceId}/preview`);
}

async function searchEvidence(workspaceId, query, limit = 10, sourceFilter, fileTypeFilter) {
  if (isMockMode()) {
    return {
      results: [],
      query,
      limit,
      total_results: 0,
      retrieval_mode: "keyword",
    };
  }
  const body = { query, limit };
  if (sourceFilter) body.source_id = sourceFilter;
  if (fileTypeFilter) body.file_type = fileTypeFilter;
  return apiFetch(`/workspaces/${workspaceId}/evidence/search`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Exposed for test use only — overrides mock mode detection */
function _setMockOverride(v) { _testMockOverride = v; }

export {
  // Data Sources
  listDataSources,
  uploadDataSource,
  getDataSource,
  deleteDataSource,
  parseDataSource,
  indexDataSource,
  getDataSourceStatus,
  getDataSourceProfile,
  getDataSourceChunks,
  getDataSourcePreview,
  searchEvidence,
  // Verification
  verifyClaim,
  verifyExecutionClaims,
  verifyWorkspaceClaims,
  getClaimVerification,
  getExecutionVerificationSummary,
  getWorkspaceVerificationSummary,
  scanWorkspaceContradictions,
  listWorkspaceContradictions,
  listClaimContradictions,
  generateTrustReport,
  getReport,
  exportReport,
  getReportMarkdown,
  getBaseUrl,
  _setMockOverride,
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
  listProviders,
  createProvider,
  deleteProvider,
  checkProvider,
  setDefaultProvider,
  updateProvider,
  listReviews,
  resolveReview,
  listExecutionHistory,
  getExecutionDetail,
  deleteExecutionHistory,
  listWorkflowVersions,
  getWorkflowVersion,
  streamReplayEvents,
  // Workspaces
  listWorkspaces,
  getWorkspaceStatus,
  createWorkspace,
  activateWorkspace,
  getActiveWorkspaceId,
};
