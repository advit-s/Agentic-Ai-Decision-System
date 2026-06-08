const API_STORAGE_KEY = "decisionSystemApiBaseUrl";

const DATASETS = {
  report: {
    apiPath: "/reports/latest",
    mockPath: "mock-data/report.json",
  },
  insights: {
    apiPath: "/insights",
    mockPath: "mock-data/insights.json",
  },
  ontology: {
    apiPath: "/ontology",
    mockPath: "mock-data/ontology.json",
  },
  warRoom: {
    apiPath: "/war-room/latest",
    mockPath: "mock-data/war-room.json",
  },
  providerEvals: {
    apiPath: "/provider-evals/latest",
    mockPath: "mock-data/provider-evals.json",
  },
  dataProfiles: {
    apiPath: "/data-profiles",
    mockPath: "mock-data/data-profiles.json",
  },
  graph: {
    apiPath: "/graph",
    mockPath: "mock-data/graph.json",
  },
};

const FALLBACK_DATA = {
  report: {
    question: "Where are we losing money?",
    generated_at: "2026-06-06T00:00:00Z",
    confidence: "medium",
    recommendation: "Review revenue concentration, refunds, and migration risk before committing spend.",
    markdown: "# Mock Decision Report\n\n## Recommendation\nUse the mock data path until a backend API is configured.\n\n## Evidence\n- Local fixtures are available under `web/mock-data/`.\n- Fake provider mode remains the default.\n",
    citations: ["mock-report"],
  },
  insights: { insights: [] },
  ontology: { mappings: [] },
  warRoom: { roles: [], artifacts: [], judge_interventions: [] },
  providerEvals: { provider_name: "fake", results: [] },
  dataProfiles: { profiles: [] },
  graph: { entities: [], relationships: [] },
};

const state = {
  apiBaseUrl: localStorage.getItem(API_STORAGE_KEY) || "",
  source: "mock",
  data: structuredClone(FALLBACK_DATA),
};

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
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function loadDataset(key, config, apiBaseUrl) {
  if (apiBaseUrl) {
    try {
      const payload = await fetchJson(joinUrl(apiBaseUrl, config.apiPath));
      return { payload, source: "api" };
    } catch (error) {
      console.warn(`API load failed for ${key}; using mock data.`, error);
    }
  }

  try {
    const payload = await fetchJson(config.mockPath);
    return { payload, source: "mock" };
  } catch (error) {
    console.warn(`Mock fixture load failed for ${key}; using fallback data.`, error);
    return { payload: structuredClone(FALLBACK_DATA[key]), source: "fallback" };
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
    state.data[key] = result.payload || structuredClone(FALLBACK_DATA[key]);
    if (result.source !== "api") {
      source = result.source;
    }
  }
  state.source = source;
  renderAll();
}

