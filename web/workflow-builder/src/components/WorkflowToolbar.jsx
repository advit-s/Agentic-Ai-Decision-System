// components/WorkflowToolbar.jsx
import React, { useState, useEffect, useCallback } from "react";
import LoadDropdown from "./LoadDropdown";
import ThemeToggle from "./ThemeToggle";
import { getBaseUrl, isMockMode } from "../api";
import "../styles/toolbar.css";

function WorkflowToolbar({
  onNew,
  onSave,
  onLoad,
  onExecute,
  onExport,
  onHistory,
  historyPanel,
  onSchedules,
  onProviders,
  schedulePanel,
  providerPanel,
  workflows,
  currentWorkflowName,
  isExecuting,
  hasUnsavedChanges,
  onShortcuts,
}) {
  const [editingUrl, setEditingUrl] = useState(false);
  const [urlInput, setUrlInput] = useState("");

  const mock = isMockMode();
  const baseUrl = getBaseUrl();

  // Sync the input when opening edit
  const handleStartEdit = useCallback(() => {
    setUrlInput(baseUrl);
    setEditingUrl(true);
  }, [baseUrl]);

  const handleSaveUrl = useCallback(() => {
    const trimmed = urlInput.trim();
    if (trimmed) {
      localStorage.setItem("wfBuilderApiBaseUrl", trimmed);
    } else {
      localStorage.removeItem("wfBuilderApiBaseUrl");
    }
    setEditingUrl(false);
    window.location.reload(); // Reload to pick up the new mock/real state
  }, [urlInput]);

  const handleCancelUrl = useCallback(() => {
    setEditingUrl(false);
  }, []);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === "Enter") handleSaveUrl();
      if (e.key === "Escape") handleCancelUrl();
    },
    [handleSaveUrl, handleCancelUrl]
  );

  // Auto focus input when editing
  useEffect(() => {
    if (editingUrl) {
      const input = document.querySelector(".connection-url-input");
      if (input) input.focus();
    }
  }, [editingUrl]);

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
        <button
          className={`toolbar-btn ${historyPanel ? "toolbar-btn-active" : ""}`}
          onClick={onHistory}
          title="View execution history"
        >
          📊 History
        </button>
        <button
          className={`toolbar-btn ${schedulePanel ? "toolbar-btn-active" : ""}`}
          onClick={onSchedules}
          title="Manage schedules"
        >
          📅 Schedules
        </button>
        <button
          className={`toolbar-btn ${providerPanel ? "toolbar-btn-active" : ""}`}
          onClick={onProviders}
          title="Manage LLM providers"
        >
          🤖 Providers
        </button>
      </div>
      <div className="toolbar-center">
        <span className="toolbar-workflow-name">
          {currentWorkflowName || "Untitled Workflow"}
        </span>
      </div>
      <div className="toolbar-right">
        <ThemeToggle />
        <button
          className="toolbar-btn"
          onClick={onShortcuts}
          title="Keyboard shortcuts"
          style={{ fontSize: "15px", padding: "4px 10px", marginRight: "4px" }}
        >
          {"⌨︎"}
        </button>
        {editingUrl ? (
          <div className="connection-edit">
            <span className="connection-url-label">API URL:</span>
            <input
              className="connection-url-input"
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="http://localhost:8000"
            />
            <button className="connection-url-btn" onClick={handleSaveUrl} title="Save URL">
              ✓
            </button>
            <button className="connection-url-btn" onClick={handleCancelUrl} title="Cancel">
              ✗
            </button>
          </div>
        ) : (
          <button
            className={`connection-badge ${mock ? "connection-badge-mock" : "connection-badge-live"}`}
            onClick={handleStartEdit}
            title="Click to change API URL"
          >
            {mock ? "🟡 Mock Mode" : `🟢 ${baseUrl.replace(/^https?:\/\//, "")}`}
          </button>
        )}
      </div>
    </div>
  );
}

export default WorkflowToolbar;
