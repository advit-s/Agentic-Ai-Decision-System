// components/ExecutionPanel.jsx
import React, { useState } from "react";
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

function ExecutionPanel({ nodeStatuses, workflowStatus, elapsed, onClose }) {
  const [expandedNode, setExpandedNode] = useState(null);

  const statusIcon = (s) => STATUS_ICONS[s] || "○";
  const statusColor = (s) => STATUS_COLORS[s] || "#d1d5db";

  const completedCount = nodeStatuses.filter(
    (n) => n.status === "completed" || n.status === "skipped"
  ).length;

  const toggleExpand = (nodeId) => {
    setExpandedNode((prev) => (prev === nodeId ? null : nodeId));
  };

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
                    <pre className="execution-data-json">{formatData(ns.outputs)}</pre>
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
