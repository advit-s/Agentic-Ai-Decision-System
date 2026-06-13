// components/WorkflowDiff.jsx — Side-by-side workflow version comparison
import React, { useState } from "react";
import "../styles/workflow-diff.css";

/* ── Helpers ──────────────────────────────────── */

function compareNodes(nodesA, nodesB) {
  const mapA = {};
  (nodesA || []).forEach(n => { mapA[n.id] = n; });

  const added = [];
  const removed = [];
  const changed = [];
  const same = [];

  (nodesB || []).forEach(n => {
    if (!mapA[n.id]) {
      added.push(n);
    } else {
      const a = mapA[n.id];
      const aConfig = JSON.stringify(a.config || {});
      const bConfig = JSON.stringify(n.config || {});
      if (aConfig !== bConfig || a.label !== n.label || a.type !== n.type) {
        changed.push({ a, b: n });
      } else {
        same.push(n);
      }
    }
  });

  (nodesA || []).forEach(n => {
    if (!(nodesB || []).some(b => b.id === n.id)) {
      removed.push(n);
    }
  });

  return { added, removed, changed, same };
}

function compareConnections(connsA, connsB) {
  const keyFn = (c) => `${c.source_node}->${c.target_node}`;
  const setA = new Set((connsA || []).map(keyFn));
  const setB = new Set((connsB || []).map(keyFn));

  const added = (connsB || []).filter(c => !setA.has(keyFn(c)));
  const removed = (connsA || []).filter(c => !setB.has(keyFn(c)));

  return { added, removed };
}

function configDiff(configA, configB) {
  const allKeys = new Set([
    ...Object.keys(configA || {}),
    ...Object.keys(configB || {}),
  ]);
  const diffs = [];
  allKeys.forEach(k => {
    const vA = configA ? configA[k] : undefined;
    const vB = configB ? configB[k] : undefined;
    if (JSON.stringify(vA) !== JSON.stringify(vB)) {
      diffs.push({ key: k, from: vA, to: vB });
    }
  });
  return diffs;
}

/* ── Component ────────────────────────────────── */

