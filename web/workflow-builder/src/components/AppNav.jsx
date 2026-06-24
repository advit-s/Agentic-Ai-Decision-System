// AppNav.jsx — Sidebar navigation for main app sections with security status
import React from "react";
import { usePermission } from "../hooks/usePermission";

const NAV_ITEMS = [
  { id: "demo", label: "Demo Flow", icon: "🚀" },
  { id: "workflow", label: "Workflow Builder", icon: "⚡" },
  { id: "data-sources", label: "Data Sources", icon: "📁" },
  { id: "connectors", label: "Connectors", icon: "🔌" },
  { id: "graph", label: "Knowledge Graph", icon: "🔗" },
  { id: "risk-dashboard", label: "Risk Dashboard", icon: "🛡️" },
  { id: "evidence", label: "Evidence Search", icon: "🔍" },
  { id: "executions", label: "Execution History", icon: "📊" },
  { id: "claims", label: "Claim Ledger", icon: "📋" },
  { id: "trust", label: "Trust Dashboard", icon: "🛡️" },
  { id: "reports", label: "Reports", icon: "📄" },
  { id: "providers", label: "Providers", icon: "🤖" },
  { id: "settings", label: "Settings", icon: "⚙️" },
];

function AppNav({ activeSection, onNavigate, workspaceName, backendMode, systemStatus, backendConnected }) {
  const { currentUser, currentRole, roleLabel, securityMode, isDemoMode, isGovernedMode } = usePermission();

  const modeLabel = isGovernedMode ? "Governed" : "Demo";
  const modeIcon = isGovernedMode ? "🟢" : "🟡";

  return (
    <aside className="app-nav">
      <div className="app-nav-brand">
        <span className="app-nav-logo">CI</span>
        <div className="app-nav-brand-text">
          <span className="app-nav-eyebrow">Decision System</span>
          <button
            className="app-nav-workspace-btn"
            onClick={() => onNavigate("settings")}
            title="Switch workspace"
          >
            {workspaceName || "No Workspace"}
          </button>
        </div>
      </div>

      <nav className="app-nav-items">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            className={`app-nav-item ${activeSection === item.id ? "app-nav-item-active" : ""}`}
            onClick={() => onNavigate(item.id)}
            title={item.label}
          >
            <span className="app-nav-item-icon">{item.icon}</span>
            <span className="app-nav-item-label">{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="app-nav-footer">
        {/* Beta label */}
        <div className="app-nav-beta" style={{ padding: "4px 12px", background: "#fff3cd", color: "#856404", fontSize: "11px", fontWeight: 600, textAlign: "center", letterSpacing: "0.5px" }}>
          ⚡ LOCAL BETA {systemStatus?.version ? `v${systemStatus.version}` : "v1.33.0-dev"}
        </div>
        {/* Security status */}
        <div className="app-nav-security" style={{ padding: "8px 12px", borderTop: "1px solid #eee", fontSize: "12px", lineHeight: 1.6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span>👤</span>
            <span title={currentUser?.user_id}>{currentUser?.display_name || "Unknown"}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span>🎭</span>
            <span>{roleLabel} ({currentRole})</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span>{modeIcon}</span>
            <span>{modeLabel} Mode</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
            <span>📂</span>
            <span title={systemStatus?.data_dir || ".decision_system"}>Data: {systemStatus?.data_dir || ".decision_system"}</span>
          </div>
          {systemStatus?.warnings && systemStatus.warnings.length > 0 && (
            <div style={{ display: "flex", alignItems: "flex-start", gap: "4px", marginTop: "4px", padding: "4px", background: "#fff8e1", borderRadius: "4px", fontSize: "10px", color: "#856404" }}>
              <span>⚠️</span>
              <span>{systemStatus.warnings[0]}</span>
            </div>
          )}
        </div>
        <div className={`app-nav-mode app-nav-mode-${backendMode}`}>
          {backendMode === "mock" && "🟡 Mock Mode"}
          {backendMode === "live" && "🟢 Live"}
          {backendMode === "unavailable" && "🔴 Offline"}
          {backendConnected && systemStatus?.security_mode && (
            <span style={{ marginLeft: "4px", fontSize: "10px", opacity: 0.7 }}>
              | {systemStatus.security_mode === "demo" ? "Demo" : "Governed"}
            </span>
          )}
        </div>
      </div>
    </aside>
  );
}

export default AppNav;
