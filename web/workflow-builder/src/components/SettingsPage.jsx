// SettingsPage.jsx — App settings and workspace management
import React from "react";
import WorkspaceSelector from "./WorkspaceSelector";

function SettingsPage({ workspaceId, onWorkspaceChange }) {
  return (
    <div className="section-page">
      <div className="section-header">
        <h2>⚙️ Settings</h2>
        <p className="section-subtitle">Manage workspaces and application preferences</p>
      </div>
      <div className="section-content">
        <div className="placeholder-card">
          <WorkspaceSelector
            workspaceId={workspaceId}
            onWorkspaceChange={onWorkspaceChange || (() => {})}
          />
        </div>
        <div className="placeholder-card">
          <h3>About</h3>
          <p className="text-muted">
            Agentic Decision System — v1.24.0-dev<br />
            Local-first Company Intelligence Engine
          </p>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
