/* ── v1.7 Company Intelligence Engine Web UI ── */

const API_STORAGE_KEY = "decisionSystemApiBaseUrl";

/* =========================================================================
   Data sources: API paths + mock fallback paths for every section
   ========================================================================= */
const DATASETS = {
  dashboard:  { apiPath: "/dashboard",               mockPath: "mock-data/dashboard.json" },
  report:     { apiPath: "/reports/latest",           mockPath: "mock-data/report.json" },
  insights:   { apiPath: "/insights",                 mockPath: "mock-data/insights.json" },
  ontology:   { apiPath: "/ontology",                 mockPath: "mock-data/ontology.json" },
  warRoom:    { apiPath: "/war-room/latest",          mockPath: "mock-data/war-room.json" },
  dataProfiles: { apiPath: "/data-profiles",          mockPath: "mock-data/data-profiles.json" },
  graph:      { apiPath: "/graph",                    mockPath: "mock-data/graph.json" },
  security:   { apiPath: "/security/policy",          mockPath: "mock-data/security.json" },
  connector:  { apiPath: "/connectors",               mockPath: "mock-data/connectors.json" },
  observability: { apiPath: "/observability/metrics", mockPath: "mock-data/observability.json" },
  enterprise: { apiPath: "/enterprise-readiness",     mockPath: "mock-data/enterprise-readiness.json" },
};

const FALLBACK_DATA = {
  report: {
    question: "Where are we losing money?",
    generated_at: "2026-06-09T00:00:00Z",
    confidence: "medium",
    recommendation: "Review revenue concentration, refunds, and migration risk before committing spend.",
    markdown: "# Mock Decision Report\n\n## Recommendation\nUse the mock data path until a backend API is configured.\n\n## Evidence\n- Local fixtures are available under `web/mock-data/`.\n- Fake provider mode remains the default.\n",
    citations: ["mock-report"],
  },
  insights: { insights: [] },
  ontology: { mappings: [] },
  warRoom: { roles: [], artifacts: [], judge_interventions: [] },
  dataProfiles: { profiles: [] },
  graph: { entities: [], relationships: [] },
  security: { policy: { checks: [] }, approval_requests: [], audit_events: [] },
  connector: { connectors: [], jobs: [] },
  observability: { metrics: {}, metric_count: 0, eval_runs: [], eval_count: 0, quality_reports: [], quality_count: 0, traces: [], trace_count: 0 },
  enterprise: { version: "1.8.0", readiness_level: "prototype-ready", passed_count: 0, missing_count: 0, passed_items: [], missing_items: [] },
};

/* =========================================================================
   State
   ========================================================================= */
const state = {
  apiBaseUrl: localStorage.getItem(API_STORAGE_KEY) || "",
  source: "mock",
  data: {},
  connectors: { connectors: [], jobs: [] },
};

/* =========================================================================
   Helpers
   ========================================================================= */
const el = (id) => document.getElementById(id);
const safe = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

function joinUrl(base, path) {
  return `${base.replace(/\/+$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

/* =========================================================================
   Data loading
   ========================================================================= */
async function loadDataset(key, config, apiBaseUrl) {
  if (apiBaseUrl) {
    try {
      const payload = await fetchJson(joinUrl(apiBaseUrl, config.apiPath));
      return { payload, source: "api" };
    } catch (_) { /* fall through to mock */ }
  }
  try {
    const payload = await fetchJson(config.mockPath);
    return { payload, source: "mock" };
  } catch (_) {
    return { payload: structuredClone(FALLBACK_DATA[key] || {}), source: "fallback" };
  }
}

async function loadAllData() {
  const apiBaseUrl = state.apiBaseUrl.trim();
  const entries = await Promise.all(
    Object.entries(DATASETS).map(async ([key, config]) => {
      const result = await loadDataset(key, config, apiBaseUrl);
      return [key, result];
    })
  );

  let source = apiBaseUrl ? "api" : "mock";
  for (const [key, result] of entries) {
    state.data[key] = result.payload || structuredClone(FALLBACK_DATA[key] || {});
    if (result.source !== "api") source = result.source;
  }
  state.source = source;
  renderAll();
}

/* ── Load connectors separately (different path registry) ── */
async function loadConnectorsData() {
  const apiBaseUrl = state.apiBaseUrl.trim();
  if (apiBaseUrl) {
    try {
      const payload = await fetchJson(joinUrl(apiBaseUrl, "/connectors"));
      state.connectors = payload;
      return;
    } catch (_) { /* fall through */ }
  }
  try {
    const payload = await fetchJson("mock-data/connectors.json");
    state.connectors = payload;
  } catch (_) {
    state.connectors = { connectors: FALLBACK_DATA.connector.connectors, jobs: [] };
  }
}

/* =========================================================================
   Markdown renderer
   ========================================================================= */
function renderMarkdown(markdown) {
  const lines = String(markdown ?? "").split(/\r?\n/);
  const html = [];
  let inList = false;
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) { if (inList) { html.push("</ul>"); inList = false; } continue; }
    if (line.startsWith("### ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<h3>${inlineMd(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<h2>${inlineMd(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<h1>${inlineMd(line.slice(2))}</h1>`);
    } else if (line.startsWith("- ")) {
      if (!inList) { html.push("<ul>"); inList = true; }
      html.push(`<li>${inlineMd(line.slice(2))}</li>`);
    } else {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push(`<p>${inlineMd(line)}</p>`);
    }
  }
  if (inList) html.push("</ul>");
  return html.join("");
}

