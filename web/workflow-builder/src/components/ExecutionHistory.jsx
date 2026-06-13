import React, { useState, useEffect, useCallback } from "react";
import { listExecutionHistory, getExecutionDetail } from "../api";
import "../styles/execution-panel.css";

function formatDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${months[d.getMonth()]} ${d.getDate()}, ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatDuration(ms) {
  if (ms == null) return "";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function statusBadgeClass(status) {
  if (status === "completed") return "eh-run-status-badge eh-status-completed";
  if (status === "failed") return "eh-run-status-badge eh-status-failed";
  return "eh-run-status-badge eh-status-running";
}

function statusBadgeText(status) {
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  return "Running";
}

function claimPills(summary) {
  if (!summary || summary.total === 0) return <span className="eh-claim-pills">No claims</span>;
  const parts = [];
  if (summary.verified > 0) parts.push(<span key="v" className="eh-pill eh-pill-verified">{summary.verified} verified</span>);
  if (summary.unsupported > 0) parts.push(<span key="u" className="eh-pill eh-pill-unsupported">{summary.unsupported} unsupported</span>);
  if (summary.contradicted > 0) parts.push(<span key="c" className="eh-pill eh-pill-contradicted">{summary.contradicted} contradicted</span>);
  return <span className="eh-claim-pills">{parts}</span>;
}

function ExecutionHistory({ onClose, onSelectRun, onCompare, onCompareVersions }) {
  const [runs, setRuns] = useState([]);
  const [selectedRuns, setSelectedRuns] = useState(new Set());
  const [detailId, setDetailId] = useState(null);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);
  const [filter, setFilter] = useState("");
  const [sortBy, setSortBy] = useState("date_desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listExecutionHistory()
      .then((data) => {
        setRuns(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Failed to load history");
        setLoading(false);
      });
  }, []);

  const toggleSelect = useCallback((id) => {
    setSelectedRuns((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= 2) {
          const first = next.values().next().value;
          next.delete(first);
        }
        next.add(id);
      }
      return next;
    });
  }, []);

  const openDetail = useCallback((id) => {
    setDetailId(id);
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    getExecutionDetail(id)
      .then((data) => {
        setDetail(data);
        setDetailLoading(false);
      })
      .catch((err) => {
        setDetailError(err.message || "Failed to load detail");
        setDetailLoading(false);
      });
  }, []);

  const handleCompare = useCallback(() => {
    const ids = Array.from(selectedRuns);
    if (ids.length === 2 && onCompare) {
      onCompare(ids[0], ids[1]);
    }
  }, [selectedRuns, onCompare]);

  const filteredRuns = runs
    .filter((r) => {
      if (!filter) return true;
      return r.workflow_name?.toLowerCase().includes(filter.toLowerCase());
    })
    .sort((a, b) => {
      if (sortBy === "date_asc") return new Date(a.started_at || 0) - new Date(b.started_at || 0);
      if (sortBy === "date_desc") return new Date(b.started_at || 0) - new Date(a.started_at || 0);
      if (sortBy === "duration") return (b.duration_ms || 0) - (a.duration_ms || 0);
      if (sortBy === "claims") {
        const ca = a.claim_summary?.total || 0;
        const cb = b.claim_summary?.total || 0;
        return cb - ca;
      }
      return 0;
    });

  // --- Loading state ---
  if (loading) {
    return (
      <div className="eh-panel">
        <div className="eh-header">
          <span className="eh-header-title">Execution History</span>
          <button className="eh-close" onClick={onClose}>&times;</button>
        </div>
        <div className="eh-loading">
          <div className="eh-spinner"></div>
          <span>Loading execution history...</span>
        </div>
      </div>
    );
  }

  // --- Error state ---
  if (error) {
    return (
      <div className="eh-panel">
        <div className="eh-header">
          <span className="eh-header-title">Execution History</span>
          <button className="eh-close" onClick={onClose}>&times;</button>
        </div>
        <div className="eh-error">
          <span className="eh-error-icon">!</span>
          <span>{error}</span>
        </div>
      </div>
    );
  }

  // --- Detail view ---
  if (detailId) {
    return (
      <div className="eh-panel">
        <div className="eh-header">
          <button className="eh-back-btn" onClick={() => { setDetailId(null); setDetail(null); }}>&larr; Back</button>
          <span className="eh-header-title">Run Detail</span>
          <button className="eh-close" onClick={onClose}>&times;</button>
        </div>
        {detailLoading && (
          <div className="eh-loading">
            <div className="eh-spinner"></div>
            <span>Loading execution detail...</span>
          </div>
        )}
        {detailError && (
          <div className="eh-error">
            <span className="eh-error-icon">!</span>
            <span>{detailError}</span>
          </div>
        )}
        {detail && !detailLoading && (
          <div className="eh-detail-scroll">
            <div className="eh-detail-header">
              <span className={statusBadgeClass(detail.status)}>{statusBadgeText(detail.status)}</span>
              <span className="eh-detail-date">{formatDate(detail.started_at)}</span>
              <span className="eh-detail-duration">{formatDuration(detail.completed_at ? new Date(detail.completed_at) - new Date(detail.started_at) : 0)}</span>
            </div>

            <div className="eh-detail-section">
              <div className="eh-detail-section-title">Nodes</div>
              <div className="eh-detail-node-list">
                {(detail.node_states || []).map((node) => (
                  <div key={node.nodeId} className={`eh-node-row eh-node-${node.status}`}>
                    <span className="eh-node-status-icon">
                      {node.status === "completed" ? "✅" : node.status === "failed" ? "❌" : node.status === "skipped" ? "⏭" : "⏳"}
                    </span>
                    <span className="eh-node-label">{node.label}</span>
                    <span className="eh-node-duration">{node.duration ? `${node.duration}s` : ""}</span>
                    {node.error && <span className="eh-node-error-text">{node.error}</span>}
                  </div>
                ))}
              </div>
            </div>

            <div className="eh-detail-section">
              <div className="eh-detail-section-title">Claims</div>
              <div className="eh-detail-claim-list">
                {(detail.claims || []).length === 0 ? (
                  <div className="eh-empty-mini">No claims recorded</div>
                ) : (
                  (detail.claims || []).map((claim, idx) => (
                    <div key={idx} className={`eh-claim-row eh-claim-${claim.status}`}>
                      <div className="eh-claim-row-header">
                        <span className={`eh-claim-status-tag eh-tag-${claim.status}`}>
                          {claim.status}
                        </span>
                        <span className="eh-claim-confidence">
                          {Math.round(claim.confidence * 100)}%
                        </span>
                        <span className="eh-claim-source">{claim.sourceNode}</span>
                      </div>
                      <div className="eh-claim-statement">{claim.statement}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // --- Empty state ---
  if (runs.length === 0) {
    return (
      <div className="eh-panel">
        <div className="eh-header">
          <span className="eh-header-title">Execution History</span>
          <button className="eh-close" onClick={onClose}>&times;</button>
        </div>
        <div className="eh-empty">
          <div className="eh-empty-icon">No execution history yet</div>
          <div className="eh-empty-hint">Run a workflow to see its results here.</div>
        </div>
      </div>
    );
  }

  // --- List view (default) ---
  return (
    <div className="eh-panel">
      <div className="eh-header">
        <span className="eh-header-title">Execution History</span>
        <button className="eh-close" onClick={onClose}>&times;</button>
      </div>

      <div className="eh-toolbar">
        <input
          className="eh-search-input"
          type="text"
          placeholder="Filter by workflow name..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        />
        {onCompareVersions && (
          <button className="eh-compare-btn" onClick={onCompareVersions} title="Compare workflow versions">
            {"📋"} Compare Versions
          </button>
        )}
        <select className="eh-sort-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="date_desc">Newest</option>
          <option value="date_asc">Oldest</option>
          <option value="duration">Duration</option>
          <option value="claims">Claims Count</option>
        </select>
      </div>

      {selectedRuns.size === 2 && (
        <div className="eh-compare-bar">
          <button className="eh-compare-btn" onClick={handleCompare}>
            Compare Selected
          </button>
        </div>
      )}

      <div className="eh-run-list">
        {filteredRuns.length === 0 && filter && (
          <div className="eh-empty-filter">
            No runs match "{filter}"
          </div>
        )}
        {filteredRuns.map((run) => (
          <div
            key={run.id}
            className={`eh-run-card ${selectedRuns.has(run.id) ? "eh-run-selected" : ""}`}
            onClick={() => {
              if (selectedRuns.size > 0) {
                toggleSelect(run.id);
              } else {
                openDetail(run.id);
              }
            }}
          >
            <div className="eh-run-card-header">
              <label className="eh-checkbox-label" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  className="eh-checkbox"
                  checked={selectedRuns.has(run.id)}
                  onChange={() => toggleSelect(run.id)}
                />
              </label>
              <span className={statusBadgeClass(run.status)}>{statusBadgeText(run.status)}</span>
              <span className="eh-run-date">{formatDate(run.started_at)}</span>
            </div>
            <div className="eh-run-name">{run.workflow_name}</div>
            <div className="eh-run-meta">
              <span className="eh-run-duration">{formatDuration(run.duration_ms)}</span>
              <span className="eh-run-nodes">{run.completed_nodes || 0}/{run.node_count || 0} nodes</span>
            </div>
            <div className="eh-run-claims">
              {claimPills(run.claim_summary)}
            </div>
            {run.error && (
              <div className="eh-run-error" title={run.error}>
                {run.error}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default ExecutionHistory;
