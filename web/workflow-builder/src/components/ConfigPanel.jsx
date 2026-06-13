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

  function handleConfigChange(changes) {
    onUpdateConfig(selectedNode.id, { ...selectedNode.data.config, ...changes });
  }

  function handleLabelChange(e) {
    onUpdateLabel(selectedNode.id, e.target.value);
  }

  function handleErrorPolicyChange(e) {
    onUpdateConfig(selectedNode.id, {
      ...selectedNode.data.config,
      error_policy: e.target.value,
    });
  }

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

        <div className="config-section">
          <div className="config-section-title">Configuration</div>
          <SchemaForm
            schema={nodeType.config_schema}
            values={selectedNode.data.config || {}}
            onChange={handleConfigChange}
          />
        </div>

        {(errorPolicies && errorPolicies.length > 0) && (
          <div className="config-section">
            <label className="config-label">Error Policy</label>
            <select
              className="config-input"
              value={selectedNode.data.config?.error_policy || "fail_workflow"}
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