function inlineMd(value) {
  return safe(value).replace(/`([^`]+)`/g, "<code>$1</code>");
}

/* =========================================================================
   Renderers — one per section
   ========================================================================= */

function renderConnection() {
  const mode = state.source === "api" ? "API" : state.source === "fallback" ? "Fallback" : "Mock-first";
  el("connectionMode").textContent = mode;
  el("dataSourceStatus").textContent = state.apiBaseUrl
    ? `Configured: ${state.apiBaseUrl}`
    : "Using mock data";
}

/* ── 1. Dashboard ── */
function renderDashboard() {
  const d = state.data.dashboard || {};
  const profiles = state.data.dataProfiles?.profiles || [];
  const insights = state.data.insights?.insights || [];
  const graph = state.data.graph || {};
  const connectors = state.connectors.connectors || [];

  el("dashboardVersion").textContent = `v${d.version || "1.8.0"}`;

  // Readiness
  const ready = d.system_ready !== false;
  el("readinessStatus").innerHTML = `<span class="status-indicator ${ready ? 'ok' : 'warn'}">&#9679;</span> <span>${ready ? 'Prototype ready' : 'Setup required'}</span>`;
  el("providerName").textContent = d.provider || "fake";
  el("indexStatus").textContent = d.index_status === "indexed" ? "Indexed" : "Not indexed";
  el("wsStatus").textContent = d.workspace_status === "ok" ? "Active workspace" : "No active workspace";

  // Metrics
  el("dashProfiles").textContent = profiles.length;
  el("dashInsights").textContent = insights.length;
  el("dashEntities").textContent = graph.entities?.length || 0;
  el("dashRelationships").textContent = graph.relationships?.length || 0;
  el("dashConnectors").textContent = connectors.length;
  el("dashWarRooms").textContent = d.war_room_runs || 0;

  // Quick links
  const links = d.quick_links || [
    { label: "Decision Brief", icon: "Q", section: "ask" },
    { label: "Data & Ontology", icon: "D", section: "data" },
    { label: "War Room", icon: "W", section: "war-room" },
    { label: "Security", icon: "S", section: "security" },
  ];
  const icons = { document: "D", question: "Q", "war-room": "W", security: "S" };
  el("quickLinks").innerHTML = links.map(link => {
    const ic = link.icon || icons[link.icon] || "•";
    return `<button class="quick-link" data-section="${link.section}"><span class="quick-link-icon">${ic}</span> ${safe(link.label)}</button>`;
  }).join("");
  document.querySelectorAll(".quick-link").forEach(btn => {
    btn.addEventListener("click", () => navigateTo(btn.dataset.section));
  });
}

/* ── 2. Ask / Decision Brief ── */
function renderAskResponse(markdown, mode) {
  el("answerMode").textContent = mode || state.source;
  el("askResponse").innerHTML = renderMarkdown(markdown || "# Response\n\nAsk a business question to see the decision brief.");

  // Try to show claim summary from report data
  const report = state.data.report;
  if (report && report.claims && report.claims.length) {
    el("claimSummary").style.display = "block";
    el("claimPills").innerHTML = report.claims.map(c =>
      `<span class="claim-pill ${(c.status || 'pending').toLowerCase()}">${safe(c.status || 'pending')}: ${safe(c.text || '').slice(0, 60)}</span>`
    ).join("");
  } else {
    el("claimSummary").style.display = "none";
  }
}

