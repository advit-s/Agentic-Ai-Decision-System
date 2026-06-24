// GraphPage.jsx — Knowledge Graph view with extraction, entities, relationships, risks, metrics
import React, { useState, useEffect, useCallback } from "react";
import {
  extractGraph,
  getGraph,
  listGraphNodes,
  listGraphRisks,
  listGraphMetrics,
} from "../api";
import { useToast } from "./Toast";

function GraphPage({ workspaceId }) {
  const [activeTab, setActiveTab] = useState("entities");
  const [loading, setLoading] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);
  const [risks, setRisks] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [sourceText, setSourceText] = useState("");
  const [nodeFilter, setNodeFilter] = useState("");
  const [error, setError] = useState(null);
  const { addToast } = useToast();

  const loadGraph = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const [nodeData, riskData, metricData] = await Promise.all([
        listGraphNodes(workspaceId),
        listGraphRisks(workspaceId),
        listGraphMetrics(workspaceId),
      ]);
      setNodes(Array.isArray(nodeData) ? nodeData : []);
      setRisks(Array.isArray(riskData) ? riskData : []);
      setMetrics(Array.isArray(metricData) ? metricData : []);

      // Also load edges from full graph
      const graphData = await getGraph(workspaceId);
      setEdges(Array.isArray(graphData?.edges) ? graphData.edges : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  const handleExtract = async () => {
    if (!sourceText.trim()) {
      addToast("Enter source text first", "warning");
      return;
    }
    setExtracting(true);
    setError(null);
    try {
      const result = await extractGraph(workspaceId, [
        { text: sourceText, evidence_id: "ui-ev-1", source_id: "ui-src-1", chunk_id: "ui-ch-1" },
      ]);
      addToast(`Extracted: ${result.nodes_extracted} entities, ${result.risks_extracted} risks, ${result.metrics_extracted} metrics`, "success");
      setSourceText("");
      await loadGraph();
    } catch (err) {
      setError(err.message);
      addToast("Extraction failed: " + err.message, "error");
    } finally {
      setExtracting(false);
    }
  };

  const filteredNodes = nodeFilter
    ? nodes.filter((n) => n.name?.toLowerCase().includes(nodeFilter.toLowerCase()) || n.node_type?.toLowerCase().includes(nodeFilter.toLowerCase()))
    : nodes;

  const nodeTypes = [...new Set(nodes.map((n) => n.node_type).filter(Boolean))];

  const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
  const sortedRisks = [...risks].sort((a, b) => (severityOrder[a.severity] ?? 99) - (severityOrder[b.severity] ?? 99));

  return (
    <div className="graph-page">
      <div className="graph-page-header">
        <h2>Knowledge Graph</h2>
        <span className="graph-summary-badge">
          {nodes.length} entities · {edges.length} relationships · {risks.length} risks · {metrics.length} metrics
        </span>
      </div>

      {/* Extraction input */}
      <div className="graph-extract-box">
        <textarea
          className="graph-extract-input"
          rows={3}
          placeholder="Paste company text to extract entities, risks, and metrics from..."
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
        />
        <button
          className="graph-extract-btn"
          onClick={handleExtract}
          disabled={extracting || !sourceText.trim()}
        >
          {extracting ? "Extracting..." : "Extract Graph"}
        </button>
      </div>

      {error && <div className="graph-error">Error: {error}</div>}

      {/* Tab navigation */}
      <div className="graph-tabs">
        {["entities", "relationships", "risks", "metrics"].map((tab) => (
          <button
            key={tab}
            className={`graph-tab ${activeTab === tab ? "graph-tab-active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            {tab === "entities" && ` (${filteredNodes.length})`}
            {tab === "relationships" && ` (${edges.length})`}
            {tab === "risks" && ` (${risks.length})`}
            {tab === "metrics" && ` (${metrics.length})`}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="graph-tab-content">
        {loading && <div className="graph-loading">Loading graph data...</div>}

        {!loading && activeTab === "entities" && (
          <div className="graph-section">
            <div className="graph-filter-bar">
              <input
                type="text"
                placeholder="Filter entities by name or type..."
                value={nodeFilter}
                onChange={(e) => setNodeFilter(e.target.value)}
                className="graph-filter-input"
              />
              <div className="graph-type-filters">
                {nodeTypes.map((t) => (
                  <button
                    key={t}
                    className={`graph-type-chip ${nodeFilter === t ? "graph-type-chip-active" : ""}`}
                    onClick={() => setNodeFilter(nodeFilter === t ? "" : t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
            {filteredNodes.length === 0 ? (
              <p className="graph-empty">No entities found. Extract text above to discover entities.</p>
            ) : (
              <div className="graph-list">
                {filteredNodes.map((node) => (
                  <div key={node.node_id} className="graph-list-item">
                    <div className="graph-list-item-header">
                      <strong>{node.name}</strong>
                      <span className={`graph-type-tag graph-type-${node.node_type}`}>{node.node_type}</span>
                      <span className={`graph-confidence graph-confidence-${node.confidence}`}>{node.confidence}</span>
                      {node.status !== "extracted" && <span className={`graph-status graph-status-${node.status}`}>{node.status}</span>}
                    </div>
                    {node.description && <p className="graph-list-item-desc">{node.description}</p>}
                    <div className="graph-list-item-meta">
                      {node.evidence_ids?.length > 0 && <span>Evidence: {node.evidence_ids.length} refs</span>}
                      {node.source_ids?.length > 0 && <span>Sources: {node.source_ids.length}</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === "relationships" && (
          <div className="graph-section">
            {edges.length === 0 ? (
              <p className="graph-empty">No relationships found. Extract text to discover relationships.</p>
            ) : (
              <div className="graph-list">
                {edges.map((edge) => (
                  <div key={edge.edge_id} className="graph-list-item">
                    <div className="graph-list-item-header">
                      <strong>{edge.source_node_id?.substring(0, 30)}</strong>
                      <span className="graph-arrow">→</span>
                      <strong>{edge.target_node_id?.substring(0, 30)}</strong>
                      <span className={`graph-type-tag graph-type-${edge.edge_type}`}>{edge.edge_type}</span>
                      <span className={`graph-confidence graph-confidence-${edge.confidence}`}>{edge.confidence}</span>
                    </div>
                    {edge.label && <p className="graph-list-item-desc">{edge.label}</p>}
                    {edge.evidence_ids?.length > 0 && (
                      <div className="graph-list-item-meta">
                        <span>Evidence: {edge.evidence_ids.length} refs</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === "risks" && (
          <div className="graph-section">
            {sortedRisks.length === 0 ? (
              <p className="graph-empty">No risks detected. Extract text to identify risks.</p>
            ) : (
              <div className="graph-list">
                {sortedRisks.map((risk) => (
                  <div key={risk.risk_id} className="graph-list-item">
                    <div className="graph-list-item-header">
                      <span className={`graph-risk-icon graph-risk-${risk.severity}`}>
                        {risk.severity === "critical" ? "🔴" : risk.severity === "high" ? "⚠️" : risk.severity === "medium" ? "⚡" : "ℹ️"}
                      </span>
                      <strong>{risk.title}</strong>
                      <span className={`graph-risk-severity graph-risk-${risk.severity}`}>{risk.severity}</span>
                      <span className={`graph-type-tag`}>{risk.category}</span>
                      <span className={`graph-confidence graph-confidence-${risk.confidence}`}>{risk.confidence}</span>
                    </div>
                    {risk.description && <p className="graph-list-item-desc">{risk.description}</p>}
                    <div className="graph-list-item-meta">
                      {risk.evidence_ids?.length > 0 && <span>Evidence: {risk.evidence_ids.length} refs</span>}
                      {risk.related_entity_ids?.length > 0 && <span>Related entities: {risk.related_entity_ids.length}</span>}
                    </div>
                    {risk.recommended_actions?.length > 0 && (
                      <div className="graph-risk-actions">
                        {risk.recommended_actions.slice(0, 2).map((action, i) => (
                          <span key={i} className="graph-risk-action">{action}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {!loading && activeTab === "metrics" && (
          <div className="graph-section">
            {metrics.length === 0 ? (
              <p className="graph-empty">No metrics extracted. Extract text to find metrics.</p>
            ) : (
              <table className="graph-metrics-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Value</th>
                    <th>Unit</th>
                    <th>Period</th>
                    <th>Confidence</th>
                    <th>Evidence</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((m) => (
                    <tr key={m.metric_id}>
                      <td><strong>{m.name}</strong></td>
                      <td>{m.value}</td>
                      <td>{m.unit || "-"}</td>
                      <td>{m.period || "-"}</td>
                      <td><span className={`graph-confidence graph-confidence-${m.confidence}`}>{m.confidence}</span></td>
                      <td>{m.evidence_ids?.length || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default GraphPage;
