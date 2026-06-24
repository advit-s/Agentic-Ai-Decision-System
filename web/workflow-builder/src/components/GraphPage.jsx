// GraphPage.jsx — Knowledge Graph view with extraction, entities, relationships, risks, metrics
import React, { useState, useEffect, useCallback } from "react";
import {
  extractGraph,
  getGraph,
  listGraphNodes,
  listGraphRisks,
  listGraphMetrics,
  getLatestExtraction,
  getGraphRuns,
  getGraphAuditEvents,
  getGraphMetricsAggregates,
} from "../api";
import { usePermission } from "../hooks/usePermission";
import { useToast } from "./Toast";

function GraphPage({ workspaceId }) {
    const { can } = usePermission();
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
  const [latestRun, setLatestRun] = useState(null);
  const [extractionRuns, setExtractionRuns] = useState([]);
  const [showRuns, setShowRuns] = useState(false);
  const [auditEvents, setAuditEvents] = useState([]);
  const [showEvidenceModal, setShowEvidenceModal] = useState(null);
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

      // Load latest extraction run
      try {
        const run = await getLatestExtraction(workspaceId);
        setLatestRun(run);
      } catch (_) { /* not available */ }
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
    if (!can("graph.extract")) {
      showToast("Graph extraction permission denied", "error");
      return;
    }
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
        <span className="graph-ai-notice">AI-assisted extraction is not yet available. Using deterministic extraction only.</span>
      </div>

      {/* Extraction status */}
      {latestRun && (
        <div className="graph-extraction-status">
          <span className={`graph-status-badge graph-status-${latestRun.status}`}>
            {latestRun.status === "completed" ? "✓" : latestRun.status === "failed" ? "✗" : "⋯"} Last extraction: {latestRun.status}
          </span>
          <span className="graph-extraction-time">
            {latestRun.completed_at ? new Date(latestRun.completed_at).toLocaleString() : ""}
          </span>
          <span className="graph-extraction-counts">
            {latestRun.nodes_created > 0 && <span>{latestRun.nodes_created} entities</span>}
            {latestRun.edges_created > 0 && <span> · {latestRun.edges_created} relationships</span>}
            {latestRun.risks_created > 0 && <span> · {latestRun.risks_created} risks</span>}
            {latestRun.metrics_created > 0 && <span> · {latestRun.metrics_created} metrics</span>}
            {latestRun.duration_ms > 0 && <span> · {Math.round(latestRun.duration_ms)}ms</span>}
          </span>
          {latestRun.warnings?.length > 0 && (
            <span className="graph-extraction-warnings" title={latestRun.warnings.join("; ")}>
              ⚠ {latestRun.warnings.length} warnings
            </span>
          )}
          {latestRun.errors?.length > 0 && (
            <span className="graph-extraction-errors" title={latestRun.errors.join("; ")}>
              ✗ {latestRun.errors.length} errors
            </span>
          )}
          <button className="graph-runs-btn" onClick={() => {
            getGraphRuns(workspaceId).then(r => setExtractionRuns(r.runs || [])).catch(() => {});
            setShowRuns(true);
          }}>
            View Runs
          </button>
        </div>
      )}

      {!latestRun && !loading && (
        <div className="graph-extraction-status graph-extraction-status-empty">
          <span>No extraction runs yet. Paste text and click "Extract Graph" above.</span>
        </div>
      )}

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
                      {node.evidence_ids?.length > 0 && (
                        <span className="graph-evidence-link" onClick={() => setShowEvidenceModal({type: "entity", data: node})}>
                          Evidence: {node.evidence_ids.length} refs
                        </span>
                      )}
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
                      {risk.evidence_ids?.length > 0 && (
                        <span className="graph-evidence-link" onClick={() => setShowEvidenceModal({type: "risk", data: risk})}>
                          Evidence: {risk.evidence_ids.length} refs
                        </span>
                      )}
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
                      <td>
                        {m.evidence_ids?.length > 0 ? (
                          <span className="graph-evidence-link" onClick={() => setShowEvidenceModal({type: "metric", data: m})}>
                            {m.evidence_ids.length} refs
                          </span>
                        ) : 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
      {/* Evidence preview modal */}
      {showEvidenceModal && (
        <div className="graph-modal-overlay" onClick={() => setShowEvidenceModal(null)}>
          <div className="graph-modal" onClick={(e) => e.stopPropagation()}>
            <div className="graph-modal-header">
              <h3>Evidence: {showEvidenceModal.type}</h3>
              <button className="graph-modal-close" onClick={() => setShowEvidenceModal(null)}>✕</button>
            </div>
            <div className="graph-modal-body">
              <p><strong>Name:</strong> {showEvidenceModal.data.name || showEvidenceModal.data.title || showEvidenceModal.data.metric_id}</p>
              {showEvidenceModal.data.description && <p><strong>Description:</strong> {showEvidenceModal.data.description}</p>}
              <p><strong>Evidence refs:</strong> {showEvidenceModal.data.evidence_ids?.length || 0}</p>
              {showEvidenceModal.data.evidence_ids?.length > 0 && (
                <div>
                  <p><strong>Evidence IDs:</strong></p>
                  <ul className="graph-evidence-list">
                    {showEvidenceModal.data.evidence_ids.map((eid, i) => (
                      <li key={i}><code>{eid}</code></li>
                    ))}
                  </ul>
                </div>
              )}
              <p><strong>Source refs:</strong> {showEvidenceModal.data.source_ids?.length || 0}</p>
              <p><strong>Confidence:</strong> {showEvidenceModal.data.confidence || "N/A"}</p>
              <p><strong>Status:</strong> {showEvidenceModal.data.status || "extracted"}</p>
            </div>
          </div>
        </div>
      )}

      {/* Extraction runs modal */}
      {showRuns && (
        <div className="graph-modal-overlay" onClick={() => setShowRuns(false)}>
          <div className="graph-modal graph-modal-wide" onClick={(e) => e.stopPropagation()}>
            <div className="graph-modal-header">
              <h3>Extraction Runs ({extractionRuns.length})</h3>
              <button className="graph-modal-close" onClick={() => setShowRuns(false)}>✕</button>
            </div>
            <div className="graph-modal-body">
              {extractionRuns.length === 0 ? (
                <p className="graph-empty">No extraction runs recorded.</p>
              ) : (
                <table className="graph-runs-table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Status</th>
                      <th>Entities</th>
                      <th>Edges</th>
                      <th>Risks</th>
                      <th>Metrics</th>
                      <th>Duration</th>
                      <th>Warnings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {extractionRuns.slice(0, 20).map((run) => (
                      <tr key={run.run_id}>
                        <td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : "-"}</td>
                        <td><span className={`graph-status-badge graph-status-${run.status}`}>{run.status}</span></td>
                        <td>{run.nodes_created}</td>
                        <td>{run.edges_created}</td>
                        <td>{run.risks_created}</td>
                        <td>{run.metrics_created}</td>
                        <td>{run.duration_ms ? Math.round(run.duration_ms) + "ms" : "-"}</td>
                        <td>{run.warnings?.length || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default GraphPage;