/* ── 3. Data & Ontology ── */
function renderProfiles() {
  const profiles = state.data.dataProfiles?.profiles || [];
  el("profileSummary").textContent = `${profiles.length} profiles`;
  el("profileGrid").innerHTML = profiles.length
    ? profiles.map(p => `
        <article class="profile-card">
          <h5>${safe(p.dataset)}</h5>
          <div class="meta-line">${safe(p.category)} | ${p.row_count} rows | ${p.column_count} columns</div>
          <div class="pill-row">${(p.columns || []).slice(0, 8).map(c => `<span class="pill">${safe(c)}</span>`).join("")}</div>
          ${(p.warnings || []).map(w => `<p class="small-muted">${safe(w)}</p>`).join("")}
        </article>`).join("")
    : `<p class="empty-state">No data profiles yet. Run <code>decision-system init-data-catalog</code> and <code>decision-system profile-data</code>.</p>`;
}

function renderOntology() {
  const mappings = state.data.ontology?.mappings || [];
  el("ontologySummary").textContent = `${mappings.length} mappings`;
  el("ontologyRows").innerHTML = mappings.length
    ? mappings.map(m => `
        <tr>
          <td>${safe(m.dataset)}</td>
          <td><code>${safe(m.column)}</code></td>
          <td>${safe(m.concept_name)}<div class="small-muted">${safe(m.concept_id)}</div></td>
          <td>${safe(m.concept_type)}</td>
          <td>${safe(m.confidence)}</td>
        </tr>`).join("")
    : `<tr><td colspan="5"><p class="empty-state">No ontology mappings yet. Run <code>decision-system map-ontology</code>.</p></td></tr>`;
}

function renderInsights() {
  const groups = {};
  for (const item of state.data.insights?.insights || []) {
    const s = (item.severity || "unknown").toLowerCase();
    (groups[s] = groups[s] || []).push(item);
  }
  const order = ["critical", "high", "medium", "low", "unknown"];
  el("insightGroups").innerHTML = order
    .filter(s => groups[s]?.length)
    .map(s => {
      const cards = groups[s].map(item => `
        <article class="insight-card ${safe(s)}">
          <h5>${safe(item.title)}</h5>
          <div class="meta-line">${safe(item.category)} | confidence ${safe(item.confidence)}</div>
          <p>${safe(item.summary)}</p>
          <div class="pill-row">${(item.evidence_refs || []).map(ref => `<span class="pill">${safe(ref)}</span>`).join("")}</div>
        </article>`).join("");
      return `<div class="severity-group"><h4 class="severity-heading">${safe(s)} (${groups[s].length})</h4>${cards}</div>`;
    }).join("") || `<p class="empty-state">No insights detected yet. Run <code>decision-system detect-patterns</code>.</p>`;
}

function renderGraph() {
  const graph = state.data.graph || {};
  el("graphSummary").textContent = `${graph.entities?.length || 0} entities | ${graph.relationships?.length || 0} links`;
  el("graphEntities").innerHTML = (graph.entities || []).length
    ? graph.entities.map(e => `
        <div class="compact-item">
          <strong>${safe(e.name)}</strong>
          <span class="small-muted">${safe(e.type)} | degree ${e.degree ?? 0}</span>
        </div>`).join("")
    : `<p class="empty-state">No entities extracted yet. Run <code>decision-system extract-graph</code>.</p>`;
  el("graphRelationships").innerHTML = (graph.relationships || []).length
    ? graph.relationships.map(r => `
        <div class="compact-item">
          <strong>${safe(r.source)} &rarr; ${safe(r.target)}</strong>
          <span class="small-muted">${safe(r.type)} | ${safe(r.evidence_id || "")}</span>
        </div>`).join("")
    : `<p class="empty-state">No relationships extracted yet.</p>`;
}

