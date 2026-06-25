// components/TrustDashboard.jsx — Workspace trust dashboard
// Shows verification summary, contradiction list, trust health, and reports.
import React, { useState, useEffect, useCallback } from "react";
import {
  verifyWorkspaceClaims,
  getWorkspaceVerificationSummary,
  scanWorkspaceContradictions,
  listWorkspaceContradictions,
} from "../api";

const HEALTH_LABELS = {
  healthy: { label: "Healthy", color: "#166534", bg: "#dcfce7" },
  needs_review: { label: "Needs Review", color: "#854d0e", bg: "#fef9c3" },
  high_contradiction: { label: "High Contradiction Risk", color: "#991b1b", bg: "#fee2e2" },
  low_evidence: { label: "Low Evidence Coverage", color: "#6b7280", bg: "#f3f4f6" },
  no_claims: { label: "No Claims Yet", color: "#4b5563", bg: "#f3f4f6" },
};

function getTrustHealth(summary) {
  if (!summary || !summary.total_claims) return HEALTH_LABELS.no_claims;
  if (summary.contradicted > summary.total_claims * 0.3) return HEALTH_LABELS.high_contradiction;
  if (summary.evidence_coverage_score < 0.3) return HEALTH_LABELS.low_evidence;
  if (summary.unsupported > summary.total_claims * 0.4) return HEALTH_LABELS.needs_review;
  return HEALTH_LABELS.healthy;
}

/* ── Internal components ────────────────────────── */

function TrustHealthBadge({ health }) {
  return (
    <span style={{
      display: "inline-block",
      background: health.bg,
      color: health.color,
      padding: "4px 12px",
      borderRadius: "20px",
      fontSize: "0.85rem",
      fontWeight: 600,
    }}>
      {health.label}
    </span>
  );
}

function MetricCard({ label, value, color }) {
  return (
    <div style={{ background: "#fff", borderRadius: "8px", padding: "12px", textAlign: "center", border: "1px solid #e5e7eb" }}>
      <div style={{ fontSize: "1.5rem", fontWeight: 700, color: color || "#374151" }}>{value ?? "—"}</div>
      <div style={{ fontSize: "0.75rem", color: "#6b7280", marginTop: "4px" }}>{label}</div>
    </div>
  );
}

/* ── Main component ────────────────────────────── */

