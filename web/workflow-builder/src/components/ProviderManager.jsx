// components/ProviderManager.jsx — Manage LLM provider configurations

import React, { useState, useEffect, useCallback } from "react";
import {
  listProviders,
  createProvider,
  deleteProvider,
  checkProvider,
  setDefaultProvider,
  updateProvider,
} from "../api";
import "../styles/provider-manager.css";

function ProviderManager({ onClose }) {
  const [providers, setProviders] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    name: "",
    api_base: "",
    api_key_env: "",
    default_model: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [healthStatuses, setHealthStatuses] = useState({});

  const loadProviders = useCallback(async () => {
    try {
      const data = await listProviders();
      setProviders(data.providers || []);
    } catch {
      setProviders([]);
    }
  }, []);

  useEffect(() => {
    loadProviders();
  }, [loadProviders]);

  function handleFormChange(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function resetForm() {
    setForm({ name: "", api_base: "", api_key_env: "", default_model: "" });
    setError(null);
    setTestResult(null);
  }

  async function handleAdd() {
    if (!form.name || !form.api_base || !form.default_model) {
      setError("Name, API Base, and Default Model are required");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await createProvider(form);
      setShowAdd(false);
      resetForm();
      await loadProviders();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(name) {
    try {
      await deleteProvider(name);
      await loadProviders();
    } catch {
      // silently ignore
    }
  }

  async function handleCheck(name) {
    setTesting(name);
    try {
      const result = await checkProvider(name);
      setHealthStatuses((prev) => ({ ...prev, [name]: result }));
    } catch (err) {
      setHealthStatuses((prev) => ({
        ...prev,
        [name]: { status: "error", error: err.message },
      }));
    } finally {
      setTesting(null);
    }
  }

  async function handleCheckAll() {
    const names = providers.map((p) => p.name);
    await Promise.all(names.map((name) => handleCheck(name)));
  }

  async function handleSetDefault(name) {
    try {
      await setDefaultProvider(name);
      await loadProviders();
    } catch {
      // silently ignore
    }
  }

  return (
    <div className="provider-manager">
      <div className="provider-manager-header">
        <span>🤖 LLM Providers</span>
        <div className="provider-header-actions">
          {providers.length > 0 && (
            <button
              onClick={handleCheckAll}
              className="check-all-btn"
              title="Check all provider connections"
            >
              🔄 Check All
            </button>
          )}
          <button
            onClick={() => {
              setShowAdd(!showAdd);
              if (!showAdd) resetForm();
            }}
            title={showAdd ? "Cancel" : "Add provider"}
          >
            {showAdd ? "✕" : "+"}
          </button>
        </div>
      </div>

      <div className="provider-list">
        {providers.length === 0 && !showAdd && (
          <div className="provider-empty">No providers configured</div>
        )}

        {providers.map((p, i) => {
          const health = healthStatuses[p.name];
          const healthOk = health?.status === "ok";
          return (
            <div key={p.name} className="provider-card">
              <div className="provider-card-header">
                <span className="provider-name">
                  {i === 0 && <span title="Default provider" className="provider-default-badge">★</span>}
                  <span
                    className={`provider-health-dot ${health ? (healthOk ? "health-ok" : "health-err") : "health-unknown"}`}
                    title={
                      health
                        ? healthOk
                          ? `Connected (${health.model})`
                          : `Error: ${health.error}`
                        : "Not checked yet"
                    }
                  />
                  {p.name}
                </span>
                <div className="provider-card-actions">
                  <button
                    onClick={() => handleSetDefault(p.name)}
                    className="default-btn"
                    title="Set as default"
                    disabled={i === 0}
                  >
                    ◎
                  </button>
                  <button
                    onClick={() => handleDelete(p.name)}
                    className="delete-btn"
                    title="Delete provider"
                  >
                    🗑
                  </button>
                </div>
              </div>

              <div className="provider-detail">
                <strong>API:</strong> {p.api_base}
              </div>
              <div className="provider-detail">
                <strong>Model:</strong> {p.default_model}
              </div>
              <div className="provider-detail">
                <strong>Key:</strong>{" "}
                <span className={p.api_key_configured ? "key-configured" : "key-missing"}>
                  {p.api_key_configured ? "✓ Configured" : "✗ Not set"}
                </span>
              </div>

              <div className="provider-test-row">
                <button
                  onClick={() => handleCheck(p.name)}
                  disabled={testing === p.name}
                  className="test-btn"
                >
                  {testing === p.name ? "⏳ Testing..." : "🔌 Test Connection"}
                </button>
              </div>

              {health && (
                <div className={`provider-test-result ${health.status}`}>
                  {health.status === "ok"
                    ? `✓ ${health.response}`
                    : `✗ ${health.error}`}
                </div>
              )}
            </div>
          );
        })}

        {showAdd && (
          <div className="provider-add-form">
            <h4>New Provider</h4>

            <label>Name *</label>
            <input
              type="text"
              placeholder="e.g. openai"
              value={form.name}
              onChange={(e) => handleFormChange("name", e.target.value)}
            />

            <label>API Base URL *</label>
            <input
              type="text"
              placeholder="https://api.openai.com/v1"
              value={form.api_base}
              onChange={(e) => handleFormChange("api_base", e.target.value)}
            />

            <label>Default Model *</label>
            <input
              type="text"
              placeholder="gpt-4o"
              value={form.default_model}
              onChange={(e) => handleFormChange("default_model", e.target.value)}
            />

            <label>API Key Env Variable</label>
            <input
              type="text"
              placeholder="OPENAI_API_KEY"
              value={form.api_key_env}
              onChange={(e) => handleFormChange("api_key_env", e.target.value)}
            />

            {error && <div className="provider-form-error">{error}</div>}

            <button onClick={handleAdd} disabled={loading}>
              {loading ? "Adding..." : "Add Provider"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProviderManager;
