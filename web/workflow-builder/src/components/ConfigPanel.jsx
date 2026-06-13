// components/ConfigPanel.jsx
import React from "react";
import SchemaForm from "./SchemaForm";
import { getNodeCategoryConfig } from "../nodeTypes";
import "../styles/config-panel.css";

const ERROR_POLICIES = ["fail_workflow", "fail_node", "retry", "skip"];

function ConfigPanel({
  selectedNode,
  nodeType,
  onUpdateConfig,
  onUpdateLabel,
  onDelete,
  errorPolicies,
}) {
  if (!selectedNode || !nodeType) return null;

  const catConfig = getNodeCategoryConfig(nodeType.categories?.[0]);
  const currentConfig = selectedNode.data.config || {};
  const hasProviderField = nodeType.config_schema?.properties?.provider !== undefined;
  const currentProvider = currentConfig.provider || "fake";

  function handleConfigChange(changes) {
    onUpdateConfig(selectedNode.id, { ...currentConfig, ...changes });
  }

  function handleLabelChange(e) {
    onUpdateLabel(selectedNode.id, e.target.value);
  }

  function handleErrorPolicyChange(e) {
    onUpdateConfig(selectedNode.id, {
      ...currentConfig,
      error_policy: e.target.value,
    });
  }

  const PROVIDER_LABELS = {
    fake: { label: "Fake (offline)", icon: "🖥️", color: "#6b7280" },
    nvidia_nim: { label: "NVIDIA NIM", icon: "🔵", color: "#3b82f6" },
    ollama: { label: "Ollama (local)", icon: "🦙", color: "#8b5cf6" },
  };

  return (
    <div className="config-panel">
      <div className="config-panel-header" style={{ borderLeftColor: catConfig.color }}>
        <div className="config-node-type">
          <span className="config-cat-icon">{catConfig.icon}</span>
          <span>{nodeType.type}</span>
        </div>
      </div>

      <div className="config-panel-body">
        <div className="config-section">
          <label className="config-label">Label</label>
          <input
            className="config-input"
            type="text"
            value={selectedNode.data.label || ""}
            onChange={handleLabelChange}
          />
        </div>

        <div className="config-section">
          <label className="config-label">Description</label>
          <p className="config-desc">{nodeType.description}</p>
        </div>

        {hasProviderField && (
          <div className="config-section">
            <div className="config-section-title">Provider</div>
            <div className="config-provider-info">
              <span
                className="config-provider-badge"
                style={{
                  borderColor: (PROVIDER_LABELS[currentProvider] || PROVIDER_LABELS.fake).color,
                }}
              >
                <span>{(PROVIDER_LABELS[currentProvider] || PROVIDER_LABELS.fake).icon}</span>
                <span>{(PROVIDER_LABELS[currentProvider] || PROVIDER_LABELS.fake).label}</span>
              </span>
              <span className="config-provider-hint">
                Configured in settings below. Change the provider per-node from the dropdown.
              </span>
            </div>
          </div>
        )}

        <div className="config-section">
          <div className="config-section-title">Configuration</div>
          <SchemaForm
            schema={nodeType.config_schema}
            values={currentConfig}
            onChange={handleConfigChange}
          />
        </div>

        {(errorPolicies && errorPolicies.length > 0) && (
          <div className="config-section">
            <label className="config-label">Error Policy</label>
            <select
              className="config-input"
              value={currentConfig.error_policy || "fail_workflow"}
              onChange={handleErrorPolicyChange}
            >
              {errorPolicies.map((ep) => (
                <option key={ep} value={ep}>
                  {ep}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="config-section">
          <div className="config-section-title">Inputs</div>
          <div className="config-schema-view">
            {Object.keys(nodeType.input_schema?.properties || {}).length === 0 ? (
              <span className="config-muted">No inputs expected</span>
            ) : (
              Object.entries(nodeType.input_schema.properties).map(([key, prop]) => (
                <div key={key} className="config-port-item config-input-port">
                  <span className="config-port-name">{key}</span>
                  <span className="config-port-type">{prop.type || "any"}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="config-section">
          <div className="config-section-title">Outputs</div>
          <div className="config-schema-view">
            {Object.keys(nodeType.output_schema?.properties || {}).length === 0 ? (
              <span className="config-muted">No outputs</span>
            ) : (
              Object.entries(nodeType.output_schema.properties).map(([key, prop]) => (
                <div key={key} className="config-port-item config-output-port">
                  <span className="config-port-name">{key}</span>
                  <span className="config-port-type">{prop.type || "any"}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="config-section">
          <button
            className="config-delete-btn"
            onClick={() => onDelete(selectedNode.id)}
          >
            🗑 Delete Node
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfigPanel;