export default function WorkflowDiff({ workflowA, workflowB, onClose }) {
  const [expandSection, setExpandSection] = useState("all");
  const [selectedChanged, setSelectedChanged] = useState(null);

  if (!workflowA || !workflowB) {
    return (
      <div className="wd-panel">
        <div className="wd-header">
          <span className="wd-header-title">Workflow Version Diff</span>
          {onClose && <button className="wd-close" onClick={onClose}>✕</button>}
        </div>
        <div className="wd-error">
          <span className="wd-error-icon">⚠️</span>
          <span>Need two workflows to compare</span>
        </div>
      </div>
    );
  }

  const nodesA = workflowA.nodes || [];
  const nodesB = workflowB.nodes || [];
  const connsA = workflowA.connections || [];
  const connsB = workflowB.connections || [];

  const { added, removed, changed } = compareNodes(nodesA, nodesB);
  const { added: connsAdded, removed: connsRemoved } = compareConnections(connsA, connsB);

  const isIdentical =
    added.length === 0 &&
    removed.length === 0 &&
    changed.length === 0 &&
    connsAdded.length === 0 &&
    connsRemoved.length === 0;

  if (isIdentical) {
    return (
      <div className="wd-panel">
        <div className="wd-header">
          <span className="wd-header-title">Workflow Version Diff</span>
          {onClose && <button className="wd-close" onClick={onClose}>✕</button>}
        </div>
        <div className="wd-empty">
          <span className="wd-empty-icon">✅</span>
          <span className="wd-empty-text">No differences</span>
          <span className="wd-empty-hint">Both workflow definitions are identical</span>
        </div>
      </div>
    );
  }

  const selectedChangedDetail = selectedChanged
    ? changed.find(c => c.b.id === selectedChanged)
    : null;
  const configDiffs = selectedChangedDetail
    ? configDiff(selectedChangedDetail.a.config, selectedChangedDetail.b.config)
    : [];

  return (
    <div className="wd-panel">
      <div className="wd-header">
        <span className="wd-header-title">Workflow Version Diff</span>
        {onClose && <button className="wd-close" onClick={onClose}>✕</button>}
      </div>

      {/* Summary bar */}
      <div className="wd-summary-bar">
        <div className="wd-summary-columns">
          <div className="wd-summary-col">
            <span className="wd-summary-name">{workflowA.name || "Version A"}</span>
            <span className="wd-summary-meta">{nodesA.length} nodes, {connsA.length} connections</span>
          </div>
          <span className="wd-summary-vs">vs</span>
          <div className="wd-summary-col">
            <span className="wd-summary-name">{workflowB.name || "Version B"}</span>
            <span className="wd-summary-meta">{nodesB.length} nodes, {connsB.length} connections</span>
          </div>
        </div>
        <div className="wd-summary-counts">
          {changed.length > 0 && (
            <span className="wd-count-item wd-count-changed">{changed.length} changed</span>
          )}
          {added.length > 0 && (
            <span className="wd-count-item wd-count-added">{added.length} added</span>
          )}
          {removed.length > 0 && (
            <span className="wd-count-item wd-count-removed">{removed.length} removed</span>
          )}
          {connsAdded.length > 0 && (
            <span className="wd-count-item wd-count-added">{connsAdded.length} connections added</span>
          )}
          {connsRemoved.length > 0 && (
            <span className="wd-count-item wd-count-removed">{connsRemoved.length} connections removed</span>
          )}
        </div>
      </div>

      {/* Section toggle */}
      <div className="wd-section-tabs">
        <button
          className={"wd-section-tab" + (expandSection === "nodes" || expandSection === "all" ? " active" : "")}
          onClick={() => setExpandSection(expandSection === "nodes" ? "all" : "nodes")}
        >
          Nodes
        </button>
        <button
          className={"wd-section-tab" + (expandSection === "config" || expandSection === "all" ? " active" : "")}
          onClick={() => setExpandSection(expandSection === "config" ? "all" : "config")}
        >
          Config Diff
        </button>
      </div>

      <div className="wd-content">
        {/* Node comparison */}
        {(expandSection === "nodes" || expandSection === "all") && (
          <div>
            <div className="wd-section-title">Nodes</div>
            <div className="wd-layout">
              <div className="wd-column">
                <div className="wd-column-header">Version A</div>
                {nodesA.map(n => {
                  const isRemoved = removed.some(r => r.id === n.id);
                  const isChanged = changed.some(c => c.a.id === n.id);
                  return (
                    <div
                      key={n.id}
                      className={
                        "wd-node-row" +
                        (isRemoved ? " wd-node-removed" : "") +
                        (isChanged ? " wd-node-changed" : "")
                      }
                    >
                      <span className="wd-node-label">{n.label}</span>
                      {isRemoved && <span className="wd-node-badge wd-badge-removed">Removed</span>}
                      {isChanged && <span className="wd-node-badge wd-badge-changed">Changed</span>}
                    </div>
                  );
                })}
              </div>
              <div className="wd-column">
                <div className="wd-column-header">Version B</div>
                {nodesB.map(n => {
                  const isAdded = added.some(a => a.id === n.id);
                  const isChanged = changed.some(c => c.b.id === n.id);
                  return (
                    <div
                      key={n.id}
                      className={
                        "wd-node-row" +
                        (isAdded ? " wd-node-added" : "") +
                        (isChanged ? " wd-node-changed" : "")
                      }
                    >
                      <span className="wd-node-label">{n.label}</span>
                      {isAdded && <span className="wd-node-badge wd-badge-added">Added</span>}
                      {isChanged && <span className="wd-node-badge wd-badge-changed">Changed</span>}
                      {isChanged && (
                        <button
                          className="wd-diff-btn"
                          onClick={() => setSelectedChanged(n.id)}
                        >
                          View Diff
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Config diff detail */}
        {selectedChangedDetail && configDiffs.length > 0 && (expandSection === "config" || expandSection === "all") && (
          <div className="wd-config-diff">
            <div className="wd-section-title">Config Diff: {selectedChangedDetail.a.label}</div>
            {configDiffs.map(d => (
              <div key={d.key} className="wd-diff-row">
                <span className="wd-diff-key">{d.key}</span>
                <div className="wd-diff-values">
                  <span className="wd-diff-old">{JSON.stringify(d.from)}</span>
                  <span className="wd-diff-arrow">→</span>
                  <span className="wd-diff-new">{JSON.stringify(d.to)}</span>
                </div>
              </div>
            ))}
            <button className="wd-close-diff" onClick={() => setSelectedChanged(null)}>Close</button>
          </div>
        )}

        {/* Connection comparison */}
        <div className="wd-connection-diff">
          <div className="wd-section-title">Connections</div>
          {connsAdded.length === 0 && connsRemoved.length === 0 ? (
            <div className="wd-conn-nochange">No connection changes</div>
          ) : (
            <div>
              {connsAdded.length > 0 && (
                <div>
                  <div className="wd-conn-subtitle">Added ({connsAdded.length})</div>
                  {connsAdded.map(c => (
                    <div key={`${c.source_node}->${c.target_node}`} className="wd-conn-row wd-conn-added">
                      <span className="wd-conn-text">{c.source_node} → {c.target_node}</span>
                      <span className="wd-node-badge wd-badge-added">New</span>
                    </div>
                  ))}
                </div>
              )}
              {connsRemoved.length > 0 && (
                <div>
                  <div className="wd-conn-subtitle">Removed ({connsRemoved.length})</div>
                  {connsRemoved.map(c => (
                    <div key={`${c.source_node}->${c.target_node}`} className="wd-conn-row wd-conn-removed">
                      <span className="wd-conn-text">{c.source_node} → {c.target_node}</span>
                      <span className="wd-node-badge wd-badge-removed">Removed</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
