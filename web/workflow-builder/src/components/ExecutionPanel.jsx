// components/ExecutionPanel.jsx
import React, { useState, useEffect, useRef, useCallback } from "react";
import StructuredNodeOutput from "./StructuredNodeOutput";
import ClaimLedgerPanel from "./ClaimLedgerPanel";
import ReviewPanel from "./ReviewPanel";
import { listReviews, resolveReview } from "../api";
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

  // Node View (default)
  const showReplay =
    workflowStatus === "completed" && typeof onReplayFrom === "function";

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
        {nodeStatuses.map((ns) => {
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
