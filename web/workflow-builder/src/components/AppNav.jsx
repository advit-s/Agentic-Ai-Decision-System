// AppNav.jsx — Sidebar navigation for main app sections
import React from "react";

const NAV_ITEMS = [
  { id: "demo", label: "Demo Flow", icon: "🚀" },
  { id: "workflow", label: "Workflow Builder", icon: "⚡" },
  { id: "data-sources", label: "Data Sources", icon: "📁" },
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

function AppNav({ activeSection, onNavigate, workspaceName, backendMode }) {
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
        <div className={`app-nav-mode app-nav-mode-${backendMode}`}>
          {backendMode === "mock" && "🟡 Mock Mode"}
          {backendMode === "live" && "🟢 Live"}
          {backendMode === "unavailable" && "🔴 Offline"}
        </div>
      </div>
    </aside>
  );
}

export default AppNav;
