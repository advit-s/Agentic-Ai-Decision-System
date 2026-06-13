// components/WorkflowToolbar.jsx
import React from "react";
import LoadDropdown from "./LoadDropdown";
import "../styles/toolbar.css";

function WorkflowToolbar({
  onNew,
  onSave,
  onLoad,
  onExecute,
  onExport,
  workflows,
  currentWorkflowName,
  isExecuting,
  hasUnsavedChanges,
}) {
  return (
    <div className="workflow-toolbar">
      <div className="toolbar-left">
        <button className="toolbar-btn" onClick={onNew} title="Create new workflow">
          + New
        </button>
        <button className="toolbar-btn" onClick={onSave} title="Save workflow">
          {hasUnsavedChanges ? "💾 Save *" : "💾 Save"}
        </button>
        <LoadDropdown workflows={workflows} onSelect={onLoad} />
        <button
          className="toolbar-btn toolbar-btn-primary"
          onClick={onExecute}
          disabled={isExecuting}
        >
          {isExecuting ? "⏳ Running..." : "▶ Execute"}
        </button>
        <button className="toolbar-btn" onClick={onExport} title="Export as JSON">
          📋 Export
        </button>
      </div>
      <div className="toolbar-center">
        <span className="toolbar-workflow-name">
          {currentWorkflowName || "Untitled Workflow"}
        </span>
      </div>
      <div className="toolbar-right">
        <span className="toolbar-mode">⚡ Workflow Builder</span>
      </div>
    </div>
  );
}

export default WorkflowToolbar;
