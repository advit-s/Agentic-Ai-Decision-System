// api.js — HTTP + WebSocket client with mock data fallback

import {
  MOCK_IDENTITY,
  MOCK_USERS,
  MOCK_MEMBERSHIPS,
  MOCK_SECURITY_SETTINGS,
  MOCK_PERMISSION_MATRIX,
  MOCK_AUDIT_EVENTS,
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

// ---------------------------------------------------------------------------
// Connector API (v1.28 read-only connector framework)
// ---------------------------------------------------------------------------

function listConnectorDefinitions() {
  return apiFetch("/connectors");
}

function getConnectorDefinition(connectorId) {
  return apiFetch(`/connectors/${connectorId}`);
}

function listConnectorSchemas() {
  return apiFetch("/connectors/schemas");
}

function getConnectorSchema(connectorId) {
  return apiFetch(`/connectors/${connectorId}/schema`);
}

function getConnectorCredentialStatus(connectorId) {
  return apiFetch(`/connectors/${connectorId}/credential-status`);
}

function listConnectorConfigs(workspaceId) {
  return apiFetch(`/workspaces/${workspaceId}/connectors`);
}

function createConnectorConfig(workspaceId, data) {
  return apiFetch(`/workspaces/${workspaceId}/connectors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

function getConnectorConfig(workspaceId, connectorId) {
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}`);
}

function updateConnectorConfig(workspaceId, connectorId, data) {
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

function deleteConnectorConfig(workspaceId, connectorId) {
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}`, {
    method: "DELETE",
  });
}

function testConnector(workspaceId, connectorId) {
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/test`, {
    method: "POST",
  });
}

function listConnectorItems(workspaceId, connectorId, path = "") {
  const params = path ? `?path=${encodeURIComponent(path)}` : "";
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/items${params}`);
}

function importConnectorItems(workspaceId, connectorId, itemIds = null) {
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

function listConnectorJobs(workspaceId) {
  return apiFetch(`/workspaces/${workspaceId}/connector-jobs`);
}

function getConnectorJob(workspaceId, jobId) {
  return apiFetch(`/workspaces/${workspaceId}/connector-jobs/${jobId}`);
}

/** Exposed for test use only — overrides mock mode detection */
function _setMockOverride(v) { _testMockOverride = v; }

export {
  getSystemStatus,
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
  // Connectors
  listConnectorDefinitions,
  getConnectorDefinition,
  listConnectorSchemas,
  getConnectorSchema,
  getConnectorCredentialStatus,
  listConnectorConfigs,
  createConnectorConfig,
  getConnectorConfig,
  updateConnectorConfig,
  deleteConnectorConfig,
  testConnector,
  listConnectorItems,
  importConnectorItems,
  listConnectorJobs,
  getConnectorJob,
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
  // Graph
  extractGraph,
  getGraph,
  listGraphNodes,
  listGraphRisks,
  listGraphMetrics,
  getGraphSummary,
  getGraphRuns,
  getGraphRun,
  getLatestExtraction,
  getGraphAuditEvents,
  getGraphMetricsAggregates,
  getEvidencePreview,
  // Identity & Security
  getCurrentIdentity,
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listWorkspaceMemberships,
  createWorkspaceMembership,
  updateWorkspaceMembership,
  deleteWorkspaceMembership,
  getSecuritySettings,
  updateSecuritySettings,
  getPermissionMatrix,
  getWorkspaceAuditEvents,
  getWorkspaceAuditSummary,
};

// --- Graph Extraction ---

async function extractGraph(workspaceId, texts) {
  if (isMockMode()) {
    return {
      workspace_id: workspaceId,
      nodes_extracted: texts.length > 0 ? (texts[0].text ? texts[0].text.split(/\s+/).length : 0) : 0,
      edges_extracted: 0,
      risks_extracted: 0,
      metrics_extracted: 0,
      warnings: [],
    };
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/extract`, {
    method: "POST",
    body: JSON.stringify({ texts }),
  });
}

async function getGraph(workspaceId) {
  if (isMockMode()) {
    return { workspace_id: workspaceId, nodes: [], edges: [] };
  }
  return apiFetch(`/workspaces/${workspaceId}/graph`);
}

