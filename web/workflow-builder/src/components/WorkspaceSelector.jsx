// WorkspaceSelector.jsx — Create, select, and manage workspaces
import React, { useState, useEffect } from "react";
import {
  listWorkspaces,
  getWorkspaceStatus,
  createWorkspace,
  activateWorkspace,
} from "../api";

function WorkspaceSelector({ workspaceId, onWorkspaceChange }) {
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWs, setActiveWs] = useState(workspaceId || null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [stats, setStats] = useState(null);

  const loadWorkspaces = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listWorkspaces();
      const wsList = data.workspaces || [];
      setWorkspaces(wsList);
      const activeId = data.active_workspace_id || null;
      if (activeId) setActiveWs(activeId);

      // Load status for active workspace
      try {
        const statusData = await getWorkspaceStatus();
        setStats(statusData);
        if (statusData.workspace?.workspace_id && !activeId) {
          setActiveWs(statusData.workspace.workspace_id);
        }
      } catch {
        // status not critical
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const result = await createWorkspace(newName.trim(), newDesc.trim(), true);
      setNewName("");
      setNewDesc("");
      setShowCreate(false);
      await loadWorkspaces();
      if (result.workspace) {
        onWorkspaceChange(result.workspace.workspace_id);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSelect = async (ws) => {
    try {
      await activateWorkspace(ws.name);
      setActiveWs(ws.workspace_id);
      onWorkspaceChange(ws.workspace_id);
      // Reload stats
      const statusData = await getWorkspaceStatus();
      setStats(statusData);
    } catch (err) {
      setError(err.message);
    }
  };

  const activeWorkspace = workspaces.find((w) => w.workspace_id === activeWs);

  return (
    <div className="workspace-selector">
      <div className="workspace-selector-header">
        <h3>Workspaces</h3>
        <button
          className="toolbar-btn toolbar-btn-sm"
          onClick={() => setShowCreate(!showCreate)}
          title="Create workspace"
        >
          + New
        </button>
      </div>

      {showCreate && (
        <div className="workspace-create-form">
          <input
            type="text"
            placeholder="Workspace name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            autoFocus
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
          />
          <div className="workspace-create-actions">
            <button className="toolbar-btn toolbar-btn-primary" onClick={handleCreate}>
              Create
            </button>
            <button className="toolbar-btn" onClick={() => setShowCreate(false)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <div className="workspace-error">{error}</div>}

      {loading ? (
        <div className="workspace-loading">Loading...</div>
      ) : (
        <div className="workspace-list">
          {workspaces.length === 0 ? (
            <div className="workspace-empty">
              <p>No workspaces yet. Create one to get started.</p>
            </div>
          ) : (
            workspaces.map((ws) => (
              <button
                key={ws.workspace_id}
                className={`workspace-item ${ws.workspace_id === activeWs ? "workspace-item-active" : ""}`}
                onClick={() => handleSelect(ws)}
              >
                <span className="workspace-item-icon">
                  {ws.workspace_id === activeWs ? "●" : "○"}
                </span>
                <div className="workspace-item-info">
                  <span className="workspace-item-name">{ws.name}</span>
                  {ws.description && (
                    <span className="workspace-item-desc">{ws.description}</span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      )}

      {activeWorkspace && stats && stats.status === "ok" && (
        <div className="workspace-stats">
          <div className="workspace-stat">
            <span className="workspace-stat-value">{stats.data_source_count || 0}</span>
            <span className="workspace-stat-label">Sources</span>
          </div>
          <div className="workspace-stat">
            <span className="workspace-stat-value">{stats.chunk_count || 0}</span>
            <span className="workspace-stat-label">Chunks</span>
          </div>
          <div className="workspace-stat">
            <span className="workspace-stat-value">{stats.claim_count || 0}</span>
            <span className="workspace-stat-label">Claims</span>
          </div>
          <div className="workspace-stat">
            <span className="workspace-stat-value">{stats.report_count || 0}</span>
            <span className="workspace-stat-label">Reports</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default WorkspaceSelector;