/* ── 4. War Room ── */
function renderWarRoom() {
  const run = state.data.warRoom || {};
  el("warRoomSummary").textContent = `${run.roles?.length || 0} roles | ${run.artifacts?.length || 0} artifacts`;
  el("warRoomRoles").innerHTML = (run.roles || []).length
    ? run.roles.map(r => `
        <div class="compact-item">
          <strong>${safe(r.name)}</strong>
          <span class="small-muted">${safe(r.objective)}</span>
          <div class="pill-row">${(r.allowed_tools || []).map(t => `<span class="pill">${safe(t)}</span>`).join("")}</div>
        </div>`).join("")
    : `<p class="empty-state">No war-room runs yet. Run <code>decision-system run-war-room</code>.</p>`;
  el("judgeInterventions").innerHTML = (run.judge_interventions || []).length
    ? run.judge_interventions.map(j => `
        <div class="compact-item">
          <strong>${safe(j.severity)}: ${safe(j.rule)}</strong>
          <span>${safe(j.message)}</span>
          <span class="small-muted">Human review: ${j.human_review_required ? "yes" : "no"}</span>
        </div>`).join("")
    : `<p class="empty-state">No judge interventions.</p>`;
  el("warRoomArtifacts").innerHTML = (run.artifacts || []).length
    ? run.artifacts.map(a => `
        <article class="artifact-card">
          <h5>${safe(a.title)}</h5>
          <div class="meta-line">${safe(a.role)} | ${safe(a.artifact_type)} | confidence ${safe(a.confidence)}</div>
          <p>${safe(a.summary)}</p>
          <div class="pill-row">${(a.evidence_refs || []).map(ref => `<span class="pill">${safe(ref)}</span>`).join("")}</div>
        </article>`).join("")
    : `<p class="empty-state">No artifacts yet.</p>`;
}

/* ── 5. Workspaces ── */
function renderWorkspaces() {
  // Try API first
  const apiBaseUrl = state.apiBaseUrl.trim();
  if (apiBaseUrl) {
    fetchJson(joinUrl(apiBaseUrl, "/workspaces/status"))
      .then(payload => {
        const ws = payload.workspace;
        if (ws) {
          el("wsActiveName").textContent = safe(ws.name);
          el("wsArtifactCount").textContent = Object.values(payload.artifact_counts || {}).reduce((a, b) => a + b, 0);
          el("wsDbPath").textContent = safe(payload.database_path || "");
          el("wsArtifactTypes").innerHTML = Object.entries(payload.artifact_counts || {})
            .map(([type, count]) => `<div class="compact-item"><strong>${safe(type)}</strong><span class="small-muted">${count} artifacts</span></div>`)
            .join("") || `<p class="empty-state">No artifacts</p>`;
        }
      })
      .catch(() => { /* keep mock state */ });
  }
  // Keep showing mock-state placeholder
  if (el("wsActiveName").textContent === "-") {
    el("wsActiveName").textContent = "Not initialized";
  }
}

/* ── 6. Connectors ── */
async function renderConnectors() {
  await loadConnectorsData();
  const connectors = state.connectors.connectors || [];
  const jobs = state.connectors.jobs || [];

  el("connectorGrid").innerHTML = connectors.length
    ? connectors.map(c => `
        <div class="connector-card ${c.is_stub ? 'stub' : 'real'}">
          <div class="connector-type">${safe(c.connector_type)}</div>
          <h5>${safe(c.name)}</h5>
          <p>${safe(c.description)}</p>
          <div class="pill-row">
            ${(c.capabilities || []).map(cap => `<span class="pill">${safe(cap)}</span>`).join("")}
          </div>
          <span class="connector-badge ${c.is_stub ? 'stub' : 'real'}">${c.is_stub ? 'Offline stub' : 'Real connector'}</span>
          ${c.requires_secrets ? '<span class="small-muted" style="margin-left:8px">Requires secrets — not implemented</span>' : ''}
        </div>`).join("")
    : `<p class="empty-state">No connectors registered.</p>`;

  el("connectorJobs").innerHTML = jobs.length
    ? jobs.map(j => `<div class="compact-item"><strong>${safe(j.connector_id || 'unknown')}</strong><span class="small-muted">${safe(j.status || '')}</span></div>`).join("")
    : `<p class="empty-state">No connector jobs yet</p>`;
}

