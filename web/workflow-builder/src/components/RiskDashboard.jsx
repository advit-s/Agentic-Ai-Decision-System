// RiskDashboard.jsx — Risk overview with severity breakdown, top risks, and metrics
import React, { useState, useEffect, useCallback } from "react";
import { listGraphRisks } from "../api";
import { useToast } from "./Toast";

function RiskDashboard({ workspaceId }) {
  const [loading, setLoading] = useState(false);
  const [risks, setRisks] = useState([]);
  const [error, setError] = useState(null);
  const { addToast } = useToast();

  const loadRisks = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listGraphRisks(workspaceId);
      setRisks(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadRisks();
  }, [loadRisks]);

  // Severity breakdown
  const severityCounts = { critical: 0, high: 0, medium: 0, low: 0 };
  risks.forEach((r) => {
    const s = r.severity || "medium";
    if (severityCounts[s] !== undefined) severityCounts[s]++;
  });

  // Category breakdown
  const categoryCounts = {};
  risks.forEach((r) => {
    const c = r.category || "unknown";
    categoryCounts[c] = (categoryCounts[c] || 0) + 1;
  });

  // Top risks (sorted by severity)
  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const topRisks = [...risks]
    .sort((a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99))
    .slice(0, 5);

  return (
    <div className="risk-dashboard">
      <div className="risk-dashboard-header">
        <h2>Risk Dashboard</h2>
        <span className="risk-dashboard-count">Total: {risks.length} risks</span>
      </div>

      {error && <div className="graph-error">Error: {error}</div>}

      {loading && <div className="graph-loading">Loading risks...</div>}

      {!loading && risks.length === 0 && (
        <div className="risk-empty">
          <p>No risks detected yet.</p>
          <p>Use the <strong>Graph</strong> page to extract intelligence from company text, then return here to see risks.</p>
        </div>
      )}

      {!loading && risks.length > 0 && (
        <>
          {/* Summary cards */}
          <div className="risk-summary-cards">
            {["critical", "high", "medium", "low"].map((sev) => (
              <div key={sev} className={`risk-summary-card risk-summary-${sev}`}>
                <div className="risk-summary-count">{severityCounts[sev] || 0}</div>
                <div className="risk-summary-label">
                  {sev === "critical" ? "🔴 " : sev === "high" ? "⚠️ " : sev === "medium" ? "⚡ " : "ℹ️ "}
                  {sev.charAt(0).toUpperCase() + sev.slice(1)}
                </div>
              </div>
            ))}
          </div>

          {/* Top risks */}
          <div className="risk-section">
            <h3>Top Risks</h3>
            <div className="risk-list">
              {topRisks.map((risk) => (
                <div key={risk.risk_id} className="risk-item">
                  <div className="risk-item-header">
                    <span className={`graph-risk-icon graph-risk-${risk.severity}`}>
                      {risk.severity === "critical" ? "🔴" : risk.severity === "high" ? "⚠️" : risk.severity === "medium" ? "⚡" : "ℹ️"}
                    </span>
                    <strong>{risk.title}</strong>
                    <span className={`graph-risk-severity graph-risk-${risk.severity}`}>{risk.severity}</span>
                    <span className="risk-category-badge">{risk.category}</span>
                    <span className={`graph-confidence graph-confidence-${risk.confidence}`}>{risk.confidence}</span>
                  </div>
                  {risk.description && <p className="risk-description">{risk.description}</p>}
                  {risk.recommended_actions?.length > 0 && (
                    <div className="risk-actions">
                      {risk.recommended_actions.slice(0, 2).map((action, i) => (
                        <span key={i} className="risk-action-tag">{action}</span>
                      ))}
                    </div>
                  )}
                  <div className="risk-meta">
                    {risk.evidence_ids?.length > 0 && <span>Evidence: {risk.evidence_ids.length} sources</span>}
                    {risk.related_entity_ids?.length > 0 && <span>Related entities: {risk.related_entity_ids.length}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Category breakdown */}
          {Object.keys(categoryCounts).length > 0 && (
            <div className="risk-section">
              <h3>Risk Categories</h3>
              <div className="risk-categories">
                {Object.entries(categoryCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cat, count]) => (
                    <div key={cat} className="risk-category-item">
                      <span className="risk-category-name">{cat}</span>
                      <span className="risk-category-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Refresh button */}
      <button className="risk-refresh-btn" onClick={loadRisks} disabled={loading}>
        {loading ? "Loading..." : "Refresh Risks"}
      </button>
    </div>
  );
}

export default RiskDashboard;
