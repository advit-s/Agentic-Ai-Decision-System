// components/ExecutionPanel.jsx
import React from "react";
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

function ExecutionPanel({ nodeStatuses, workflowStatus, elapsed, onClose }) {
  const statusIcon = (s) => STATUS_ICONS[s] || "○";
  const statusColor = (s) => STATUS_COLORS[s] || "#d1d5db";

  const completedCount = nodeStatuses.filter(
    (n) => n.status === "completed" || n.status === "skipped"
  ).length;

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

      <div className="execution-node-list">
        {nodeStatuses.map((ns) => (
          <div
            key={ns.nodeId}
            className="execution-node-item"
            style={{ borderLeftColor: statusColor(ns.status) || "#d1d5db" }}
          >
            <div className="execution-node-header">
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
            </div>
            {ns.error && <div className="execution-node-error">{ns.error}</div>}
            {ns.status === "running" && (
              <div className="execution-progress-bar">
                <div className="execution-progress-fill" />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExecutionPanel;