/* ── 7. Security ── */
function renderSecurity() {
  const sec = state.data.security || {};
  const policy = sec.policy || {};
  const checks = (policy.checks || []).slice(0, 8);
  el("securityPolicyStatus").innerHTML = checks.length
    ? checks.map(c => {
        const cls = c.passed ? "status-pass" : "status-fail";
        return `<div class="compact-item"><strong class="${cls}">${safe(c.name)}</strong><span class="small-muted">${safe(c.message || "")}</span></div>`;
      }).join("")
    : `<p class="empty-state">No policy data</p>`;
  el("securityAuditLog").innerHTML = (sec.audit_events || []).length
    ? sec.audit_events.slice(0, 5).map(ev =>
        `<div class="compact-item"><strong>${safe(ev.event_type)}</strong><span class="small-muted">${ev.created_at ? new Date(ev.created_at).toLocaleString() : ""}</span>${ev.message ? `<div>${safe(ev.message)}</div>` : ""}</div>`
      ).join("")
    : `<p class="empty-state">No audit events</p>`;
  el("securityApprovals").innerHTML = (sec.approval_requests || []).length
    ? sec.approval_requests.slice(0, 5).map(r => {
        const cls = r.status === "approved" ? "status-pass" : r.status === "rejected" ? "status-fail" : "";
        return `<div class="compact-item"><strong class="${cls}">#${safe(r.approval_id || r.id || "?")}</strong><span>${safe(r.reason || r.message || "")}</span><span class="small-muted">${safe(r.status || "pending")}</span></div>`;
      }).join("")
    : `<p class="empty-state">No approval requests yet</p>`;
}

/* ── 8. Observability ── */
function renderObservability() {
  const obs = state.data.observability || {};

  // Metrics
  const mCount = obs.metric_count || Object.keys(obs.metrics || {}).length;
  el("obsMetrics").innerHTML = mCount > 0
    ? `<div class="compact-list">${Object.entries(obs.metrics || {}).map(([name, data]) =>
        `<div class="compact-item"><strong>${safe(name)}</strong><span class="small-muted">${data.summary ? `${data.summary.count} points, last: ${data.summary.last_value || ''}` : 'no summary'}</span></div>`
      ).join("")}</div>`
    : `<p class="empty-state">No metrics recorded yet. Run <code>decision-system metrics</code>.</p>`;

  // Eval history
  const evals = obs.eval_runs || [];
  el("obsEvalHistory").innerHTML = evals.length
    ? `<div class="compact-list">${evals.slice(0, 5).map(e =>
        `<div class="compact-item"><strong>${safe(e.eval_type || e.type || 'eval')}</strong><span class="small-muted">${e.passed || 0}/${e.total || 0} passed</span></div>`
      ).join("")}</div>`
    : `<p class="empty-state">No eval runs recorded yet. Run <code>decision-system eval-history</code>.</p>`;

  // Quality reports
  const reports = obs.quality_reports || [];
  el("obsQualityReports").innerHTML = reports.length
    ? `<div class="compact-list">${reports.slice(0, 5).map(r =>
        `<div class="compact-item"><strong>${safe(r.target || r.name || 'report')}</strong><span class="small-muted">Score: ${r.score || r.overall_score || 'N/A'}</span></div>`
      ).join("")}</div>`
    : `<p class="empty-state">No quality reports yet. Run <code>decision-system quality-report</code>.</p>`;

  // Traces
  const traces = obs.traces || [];
  el("obsTraces").innerHTML = traces.length
    ? `<div class="compact-list">${traces.slice(0, 5).map(t =>
        `<div class="compact-item"><strong>${safe(t.workflow_type || t.type || 'workflow')}</strong><span class="small-muted">${t.duration ? `${t.duration.toFixed(2)}s` : ''} | ${t.node_count || 0} nodes</span></div>`
      ).join("")}</div>`
    : `<p class="empty-state">No traces recorded yet. Run <code>decision-system trace-summary</code>.</p>`;
}

/* ── 9. Enterprise Readiness ── */
function renderEnterprise() {
  const ent = state.data.enterprise || {};
  el("enterpriseVersion").textContent = `v${ent.version || "1.8.0"}`;
  const level = ent.readiness_level || "prototype-ready";
  el("readinessLevel").innerHTML = `<span class="level-badge ${level === 'prototype-ready' ? 'prototype' : level === 'enterprise-ready' ? 'enterprise' : 'production'}">${level === 'prototype-ready' ? 'Prototype Ready' : level === 'enterprise-ready' ? 'Enterprise Ready' : 'Production Ready'}</span>`;
  el("entPassed").textContent = ent.passed_count || 0;
  el("entMissing").textContent = ent.missing_count || 0;
  el("entPassedList").innerHTML = (ent.passed_items || []).length
    ? ent.passed_items.map(item => `<div class="compact-item"><strong class="status-pass">${safe(item)}</strong></div>`).join("")
    : `<p class="empty-state">No data</p>`;
  el("entMissingList").innerHTML = (ent.missing_items || []).length
    ? ent.missing_items.map(item =>
        `<div class="compact-item"><strong class="status-fail">${safe(item.gap)}</strong><span class="small-muted">${safe(item.severity)} — ${safe(item.notes)}</span></div>`
      ).join("")
    : `<p class="empty-state">No gaps identified</p>`;
}