export default function TrustDashboard({ workspaceId, onClose }) {
  const [summary, setSummary] = useState(null);
  const [contradictions, setContradictions] = useState([]);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [scanning, setScanning] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const s = await getWorkspaceVerificationSummary(workspaceId);
      if (s) setSummary(s);
    } catch {
      // No data
    }
    try {
      const cons = await listWorkspaceContradictions(workspaceId);
      if (cons && cons.contradictions) setContradictions(cons.contradictions);
    } catch {
      // No contradictions
    }
    try {
      // Try to load existing reports for the workspace
      const base = typeof window !== "undefined" && localStorage.getItem("wfBuilderApiBaseUrl");
      if (base) {
        const resp = await fetch(`${base}/workspaces/${workspaceId}/reports`);
        if (resp.ok) {
          const data = await resp.json();
          setReports(data.reports || []);
        }
      }
    } catch {
      // Mock mode or no reports
    }
    setLoading(false);
  }, [workspaceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const health = getTrustHealth(summary);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await verifyWorkspaceClaims(workspaceId);
      // Reload summary from the dedicated summary endpoint
      const s = await getWorkspaceVerificationSummary(workspaceId);
      if (s) setSummary(s);
    } catch (err) {
      console.error("Workspace verification failed", err);
    }
    setVerifying(false);
  };

  const handleScan = async () => {
    setScanning(true);
    try {
      const result = await scanWorkspaceContradictions(workspaceId);
      if (result && result.contradictions) setContradictions(result.contradictions);
    } catch (err) {
      console.error("Contradiction scan failed", err);
    }
    setScanning(false);
  };

  const handleGenerateReport = async () => {
    try {
      // Try listing executions to find the latest one
      const base = typeof window !== "undefined" && localStorage.getItem("wfBuilderApiBaseUrl");
      if (base) {
        const execResp = await fetch(base + "/workspaces/" + workspaceId + "/executions");
        if (execResp.ok) {
          const execData = await execResp.json();
          const execs = Array.isArray(execData) ? execData : (execData.executions || execData.items || []);
          if (execs.length > 0) {
            const latestExecId = execs[0].execution_id || execs[0].id;
            await fetch(base + "/executions/" + latestExecId + "/report?mode=deterministic", { method: "POST" });
          }
        }
      }
      // Reload data to pick up new report
      await loadData();
    } catch (err) {
      console.error("Report generation failed", err);
    }
  };

  const metrics = [
    { key: "total_claims", label: "Total Claims", color: "#6b7280" },
    { key: "supported", label: "Supported", color: "#166534" },
    { key: "contradicted", label: "Contradicted", color: "#991b1b" },
    { key: "unsupported", label: "Unsupported", color: "#854d0e" },
    { key: "uncertain", label: "Uncertain", color: "#6b7280" },
    { key: "needs_review", label: "Needs Review", color: "#7c3aed" },
  ];

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Trust Dashboard</div>
        <button className="execution-close" onClick={onClose}>✕</button>
      </div>

      <div style={{ padding: "12px", overflow: "auto", flex: 1 }}>
        {/* Trust Health */}
        {!loading && (
          <div style={{ marginBottom: "16px", textAlign: "center" }}>
            <TrustHealthBadge health={health} />
            <div style={{ fontSize: "0.8rem", color: "#6b7280", marginTop: "4px" }}>
              Workspace trust health assessment
            </div>
          </div>
        )}

        {/* Action buttons */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}>
          <button
            className="execution-replay-btn"
            style={{ background: "#059669", color: "#fff", borderColor: "#059669" }}
            onClick={handleVerify}
            disabled={verifying}
          >
            {verifying ? "Verifying..." : "✓ Verify All Claims"}
          </button>
          <button
            className="execution-replay-btn"
            style={{ background: "#2563eb", color: "#fff", borderColor: "#2563eb" }}
            onClick={handleGenerateReport}
            disabled={loading || !summary}
          >
            {"📄 Generate Report"}
          </button>
          <button
            className="execution-replay-btn"
            style={{ background: "#d97706", color: "#fff", borderColor: "#d97706" }}
            onClick={handleScan}
            disabled={scanning}
          >
            {scanning ? "Scanning..." : "⚡ Scan Contradictions"}
          </button>
          <button
            className="execution-replay-btn"
            style={{ background: "#f3f4f6", color: "#374151", borderColor: "#d1d5db" }}
            onClick={loadData}
          >
            🔄 Refresh
          </button>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ textAlign: "center", padding: "40px", color: "#6b7280" }}>
            Loading trust data...
          </div>
        )}

        {/* No data state */}
        {!loading && (!summary || !summary.total_claims) && (
          <div style={{ textAlign: "center", padding: "40px 20px", color: "#6b7280" }}>
            <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🔍</div>
            <div style={{ fontWeight: 500 }}>No claims or verification data found.</div>
            <div style={{ fontSize: "0.85rem", marginTop: "4px" }}>
              Run a workflow to generate claims, then verify them to see trust metrics.
            </div>
          </div>
        )}

        {/* Metrics grid */}
        {summary && summary.total_claims > 0 && (
          <>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px" }}>Verification Overview</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px", marginBottom: "16px" }}>
              {metrics.map(m => (
                <MetricCard key={m.key} label={m.label} value={summary[m.key]} color={m.color} />
              ))}
            </div>

            {/* Additional metrics */}
            <div style={{ background: "#f9fafb", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
              <div style={{ display: "flex", gap: "20px", fontSize: "0.85rem", color: "#374151", flexWrap: "wrap" }}>
                {summary.average_confidence != null && (
                  <span><strong>Avg Confidence:</strong> {(summary.average_confidence * 100).toFixed(0)}%</span>
                )}
                {summary.evidence_coverage_score != null && (
                  <span><strong>Evidence Coverage:</strong> {(summary.evidence_coverage_score * 100).toFixed(0)}%</span>
                )}
                {summary.contradiction_count != null && (
                  <span><strong>Contradictions:</strong> {summary.contradiction_count}</span>
                )}
              </div>
            </div>

            {/* Evidence breakdown */}
            {summary.evidence_breakdown && (
              <div style={{ background: "#f9fafb", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
                <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px" }}>Evidence Quality</div>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
                  {Object.entries(summary.evidence_breakdown).map(([key, val]) => (
                    <MetricCard key={key} label={key.charAt(0).toUpperCase() + key.slice(1)} value={val} />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Recent reports */}
        {reports.length > 0 && (
          <div style={{ background: "#f9fafb", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px" }}>
              📄 Reports ({reports.length})
            </div>
            {reports.slice(0, 5).map((r, i) => (
              <div key={r.report_id || i} style={{
                padding: "8px", borderBottom: i < Math.min(reports.length, 5) - 1 ? "1px solid #e5e7eb" : "none",
                fontSize: "0.85rem", cursor: "pointer"
              }}>
                <div style={{ fontWeight: 500 }}>{r.title || `Report ${r.report_id}`}</div>
                <div style={{ color: "#6b7280", fontSize: "0.75rem" }}>
                  {r.generated_at ? new Date(r.generated_at).toLocaleString() : ""}
                  {r.status ? ` — ${r.status}` : ""}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Contradictions */}
        {contradictions.length > 0 && (
          <div style={{ background: "#fef2f2", borderRadius: "8px", padding: "12px", marginBottom: "16px" }}>
            <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px", color: "#991b1b" }}>
              ⚡ Contradictions ({contradictions.length})
            </div>
            {contradictions.map((con, i) => (
              <div key={con.id || i} style={{ padding: "8px", borderBottom: i < contradictions.length - 1 ? "1px solid #fecaca" : "none", fontSize: "0.85rem" }}>
                <div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "4px" }}>
                  <span style={{
                    background: con.severity === "high" ? "#fee2e2" : con.severity === "medium" ? "#fef9c3" : "#f3f4f6",
                    color: con.severity === "high" ? "#991b1b" : con.severity === "medium" ? "#854d0e" : "#4b5563",
                    padding: "0 6px", borderRadius: "4px", fontSize: "0.7rem", fontWeight: 600
                  }}>{con.severity}</span>
                  <span style={{ fontWeight: 500 }}>{con.type?.replace(/_/g, ' ')}</span>
                </div>
                <div style={{ color: "#4b5563" }}>{con.description}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
