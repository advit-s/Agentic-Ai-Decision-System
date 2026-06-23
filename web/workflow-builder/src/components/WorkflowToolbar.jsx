// components/WorkflowToolbar.jsx
import React, { useState, useEffect, useCallback } from "react";
import LoadDropdown from "./LoadDropdown";
import ThemeToggle from "./ThemeToggle";
import { getBaseUrl, getBackendMode, isMockMode, listProviders, checkProvider } from "../api";
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
  onTemplates,
  onTrust,
  schedulePanel,
  providerPanel,
  trustPanel,
  workflows,
  currentWorkflowName,
  isExecuting,
  hasUnsavedChanges,
  onShortcuts,
}) {
  const [editingUrl, setEditingUrl] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [providerHealth, setProviderHealth] = useState("unknown"); // "ok" | "warn" | "unknown"

  // Check provider health on mount
  useEffect(() => {
    listProviders()
      .then((data) => {
        const providers = data.providers || data || [];
        if (providers.length === 0) {
          setProviderHealth("unknown");
          return;
        }
        // Check the default (first) provider
        return checkProvider(providers[0].name).then((result) => {
          setProviderHealth(result.status === "ok" ? "ok" : "warn");
        });
      })
      .catch(() => setProviderHealth("unknown"));
  }, []);

  const mock = isMockMode();
  const baseUrl = getBaseUrl();
  const backendMode = getBackendMode();

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

  // Compute connection badge label/class
  let badgeLabel, badgeClass;
  if (mock) {
    badgeLabel = "🟡 Mock mode";
    badgeClass = "connection-badge-mock";
  } else if (backendMode === "live" && window.location.port === "3000") {
    badgeLabel = "🟢 Local live backend";
    badgeClass = "connection-badge-live";
  } else if (backendMode === "live") {
    badgeLabel = `🟢 ${baseUrl.replace(/^https?:\/\//, "")}`;
    badgeClass = "connection-badge-live";
  } else {
    badgeLabel = "🔴 Backend unavailable";
    badgeClass = "connection-badge-mock";
  }

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
        <button className="toolbar-btn" onClick={onTemplates} title="New from template">
          📋 Templates
        </button>
        <div className="toolbar-divider" />
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
          <span className="provider-toolbar-indicator">
            <span
              className={`provider-indicator-dot provider-indicator-${providerHealth}`}
            />
          </span>
          🤖 Providers
        </button>
        <button
          className={`toolbar-btn ${trustPanel ? "toolbar-btn-active" : ""}`}
          onClick={onTrust}
          title="Open trust dashboard"
        >
          🛡️ Trust
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
            className={`connection-badge ${badgeClass}`}
            onClick={handleStartEdit}
            title="Click to change API URL"
          >
            {badgeLabel}
          </button>
        )}
      </div>
    </div>
  );
}

export default WorkflowToolbar;
