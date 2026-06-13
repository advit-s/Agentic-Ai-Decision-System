// components/WorkflowCanvas.jsx
import React from "react";
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
}) {
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
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e5e7eb" />
        <Controls />
        <MiniMap
          nodeStrokeColor="#6b7280"
          nodeColor="#f3f4f6"
          maskColor="rgba(0,0,0,0.1)"
          style={{ border: "1px solid #e5e7eb", borderRadius: "6px" }}
        />
      </ReactFlow>
    </div>
  );
}

export default WorkflowCanvas;