async function listGraphNodes(workspaceId, nodeType) {
  if (isMockMode()) {
    return [];
  }
  const params = nodeType ? `?node_type=${encodeURIComponent(nodeType)}` : "";
  return apiFetch(`/workspaces/${workspaceId}/graph/nodes${params}`);
}

async function listGraphRisks(workspaceId, severity, category) {
  if (isMockMode()) {
    return [];
  }
  const params = new URLSearchParams();
  if (severity) params.set("severity", severity);
  if (category) params.set("category", category);
  const qs = params.toString();
  return apiFetch(`/workspaces/${workspaceId}/graph/risks${qs ? "?" + qs : ""}`);
}

async function listGraphMetrics(workspaceId) {
  if (isMockMode()) {
    return [];
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/metrics`);
}

async function getGraphSummary(workspaceId) {
  if (isMockMode()) {
    return { workspace_id: workspaceId, node_count: 0, edge_count: 0, risk_count: 0, metric_count: 0 };
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/summary`);
}

async function getGraphRuns(workspaceId, limit = 50) {
  if (isMockMode()) {
    return { workspace_id: workspaceId, runs: [], total_count: 0 };
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/extraction-runs?limit=${limit}`);
}

async function getGraphRun(workspaceId, runId) {
  if (isMockMode()) {
    return null;
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/extraction-runs/${runId}`);
}

async function getLatestExtraction(workspaceId) {
  if (isMockMode()) {
    return null;
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/latest-extraction`);
}

async function getGraphAuditEvents(workspaceId, eventType, limit = 100) {
  if (isMockMode()) {
    return { workspace_id: workspaceId, events: [], total_count: 0 };
  }
  const params = new URLSearchParams();
  if (eventType) params.set("event_type", eventType);
  params.set("limit", String(limit));
  return apiFetch(`/workspaces/${workspaceId}/graph/audit-events?${params.toString()}`);
}

async function getGraphMetricsAggregates(workspaceId) {
  if (isMockMode()) {
    return { workspace_id: workspaceId, metrics: {}, last_extraction_at: null };
  }
  return apiFetch(`/workspaces/${workspaceId}/graph/metrics/aggregates`);
}

async function getEvidencePreview(workspaceId, evidenceId) {
  if (isMockMode()) {
    return null;
  }
  return apiFetch(`/workspaces/${workspaceId}/evidence/${evidenceId}`);
}


// --- Identity & Security API methods ---

let _mockIdentityUsers = null;
let _mockIdentityMemberships = null;
let _mockIdentitySettings = null;

function _getIdentityData() {
  if (!_mockIdentityUsers) {
    _mockIdentityUsers = JSON.parse(JSON.stringify(MOCK_USERS));
    _mockIdentityMemberships = JSON.parse(JSON.stringify(MOCK_MEMBERSHIPS));
    _mockIdentitySettings = JSON.parse(JSON.stringify(MOCK_SECURITY_SETTINGS));
  }
  return { users: _mockIdentityUsers, memberships: _mockIdentityMemberships, settings: _mockIdentitySettings };
}

async function getCurrentIdentity() {
  if (isMockMode()) {
    return Promise.resolve(JSON.parse(JSON.stringify(MOCK_IDENTITY)));
  }
  return apiFetch("/identity/me");
}

async function listUsers() {
  if (isMockMode()) {
    return Promise.resolve(JSON.parse(JSON.stringify([..._getIdentityData().users])));
  }
  return apiFetch("/identity/users");
}

async function createUser(displayName, role = "viewer", metadata = {}) {
  if (isMockMode()) {
    const user = {
      user_id: "user-" + Date.now(),
      display_name: displayName,
      role,
      created_at: new Date().toISOString(),
      metadata,
    };
    _getIdentityData().users.push(user);
    return Promise.resolve(JSON.parse(JSON.stringify(user)));
  }
  return apiFetch("/identity/users", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, role, metadata }),
  });
}

async function updateUser(userId, updates) {
  if (isMockMode()) {
    const data = _getIdentityData();
    const idx = data.users.findIndex((u) => u.user_id === userId);
    if (idx < 0) return Promise.reject(new Error("User not found"));
    Object.assign(data.users[idx], updates);
    return Promise.resolve(JSON.parse(JSON.stringify(data.users[idx])));
  }
  return apiFetch(`/identity/users/${userId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

async function deleteUser(userId) {
  if (isMockMode()) {
    if (userId === "local/system") return Promise.reject(new Error("Cannot delete the default local user"));
    _getIdentityData().users = _getIdentityData().users.filter((u) => u.user_id !== userId);
    return Promise.resolve({ status: "deleted", user_id: userId });
  }
  return apiFetch(`/identity/users/${userId}`, { method: "DELETE" });
}

async function listWorkspaceMemberships(workspaceId) {
  if (isMockMode()) {
    return Promise.resolve(JSON.parse(JSON.stringify(_getIdentityData().memberships[workspaceId] || [])));
  }
  return apiFetch(`/workspaces/${workspaceId}/memberships`);
}

async function createWorkspaceMembership(workspaceId, userId, role = "viewer") {
  if (isMockMode()) {
    const data = _getIdentityData();
    if (!data.memberships[workspaceId]) data.memberships[workspaceId] = [];
    const m = { workspace_id: workspaceId, user_id: userId, role, joined_at: new Date().toISOString() };
    data.memberships[workspaceId].push(m);
    return Promise.resolve(JSON.parse(JSON.stringify(m)));
  }
  return apiFetch(`/workspaces/${workspaceId}/memberships`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId, role }),
  });
}

