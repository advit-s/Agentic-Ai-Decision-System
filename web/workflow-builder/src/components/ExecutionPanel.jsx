// components/ExecutionPanel.jsx
import React, { useState, useEffect } from "react";
import StructuredNodeOutput from "./StructuredNodeOutput";
import ClaimLedgerPanel from "./ClaimLedgerPanel";
import ReviewPanel from "./ReviewPanel";
import { listReviews, resolveReview } from "../api";
import "../styles/execution-panel.css";

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

function ExecutionPanel({ nodeStatuses, workflowStatus, elapsed, onClose, onExportReport }) {
  const [expandedNode, setExpandedNode] = useState(null);
  const [view, setView] = useState("ledger");
  const [reviews, setReviews] = useState([]);

  useEffect(() => {
    listReviews()
      .then((data) => setReviews(data.reviews || data || []))
      .catch(() => {});
  }, []);

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

  const statusIcon = (s) => STATUS_ICONS[s] || "○";
  const statusColor = (s) => STATUS_COLORS[s] || "#d1d5db";

  const completedCount = nodeStatuses.filter(
    (n) => n.status === "completed" || n.status === "skipped"
  ).length;

  const toggleExpand = (nodeId) => {
    setExpandedNode((prev) => (prev === nodeId ? null : nodeId));
  };

  const viewToggle = (
    <div className="execution-view-toggle">
      <button
        className={"execution-view-btn" + (view === "nodes" ? " active" : "")}
        onClick={() => setView("nodes")}
      >
        📋 Node View
      </button>
      <button
        className={"execution-view-btn" + (view === "ledger" ? " active" : "")}
        onClick={() => setView("ledger")}
      >
        📒 Claim Ledger
      </button>
      <button
        className={"execution-view-btn" + (view === "reviews" ? " active" : "")}
        onClick={() => setView("reviews")}
      >
        👁️ Reviews
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

  return (
    <div className="execution-panel">
      <div className="execution-panel-header">
        <div className="execution-panel-title">Execution</div>
        <button className="execution-close" onClick={onClose}>
          ✕
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

      {/* View toggle */}
      {viewToggle}

      <div className="execution-node-list">
        {nodeStatuses.map((ns) => (
          <div
            key={ns.nodeId}
            className={"execution-node-item" + (expandedNode === ns.nodeId ? " expanded" : "")}
            style={{ borderLeftColor: statusColor(ns.status) || "#d1d5db" }}
          >
            <div
              className="execution-node-header"
              onClick={() => toggleExpand(ns.nodeId)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") toggleExpand(ns.nodeId); }}
            >
              <span
                className="execution-node-icon"
                style={{ color: statusColor(ns.status) }}
              >
                {statusIcon(ns.status)}
              </span>
              <span className="execution-node-label">{ns.label}</span>
              {ns.duration !== undefined && (
                <span className="execution-node-duration">
                  {ns.duration.toFixed(2)}s
                </span>
              )}
              {(ns.inputs || ns.outputs) && (
                <span className="execution-node-expand-icon">
                  {expandedNode === ns.nodeId ? "▾" : "▸"}
                </span>
              )}
            </div>
            {ns.error && <div className="execution-node-error">{ns.error}</div>}
            {ns.status === "running" && (
              <div className="execution-progress-bar">
                <div className="execution-progress-fill" />
              </div>
            )}
            {expandedNode === ns.nodeId && (ns.inputs || ns.outputs) && (
              <div className="execution-node-data">
                {ns.inputs && Object.keys(ns.inputs).length > 0 && (
                  <div className="execution-data-section">
                    <div className="execution-data-label">Inputs</div>
                    <pre className="execution-data-json">{formatData(ns.inputs)}</pre>
                  </div>
                )}
                {ns.outputs && Object.keys(ns.outputs).length > 0 && (
                  <div className="execution-data-section">
                    <div className="execution-data-label">Outputs</div>
                    <StructuredNodeOutput outputs={ns.outputs} />
                    <details className="execution-raw-toggle">
                      <summary className="execution-raw-toggle-label">Raw JSON</summary>
                      <pre className="execution-data-json">{formatData(ns.outputs)}</pre>
                    </details>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExecutionPanel;
