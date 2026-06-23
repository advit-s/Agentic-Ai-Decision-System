// components/ClaimLedgerPanel.jsx — Unified claim ledger view
// Supports v1.20 verification statuses: supported, contradicted, unsupported, uncertain, needs_review
import React, { useMemo, useState, useCallback, useEffect } from "react";
import "../styles/execution-panel.css";

import {
  verifyClaim,
  getClaimVerification,
  listClaimContradictions,
} from "../api";

/* ── Helpers ────────────────────────────────────────────────────────── */

function resolveClaims(nodeStatuses) {
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

  for (const { issues } of issuesByNode) {
    for (const issue of issues) {
      let claimIdx = -1;
      const locMatch = (issue.location || "").match(/Claim\s+(\d+)/i);
      if (locMatch) {
        claimIdx = parseInt(locMatch[1], 10) - 1;
      }
      if (claimIdx >= 0 && claimIdx < claims.length) {
        if (!claims[claimIdx].issues) claims[claimIdx].issues = [];
        claims[claimIdx].issues.push(issue);
      } else {
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
    claim.claimPath = hasCritic
      ? "Researcher → Critic → Ledger"
      : "Researcher → Ledger";
  }
  return claims;
}

function enrichClaimsWithVerification(claims, verificationMap, contradictionMap) {
  return claims.map((claim) => {
    const ver = verificationMap[claim.id];
    const cons = contradictionMap[claim.id] || [];
    if (ver) {
      return {
        ...claim,
        verification_status: ver.status || claim.status,
        verification_confidence: ver.confidence != null ? (typeof ver.confidence === "number" ? ver.confidence : parseFloat(ver.confidence) || claim.confidence) : claim.confidence,
        evidence_quality: ver.evidence_quality || null,
        verification_method: ver.verification_method || null,
        verification_reason: ver.verification_reason || null,
        requires_review: ver.requires_review || false,
        verification_evidence_count: ver.evidence_count ?? claim.evidence.length,
        verification_contradiction_count: ver.contradiction_count ?? 0,
        verified_at: ver.verified_at || null,
        contradictions: cons,
      };
    }
    return claim;
  });
}

const VERIFICATION_STATUS_STYLES = {
  supported: { icon: "✅", bg: "#dcfce7", color: "#166534", label: "Supported" },
  verified: { icon: "✅", bg: "#dcfce7", color: "#166534", label: "Verified" },
  contradicted: { icon: "⚡", bg: "#fee2e2", color: "#991b1b", label: "Contradicted" },
  unsupported: { icon: "❓", bg: "#fef9c3", color: "#854d0e", label: "Unsupported" },
  uncertain: { icon: "◌", bg: "#f3f4f6", color: "#6b7280", label: "Uncertain" },
  needs_review: { icon: "🔍", bg: "#ede9fe", color: "#7c3aed", label: "Needs Review" },
  pending: { icon: "○", bg: "#f3f4f6", color: "#4b5563", label: "Pending" },
};

const EVIDENCE_QUALITY_STYLES = {
  strong: { bg: "#dcfce7", color: "#166534", label: "Strong" },
  moderate: { bg: "#fef9c3", color: "#854d0e", label: "Moderate" },
  weak: { bg: "#fee2e2", color: "#991b1b", label: "Weak" },
  missing: { bg: "#f3f4f6", color: "#4b5563", label: "Missing" },
  contradicted: { bg: "#fecaca", color: "#7f1d1d", label: "Contradicted" },
};

const VERIFICATION_STATUS_FILTERS = [
  { key: "all", label: "All" },
  { key: "supported", label: "Supported" },
  { key: "verified", label: "Verified" },
  { key: "contradicted", label: "Contradicted" },
  { key: "unsupported", label: "Unsupported" },
  { key: "uncertain", label: "Uncertain" },
  { key: "needs_review", label: "Needs Review" },
  { key: "pending", label: "Pending" },
];

const ISSUE_TYPE_ICONS = {
  contradiction: "⚡",
  unsupported: "❓",
  logical_fallacy: "🧠",
  misconfidence: "📊",
};

/* ── SummaryBar ─────────────────────────────────────────────────────── */

function SummaryBar({ claims, onVerifyAll, verifying }) {
  const total = claims.length;
  const getStatus = (c) => c.verification_status || c.status;
  const statusCounts = [
    { key: "supported", label: "Supported", bg: "#dcfce7", color: "#166534" },
    { key: "verified", label: "Verified", bg: "#dcfce7", color: "#166534" },
    { key: "contradicted", label: "Contradicted", bg: "#fee2e2", color: "#991b1b" },
    { key: "unsupported", label: "Unsupported", bg: "#fef9c3", color: "#854d0e" },
    { key: "uncertain", label: "Uncertain", bg: "#f3f4f6", color: "#6b7280" },
    { key: "needs_review", label: "Needs Review", bg: "#ede9fe", color: "#7c3aed" },
    { key: "pending", label: "Pending", bg: "#f3f4f6", color: "#4b5563" },
  ];

  const activeCounts = statusCounts
    .map((s) => ({ ...s, count: claims.filter((c) => getStatus(c) === s.key).length }))
    .filter((s) => s.count > 0);

  return (
    <div className="cl-summary-bar">
      <div className="cl-summary-stats">
        <span className="cl-summary-total">{total} claims</span>
        {onVerifyAll && (
          <button className="cl-verify-btn cl-verify-all-btn" onClick={onVerifyAll} disabled={verifying} title="Verify all claims">
            {verifying ? "Verifying..." : "✓ Verify All"}
          </button>
        )}
      </div>
      <div className="cl-summary-breakdown">
        {activeCounts.map((s) => (
          <span key={s.key} className="cl-status-pill" style={{ background: s.bg, color: s.color }}>
            {s.count} {s.label}
          </span>
        ))}
      </div>
      {total > 0 && (
        <div className="cl-progress-bar">
          {activeCounts.map((s) => (
            <div key={s.key} className={"cl-progress-segment"} style={{ width: `${(s.count / total) * 100}%`, background: s.color, opacity: 0.6 }} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ── ClaimCard ──────────────────────────────────────────────────────── */

function ClaimCard({ claim, index, onVerify, onViewContradictions }) {
  const [expanded, setExpanded] = useState(false);
  const statusKey = claim.verification_status || claim.status;
  const st = VERIFICATION_STATUS_STYLES[statusKey] || VERIFICATION_STATUS_STYLES.pending;
  const eq = claim.evidence_quality;
  const eqLabel = eq ? (eq.label || eq) : null;
  const eqStyle = eqLabel ? EVIDENCE_QUALITY_STYLES[eqLabel] || EVIDENCE_QUALITY_STYLES.missing : null;
  const hasContradiction = claim.verification_contradiction_count > 0 || (claim.issues || []).some((i) => i.type === "contradiction");
  const needsVerify = !claim.verified_at && statusKey === "pending";
  const conf = claim.verification_confidence || claim.confidence || 0;

  const confBg = conf >= 0.7 ? "#dcfce7" : conf >= 0.4 ? "#fef9c3" : "#fee2e2";
  const confColor = conf >= 0.7 ? "#166534" : conf >= 0.4 ? "#854d0e" : "#991b1b";

  return (
    <div className={"cl-claim-card" + (hasContradiction ? " cl-has-contradiction" : "")} onClick={() => setExpanded(!expanded)}>
      <div className="cl-claim-header">
        <span className="cl-claim-num">#{index + 1}</span>
        <span className="cl-claim-status-badge" style={{ background: st.bg, color: st.color }}>
          {st.icon} {st.label}
        </span>
        {claim.requires_review && (
          <span className="cl-review-required-badge" style={{ background: "#ede9fe", color: "#7c3aed", fontSize: "0.7rem", padding: "0 6px", borderRadius: "4px", marginRight: "4px" }}>Review</span>
        )}
        {eqStyle && (
          <span className="cl-evidence-quality-badge" style={{ background: eqStyle.bg, color: eqStyle.color, fontSize: "0.7rem", padding: "0 6px", borderRadius: "4px", marginRight: "4px" }}>
            {eqStyle.label}
          </span>
        )}
        <span className="cl-claim-node-label">{claim.sourceNode}</span>
        {claim.claimPath && <span className="cl-claim-path">{claim.claimPath}</span>}
        <span className="cl-claim-expand">{expanded ? "▾" : "▸"}</span>
      </div>

      <div className="cl-claim-statement">{claim.statement}</div>

      <div className="cl-claim-meta">
        <span className="so-confidence-badge" style={{ background: confBg, color: confColor }}>
          {Math.round(conf * 100)}%
        </span>
        <span className="cl-claim-evidence-count">
          📄 {claim.verification_evidence_count ?? claim.evidence.length} evidence
        </span>
        {claim.verification_method && (
          <span className="cl-verification-method" style={{ fontSize: "0.75rem", color: "#6b7280", marginLeft: "8px" }}>
            {claim.verification_method}
          </span>
        )}
        {needsVerify && onVerify && (
          <button className="cl-verify-btn" onClick={(e) => { e.stopPropagation(); onVerify(claim); }} title="Verify this claim against evidence">
            ✓ Verify
          </button>
        )}
        {hasContradiction && onViewContradictions && (
          <button className="cl-view-contradictions-btn" onClick={(e) => { e.stopPropagation(); onViewContradictions(claim); }} title="View contradictions">
            ⚡ Contradictions
          </button>
        )}
        {claim.verified_at && (
          <span className="cl-verified-at" style={{ fontSize: "0.7rem", color: "#9ca3af", marginLeft: "8px" }}>
            {new Date(claim.verified_at).toLocaleString()}
          </span>
        )}
        {claim.citation && <span className="cl-claim-citation">📎 {claim.citation}</span>}
        {claim.sourceType && <span className="cl-claim-source-type">{claim.sourceType}</span>}
      </div>

      {expanded && claim.verification_reason && (
        <div className="cl-verification-reason" style={{ padding: "8px 12px", background: "#f9fafb", borderRadius: "6px", margin: "4px 12px", fontSize: "0.85rem", color: "#374151" }}>
          <strong>Verification:</strong> {claim.verification_reason}
        </div>
      )}

      {expanded && claim.issues && claim.issues.length > 0 && (
        <div className="cl-claim-issues">
          <div className="cl-claim-issues-title">Issues ({claim.issues.length})</div>
          {claim.issues.map((iss, j) => (
            <div key={j} className={"cl-issue-row" + (iss.type === "contradiction" ? " cl-contradiction-highlight" : "")}>
              <span className="cl-issue-icon">{iss.type === "contradiction" ? "⚠️ " : ""}{ISSUE_TYPE_ICONS[iss.type] || "●"}</span>
              <span className="cl-issue-sev" style={{
                background: iss.severity === "high" ? "#fee2e2" : iss.severity === "medium" ? "#fef9c3" : "#f3f4f6",
                color: iss.severity === "high" ? "#991b1b" : iss.severity === "medium" ? "#854d0e" : "#4b5563",
              }}>{iss.severity}</span>
              <span className="cl-issue-desc">{iss.description}</span>
              {iss.suggestion && <span className="cl-issue-suggestion">💡 {iss.suggestion}</span>}
            </div>
          ))}
        </div>
      )}

      {expanded && claim.contradictions && claim.contradictions.length > 0 && (
        <div className="cl-claim-contradictions" style={{ padding: "8px 12px", background: "#fef2f2", borderRadius: "6px", margin: "4px 12px" }}>
          <div className="cl-claim-issues-title">Contradictions ({claim.contradictions.length})</div>
          {claim.contradictions.map((con, j) => (
            <div key={j} className="cl-issue-row cl-contradiction-highlight">
              <span className="cl-issue-icon">⚠️</span>
              <span className="cl-issue-sev" style={{
                background: con.severity === "high" ? "#fee2e2" : con.severity === "medium" ? "#fef9c3" : "#f3f4f6",
                color: con.severity === "high" ? "#991b1b" : con.severity === "medium" ? "#854d0e" : "#4b5563",
              }}>{con.severity}</span>
              <span className="cl-issue-desc">{con.description}</span>
            </div>
          ))}
        </div>
      )}

      {expanded && claim.evidence.length > 0 && (
        <div className="cl-claim-evidence-section">
          <div className="cl-claim-evidence-title">Evidence ({claim.evidence.length})</div>
          <div className="cl-evidence-list">
            {claim.evidence.map((e, k) => (
              <div key={k} className="cl-evidence-card">
                <div className="cl-evidence-card-content">
                  {typeof e === "string" ? (e.length > 80 ? e.slice(0, 80) + "…" : e) : JSON.stringify(e).length > 80 ? JSON.stringify(e).slice(0, 80) + "…" : JSON.stringify(e)}
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
        Add a <strong>Researcher</strong> node to generate findings, then a <strong>Critic</strong> to evaluate them.
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────── */

export default function ClaimLedgerPanel({ nodeStatuses, onClose, onExportReport, viewToggle, workspaceId }) {
  const claims = useMemo(() => resolveClaims(nodeStatuses), [nodeStatuses]);
  const [filter, setFilter] = useState("all");
  const [sortBy, setSortBy] = useState("index");
  const [search, setSearch] = useState("");
  const [verificationMap, setVerificationMap] = useState({});
  const [contradictionMap, setContradictionMap] = useState({});
  const [verifying, setVerifying] = useState(false);
  const [expandedClaimId, setExpandedClaimId] = useState(null);

  const enrichedClaims = useMemo(() => {
    return enrichClaimsWithVerification(claims, verificationMap, contradictionMap);
  }, [claims, verificationMap, contradictionMap]);

  useEffect(() => {
    if (claims.length === 0) return;
    let mounted = true;
    const loadVerification = async () => {
      const vm = {};
      const cm = {};
      for (const claim of claims) {
        try {
          const ver = await getClaimVerification(claim.id);
          if (ver && mounted) vm[claim.id] = ver;
        } catch {
          // No verification data yet
        }
        try {
          const cons = await listClaimContradictions(claim.id);
          if (cons && cons.contradictions && mounted) cm[claim.id] = cons.contradictions;
        } catch {
          // No contradictions
        }
      }
      if (mounted) {
        setVerificationMap(vm);
        setContradictionMap(cm);
      }
    };
    loadVerification();
    return () => { mounted = false; };
  }, [claims]);

  const getFilterStatus = (c) => c.verification_status || c.status;

  const filtered = useMemo(() => {
    let result = filter === "all" ? [...enrichedClaims] : enrichedClaims.filter((c) => getFilterStatus(c) === filter);

    if (sortBy === "confidence") {
      result.sort((a, b) => (b.verification_confidence || b.confidence) - (a.verification_confidence || a.confidence));
    } else if (sortBy === "status") {
      const order = ["contradicted", "unsupported", "uncertain", "needs_review", "supported", "verified", "pending"];
      result.sort((a, b) => order.indexOf(getFilterStatus(a)) - order.indexOf(getFilterStatus(b)));
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((c) => c.statement.toLowerCase().includes(q));
    }
    return result;
  }, [enrichedClaims, filter, sortBy, search]);

  const handleVerify = useCallback(async (claim) => {
    try {
      const result = await verifyClaim(claim.id, workspaceId);
      setVerificationMap(prev => ({ ...prev, [claim.id]: result }));
    } catch (err) {
      console.error("Verification failed for claim", claim.id, err);
    }
  }, [workspaceId]);

  const handleVerifyAll = useCallback(async () => {
    setVerifying(true);
    for (const claim of claims) {
      try {
        const result = await verifyClaim(claim.id, workspaceId);
        setVerificationMap(prev => ({ ...prev, [claim.id]: result }));
      } catch {
        // Continue with remaining claims
      }
    }
    setVerifying(false);
  }, [claims, workspaceId]);

  const handleViewContradictions = useCallback((claim) => {
    setExpandedClaimId(claim.id);
  }, []);

  const handleExport = useCallback(() => {
    const report = {
      title: "Claim Ledger Report",
      generated_at: new Date().toISOString(),
      total_claims: enrichedClaims.length,
      summary: {
        supported: enrichedClaims.filter((c) => getFilterStatus(c) === "supported").length,
        verified: enrichedClaims.filter((c) => getFilterStatus(c) === "verified").length,
        unsupported: enrichedClaims.filter((c) => getFilterStatus(c) === "unsupported").length,
        contradicted: enrichedClaims.filter((c) => getFilterStatus(c) === "contradicted").length,
        uncertain: enrichedClaims.filter((c) => getFilterStatus(c) === "uncertain").length,
        needs_review: enrichedClaims.filter((c) => getFilterStatus(c) === "needs_review").length,
        pending: enrichedClaims.filter((c) => getFilterStatus(c) === "pending").length,
      },
      claims: enrichedClaims.map((c) => ({
        statement: c.statement,
        status: getFilterStatus(c),
        confidence: c.verification_confidence || c.confidence,
        evidence_quality: c.evidence_quality,
        verification_method: c.verification_method,
        verification_reason: c.verification_reason,
        citation: c.citation,
        source_node: c.sourceNode,
      })),
    };

    const dateStr = new Date().toISOString().slice(0, 10);
    const filename = "claim-ledger-report-" + dateStr + ".json";
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (onExportReport) onExportReport(report);
  }, [enrichedClaims, onExportReport]);

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Claim Ledger</div>
        <button className="cl-export-btn" onClick={handleExport} title="Export claim ledger as JSON">📄 Export Report</button>
        <button className="execution-close" onClick={onClose}>✕</button>
      </div>

      {viewToggle}

      {verifying && (
        <div className="cl-verifying-banner" style={{ padding: "8px 16px", background: "#eff6ff", color: "#1e40af", fontSize: "0.85rem" }}>
          Verifying claims...
        </div>
      )}

      {enrichedClaims.length > 0 ? (
        <>
          <SummaryBar claims={enrichedClaims} onVerifyAll={handleVerifyAll} verifying={verifying} />

          <div className="cl-toolbar">
            <div className="cl-filter-group">
              {VERIFICATION_STATUS_FILTERS.map((f) => (
                <button key={f.key} className={"cl-filter-btn" + (filter === f.key ? " active" : "")} onClick={() => setFilter(f.key)}>
                  {f.label}
                </button>
              ))}
            </div>
            <input type="text" className="cl-search-input" placeholder="Search claims..." value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="cl-sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="index">Order</option>
              <option value="confidence">Confidence</option>
              <option value="status">Status</option>
            </select>
          </div>

          <div className="cl-claim-list">
            {filtered.length > 0 ? (
              filtered.map((claim, i) => (
                <ClaimCard key={claim.id} claim={claim} index={i} onVerify={handleVerify} onViewContradictions={handleViewContradictions} />
              ))
            ) : (
              <div className="cl-empty-filter">
                {search.trim() ? 'No claims match "' + search + '".' : 'No claims match the "' + filter + '" filter.'}
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