function renderMarkdown(markdown) {
  const lines = String(markdown ?? "").split(/\r?\n/);
  const html = [];
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      continue;
    }

    if (line.startsWith("### ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h3>${inlineMarkdown(line.slice(4))}</h3>`);
    } else if (line.startsWith("## ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h2>${inlineMarkdown(line.slice(3))}</h2>`);
    } else if (line.startsWith("# ")) {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<h1>${inlineMarkdown(line.slice(2))}</h1>`);
    } else if (line.startsWith("- ")) {
      if (!inList) {
        html.push("<ul>");
        inList = true;
      }
      html.push(`<li>${inlineMarkdown(line.slice(2))}</li>`);
    } else {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
      html.push(`<p>${inlineMarkdown(line)}</p>`);
    }
  }

  if (inList) {
    html.push("</ul>");
  }
  return html.join("");
}

function inlineMarkdown(value) {
  return safe(value).replace(/`([^`]+)`/g, "<code>$1</code>");
}

function renderConnection() {
  const mode = state.source === "api" ? "API" : state.source === "fallback" ? "Fallback" : "Mock-first";
  el("connectionMode").textContent = mode;
  el("dataSourceStatus").textContent = state.apiBaseUrl
    ? `Configured: ${state.apiBaseUrl}`
    : "Using mock data";
}

function renderMetrics() {
  el("metricReports").textContent = state.data.report ? "1" : "0";
  el("metricInsights").textContent = state.data.insights?.insights?.length ?? 0;
  el("metricArtifacts").textContent = state.data.warRoom?.artifacts?.length ?? 0;
  el("metricGraph").textContent = state.data.graph?.relationships?.length ?? 0;
}

function renderAskResponse(markdown, mode = state.source) {
  el("answerMode").textContent = mode;
  el("askResponse").innerHTML = renderMarkdown(markdown);
}

function renderReport() {
  const report = state.data.report || FALLBACK_DATA.report;
  el("reportDate").textContent = report.generated_at ? new Date(report.generated_at).toLocaleDateString() : "";
  el("reportMeta").innerHTML = `
    <div>
      <strong>${safe(report.question)}</strong>
      <div class="small-muted">Confidence: ${safe(report.confidence || "unknown")}</div>
    </div>
    <span class="tag">${safe(report.recommendation || "No recommendation")}</span>
  `;
  el("reportMarkdown").innerHTML = renderMarkdown(report.markdown || report.text || "");
  renderAskResponse(report.markdown || report.text || "", state.source);
}

function renderInsights() {
  const groups = {};
  for (const item of state.data.insights?.insights || []) {
    const severity = (item.severity || "unknown").toLowerCase();
    groups[severity] = groups[severity] || [];
    groups[severity].push(item);
  }

  const severityOrder = ["critical", "high", "medium", "low", "unknown"];
  el("insightGroups").innerHTML = severityOrder
    .filter((severity) => groups[severity]?.length)
    .map((severity) => {
      const cards = groups[severity]
        .map(
          (item) => `
            <article class="insight-card ${safe(severity)}">
              <h5>${safe(item.title)}</h5>
              <div class="meta-line">${safe(item.category)} | confidence ${safe(item.confidence)}</div>
              <p>${safe(item.summary)}</p>
              <div class="pill-row">${(item.evidence_refs || []).map((ref) => `<span class="pill">${safe(ref)}</span>`).join("")}</div>
            </article>
          `
        )
        .join("");
      return `
        <div class="severity-group">
          <h4 class="severity-heading">${safe(severity)} (${groups[severity].length})</h4>
          ${cards}
        </div>
      `;
    })
    .join("");
}

function renderOntology() {
  const mappings = state.data.ontology?.mappings || [];
  el("ontologySummary").textContent = `${mappings.length} mappings`;
  el("ontologyRows").innerHTML = mappings
    .map(
      (item) => `
        <tr>
          <td>${safe(item.dataset)}</td>
          <td><code>${safe(item.column)}</code></td>
          <td>${safe(item.concept_name)}<div class="small-muted">${safe(item.concept_id)}</div></td>
          <td>${safe(item.concept_type)}</td>
          <td>${safe(item.confidence)}</td>
        </tr>
      `
    )
    .join("");
}

function renderWarRoom() {
  const run = state.data.warRoom || FALLBACK_DATA.warRoom;
  el("warRoomSummary").textContent = `${run.roles?.length || 0} roles | ${run.artifacts?.length || 0} artifacts`;
  el("warRoomRoles").innerHTML = (run.roles || [])
    .map(
      (role) => `
        <div class="compact-item">
          <strong>${safe(role.name)}</strong>
          <span class="small-muted">${safe(role.objective)}</span>
          <div class="pill-row">${(role.allowed_tools || []).map((tool) => `<span class="pill">${safe(tool)}</span>`).join("")}</div>
        </div>
      `
    )
    .join("");
  el("judgeInterventions").innerHTML = (run.judge_interventions || [])
    .map(
      (item) => `
        <div class="compact-item">
          <strong>${safe(item.severity)}: ${safe(item.rule)}</strong>
          <span>${safe(item.message)}</span>
          <span class="small-muted">Human review: ${item.human_review_required ? "yes" : "no"}</span>
        </div>
      `
    )
    .join("");
  el("warRoomArtifacts").innerHTML = (run.artifacts || [])
    .map(
      (item) => `
        <article class="artifact-card">
          <h5>${safe(item.title)}</h5>
          <div class="meta-line">${safe(item.role)} | ${safe(item.artifact_type)} | confidence ${safe(item.confidence)}</div>
          <p>${safe(item.summary)}</p>
          <div class="pill-row">${(item.evidence_refs || []).map((ref) => `<span class="pill">${safe(ref)}</span>`).join("")}</div>
        </article>
      `
    )
    .join("");
}

function renderProviderEvals() {
  const suite = state.data.providerEvals || FALLBACK_DATA.providerEvals;
  el("providerEvalSummary").textContent = `${safe(suite.provider_name)} | ${suite.passed_cases || 0}/${suite.total_cases || 0} passed`;
  el("providerEvalRows").innerHTML = (suite.results || [])
    .map((item) => {
      const statusClass = item.status === "passed" ? "status-pass" : "status-fail";
      return `
        <article class="eval-row">
          <strong class="${statusClass}">${safe(item.status)}</strong>
          <div>
            <h5>${safe(item.case_id)}</h5>
            <div class="small-muted">${safe(item.question || "")}</div>
          </div>
          <span class="tag muted">${safe(item.claim_count || 0)} claims</span>
        </article>
      `;
    })
    .join("");
}

function renderProfiles() {
  const profiles = state.data.dataProfiles?.profiles || [];
  el("profileSummary").textContent = `${profiles.length} profiles`;
  el("profileGrid").innerHTML = profiles
    .map(
      (profile) => `
        <article class="profile-card">
          <h5>${safe(profile.dataset)}</h5>
          <div class="meta-line">${safe(profile.category)} | ${safe(profile.row_count)} rows | ${safe(profile.column_count)} columns</div>
          <div class="pill-row">${(profile.columns || []).slice(0, 8).map((column) => `<span class="pill">${safe(column)}</span>`).join("")}</div>
          ${(profile.warnings || []).map((warning) => `<p class="small-muted">${safe(warning)}</p>`).join("")}
        </article>
      `
    )
    .join("");
}

function renderGraph() {
  const graph = state.data.graph || FALLBACK_DATA.graph;
  el("graphSummary").textContent = `${graph.entities?.length || 0} entities | ${graph.relationships?.length || 0} links`;
  el("graphEntities").innerHTML = (graph.entities || [])
    .map(
      (entity) => `
        <div class="compact-item">
          <strong>${safe(entity.name)}</strong>
          <span class="small-muted">${safe(entity.type)} | degree ${safe(entity.degree ?? 0)}</span>
        </div>
      `
    )
    .join("");
  el("graphRelationships").innerHTML = (graph.relationships || [])
    .map(
      (rel) => `
        <div class="compact-item">
          <strong>${safe(rel.source)} -> ${safe(rel.target)}</strong>
          <span class="small-muted">${safe(rel.type)} | ${safe(rel.evidence_id)}</span>
        </div>
      `
    )
    .join("");
}
function renderSecurity() {
      const sec = state.data.security || structuredClone(FALLBACK_DATA.security);
      const policy = sec.policy;
      const checks = (policy && policy.checks ? policy.checks : []).slice(0, 6);
      el("securityPolicyStatus").innerHTML = checks.length ? checks.map((c) => {
        const cls = c.passed ? "status-pass" : "status-fail";
        return `<div class="compact-item"><strong class="${cls}">${safe(c.name)}</strong> <span class="small-muted">${safe(c.message || "")}</span></div>`;
      }).join("") : "<p class="empty-state">No policy data</p>";
      el("securityAuditLog").innerHTML = (sec.audit_events || []).slice(0, 5).map((ev) => {
        return `<div class="compact-item"><strong>${safe(ev.event_type)}</strong> <span class="small-muted">${ev.created_at ? new Date(ev.created_at).toLocaleString() : ""}</span> ${ev.message ? `<div>${safe(ev.message)}</div>` : ""}</div>`;
      }).join("") || "<p class="empty-state">No audit events</p>";
      el("securityApprovals").innerHTML = (sec.approval_requests || []).slice(0, 5).map((r) => {
        const cls = r.status === "approved" ? "status-pass" : r.status === "rejected" ? "status-fail" : "";
        return `<div class="compact-item"><strong class="${cls}">#${safe(r.approval_id || r.id || "?")}</strong> <span>${safe(r.reason || r.message || "")}</span> <span class="small-muted">${safe(r.requested_by || r.actor || "unknown")} | ${safe(r.status || "pending")}</span></div>`;
      }).join("") || "<p class="empty-state">No approval requests yet</p>";
    }
function renderAll() {
  renderConnection();
  renderMetrics();
  renderReport();
  renderInsights();
  renderOntology();
  renderWarRoom();
  renderProviderEvals();
  renderProfiles();
  renderGraph();
  renderSecurity();
}

async function submitQuestion(event) {
  event.preventDefault();
  const question = el("questionInput").value.trim();
  if (!question) {
    renderAskResponse("# Response\n\nAdd a business question first.", "local");
    return;
  }

  if (state.apiBaseUrl.trim()) {
    try {
      const response = await fetch(joinUrl(state.apiBaseUrl.trim(), "/ask"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      const markdown = payload.markdown || payload.report || payload.text || JSON.stringify(payload, null, 2);
      renderAskResponse(markdown, "api");
      return;
    } catch (error) {
      console.warn("API ask failed; using mock response.", error);
    }
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

function bindNavigation() {
  document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active-view"));
      button.classList.add("active");
      el(button.dataset.view).classList.add("active-view");
    });
  });
}

function bindControls() {
  el("apiBaseUrl").value = state.apiBaseUrl;
  el("saveApiBase").addEventListener("click", () => {
    state.apiBaseUrl = el("apiBaseUrl").value.trim();
    if (state.apiBaseUrl) {
      localStorage.setItem(API_STORAGE_KEY, state.apiBaseUrl);
    } else {
      localStorage.removeItem(API_STORAGE_KEY);
    }
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

bindNavigation();
bindControls();
loadAllData();
