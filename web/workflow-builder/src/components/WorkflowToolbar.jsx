// components/WorkflowToolbar.jsx — Toolbar with save, load, execute, validate, history, schedules, providers, trust
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
  onImport,
  onExport,
  onHistory,
  historyPanel,
  onSchedules,
  onProviders,
  onTemplates,
  onTrust,
  onValidate,
  validationResult,
  schedulePanel,
  providerPanel,
  trustPanel,
  workflows,
  currentWorkflowName,
  isExecuting,
  hasUnsavedChanges,
  onShortcuts,
  showValidationDialog,
  setShowValidationDialog,
}) {
  const [editingUrl, setEditingUrl] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [providerHealth, setProviderHealth] = useState("unknown");

  useEffect(() => {
    listProviders()
      .then((data) => {
        const providers = data.providers || data || [];
        if (providers.length === 0) {
          setProviderHealth("unknown");
          return;
        }
        return checkProvider(providers[0].name).then((result) => {
          setProviderHealth(result.status === "ok" ? "ok" : "warn");
        });
      })
      .catch(() => setProviderHealth("unknown"));
  }, []);

  const mock = isMockMode();
  const baseUrl = getBaseUrl();
  const backendMode = getBackendMode();

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
    window.location.reload();
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

  useEffect(() => {
    if (editingUrl) {
      const input = document.querySelector(".connection-url-input");
      if (input) input.focus();
    }
  }, [editingUrl]);

  const handleValidateClick = useCallback(() => {
    if (onValidate) onValidate();
    if (setShowValidationDialog) setShowValidationDialog(true);
  }, [onValidate, setShowValidationDialog]);

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

  const hasErrors = validationResult && !validationResult.valid;
  const hasWarnings = validationResult && validationResult.warnings && validationResult.warnings.length > 0;

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
        <button className="toolbar-btn" onClick={handleValidateClick} title="Validate workflow before run">
          ✓ Validate
        </button>
        {hasErrors && (
          <span className="toolbar-validation-badge toolbar-validation-error" title="Workflow has errors">
            {validationResult.errors.length} err
          </span>
        )}
        {hasWarnings && !hasErrors && (
          <span className="toolbar-validation-badge toolbar-validation-warn" title="Workflow has warnings">
            {validationResult.warnings.length} warn
          </span>
        )}
        <button
          className="toolbar-btn toolbar-btn-primary"
          onClick={onExecute}
          disabled={isExecuting || hasErrors}
        >
          {isExecuting ? "⏳ Running..." : "▶ Execute"}
        </button>
        <button className="toolbar-btn" onClick={onTemplates} title="New from template">
          📋 Templates
        </button>
        <button className="toolbar-btn" onClick={onImport} title="Import workflow from JSON file">📂 Import</button>
        <button className="toolbar-btn" onClick={onExport} title="Export as JSON">
          📋 Export
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
            <span className={`provider-indicator-dot provider-indicator-${providerHealth}`} />
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
