// ConnectorsPage.jsx — Read-only connector manager for v1.28
// Supports create/test/import for Local Folder, GitHub Repo, and URL connectors.
import React, { useState, useEffect, useCallback } from "react";
import {
  listConnectorDefinitions,
  listConnectorConfigs,
  createConnectorConfig,
  getConnectorConfig,
  updateConnectorConfig,
  deleteConnectorConfig,
  testConnector,
  listConnectorItems,
  importConnectorItems,
  listConnectorJobs,
  getConnectorJob,
} from "../api";
import { usePermission } from "../hooks/usePermission";
import { useToast } from "./Toast";

const CONNECTOR_TYPES = [
  { value: "local-files", label: "Local Folder", icon: "📁", description: "Import files from a local folder (read-only)" },
  { value: "github", label: "GitHub Repository", icon: "🐙", description: "Import files from a public GitHub repository" },
  { value: "url-import", label: "URL / Web Page", icon: "🌐", description: "Import a single web page as a data source" },
];

function ConnectorsPage({ workspaceId, onNavigate }) {
  const [definitions, setDefinitions] = useState([]);
  const [configs, setConfigs] = useState([]);
  const { can } = usePermission();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState("list"); // list | create | detail | items | jobs
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [items, setItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [importing, setImporting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [formData, setFormData] = useState({
    name: "",
    connector_type: "local-files",
    config: {},
    folder_path: "",
    repository_url: "",
    url: "",
  });

  // Load definitions and configs
  const loadData = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const [defResp, configResp] = await Promise.all([
        listConnectorDefinitions(),
        listConnectorConfigs(workspaceId),
      ]);
      setDefinitions(defResp?.connectors || []);
      setConfigs(configResp?.connectors || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Create connector
  const handleCreate = async () => {
    const config = {};
    if (formData.connector_type === "local-files" && formData.folder_path) {
      config.folder_path = formData.folder_path;
    } else if (formData.connector_type === "github" && formData.repository_url) {
      config.repository_url = formData.repository_url;
    } else if (formData.connector_type === "url-import" && formData.url) {
      config.url = formData.url;
    }

    try {
      await createConnectorConfig(workspaceId, {
        name: formData.name || `${formData.connector_type} connector`,
        connector_type: formData.connector_type,
        config,
      });
      showToast("Connector created", "success");
      setView("list");
      setFormData({ name: "", connector_type: "local-files", config: {}, folder_path: "", repository_url: "", url: "" });
      loadData();
    } catch (err) {
      showToast(`Failed to create connector: ${err.message}`, "error");
    }
  };

  // Delete connector
  const handleDelete = async (configId) => {
    if (!window.confirm("Delete this connector configuration?")) return;
    try {
      await deleteConnectorConfig(workspaceId, configId);
      showToast("Connector deleted", "success");
      setView("list");
      setSelectedConfig(null);
      loadData();
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`, "error");
    }
  };

  // Test connection
  const handleTest = async (configId) => {
    setTesting(true);
    try {
      const result = await testConnector(workspaceId, configId);
      const r = result?.result || {};
      showToast(r.success ? `✅ ${r.message}` : `❌ ${r.message}`, r.success ? "success" : "error");
    } catch (err) {
      showToast(`Test failed: ${err.message}`, "error");
    } finally {
      setTesting(false);
    }
  };

  // List items
  const handleListItems = async (config) => {
    setSelectedConfig(config);
    setView("items");
    setSelectedItems([]);
    try {
      const result = await listConnectorItems(workspaceId, config.connector_id);
      setItems(result?.items || []);
    } catch (err) {
      showToast(`Failed to list items: ${err.message}`, "error");
      setItems([]);
    }
  };

  // Import selected items
  const handleImport = async () => {
    setImporting(true);
    try {
      const result = await importConnectorItems(
        workspaceId,
        selectedConfig.connector_id,
        selectedItems.length > 0 ? selectedItems : null
      );
      showToast(
        `Import complete: ${result?.result?.imported_count || 0} imported, ${result?.result?.skipped_count || 0} skipped`,
        "success"
      );
      setView("jobs");
      loadJobs();
    } catch (err) {
      showToast(`Import failed: ${err.message}`, "error");
    } finally {
      setImporting(false);
    }
  };

  // Load jobs
  const loadJobs = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const result = await listConnectorJobs(workspaceId);
      setJobs(result?.jobs || []);
    } catch (err) {
      // silent
    }
  }, [workspaceId]);

  const handleViewJobs = () => {
    setView("jobs");
    loadJobs();
  };

  const handleViewDetail = (config) => {
    setSelectedConfig(config);
    setView("detail");
  };

  const handleConfigChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Get display info for a connector type
  const getTypeInfo = (type) => CONNECTOR_TYPES.find((t) => t.value === type) || { label: type, icon: "🔌", description: "" };

  // Toggle item selection
  const toggleItem = (externalId) => {
    setSelectedItems((prev) =>
      prev.includes(externalId) ? prev.filter((id) => id !== externalId) : [...prev, externalId]
    );
  };

  const selectAllItems = () => {
    const fileItems = items.filter((i) => i.item_type === "file");
    if (selectedItems.length === fileItems.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems(fileItems.map((i) => i.external_id));
    }
  };

  // Render
  if (!workspaceId) {
    return <div className="section-page"><p>Select a workspace to manage connectors.</p></div>;
  }

  const canManage = can?.("connector.manage");
  const canImport = can?.("connector.import");
  const canRead = can?.("connector.read");

  if (!canRead) {
    return (
      <div className="section-page">
        <div className="section-header">
          <h2>🔌 Connectors</h2>
          <p className="section-subtitle">You do not have permission to view connectors.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>🔌 Connectors</h2>
        <p className="section-subtitle">
          Read-only connector imports. This app imports a local copy and never writes back.
          {canManage && (
            <button className="btn btn-sm" style={{ marginLeft: 12 }} onClick={() => setView("create")}>
              + New Connector
            </button>
          )}
          <button className="btn btn-sm" style={{ marginLeft: 8 }} onClick={handleViewJobs}>
            Import Jobs
          </button>
          <button className="btn btn-sm" style={{ marginLeft: 8 }} onClick={() => { setView("list"); loadData(); }}>
            Back to List
          </button>
        </p>
      </div>

      {loading && <div className="loading-spinner" />}
      {error && <div className="error-banner">{error}</div>}

      {view === "create" && canManage && (
        <div className="connector-form">
          <h3>New Connector</h3>
          <div className="form-group">
            <label>Connector Name</label>
            <input
              type="text"
              className="form-input"
              placeholder="My Connector"
              value={formData.name}
              onChange={(e) => handleConfigChange("name", e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Type</label>
            <select
              className="form-input"
              value={formData.connector_type}
              onChange={(e) => handleConfigChange("connector_type", e.target.value)}
            >
              {CONNECTOR_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.icon} {t.label} — {t.description}
                </option>
              ))}
            </select>
          </div>

          {formData.connector_type === "local-files" && (
            <div className="form-group">
              <label>Folder Path</label>
              <input
                type="text"
                className="form-input"
                placeholder="/path/to/folder"
                value={formData.folder_path}
                onChange={(e) => handleConfigChange("folder_path", e.target.value)}
              />
              <p className="form-hint">Absolute path to a local folder containing files to import.</p>
            </div>
          )}

          {formData.connector_type === "github" && (
            <div className="form-group">
              <label>Repository URL</label>
              <input
                type="text"
                className="form-input"
                placeholder="https://github.com/owner/repo"
                value={formData.repository_url}
                onChange={(e) => handleConfigChange("repository_url", e.target.value)}
              />
              <p className="form-hint">
                Public GitHub repository URL. Optional GITHUB_TOKEN env var for rate-limit increases.
              </p>
            </div>
          )}

          {formData.connector_type === "url-import" && (
            <div className="form-group">
              <label>URL</label>
              <input
                type="text"
                className="form-input"
                placeholder="https://example.com/page"
                value={formData.url}
                onChange={(e) => handleConfigChange("url", e.target.value)}
              />
              <p className="form-hint">
                Public URL to import. Private/internal network addresses are blocked by default.
              </p>
            </div>
          )}

          <div className="form-actions">
            <button className="btn btn-primary" onClick={handleCreate}>
              Create Connector
            </button>
            <button className="btn" onClick={() => setView("list")}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {view === "list" && (
        <div className="connector-list">
          {configs.length === 0 && !loading && (
            <div className="empty-state">
              <p>No connectors configured.</p>
              {canManage && <p>Click "New Connector" to add one.</p>}
            </div>
          )}
          {configs.map((cfg) => {
            const typeInfo = getTypeInfo(cfg.connector_type);
            return (
              <div key={cfg.connector_id} className="connector-card">
                <div className="connector-card-header">
                  <span className="connector-card-icon">{typeInfo.icon}</span>
                  <div className="connector-card-info">
                    <strong>{cfg.name}</strong>
                    <span className="connector-card-type">{typeInfo.label}</span>
                    <span className={`connector-status-badge status-${cfg.status}`}>
                      {cfg.status}
                    </span>
                  </div>
                </div>
                <div className="connector-card-actions">
                  <span className="connector-mode-badge">🔒 Read-only</span>
                  <button className="btn btn-xs" onClick={() => handleViewDetail(cfg)}>
                    View
                  </button>
                  <button className="btn btn-xs" onClick={() => handleTest(cfg.connector_id)} disabled={testing}>
                    {testing ? "Testing..." : "Test"}
                  </button>
                  {canImport && (
                    <button className="btn btn-xs btn-primary" onClick={() => handleListItems(cfg)}>
                      Import
                    </button>
                  )}
                  {canManage && (
                    <button className="btn btn-xs btn-danger" onClick={() => handleDelete(cfg.connector_id)}>
                      Delete
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {view === "detail" && selectedConfig && (
        <div className="connector-detail">
          <h3>{selectedConfig.name}</h3>
          <table className="detail-table">
            <tbody>
              <tr><td>Type</td><td>{getTypeInfo(selectedConfig.connector_type).label}</td></tr>
              <tr><td>Mode</td><td>🔒 Read-only</td></tr>
              <tr><td>Status</td><td><span className={`connector-status-badge status-${selectedConfig.status}`}>{selectedConfig.status}</span></td></tr>
              <tr><td>Created</td><td>{selectedConfig.created_at ? new Date(selectedConfig.created_at).toLocaleString() : "-"}</td></tr>
              <tr><td>Config</td><td><pre className="config-preview">{JSON.stringify(selectedConfig.config, null, 2)}</pre></td></tr>
            </tbody>
          </table>
          <div className="form-actions">
            <button className="btn btn-xs" onClick={() => handleTest(selectedConfig.connector_id)} disabled={testing}>
              {testing ? "Testing..." : "Test Connection"}
            </button>
            {canImport && (
              <button className="btn btn-xs btn-primary" onClick={() => handleListItems(selectedConfig)}>
                Import Items
              </button>
            )}
            <button className="btn btn-xs" onClick={() => setView("list")}>Back</button>
          </div>
        </div>
      )}

      {view === "items" && selectedConfig && (
        <div className="connector-items">
          <h3>Items in {selectedConfig.name}</h3>
          <p className="section-subtitle">
            Select items to import as workspace data sources.
            {items.length > 0 && (
              <label style={{ marginLeft: 12 }}>
                <input type="checkbox" onChange={selectAllItems} checked={items.filter(i => i.item_type === 'file').length > 0 && selectedItems.length === items.filter(i => i.item_type === 'file').length} /> Select all
              </label>
            )}
          </p>

          {items.length === 0 && <div className="empty-state"><p>No items found or connector cannot list items.</p></div>}

          <div className="items-grid">
            {items.map((item) => (
              <div key={item.external_id} className={`item-card ${item.item_type === "folder" ? "item-folder" : ""}`}>
                <div className="item-card-select">
                  {item.item_type === "file" && (
                    <input
                      type="checkbox"
                      checked={selectedItems.includes(item.external_id)}
                      onChange={() => toggleItem(item.external_id)}
                    />
                  )}
                </div>
                <div className="item-card-icon">{item.item_type === "folder" ? "📁" : "📄"}</div>
                <div className="item-card-info">
                  <strong>{item.title}</strong>
                  {item.source_url && <span className="item-url">{item.source_url}</span>}
                  {item.size_bytes > 0 && <span className="item-size">{(item.size_bytes / 1024).toFixed(1)} KB</span>}
                </div>
              </div>
            ))}
          </div>

          {canImport && items.length > 0 && (
            <div className="form-actions" style={{ marginTop: 16 }}>
              <button
                className="btn btn-primary"
                onClick={handleImport}
                disabled={importing || selectedItems.length === 0}
              >
                {importing ? "Importing..." : `Import Selected (${selectedItems.length})`}
              </button>
              {selectedItems.length === 0 && items.filter(i => i.item_type === 'file').length > 0 && (
                <button className="btn" onClick={() => setSelectedItems(items.filter(i => i.item_type === 'file').map(i => i.external_id))}>
                  Import All
                </button>
              )}
              <button className="btn" onClick={() => { setView("list"); setSelectedConfig(null); }}>
                Cancel
              </button>
            </div>
          )}
        </div>
      )}

      {view === "jobs" && (
        <div className="connector-jobs">
          <h3>Import Jobs</h3>
          {jobs.length === 0 && <div className="empty-state"><p>No import jobs yet.</p></div>}
          {jobs.map((job) => (
            <div key={job.job_id} className="job-card">
              <div className="job-card-header">
                <strong>Job: {job.job_id?.slice(0, 8)}...</strong>
                <span className={`connector-status-badge status-${job.status}`}>{job.status}</span>
              </div>
              <div className="job-card-details">
                <span>Found: {job.items_found || 0}</span>
                <span>Imported: {job.imported_count || 0}</span>
                <span>Skipped: {job.skipped_count || 0}</span>
                <span>Failed: {job.items_failed || 0}</span>
              </div>
              {job.warnings?.length > 0 && (
                <div className="job-warnings">
                  {job.warnings.map((w, i) => <p key={i} className="warning-text">⚠️ {w}</p>)}
                </div>
              )}
              {job.errors?.length > 0 && (
                <div className="job-errors">
                  {job.errors.map((e, i) => <p key={i} className="error-text">❌ {e}</p>)}
                </div>
              )}
              {job.completed_at && (
                <div className="job-timestamp">Completed: {new Date(job.completed_at).toLocaleString()}</div>
              )}
            </div>
          ))}
          <button className="btn" style={{ marginTop: 12 }} onClick={() => { setView("list"); loadData(); }}>
            Back
          </button>
        </div>
      )}
    </div>
  );
}

export default ConnectorsPage;
