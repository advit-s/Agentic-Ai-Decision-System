// components/ExecutionPanel.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import StructuredNodeOutput from "./StructuredNodeOutput";
import ClaimLedgerPanel from "./ClaimLedgerPanel";
import ReviewPanel from "./ReviewPanel";
import { listReviews, resolveReview } from "../api";
import {
  verifyExecutionClaims,
  getExecutionVerificationSummary,
  scanWorkspaceContradictions,
  listWorkspaceContradictions,
  generateTrustReport,
} from "../api";
import "../styles/execution-panel.css";
import "../styles/execution-timeline.css";

const STATUS_ICONS = {
  pending: "○",
  running: "⟳",
  completed: "✅",
  failed: "❌",
  skipped: "⏭",
};

const STATUS_COLORS = {
  pending: "#9ca3af",
  running: "#eab308",
  completed: "#22c55e",
  failed: "#ef4444",
  skipped: "#6b7280",
};

/* ── Output preview badge helper ───────────────── */

function getOutputBadge(outputs) {
  if (!outputs || Object.keys(outputs).length === 0) return null;

  // Specialized node type detection (mirrors StructuredNodeOutput logic)
  if (Array.isArray(outputs.findings) && outputs.findings.length > 0) {
    const first = outputs.findings[0];
    if (typeof first.statement === "string") {
      return { emoji: "📚", text: `${outputs.findings.length} findings` };
    }
  }

  if (typeof outputs.passed === "boolean" && Array.isArray(outputs.issues)) {
    return { emoji: "⚖️", text: `${outputs.issues.length} issues` };
  }

  if (Array.isArray(outputs.options) && outputs.options.length > 0) {
    const first = outputs.options[0];
    if (typeof first.title === "string" || typeof first.name === "string") {
      return { emoji: "🎯", text: `${outputs.options.length} options` };
    }
  }

  if (
    typeof outputs.analysis === "object" &&
    outputs.analysis !== null &&
    !Array.isArray(outputs.analysis)
  ) {
    const keyCount = Object.keys(outputs.analysis).length;
    return { emoji: "📊", text: `${keyCount} metrics` };
  }

  // Generic fallback
  const keyCount = Object.keys(outputs).length;
  return { emoji: "📦", text: `${keyCount} keys` };
}

/* ── Timeline view sub-component ───────────────── */

