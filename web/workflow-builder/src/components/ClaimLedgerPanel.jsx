// components/ClaimLedgerPanel.jsx — Unified claim ledger view
// Aggregates Researcher findings and Critic issues into a claim-centric view.
import React, { useMemo, useState, useCallback } from "react";
import "../styles/execution-panel.css";

/* ── Helpers ────────────────────────────────────────────────────────── */

function resolveClaims(nodeStatuses) {
  // Collect all findings from Researcher-type nodes
  const findingsByNode = [];
  const issuesByNode = [];

  for (const ns of nodeStatuses) {
    const outs = ns.outputs || {};
    const findings = outs.findings;
    if (Array.isArray(findings) && findings.length > 0) {
      findingsByNode.push({ nodeId: ns.nodeId, label: ns.label, findings });
    }
    const issues = outs.issues;
    if (Array.isArray(issues) && issues.length > 0) {
      issuesByNode.push({ nodeId: ns.nodeId, label: ns.label, issues });
    }
  }

  const hasCritic = issuesByNode.length > 0;

  // Merge findings into a unified claim list
  const claims = [];
  for (const { nodeId, label, findings } of findingsByNode) {
    for (const f of findings) {
      claims.push({
        id: `${nodeId}-f${claims.length}`,
        statement: f.statement || f.text || "",
        confidence: f.confidence ?? 0.5,
        evidence: f.evidence || f.chunks || f.sources || [],
        citation: f.citation || "",
        sourceType: f.source_type || "",
        sourceNode: label,
        sourceNodeId: nodeId,
        issues: [],
      });
    }
  }

  // Match Critic issues to claims by location index and text
  for (const { issues } of issuesByNode) {
    for (const issue of issues) {
      // Try to extract claim index from location like "Claim 1" (1-indexed)
      let claimIdx = -1;
      const locMatch = (issue.location || "").match(/Claim\s+(\d+)/i);
      if (locMatch) {
        claimIdx = parseInt(locMatch[1], 10) - 1;
      }

      if (claimIdx >= 0 && claimIdx < claims.length) {
        // Found by index
        if (!claims[claimIdx].issues) claims[claimIdx].issues = [];
        claims[claimIdx].issues.push(issue);
      } else {
        // Fallback: text match — find first claim whose statement appears in description
        const desc = (issue.description || "").toLowerCase();
        const match = claims.find(
          (c) => desc.includes(c.statement.toLowerCase().slice(0, 40))
        );
        if (match) {
          if (!match.issues) match.issues = [];
          match.issues.push(issue);
        }
      }
    }
  }

  // Derive status and claim path for each claim
  for (const claim of claims) {
    const iss = claim.issues || [];
    if (iss.some((i) => i.type === "contradiction")) {
      claim.status = "contradicted";
    } else if (iss.some((i) => i.type === "unsupported")) {
      claim.status = "unsupported";
    } else if (claim.evidence.length > 0) {
      claim.status = "verified";
    } else {
      claim.status = "pending";
    }

    // Claim path: if critic touched this claim, show full chain
    claim.claimPath = hasCritic
      ? "Researcher → Critic → Ledger"
      : "Researcher → Ledger";
  }

  return claims;
}

/* ── Export helper ──────────────────────────────────────────────────── */

function buildExportReport(claims) {
  const statusCounts = {
    verified: claims.filter((c) => c.status === "verified").length,
    unsupported: claims.filter((c) => c.status === "unsupported").length,
    contradicted: claims.filter((c) => c.status === "contradicted").length,
    pending: claims.filter((c) => c.status === "pending").length,
  };

  return {
    title: "Claim Ledger Report",
    generated_at: new Date().toISOString(),
    total_claims: claims.length,
    summary: statusCounts,
    claims: claims.map((c) => ({
      statement: c.statement,
      status: c.status,
      confidence: c.confidence,
      citation: c.citation,
      source_node: c.sourceNode,
      issues: (c.issues || []).map((i) => ({
        description: i.description,
        severity: i.severity,
        type: i.type,
      })),
      evidence: c.evidence.map((e) =>
        typeof e === "string" ? e : JSON.stringify(e)
      ),
    })),
  };
}

/* ── Summary bar ────────────────────────────────────────────────────── */

