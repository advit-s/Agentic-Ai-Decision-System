// components/NodeComponent.jsx — Custom React Flow node with status effects
import React, { memo } from "react";
import { Handle, Position } from "reactflow";
import { getNodeCategoryConfig } from "../nodeTypes";

const STATUS_GLYPH = {
  idle: "",
  running: "⟳",
  completed: "✓",
  failed: "✕",
  skipped: "—",
};

const NodeComponent = memo(({ id, data, selected }) => {
  const catConfig = getNodeCategoryConfig(data.category);
  const status = data.status || "idle";

  // Use per-type icon/color from node data, fall back to category config
  const nodeIcon = data.icon || catConfig.icon;
  const nodeColor = data.color || catConfig.color;

  const statusClasses = {
    idle: "",
    running: "node-status-running",
    completed: "node-status-completed",
    failed: "node-status-failed",
    skipped: "node-status-skipped",
  };

  const hasInputs = data.inputPorts && data.inputPorts.length > 0;
  const hasOutputs = data.outputPorts && data.outputPorts.length > 0;

  const isTerminal = status === "completed" || status === "failed" || status === "skipped";

  return (
    <div
      className={`custom-node ${selected ? "selected" : ""} ${statusClasses[status] || ""}`}
      style={{ borderColor: nodeColor }}
    >
      {/* Input handles */}
      {hasInputs
        ? data.inputPorts.map((port, i) => (
            <Handle
              key={`in-${port}`}
              type="target"
              position={Position.Left}
              id={port}
              style={{ top: `${((i + 1) / (data.inputPorts.length + 1)) * 100}%` }}
              title={port}
            />
          ))
        : (
          <Handle type="target" position={Position.Left} id="default" style={{ top: "50%" }} />
        )}

      {/* Node header */}
      <div className="node-header" style={{ background: nodeColor }}>
        <span className="node-icon">{nodeIcon}</span>
        <span className="node-type-label">{data.label || data.typeLabel}</span>
      </div>

      {/* Node body */}
      <div className="node-body">
        {status === "running" ? (
          <span className="node-spinner" title="Running…">⟳</span>
        ) : isTerminal ? (
          <span
            className="node-status-glyph"
            style={{
              fontSize: "14px",
              fontWeight: 700,
              color:
                status === "completed" ? "var(--color-success)"
                : status === "failed" ? "var(--color-danger)"
                : "var(--color-text-muted)",
            }}
          >
            {STATUS_GLYPH[status]}
          </span>
        ) : data.description ? (
          <span className="node-description">{data.description}</span>
        ) : null}
      </div>

      {/* Output handles */}
      {hasOutputs
        ? data.outputPorts.map((port, i) => (
            <Handle
              key={`out-${port}`}
              type="source"
              position={Position.Right}
              id={port}
              style={{ top: `${((i + 1) / (data.outputPorts.length + 1)) * 100}%` }}
              title={port}
            />
          ))
        : (
          <Handle type="source" position={Position.Right} id="default" style={{ top: "50%" }} />
        )}
    </div>
  );
});

NodeComponent.displayName = "NodeComponent";

export default NodeComponent;
