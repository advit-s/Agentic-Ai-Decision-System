// components/WorkflowCanvas.jsx
import React, { useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";
import "../styles/canvas.css";
import NodeComponent from "./NodeComponent";

const nodeTypes = { custom: NodeComponent };

function WorkflowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onPaneClick,
  onDrop,
  onDragOver,
  nodeTypes: customNodeTypes,
  onZoomToFit,
  showMinimap: initialShowMinimap = true,
}) {
  const [showMinimap, setShowMinimap] = useState(initialShowMinimap);

  return (
    <div className="canvas-wrapper">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        nodeTypes={customNodeTypes || nodeTypes}
        fitView
        deleteKeyCode={["Backspace", "Delete"]}
        snapToGrid
        snapGrid={[20, 20]}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="var(--color-border)"
        />
        <Controls showInteractive={false} />
        {showMinimap && (
          <MiniMap
            nodeStrokeColor="var(--color-text-muted)"
            nodeColor="var(--color-surface)"
            maskColor="rgba(0,0,0,0.1)"
            style={{
              border: "1px solid var(--color-border)",
              borderRadius: "6px",
            }}
          />
        )}
      </ReactFlow>
      <div className="canvas-controls-overlay">
        <button
          className="canvas-control-btn"
          onClick={() => setShowMinimap((v) => !v)}
          title={showMinimap ? "Hide minimap" : "Show minimap"}
        >
          {showMinimap ? "⊟ Map" : "⊞ Map"}
        </button>
        {onZoomToFit && (
          <button
            className="canvas-control-btn"
            onClick={onZoomToFit}
            title="Zoom to fit"
          >
            ⊞ Fit
          </button>
        )}
      </div>
    </div>
  );
}

export default WorkflowCanvas;