/* =========================================================================
   Data tab switching (Data & Ontology)
   ========================================================================= */
function bindDataTabs() {
  document.querySelectorAll(".data-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".data-tab").forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".data-panel").forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const panel = el(`tab-${tab.dataset.tab}`);
      if (panel) panel.classList.add("active");
    });
  });
}

/* =========================================================================
   Navigation
   ========================================================================= */
function navigateTo(sectionId) {
  document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
  document.querySelectorAll(".view").forEach(view => view.classList.remove("active-view"));
  const navBtn = document.querySelector(`.nav-item[data-view="${sectionId}"]`);
  if (navBtn) navBtn.classList.add("active");
  const view = el(sectionId);
  if (view) view.classList.add("active-view");
  // Update title
  const sectionNames = {
    dashboard: "Dashboard", ask: "Decision Brief", data: "Data & Ontology",
    "war-room": "War Room", workspaces: "Workspaces", connectors: "Connectors",
    security: "Security & Governance", observability: "Observability", enterprise: "Enterprise Readiness",
  };
  el("appTitle").textContent = sectionNames[sectionId] || sectionId;
}

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach(button => {
    button.addEventListener("click", () => {
      navigateTo(button.dataset.view);
    });
  });
}

/* =========================================================================
   Ask form submission
   ========================================================================= */
async function submitQuestion(event) {
  event.preventDefault();
  const question = el("questionInput").value.trim();
  if (!question) {
    renderAskResponse("# Response\n\nAdd a business question first.", "local");
    return;
  }

  const apiBaseUrl = state.apiBaseUrl.trim();
  if (apiBaseUrl) {
    try {
      const response = await fetch(joinUrl(apiBaseUrl, "/ask"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const markdown = payload.markdown || payload.report?.markdown || payload.report?.text || payload.text || JSON.stringify(payload, null, 2);
      renderAskResponse(markdown, "api");
      return;
    } catch (_) { /* fall through */ }
  }

  const report = state.data.report || FALLBACK_DATA.report;
  const markdown = [
    "# Mock Answer",
    "",
    `## Question`,
    question,
    "",
    "## Prototype response",
    report.recommendation || "Use the mock fixture views to inspect local decision-system artifacts.",
    "",
    "## Source",
    "This response used mock data because no reachable API handled the request.",
  ].join("\n");
  renderAskResponse(markdown, "mock");
}

/* =========================================================================
   Control bindings
   ========================================================================= */
function bindControls() {
  el("apiBaseUrl").value = state.apiBaseUrl;
  el("saveApiBase").addEventListener("click", () => {
    state.apiBaseUrl = el("apiBaseUrl").value.trim();
    if (state.apiBaseUrl) localStorage.setItem(API_STORAGE_KEY, state.apiBaseUrl);
    else localStorage.removeItem(API_STORAGE_KEY);
    loadAllData();
  });
  el("resetMocks").addEventListener("click", () => {
    state.apiBaseUrl = "";
    el("apiBaseUrl").value = "";
    localStorage.removeItem(API_STORAGE_KEY);
    loadAllData();
  });
  el("askForm").addEventListener("submit", submitQuestion);
}

/* =========================================================================
   Main render
   ========================================================================= */
function renderAll() {
  renderConnection();
  renderDashboard();
  renderAskResponse(null, state.source);
  renderProfiles();
  renderOntology();
  renderInsights();
  renderGraph();
  renderWarRoom();
  renderWorkspaces();
  renderConnectors().then(() => {});
  renderSecurity();
  renderObservability();
  renderEnterprise();
}

/* =========================================================================
   Init
   ========================================================================= */
bindNavigation();
bindDataTabs();
bindControls();
loadAllData();
