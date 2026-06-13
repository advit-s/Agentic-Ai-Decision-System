// components/ScheduleManager.jsx — Manage workflow schedules and triggers

import React, { useState, useEffect, useCallback } from "react";
import {
  listSchedules,
  createSchedule,
  toggleSchedule,
  deleteSchedule,
} from "../api";
import "../styles/schedule-manager.css";

const TRIGGER_CONFIG_PLACEHOLDERS = {
  cron: {
    expression: { label: "Cron Expression", placeholder: "0 9 * * 1", default: "0 9 * * 1" },
  },
  webhook: {
    webhook_path: { label: "Webhook Path", placeholder: "my-webhook", default: "my-webhook" },
  },
  file_watch: {
    directory: { label: "Directory", placeholder: "/tmp/watch", default: "/tmp/watch" },
    pattern: { label: "File Pattern", placeholder: "*.csv", default: "*.csv" },
  },
};

const TRIGGER_ICONS = {
  cron: "🕐",
  webhook: "🔗",
  file_watch: "👁",
};

function ScheduleManager({ workflowId, onClose }) {
  const [schedules, setSchedules] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createType, setCreateType] = useState("cron");
  const [createConfig, setCreateConfig] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadSchedules = useCallback(async () => {
    if (!workflowId) {
      setSchedules([]);
      return;
    }
    try {
      const data = await listSchedules(workflowId);
      setSchedules(data.schedules || []);
    } catch {
      setSchedules([]);
    }
  }, [workflowId]);

  useEffect(() => {
    loadSchedules();
  }, [loadSchedules]);

  useEffect(() => {
    setCreateConfig(getDefaults(createType));
  }, [createType]);

  function getDefaults(type) {
    const fields = TRIGGER_CONFIG_PLACEHOLDERS[type] || {};
    const defaults = {};
    Object.entries(fields).forEach(([key, cfg]) => {
      defaults[key] = cfg.default;
    });
    return defaults;
  }

  async function handleCreate() {
    if (!workflowId) return;
    setLoading(true);
    setError(null);
    try {
      await createSchedule({
        workflow_id: workflowId,
        trigger_type: createType,
        trigger_config: { ...createConfig },
      });
      setShowCreate(false);
      setCreateType("cron");
      setCreateConfig(getDefaults("cron"));
      await loadSchedules();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggle(id) {
    try {
      await toggleSchedule(id);
      await loadSchedules();
    } catch {
      // silently ignore
    }
  }

  async function handleDelete(id) {
    try {
      await deleteSchedule(id);
      await loadSchedules();
    } catch {
      // silently ignore
    }
  }

  function handleConfigChange(key, value) {
    setCreateConfig((prev) => ({ ...prev, [key]: value }));
  }

  if (!workflowId) {
    return (
      <div className="schedule-manager">
        <div className="schedule-manager-header">
          <span>📅 Schedules</span>
          <button onClick={onClose} title="Close">✕</button>
        </div>
        <div className="schedule-empty">
          Save a workflow first to manage its schedules
        </div>
      </div>
    );
  }

  const fields = TRIGGER_CONFIG_PLACEHOLDERS[createType] || {};

  return (
    <div className="schedule-manager">
      <div className="schedule-manager-header">
        <span>📅 Schedules</span>
        <button onClick={() => setShowCreate(!showCreate)} title={showCreate ? "Cancel" : "Add schedule"}>
          {showCreate ? "✕" : "+"}
        </button>
      </div>

      <div className="schedule-list">
        {schedules.length === 0 && !showCreate && (
          <div className="schedule-empty">No schedules yet</div>
        )}

        {schedules.map((s) => (
          <div key={s.id} className="schedule-card">
            <div className="schedule-card-header">
              <span className={`schedule-trigger-badge ${s.trigger_type}`}>
                {TRIGGER_ICONS[s.trigger_type] || "📌"} {s.trigger_type}
              </span>
              <div className="schedule-card-actions">
                <button
                  onClick={() => handleDelete(s.id)}
                  className="delete-btn"
                  title="Delete schedule"
                >
                  🗑
                </button>
              </div>
            </div>

            {s.trigger_type === "cron" && (
              <div className="schedule-detail">
                <strong>Expression:</strong> {s.trigger_config?.expression || "-"}
              </div>
            )}
            {s.trigger_type === "webhook" && (
              <div className="schedule-detail">
                <strong>Path:</strong> /{s.trigger_config?.webhook_path || "-"}
              </div>
            )}
            {s.trigger_type === "file_watch" && (
              <>
                <div className="schedule-detail">
                  <strong>Dir:</strong> {s.trigger_config?.directory || "-"}
                </div>
                <div className="schedule-detail">
                  <strong>Pattern:</strong> {s.trigger_config?.pattern || "-"}
                </div>
              </>
            )}

            <div className="schedule-toggle">
              <input
                type="checkbox"
                checked={s.enabled}
                onChange={() => handleToggle(s.id)}
                id={`toggle-${s.id}`}
              />
              <label htmlFor={`toggle-${s.id}`}>{s.enabled ? "Enabled" : "Disabled"}</label>
            </div>

            {s.last_fired && (
              <div className="schedule-last-fired">
                Last fired: {new Date(s.last_fired).toLocaleString()}
              </div>
            )}
          </div>
        ))}

        {showCreate && (
          <div className="schedule-create-form">
            <h4>New Schedule</h4>
            <select
              value={createType}
              onChange={(e) => setCreateType(e.target.value)}
            >
              <option value="cron">🕐 Cron</option>
              <option value="webhook">🔗 Webhook</option>
              <option value="file_watch">👁 File Watch</option>
            </select>

            {Object.entries(fields).map(([key, cfg]) => (
              <input
                key={key}
                type="text"
                placeholder={cfg.placeholder}
                value={createConfig[key] || ""}
                onChange={(e) => handleConfigChange(key, e.target.value)}
              />
            ))}

            {error && (
              <div style={{ color: "#dc2626", fontSize: 12, marginBottom: 6 }}>
                {error}
              </div>
            )}

            <button onClick={handleCreate} disabled={loading}>
              {loading ? "Creating..." : "Create Schedule"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ScheduleManager;