function ExecutionTimeline({ nodeStatuses }) {
  const hasDurations = nodeStatuses.some(n => n.duration !== undefined && n.duration > 0);
  const totalElapsed = nodeStatuses.reduce(
    (max, n) => Math.max(max, n.duration || 0),
    0
  );

  if (!hasDurations || totalElapsed === 0) {
    return (
      <div className="et-panel">
        <div className="et-empty">
          Running...<div className="et-empty-hint">Timeline will appear once nodes complete</div>
        </div>
      </div>
    );
  }

  return (
    <div className="et-panel">
      <div className="et-header">Execution Timeline</div>
      <div className="et-bar-chart">
        {nodeStatuses.map(ns => {
          const pct = totalElapsed > 0 ? ((ns.duration || 0) / totalElapsed) * 100 : 0;
          return (
            <div key={ns.nodeId} className="et-bar-row">
              <span className="et-bar-label" title={ns.label}>
                {ns.label}
              </span>
              <div className="et-bar-track">
                <div
                  className={"et-bar-fill et-status-" + (ns.status || "pending")}
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
              </div>
              <span className="et-bar-duration">
                {ns.duration !== undefined ? `${ns.duration.toFixed(2)}s` : "—"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Verification summary view ──────────────────── */

function VerificationSummaryView({ summary, contradictions, onVerify, onScanContradictions, onGenerateReport, verifying, scanning, generatingReport, reportResult, nodeStatuses }) {
  const hasData = summary && summary.total_claims > 0;
  const hasClaims = nodeStatuses.some(ns => {
    const outs = ns.outputs || {};
    return (Array.isArray(outs.findings) && outs.findings.length > 0) || (Array.isArray(outs.issues) && outs.issues.length > 0);
  });

  const metrics = [
    { key: "total_claims", label: "Total Claims", color: "#6b7280" },
    { key: "supported", label: "Supported", color: "#166534" },
    { key: "contradicted", label: "Contradicted", color: "#991b1b" },
    { key: "unsupported", label: "Unsupported", color: "#854d0e" },
    { key: "uncertain", label: "Uncertain", color: "#6b7280" },
    { key: "needs_review", label: "Needs Review", color: "#7c3aed" },
  ];

  return (
    <div style={{ padding: "12px", overflow: "auto", flex: 1 }}>
      {/* Action buttons */}
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        <button
          className="execution-replay-btn"
          style={{ background: "#059669", color: "#fff", borderColor: "#059669" }}
          onClick={onVerify}
          disabled={verifying || !hasClaims}
          title="Verify all claims in this execution"
        >
          {verifying ? "Verifying..." : "✓ Verify Execution"}
        </button>
        <button
          className="execution-replay-btn"
          style={{ background: "#d97706", color: "#fff", borderColor: "#d97706" }}
          onClick={onScanContradictions}
          disabled={scanning || !hasClaims}
          title="Scan for contradictions in this execution"
        >
          {scanning ? "Scanning..." : "⚡ Scan Contradictions"}
        </button>
        <button
          className="execution-replay-btn"
          style={{ background: "#7c3aed", color: "#fff", borderColor: "#7c3aed" }}
          onClick={onGenerateReport}
          disabled={generatingReport || !hasData}
          title="Generate trust report from verification results"
        >
          {generatingReport ? "Generating..." : "📄 Generate Trust Report"}
        </button>
      </div>

      {/* No claims state */}
      {!hasClaims && !hasData && (
        <div style={{ textAlign: "center", padding: "40px 20px", color: "#6b7280" }}>
          <div style={{ fontSize: "2rem", marginBottom: "8px" }}>🔍</div>
          <div style={{ fontWeight: 500 }}>Verification has not been run for this execution yet.</div>
          <div style={{ fontSize: "0.85rem", marginTop: "4px" }}>Execute a workflow with Researcher nodes to generate claims, then verify them.</div>
        </div>
      )}

      {/* Verification summary */}
      {hasData && (
        <div style={{ background: "#f9fafb", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
          <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px" }}>Verification Summary</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "8px" }}>
            {metrics.map(m => (
              <div key={m.key} style={{ background: "#fff", borderRadius: "6px", padding: "8px", textAlign: "center", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: "1.2rem", fontWeight: 700, color: m.color }}>{summary[m.key] ?? 0}</div>
                <div style={{ fontSize: "0.7rem", color: "#6b7280", marginTop: "2px" }}>{m.label}</div>
              </div>
            ))}
          </div>
          <div style={{ display: "flex", gap: "16px", marginTop: "8px", fontSize: "0.85rem", color: "#374151" }}>
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
      )}

      {/* Evidence breakdown */}
      {hasData && summary.evidence_breakdown && (
        <div style={{ background: "#f9fafb", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
          <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "8px" }}>Evidence Quality Breakdown</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(100px, 1fr))", gap: "8px" }}>
            {Object.entries(summary.evidence_breakdown).map(([key, val]) => (
              <div key={key} style={{ background: "#fff", borderRadius: "6px", padding: "8px", textAlign: "center", border: "1px solid #e5e7eb" }}>
                <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "#374151" }}>{val}</div>
                <div style={{ fontSize: "0.7rem", color: "#6b7280", marginTop: "2px", textTransform: "capitalize" }}>{key}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Contradictions */}
      {contradictions.length > 0 && (
        <div style={{ background: "#fef2f2", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
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

      {/* Report result */}
      {reportResult && (
        <div style={{ background: "#ecfdf5", borderRadius: "8px", padding: "12px", marginBottom: "12px" }}>
          <div style={{ fontWeight: 600, fontSize: "0.85rem", marginBottom: "4px", color: "#065f46" }}>
            ✅ Trust Report Generated
          </div>
          <div style={{ fontSize: "0.85rem", color: "#374151" }}>
            Report ID: {reportResult.report_id}<br />
            Title: {reportResult.title || "Trust Report"}<br />
            Generated: {new Date(reportResult.generated_at).toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Format data helper ────────────────────────── */

function formatData(data) {
  if (data === null || data === undefined) return "—";
  try {
    const str = typeof data === "object" ? JSON.stringify(data, null, 2) : String(data);
    if (str.length > 2000) return str.slice(0, 2000) + "\n… (truncated)";
    return str;
  } catch {
    return String(data);
  }
}

/* ── Main component ────────────────────────────── */

function ExecutionPanel({
  nodeStatuses,
  workflowStatus,
  elapsed,
  onClose,
  onExportReport,
  onEditNode,
  onReplayFrom,
  editReplayNodeId,
}) {
  const [expandedNode, setExpandedNode] = useState(null);
  const [view, setView] = useState("ledger");
  const [reviews, setReviews] = useState([]);
  const [autoExpand, setAutoExpand] = useState(false);
  const [verificationSummary, setVerificationSummary] = useState(null);
  const [verificationContradictions, setVerificationContradictions] = useState([]);
  const [verifying, setVerifying] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [reportResult, setReportResult] = useState(null);
  const nodeListRef = useRef(null);
  const autoExpandTimerRef = useRef(null);

  useEffect(() => {
    listReviews()
      .then((data) => setReviews(data.reviews || data || []))
      .catch(() => {});
  }, []);

  // Auto-expand and auto-scroll when autoExpand is enabled and a node completes
  useEffect(() => {
    if (!autoExpand) return;

    // Find the latest completed/failed node
    const terminalStatuses = new Set(["completed", "failed"]);
    const latest = nodeStatuses.reduce((prev, curr) => {
      if (terminalStatuses.has(curr.status)) return curr;
      return prev;
    }, null);

    if (latest && terminalStatuses.has(latest.status)) {
      // Use a small delay to let the DOM update
      clearTimeout(autoExpandTimerRef.current);
      autoExpandTimerRef.current = setTimeout(() => {
        setExpandedNode(latest.nodeId);
        // Auto-scroll
        if (nodeListRef.current) {
          const el = nodeListRef.current.querySelector(`[data-node-id="${latest.nodeId}"]`);
          if (el) {
            el.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }
      }, 100);
    }

    return () => clearTimeout(autoExpandTimerRef.current);
  }, [autoExpand, nodeStatuses]);

  const handleApprove = (reviewId, notes) => {
    resolveReview(reviewId, "approve", notes, null, "admin")
      .then((updated) => {
        setReviews((prev) =>
          prev.map((r) => ((r.review_id || r.id) === reviewId ? { ...r, ...updated } : r))
        );
      })
      .catch(() => {});
  };

  const handleReject = (reviewId, notes) => {
    resolveReview(reviewId, "reject", notes, null, "admin")
      .then((updated) => {
        setReviews((prev) =>
          prev.map((r) => ((r.review_id || r.id) === reviewId ? { ...r, ...updated } : r))
        );
      })
      .catch(() => {});
  };

  const handleRequestChanges = (reviewId, notes, modifiedData) => {
    resolveReview(reviewId, "request_changes", notes, modifiedData, "admin")
      .then((updated) => {
        setReviews((prev) =>
          prev.map((r) => ((r.review_id || r.id) === reviewId ? { ...r, ...updated } : r))
        );
      })
      .catch(() => {});
  };

  // Load verification summary when switching to verification view
  useEffect(() => {
    if (view !== "verification") return;
    const executionId = nodeStatuses.length > 0 ? nodeStatuses[0].execution_id || "exec-1" : "exec-1";
    getExecutionVerificationSummary(executionId)
      .then((data) => {
        if (data) setVerificationSummary(data);
      })
      .catch(() => {
        // No verification data yet
      });
  }, [view, nodeStatuses]);

  const handleVerifyExecution = useCallback(async () => {
    setVerifying(true);
    try {
      const executionId = nodeStatuses.length > 0 ? nodeStatuses[0].execution_id || "exec-1" : "exec-1";
      const result = await verifyExecutionClaims(executionId);
      if (result && result.summary) setVerificationSummary(result.summary);
    } catch (err) {
      console.error("Execution verification failed", err);
    }
    setVerifying(false);
  }, [nodeStatuses]);

  const handleScanContradictions = useCallback(async () => {
    setScanning(true);
    try {
      const workspaceId = "ws-1";
      const result = await scanWorkspaceContradictions(workspaceId);
      if (result && result.contradictions) setVerificationContradictions(result.contradictions);
    } catch (err) {
      console.error("Contradiction scan failed", err);
    }
    setScanning(false);
  }, []);

  const handleGenerateReport = useCallback(async () => {
    setGeneratingReport(true);
    try {
      const executionId = nodeStatuses.length > 0 ? nodeStatuses[0].execution_id || "exec-1" : "exec-1";
      const result = await generateTrustReport(executionId);
      setReportResult(result);
    } catch (err) {
      console.error("Report generation failed", err);
    }
    setGeneratingReport(false);
  }, [nodeStatuses]);

  const statusIcon = (s) => STATUS_ICONS[s] || "○";
  const statusColor = (s) => STATUS_COLORS[s] || "#d1d5db";

  const completedCount = nodeStatuses.filter(
    (n) => n.status === "completed" || n.status === "skipped"
  ).length;

  const toggleExpand = (nodeId) => {
    setExpandedNode((prev) => (prev === nodeId ? null : nodeId));
  };

  const handleEditClick = useCallback(
    (nodeId, e) => {
      e.stopPropagation();
      if (onEditNode) onEditNode(nodeId);
    },
    [onEditNode]
  );

  const handleReplayClick = useCallback(
    (nodeId, e) => {
      e.stopPropagation();
      if (onReplayFrom) onReplayFrom(nodeId);
    },
    [onReplayFrom]
  );

  const handleAutoExpandToggle = useCallback((e) => {
    setAutoExpand(e.target.checked);
  }, []);

  const viewToggle = (
    <div className="execution-view-toggle">
      <button
        className={"execution-view-btn" + (view === "nodes" ? " active" : "")}
        onClick={() => setView("nodes")}
      >
        {"📋"} Node View
      </button>
      <button
        className={"execution-view-btn" + (view === "ledger" ? " active" : "")}
        onClick={() => setView("ledger")}
      >
        {"📒"} Claim Ledger
      </button>
      <button
        className={"execution-view-btn" + (view === "reviews" ? " active" : "")}
        onClick={() => setView("reviews")}
      >
        {"👁️"} Reviews
      </button>
      <button
        className={"execution-view-btn" + (view === "timeline" ? " active" : "")}
        onClick={() => setView("timeline")}
      >
        {"📊"} Timeline
      </button>
      <button
        className={"execution-view-btn" + (view === "verification" ? " active" : "")}
        onClick={() => setView("verification")}
      >
        {"🔍"} Verification
      </button>
    </div>
  );

  // Claim Ledger view
  if (view === "ledger") {
    return (
      <ClaimLedgerPanel
        nodeStatuses={nodeStatuses}
        onClose={onClose}
        onExportReport={onExportReport}
        viewToggle={viewToggle}
      />
    );
  }

  // Reviews view
  if (view === "reviews") {
    return (
      <ReviewPanel
        reviews={reviews}
        onApprove={handleApprove}
        onReject={handleReject}
        onRequestChanges={handleRequestChanges}
        onClose={onClose}
        viewToggle={viewToggle}
      />
    );
  }

  // Timeline view
  if (view === "timeline") {
    return (
      <div className="execution-panel">
        <div className="execution-panel-header">
          <div className="execution-panel-title">Execution</div>
          <button className="execution-close" onClick={onClose}>
            {"✕"}
          </button>
        </div>
        <div className="execution-summary">
          <span
            className="execution-status-badge"
            style={{ background: statusColor(workflowStatus) || "#6b7280" }}
          >
            {workflowStatus}
          </span>
          <span className="execution-progress">
            {completedCount}/{nodeStatuses.length} nodes
          </span>
          {elapsed > 0 && (
            <span className="execution-elapsed">{elapsed.toFixed(1)}s</span>
          )}
        </div>
        {viewToggle}
        <ExecutionTimeline nodeStatuses={nodeStatuses} />
      </div>
    );
  }

  // Verification view
  if (view === "verification") {
    return (
      <div className="execution-panel">
        <div className="execution-panel-header">
          <div className="execution-panel-title">Execution Verification</div>
          <button className="execution-close" onClick={onClose}>
            {"✕"}
          </button>
        </div>
        <div className="execution-summary">
          <span
            className="execution-status-badge"
            style={{ background: statusColor(workflowStatus) || "#6b7280" }}
          >
            {workflowStatus}
          </span>
          <span className="execution-progress">
            {completedCount}/{nodeStatuses.length} nodes
          </span>
          {elapsed > 0 && (
            <span className="execution-elapsed">{elapsed.toFixed(1)}s</span>
          )}
        </div>
        {viewToggle}
        <VerificationSummaryView
          summary={verificationSummary}
          contradictions={verificationContradictions}
          onVerify={handleVerifyExecution}
          onScanContradictions={handleScanContradictions}
          onGenerateReport={handleGenerateReport}
          verifying={verifying}
          scanning={scanning}
          generatingReport={generatingReport}
          reportResult={reportResult}
          nodeStatuses={nodeStatuses}
        />
      </div>
    );
  }

  // Node View (default)
  const showReplay =
    workflowStatus === "completed" && typeof onReplayFrom === "function";

  // Skeleton loading when no nodes have been executed yet
  const showSkeletons =
    nodeStatuses.length === 0 ||
    (workflowStatus === "idle" &&
      nodeStatuses.every((n) => n.status === "pending" || n.status === "idle"));

  function renderSkeletons(count = 4) {
    return Array.from({ length: count }, (_, i) => (
      <div key={`skeleton-${i}`} className="execution-skeleton-row">
        <div className="execution-skeleton-dot" />
        <div className="execution-skeleton-bar" style={{ maxWidth: `${60 + Math.random() * 30}%` }} />
        <div className="execution-skeleton-short" />
      </div>
    ));
  }

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Execution</div>
        <button className="execution-close" onClick={onClose}>
          {"✕"}
        </button>
      </div>

      <div className="execution-summary">
        <span
          className="execution-status-badge"
          style={{ background: statusColor(workflowStatus) || "#6b7280" }}
        >
          {workflowStatus}
        </span>
        <span className="execution-progress">
          {completedCount}/{nodeStatuses.length} nodes
        </span>
        {elapsed > 0 && (
          <span className="execution-elapsed">{elapsed.toFixed(1)}s</span>
        )}
      </div>

      {/* Auto-expand toggle (C1c) */}
      <label className="execution-auto-expand-toggle">
        <input
          type="checkbox"
          checked={autoExpand}
          onChange={handleAutoExpandToggle}
        />
        Auto-expand completed nodes
      </label>

      {/* View toggle */}
      {viewToggle}

      <div className="execution-node-list execution-auto-scroll" ref={nodeListRef}>
        {showSkeletons
          ? renderSkeletons()
          : nodeStatuses.map((ns) => {
          const badge = ns.status === "completed" || ns.status === "failed"
            ? getOutputBadge(ns.outputs)
            : null;
          const isRunning = ns.status === "running";
          const isTerminal = ns.status === "completed" || ns.status === "failed";
          const canReplay = showReplay && isTerminal;

          return (
            <div
              key={ns.nodeId}
              data-node-id={ns.nodeId}
              className={
                "execution-node-item" +
                (expandedNode === ns.nodeId ? " expanded" : "") +
                (isRunning ? " execution-streaming" : "")
              }
              style={{ borderLeftColor: statusColor(ns.status) || "#d1d5db" }}
            >
              <div
                className="execution-node-header"
                onClick={() => toggleExpand(ns.nodeId)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ")
                    toggleExpand(ns.nodeId);
                }}
              >
                <span
                  className="execution-node-icon"
                  style={{ color: statusColor(ns.status) }}
                >
                  {statusIcon(ns.status)}
                </span>
                <span className="execution-node-label">{ns.label}</span>

                {/* Output preview badge (C1b) */}
                {badge && (
                  <span className="execution-preview-badge" title={badge.text}>
                    {badge.emoji} {badge.text}
                  </span>
                )}

                {/* Streaming indicator text (C1a) */}
                {isRunning && (
                  <span className="execution-streaming-text">Streaming...</span>
                )}

                {ns.duration !== undefined && (
                  <span className="execution-node-duration">
                    {ns.duration.toFixed(2)}s
                  </span>
                )}

                {/* Edit & Replay button (C2b) */}
                {canReplay && (
                  <button
                    className="execution-replay-btn"
                    onClick={(e) => handleEditClick(ns.nodeId, e)}
                    title="Edit and replay from this node"
                  >
                    {"✏️"} Edit
                  </button>
                )}

                {/* Replay from button (shown when this node is the one being edited) */}
                {canReplay && editReplayNodeId === ns.nodeId && (
                  <button
                    className="execution-replay-btn"
                    style={{
                      background: "#3b82f6",
                      color: "#fff",
                      borderColor: "#3b82f6",
                    }}
                    onClick={(e) => handleReplayClick(ns.nodeId, e)}
                    title="Replay execution from this node"
                  >
                    {"▶"} Replay
                  </button>
                )}

                {(ns.inputs || ns.outputs) && (
                  <span className="execution-node-expand-icon">
                    {expandedNode === ns.nodeId ? "▾" : "▸"}
                  </span>
                )}
              </div>
              {ns.error && <div className="execution-node-error">{ns.error}</div>}

              {/* Progress bar for running nodes */}
              {isRunning && (
                <div className="execution-progress-bar">
                  <div className="execution-progress-fill" />
                </div>
              )}

              {/* Partial output during streaming (C1a) */}
              {isRunning && ns.outputs && Object.keys(ns.outputs).length > 0 && (
                <div className="execution-partial">
                  Partial output: {JSON.stringify(ns.outputs).slice(0, 300)}
                  {JSON.stringify(ns.outputs).length > 300 ? "..." : ""}
                </div>
              )}

              {/* Expanded node data (inputs + outputs) */}
              {expandedNode === ns.nodeId && (ns.inputs || ns.outputs) && (
                <div className="execution-node-data">
                  {ns.inputs && Object.keys(ns.inputs).length > 0 && (
                    <div className="execution-data-section">
                      <div className="execution-data-label">Inputs</div>
                      <pre className="execution-data-json">
                        {formatData(ns.inputs)}
                      </pre>
                    </div>
                  )}
                  {ns.outputs && Object.keys(ns.outputs).length > 0 && (
                    <div className="execution-data-section">
                      <div className="execution-data-label">Outputs</div>
                      <StructuredNodeOutput outputs={ns.outputs} />
                      <details className="execution-raw-toggle">
                        <summary className="execution-raw-toggle-label">
                          Raw JSON
                        </summary>
                        <pre className="execution-data-json">
                          {formatData(ns.outputs)}
                        </pre>
                      </details>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ExecutionPanel;