function SummaryBar({ claims }) {
  const total = claims.length;
  const statusCounts = {
    verified: claims.filter((c) => c.status === "verified").length,
    unsupported: claims.filter((c) => c.status === "unsupported").length,
    contradicted: claims.filter((c) => c.status === "contradicted").length,
    pending: claims.filter((c) => c.status === "pending").length,
  };

  const issuesTotal = claims.reduce(
    (sum, c) => sum + (c.issues || []).length,
    0
  );

  const bars = [
    { key: "verified", label: "Verified", color: "#22c55e", bg: "#dcfce7" },
    { key: "unsupported", label: "Unsupported", color: "#eab308", bg: "#fef9c3" },
    { key: "contradicted", label: "Contradicted", color: "#ef4444", bg: "#fee2e2" },
    { key: "pending", label: "Pending", color: "#6b7280", bg: "#f3f4f6" },
  ];

  return (
    <div className="cl-summary-bar">
      <div className="cl-summary-stats">
        <span className="cl-summary-total">{total} claims</span>
        <span className="cl-summary-issues">{issuesTotal} issues flagged</span>
      </div>
      <div className="cl-summary-breakdown">
        {bars.map(
          (b) =>
            statusCounts[b.key] > 0 && (
              <span
                key={b.key}
                className="cl-status-pill"
                style={{ background: b.bg, color: b.color }}
              >
                {statusCounts[b.key]} {b.label}
              </span>
            )
        )}
      </div>
      {total > 0 && (
        <div className="cl-progress-bar">
          <div
            className="cl-progress-segment cl-progress-verified"
            style={{ width: `${(statusCounts.verified / total) * 100}%` }}
          />
          <div
            className="cl-progress-segment cl-progress-unsupported"
            style={{
              width: `${(statusCounts.unsupported / total) * 100}%`,
            }}
          />
          <div
            className="cl-progress-segment cl-progress-contradicted"
            style={{
              width: `${(statusCounts.contradicted / total) * 100}%`,
            }}
          />
          <div
            className="cl-progress-segment cl-progress-pending"
            style={{ width: `${(statusCounts.pending / total) * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}

/* ── Claim card ─────────────────────────────────────────────────────── */

const STATUS_STYLE = {
  verified: { icon: "✅", bg: "#dcfce7", color: "#166534", label: "Verified" },
  unsupported: {
    icon: "❓",
    bg: "#fef9c3",
    color: "#854d0e",
    label: "Unsupported",
  },
  contradicted: {
    icon: "⚡",
    bg: "#fee2e2",
    color: "#991b1b",
    label: "Contradicted",
  },
  pending: { icon: "○", bg: "#f3f4f6", color: "#4b5563", label: "Pending" },
};

const ISSUE_TYPE_ICONS = {
  contradiction: "⚡",
  unsupported: "❓",
  logical_fallacy: "🧠",
  misconfidence: "📊",
};

function ClaimCard({ claim, index }) {
  const [expanded, setExpanded] = useState(false);
  const st = STATUS_STYLE[claim.status] || STATUS_STYLE.pending;

  const hasContradiction = (claim.issues || []).some(
    (i) => i.type === "contradiction"
  );

  return (
    <div className="cl-claim-card" onClick={() => setExpanded(!expanded)}>
      <div className="cl-claim-header">
        <span className="cl-claim-num">#{index + 1}</span>
        <span
          className="cl-claim-status-badge"
          style={{ background: st.bg, color: st.color }}
        >
          {st.icon} {st.label}
        </span>
        <span className="cl-claim-node-label">{claim.sourceNode}</span>
        {/* Claim Path indicator */}
        {claim.claimPath && (
          <span className="cl-claim-path">{claim.claimPath}</span>
        )}
        <span className="cl-claim-expand">{expanded ? "▾" : "▸"}</span>
      </div>

      <div className="cl-claim-statement">{claim.statement}</div>

      <div className="cl-claim-meta">
        <span
          className="so-confidence-badge"
          style={{
            background:
              claim.confidence >= 0.7
                ? "#dcfce7"
                : claim.confidence >= 0.4
                  ? "#fef9c3"
                  : "#fee2e2",
            color:
              claim.confidence >= 0.7
                ? "#166534"
                : claim.confidence >= 0.4
                  ? "#854d0e"
                  : "#991b1b",
          }}
        >
          {Math.round(claim.confidence * 100)}%
        </span>
        {claim.citation && (
          <span className="cl-claim-citation">📎 {claim.citation}</span>
        )}
        {claim.sourceType && (
          <span className="cl-claim-source-type">{claim.sourceType}</span>
        )}
        <span className="cl-claim-evidence-count">
          📄 {claim.evidence.length} evidence
        </span>
      </div>

      {/* Expanded: Issues section — deeper verification trail */}
      {expanded && claim.issues && claim.issues.length > 0 && (
        <div className="cl-claim-issues">
          <div className="cl-claim-issues-title">
            Issues ({claim.issues.length})
          </div>
          {claim.issues.map((iss, j) => (
            <div
              key={j}
              className={
                "cl-issue-row" +
                (iss.type === "contradiction" ? " cl-contradiction-highlight" : "")
              }
            >
              <span className="cl-issue-icon">
                {iss.type === "contradiction" ? "⚠️ " : ""}
                {ISSUE_TYPE_ICONS[iss.type] || "●"}
              </span>
              <span
                className="cl-issue-sev"
                style={{
                  background:
                    iss.severity === "high"
                      ? "#fee2e2"
                      : iss.severity === "medium"
                        ? "#fef9c3"
                        : "#f3f4f6",
                  color:
                    iss.severity === "high"
                      ? "#991b1b"
                      : iss.severity === "medium"
                        ? "#854d0e"
                        : "#4b5563",
                }}
              >
                {iss.severity}
              </span>
              <span className="cl-issue-desc">{iss.description}</span>
              {iss.suggestion && (
                <span className="cl-issue-suggestion">
                  💡 {iss.suggestion}
                </span>
              )}

              {/* Evidence link indicator */}
              <div className="cl-evidence-link">
                {iss.evidence_link ? (
                  <span>🔗 Links to: {iss.evidence_link}</span>
                ) : (
                  <span className="cl-evidence-link-missing">
                    No specific evidence linked
                  </span>
                )}
              </div>

              {/* Full chain: Finding → Critic → Evidence */}
              <div className="cl-claim-chain">
                <span className="cl-chain-step" title={claim.statement}>
                  Finding: {claim.statement.length > 50
                    ? claim.statement.slice(0, 50) + "…"
                    : claim.statement}
                </span>
                <span className="cl-chain-arrow">→</span>
                <span className="cl-chain-step" title={iss.description}>
                  Critic: {iss.description.length > 50
                    ? iss.description.slice(0, 50) + "…"
                    : iss.description}
                </span>
                {claim.citation && (
                  <>
                    <span className="cl-chain-arrow">→</span>
                    <span className="cl-chain-step">
                      📎 {claim.citation}
                    </span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Expanded: Evidence section — small cards with preview */}
      {expanded && claim.evidence.length > 0 && (
        <div className="cl-claim-evidence-section">
          <div className="cl-claim-evidence-title">
            Evidence ({claim.evidence.length})
          </div>
          <div className="cl-evidence-list">
            {claim.evidence.map((e, k) => (
              <div key={k} className="cl-evidence-card">
                <div className="cl-evidence-card-content">
                  {typeof e === "string"
                    ? e.length > 80
                      ? e.slice(0, 80) + "…"
                      : e
                    : JSON.stringify(e).length > 80
                      ? JSON.stringify(e).slice(0, 80) + "…"
                      : JSON.stringify(e)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Empty state ────────────────────────────────────────────────────── */

function EmptyLedger() {
  return (
    <div className="cl-empty">
      <div className="cl-empty-icon">📋</div>
      <div className="cl-empty-text">No claims found in this execution.</div>
      <div className="cl-empty-hint">
        Add a <strong>Researcher</strong> node to generate findings, then a{" "}
        <strong>Critic</strong> to evaluate them.
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────── */

const STATUS_FILTERS = [
  { key: "all", label: "All" },
  { key: "verified", label: "Verified" },
  { key: "unsupported", label: "Unsupported" },
  { key: "contradicted", label: "Contradicted" },
  { key: "pending", label: "Pending" },
];

export default function ClaimLedgerPanel({ nodeStatuses, onClose, onExportReport, viewToggle }) {
  const claims = useMemo(() => resolveClaims(nodeStatuses), [nodeStatuses]);
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("index");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let result =
      filter === "all"
        ? [...claims]
        : claims.filter((c) => c.status === filter);

    if (sortBy === "confidence") {
      result.sort((a, b) => b.confidence - a.confidence);
    } else if (sortBy === "status") {
      const order = ["contradicted", "unsupported", "pending", "verified"];
      result.sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));
    }
    // "index" = insertion order (default)

    // Apply search filter
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((c) =>
        c.statement.toLowerCase().includes(q)
      );
    }

    return result;
  }, [claims, filter, sortBy, search]);

  const handleExport = useCallback(() => {
    const report = buildExportReport(claims);
    const statusCounts = report.summary;
    const dateStr = new Date().toISOString().slice(0, 10);
    const filename =
      "decision-report-v" +
      statusCounts.verified +
      "-u" +
      statusCounts.unsupported +
      "-c" +
      statusCounts.contradicted +
      "-p" +
      statusCounts.pending +
      "-" +
      dateStr +
      ".json";

    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (onExportReport) onExportReport(report);
  }, [claims, onExportReport]);

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Claim Ledger</div>
        <button className="cl-export-btn" onClick={handleExport} title="Export decision report as JSON">
          {"📄"} Export Report
        </button>
        <button className="execution-close" onClick={onClose}>
          {"✕"}
        </button>
      </div>

      {viewToggle}

      {claims.length > 0 ? (
        <>
          <SummaryBar claims={claims} />

          {/* Filters + search + sort */}
          <div className="cl-toolbar">
            <div className="cl-filter-group">
              {STATUS_FILTERS.map((f) => (
                <button
                  key={f.key}
                  className={
                    "cl-filter-btn" + (filter === f.key ? " active" : "")
                  }
                  onClick={() => setFilter(f.key)}
                >
                  {f.label}
                </button>
              ))}
            </div>
            <input
              type="text"
              className="cl-search-input"
              placeholder="Search claims..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select
              className="cl-sort-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="index">Order</option>
              <option value="confidence">Confidence</option>
              <option value="status">Status</option>
            </select>
          </div>

          {/* Claim cards */}
          <div className="cl-claim-list">
            {filtered.length > 0 ? (
              filtered.map((claim, i) => (
                <ClaimCard key={claim.id} claim={claim} index={i} />
              ))
            ) : (
              <div className="cl-empty-filter">
                {search.trim()
                  ? 'No claims match "' + search + '".'
                  : 'No claims match the "' + filter + '" filter.'}
              </div>
            )}
          </div>
        </>
      ) : (
        <EmptyLedger />
      )}
    </div>
  );
}
