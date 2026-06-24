// ConnectorsPage.jsx — Read-only connector manager for v1.28+v1.29+v1.30
// Supports create/test/import (v1.28), sync/schedule (v1.29),
// and setup wizard, credential UX, item preview (v1.30).
// Supports create/test/import (v1.28) and sync/schedule (v1.29).
import React, { useState, useEffect, useCallback } from "react";
import {
  listConnectorDefinitions,
  listConnectorSchemas,
  getConnectorCredentialStatus,
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
  triggerConnectorSync,
  getConnectorSyncState,
  listSyncSchedules,
  createSyncSchedule,
  updateSyncSchedule,
  deleteSyncSchedule,
  toggleSyncSchedule,
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
  const [schemas, setSchemas] = useState([]);
  const [credentialStatus, setCredentialStatus] = useState({});
  const { can } = usePermission();
  const { showToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [view, setView] = useState("list"); // list | create | detail | items | jobs | sync-state | schedules
  const [wizardStep, setWizardStep] = useState(0); // 0=choose, 1=configure, 2=test, 3=done
  const [selectedSchema, setSelectedSchema] = useState(null);
  const [selectedConfig, setSelectedConfig] = useState(null);
  const [items, setItems] = useState([]);
  const [selectedItems, setSelectedItems] = useState([]);
  const [importing, setImporting] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [syncState, setSyncState] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    schedule_type: "manual",
    interval_minutes: 60,
    enabled: true,
  });
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

  // -----------------------------------------------------------------------
  // v1.29 Sync operations
  // -----------------------------------------------------------------------

  // Manual sync
  const handleSync = async (configId) => {
    setSyncing(true);
    try {
      const result = await triggerConnectorSync(workspaceId, configId);
      const r = result?.result || {};
      showToast(
        `Sync complete: ${r.items_new || 0} new, ${r.items_changed || 0} changed, ${r.items_unchanged || 0} unchanged`,
        r.status === "failed" ? "error" : "success"
      );
      loadData();
    } catch (err) {
      showToast(`Sync failed: ${err.message}`, "error");
    } finally {
      setSyncing(false);
    }
  };

  // View sync state
  const handleViewSyncState = async (config) => {
    setSelectedConfig(config);
    setView("sync-state");
    try {
      const result = await getConnectorSyncState(workspaceId, config.connector_id);
      setSyncState(result?.sync_state || []);
    } catch (err) {
      showToast(`Failed to load sync state: ${err.message}`, "error");
      setSyncState([]);
    }
  };

  // View schedules
  const handleViewSchedules = async (config) => {
    setSelectedConfig(config);
    setView("schedules");
    setShowScheduleForm(false);
    try {
      const result = await listSyncSchedules(workspaceId, config.connector_id);
      setSchedules(result?.schedules || []);
    } catch (err) {
      showToast(`Failed to load schedules: ${err.message}`, "error");
      setSchedules([]);
    }
  };

  // Create schedule
  const handleCreateSchedule = async () => {
    try {
      await createSyncSchedule(workspaceId, selectedConfig.connector_id, scheduleForm);
      showToast("Schedule created", "success");
      setShowScheduleForm(false);
      handleViewSchedules(selectedConfig);
    } catch (err) {
      showToast(`Failed to create schedule: ${err.message}`, "error");
    }
  };

  // Delete schedule
  const handleDeleteSchedule = async (scheduleId) => {
    if (!window.confirm("Delete this schedule?")) return;
    try {
      await deleteSyncSchedule(workspaceId, selectedConfig.connector_id, scheduleId);
      showToast("Schedule deleted", "success");
      handleViewSchedules(selectedConfig);
    } catch (err) {
      showToast(`Failed to delete schedule: ${err.message}`, "error");
    }
  };

  // Toggle schedule
  const handleToggleSchedule = async (scheduleId) => {
    try {
      const result = await toggleSyncSchedule(workspaceId, selectedConfig.connector_id, scheduleId);
      const enabled = result?.schedule?.enabled;
      showToast(enabled ? "Schedule enabled" : "Schedule disabled", "success");
      handleViewSchedules(selectedConfig);
    } catch (err) {
      showToast(`Failed to toggle schedule: ${err.message}`, "error");
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

  // Schedule form helpers
  const updateScheduleForm = (field, value) => {
    setScheduleForm((prev) => ({ ...prev, [field]: value }));
  };

  // Render
  if (!workspaceId) {
    return <div className="section-page"><p>Select a workspace to manage connectors.</p></div>;
  }

  const canManage = can?.("connector.manage");
  const canImport = can?.("connector.import");
  const canRead = can?.("connector.read");
  const canSync = can?.("connector.sync");
  const canSchedule = can?.("connector.schedule");

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
          Connector sync is incremental — new/changed items are imported, unchanged items are skipped,
          deleted remote items are marked but local data is preserved.
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
                    {cfg.last_sync_at && (
                      <span className="connector-last-sync" style={{ marginLeft: 8, fontSize: "0.85em", color: "#888" }}>
                        Last sync: {new Date(cfg.last_sync_at).toLocaleString()}
                      </span>
                    )}
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
                  {canSync && (
                    <button className="btn btn-xs" onClick={() => handleSync(cfg.connector_id)} disabled={syncing}>
                      {syncing ? "Syncing..." : "⟳ Sync"}
                    </button>
                  )}
                  {canSync && (
                    <button className="btn btn-xs" onClick={() => handleViewSyncState(cfg)}>
                      Sync State
                    </button>
                  )}
                  {canSchedule && (
                    <button className="btn btn-xs" onClick={() => handleViewSchedules(cfg)}>
                      Schedule
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
              <tr><td>Last Sync</td><td>{selectedConfig.last_sync_at ? new Date(selectedConfig.last_sync_at).toLocaleString() : "Never"}</td></tr>
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
            {canSync && (
              <button className="btn btn-xs" onClick={() => handleSync(selectedConfig.connector_id)} disabled={syncing}>
                {syncing ? "Syncing..." : "⟳ Sync Now"}
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

      {view === "sync-state" && selectedConfig && (
        <div className="connector-sync-state">
          <h3>Sync State — {selectedConfig.name}</h3>
          <p className="section-subtitle">
            Per-item sync state tracking for incremental sync.
            {canSync && (
              <button className="btn btn-sm" style={{ marginLeft: 12 }} onClick={() => handleSync(selectedConfig.connector_id)} disabled={syncing}>
                {syncing ? "Syncing..." : "⟳ Run Sync"}
              </button>
            )}
          </p>

          {syncState.length === 0 && (
            <div className="empty-state">
              <p>No sync state yet. Run a sync to start tracking items.</p>
            </div>
          )}

          {syncState.length > 0 && (
            <div className="sync-state-table" style={{ marginTop: 12 }}>
              <table className="detail-table">
                <thead>
                  <tr>
                    <th>External ID</th>
                    <th>Status</th>
                    <th>Content Hash</th>
                    <th>Last Seen</th>
                    <th>Last Imported</th>
                  </tr>
                </thead>
                <tbody>
                  {syncState.map((item) => (
                    <tr key={item.sync_state_id || item.external_id}>
                      <td>{item.external_id}</td>
                      <td>
                        <span className={`sync-status-badge status-${item.status}`}>
                          {item.status === "new" && "🆕"}
                          {item.status === "changed" && "🔄"}
                          {item.status === "unchanged" && "✅"}
                          {item.status === "deleted_remote" && "🗑️"}
                          {item.status === "failed" && "❌"}
                          {item.status === "skipped" && "⏭️"}
                          {" "}{item.status}
                        </span>
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.8em" }}>{item.content_hash?.slice(0, 12)}...</td>
                      <td>{item.last_seen_at ? new Date(item.last_seen_at).toLocaleString() : "-"}</td>
                      <td>{item.last_imported_at ? new Date(item.last_imported_at).toLocaleString() : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="form-actions" style={{ marginTop: 16 }}>
            <button className="btn" onClick={() => { setView("list"); setSelectedConfig(null); }}>Back</button>
          </div>
        </div>
      )}

      {view === "schedules" && selectedConfig && (
        <div className="connector-schedules">
          <h3>Sync Schedules — {selectedConfig.name}</h3>
          <p className="section-subtitle">
            Configure automated sync schedules for this connector.
            {canSchedule && !showScheduleForm && (
              <button className="btn btn-sm" style={{ marginLeft: 12 }} onClick={() => setShowScheduleForm(true)}>
                + New Schedule
              </button>
            )}
          </p>

          {showScheduleForm && canSchedule && (
            <div className="schedule-form" style={{ marginBottom: 16, padding: 12, border: "1px solid #ddd", borderRadius: 8 }}>
              <h4>Create Schedule</h4>
              <div className="form-group">
                <label>Schedule Type</label>
                <select
                  className="form-input"
                  value={scheduleForm.schedule_type}
                  onChange={(e) => updateScheduleForm("schedule_type", e.target.value)}
                >
                  <option value="manual">Manual (triggered by user)</option>
                  <option value="interval">Interval (every N minutes)</option>
                </select>
              </div>
              {scheduleForm.schedule_type === "interval" && (
                <div className="form-group">
                  <label>Interval (minutes)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={scheduleForm.interval_minutes}
                    onChange={(e) => updateScheduleForm("interval_minutes", parseInt(e.target.value) || 60)}
                    min={1}
                  />
                </div>
              )}
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={scheduleForm.enabled}
                    onChange={(e) => updateScheduleForm("enabled", e.target.checked)}
                  />{" "}
                  Enabled
                </label>
              </div>
              <div className="form-actions">
                <button className="btn btn-primary" onClick={handleCreateSchedule}>
                  Create
                </button>
                <button className="btn" onClick={() => setShowScheduleForm(false)}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          {schedules.length === 0 && !showScheduleForm && (
            <div className="empty-state">
              <p>No schedules configured. Create a schedule to automate sync.</p>
            </div>
          )}

          {schedules.map((sched) => (
            <div key={sched.schedule_id} className="schedule-card" style={{ padding: 12, marginBottom: 8, border: "1px solid #ddd", borderRadius: 8 }}>
              <div className="schedule-card-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>{sched.schedule_type === "interval" ? `Every ${sched.interval_minutes} minutes` : "Manual"}</strong>
                  <span className={`connector-status-badge ${sched.enabled ? "status-healthy" : "status-configured"}`} style={{ marginLeft: 8 }}>
                    {sched.enabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <div>
                  {canSchedule && (
                    <>
                      <button className="btn btn-xs" onClick={() => handleToggleSchedule(sched.schedule_id)}>
                        {sched.enabled ? "Disable" : "Enable"}
                      </button>
                      <button className="btn btn-xs btn-danger" style={{ marginLeft: 4 }} onClick={() => handleDeleteSchedule(sched.schedule_id)}>
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </div>
              <div className="schedule-card-details" style={{ marginTop: 8, fontSize: "0.9em", color: "#666" }}>
                {sched.next_run_at && <span>Next run: {new Date(sched.next_run_at).toLocaleString()} | </span>}
                {sched.last_run_at && <span>Last run: {new Date(sched.last_run_at).toLocaleString()} | </span>}
                <span>Created: {new Date(sched.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}

          <div className="form-actions" style={{ marginTop: 16 }}>
            <button className="btn" onClick={() => { setView("list"); setSelectedConfig(null); }}>Back</button>
          </div>
        </div>
      )}

      {view === "jobs" && (
        <div className="connector-jobs">
          <h3>Import & Sync Jobs</h3>
          {jobs.length === 0 && <div className="empty-state"><p>No import or sync jobs yet.</p></div>}
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