async function updateWorkspaceMembership(workspaceId, userId, role) {
  if (isMockMode()) {
    const data = _getIdentityData();
    const list = data.memberships[workspaceId] || [];
    const m = list.find((x) => x.user_id === userId);
    if (!m) return Promise.reject(new Error("Membership not found"));
    m.role = role;
    return Promise.resolve(JSON.parse(JSON.stringify(m)));
  }
  return apiFetch(`/workspaces/${workspaceId}/memberships/${userId}`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

async function deleteWorkspaceMembership(workspaceId, userId) {
  if (isMockMode()) {
    const data = _getIdentityData();
    if (data.memberships[workspaceId]) {
      data.memberships[workspaceId] = data.memberships[workspaceId].filter((x) => x.user_id !== userId);
    }
    return Promise.resolve({ status: "removed", workspace_id: workspaceId, user_id: userId });
  }
  return apiFetch(`/workspaces/${workspaceId}/memberships/${userId}`, { method: "DELETE" });
}

async function getSecuritySettings() {
  if (isMockMode()) {
    return Promise.resolve(JSON.parse(JSON.stringify(_getIdentityData().settings)));
  }
  return apiFetch("/identity/settings");
}

async function updateSecuritySettings(updates) {
  if (isMockMode()) {
    Object.assign(_getIdentityData().settings, updates);
    return Promise.resolve(JSON.parse(JSON.stringify(_getIdentityData().settings)));
  }
  return apiFetch("/identity/settings", {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

async function getPermissionMatrix() {
  if (isMockMode()) {
    return Promise.resolve(JSON.parse(JSON.stringify(MOCK_PERMISSION_MATRIX)));
  }
  return apiFetch("/identity/permissions");
}

async function getWorkspaceAuditEvents(workspaceId, filters = {}) {
  if (isMockMode()) {
    let events = JSON.parse(JSON.stringify(MOCK_AUDIT_EVENTS));
    if (filters.event_type) events = events.filter((e) => e.event_type === filters.event_type);
    if (filters.actor) events = events.filter((e) => e.actor === filters.actor);
    return Promise.resolve({ events, total: events.length, offset: 0, limit: 100 });
  }
  const params = new URLSearchParams();
  if (filters.event_type) params.set("event_type", filters.event_type);
  if (filters.actor) params.set("actor", filters.actor);
  if (filters.artifact_type) params.set("artifact_type", filters.artifact_type);
  if (filters.artifact_id) params.set("artifact_id", filters.artifact_id);
  if (filters.limit) params.set("limit", String(filters.limit));
  if (filters.offset) params.set("offset", String(filters.offset));
  const qs = params.toString();
  return apiFetch(`/workspaces/${workspaceId}/audit/events${qs ? "?" + qs : ""}`);
}

async function getWorkspaceAuditSummary(workspaceId) {
  if (isMockMode()) {
    const events = JSON.parse(JSON.stringify(MOCK_AUDIT_EVENTS));
    const byType = {};
    const byActor = {};
    events.forEach((e) => {
      byType[e.event_type] = (byType[e.event_type] || 0) + 1;
      byActor[e.actor] = (byActor[e.actor] || 0) + 1;
    });
    return Promise.resolve({
      total_events: events.length,
      by_type: byType,
      by_actor: byActor,
    });
  }
  return apiFetch(`/workspaces/${workspaceId}/audit/summary`);
}

// ---------------------------------------------------------------------------
// v1.29 Connector sync API
// ---------------------------------------------------------------------------

export async function triggerConnectorSync(workspaceId, connectorId) {
  if (isMockMode()) {
    return { result: { status: "completed", items_new: 3, items_changed: 1, items_unchanged: 5, items_failed: 0, items_deleted_remote: 0, duration_ms: 1234, job_id: "mock-sync-job-001", error: null } };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync`, { method: "POST" });
}

export async function getConnectorSyncState(workspaceId, connectorId) {
  if (isMockMode()) {
    const mockState = [
      { sync_state_id: "s1", external_id: "doc1", content_hash: "abc123", status: "unchanged", last_seen_at: new Date().toISOString(), last_imported_at: new Date().toISOString() },
      { sync_state_id: "s2", external_id: "doc2", content_hash: "def456", status: "new", last_seen_at: new Date().toISOString() },
      { sync_state_id: "s3", external_id: "doc3", content_hash: "ghi789", status: "changed", last_seen_at: new Date().toISOString(), last_imported_at: new Date().toISOString() },
    ];
    return { sync_state: mockState, count: mockState.length };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-state`);
}

export async function listSyncSchedules(workspaceId, connectorId) {
  if (isMockMode()) {
    return { schedules: [], count: 0 };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-schedules`);
}

export async function createSyncSchedule(workspaceId, connectorId, data) {
  if (isMockMode()) {
    return { schedule: { schedule_id: "mock-schedule-1", ...data, workspace_id: workspaceId, connector_id: connectorId, created_at: new Date().toISOString(), updated_at: new Date().toISOString() } };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-schedules`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateSyncSchedule(workspaceId, connectorId, scheduleId, data) {
  if (isMockMode()) {
    return { schedule: { schedule_id: scheduleId, ...data } };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-schedules/${scheduleId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteSyncSchedule(workspaceId, connectorId, scheduleId) {
  if (isMockMode()) {
    return { status: "deleted", schedule_id: scheduleId };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-schedules/${scheduleId}`, {
    method: "DELETE",
  });
}

export async function toggleSyncSchedule(workspaceId, connectorId, scheduleId) {
  if (isMockMode()) {
    return { schedule: { schedule_id: scheduleId, enabled: true } };
  }
  return apiFetch(`/workspaces/${workspaceId}/connectors/${connectorId}/sync-schedules/${scheduleId}/toggle`, {
    method: "POST",
  });
}

export async function runDueSyncSchedules() {
  if (isMockMode()) {
    return { results: [], count: 0 };
  }
  return apiFetch("/connector-sync/run-due", { method: "POST" });
}
// --- System Status (v1.32 beta packaging) ---

async function getSystemStatus() {
  if (isMockMode()) {
    return Promise.resolve({
      version: "1.33.0-dev",
      data_dir: ".decision_system",
      security_mode: "demo",
      provider_type: "fake",
      provider_count: 0,
      connector_count: 5,
      workspace_count: 1,
      demo_data_available: true,
      ocr_available: false,
      doc_parsing_available: false,
      warnings: ["Mock mode — system status is simulated."],
    });
  }
  return apiFetch("/system/status");
}
