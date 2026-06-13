import React, { useState, useEffect, useMemo } from "react";
import { getExecutionDetail } from "../api";
import "../styles/execution-compare.css";

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
  if (status === "completed") return "ec-status-badge ec-status-completed";
  if (status === "failed") return "ec-status-badge ec-status-failed";
  return "ec-status-badge ec-status-running";
}

function statusBadgeText(status) {
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  return "Running";
}

function nodeStatusIcon(status) {
  if (status === "completed") return "✅";
  if (status === "failed") return "❌";
  if (status === "skipped") return "⏭";
  return "⏳";
}

function NodeRow({ node }) {
  return (
    <div className={`ec-node-row ec-node-${node.status}`}>
      <span className="ec-node-status">{nodeStatusIcon(node.status)}</span>
      <span className="ec-node-label">{node.label}</span>
      <span className="ec-node-duration">{node.duration ? `${node.duration}s` : ""}</span>
    </div>
  );
}

function ClaimRow({ claim }) {
  return (
    <div className={`ec-claim-row ec-claim-${claim.status}`}>
      <span className={`ec-claim-status ec-tag-${claim.status}`}>{claim.status}</span>
      <span className="ec-claim-statement">{claim.statement}</span>
      <span className="ec-claim-meta">{Math.round(claim.confidence * 100)}% &middot; {claim.sourceNode}</span>
    </div>
  );
}

function RunColumn({ run, label }) {
  if (!run) return null;
  const dur = run.completed_at && run.started_at
    ? ((new Date(run.completed_at) - new Date(run.started_at)) / 1000).toFixed(1) + "s"
    : "";
  return (
    <div className="ec-column">
      <div className="ec-column-header">
        <span className="ec-column-label">{label}</span>
        <span className={statusBadgeClass(run.status)}>{statusBadgeText(run.status)}</span>
        <span className="ec-column-date">{formatDate(run.started_at)}</span>
        <span className="ec-column-duration">{dur}</span>
      </div>

      <div className="ec-column-section">
        <div className="ec-column-section-title">Nodes</div>
        <div className="ec-column-node-list">
          {(run.node_states || []).map((node) => (
            <NodeRow key={node.nodeId} node={node} />
          ))}
        </div>
      </div>

      <div className="ec-column-section">
        <div className="ec-column-section-title">Claims</div>
        <div className="ec-column-claim-list">
          {(run.claims || []).length === 0 ? (
            <div className="ec-empty-mini">No claims</div>
          ) : (
            (run.claims || []).map((claim, idx) => (
              <ClaimRow key={idx} claim={claim} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function ExecutionCompare({ runIdA, runIdB, onClose }) {
  const [detailA, setDetailA] = useState(null);
  const [detailB, setDetailB] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getExecutionDetail(runIdA).catch(() => null),
      getExecutionDetail(runIdB).catch(() => null),
    ])
      .then(([a, b]) => {
        if (!a || !b) {
          setError("Could not load one or both executions");
          setLoading(false);
          return;
        }
        setDetailA(a);
        setDetailB(b);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not load one or both executions");
        setLoading(false);
      });
  }, [runIdA, runIdB]);

  const differences = useMemo(() => {
    if (!detailA || !detailB) return [];
    const diffs = [];

    // Duration diff
    const durA = detailA.completed_at && detailA.started_at
      ? new Date(detailA.completed_at) - new Date(detailA.started_at)
      : 0;
    const durB = detailB.completed_at && detailB.started_at
      ? new Date(detailB.completed_at) - new Date(detailB.started_at)
      : 0;
    if (durA !== durB) {
      diffs.push({
        type: "duration",
        text: `Duration: ${formatDuration(durA)} vs ${formatDuration(durB)} (${durA > durB ? "A slower" : "B slower"})`,
      });
    }

    // Status diff
    if (detailA.status !== detailB.status) {
      diffs.push({
        type: "status",
        text: `Final status: ${detailA.status} vs ${detailB.status}`,
      });
    }

    // Node diffs
    const nodesA = detailA.node_states || [];
    const nodesB = detailB.node_states || [];
    const nodeMapB = {};
    nodesB.forEach((n) => { nodeMapB[n.nodeId] = n; });

    nodesA.forEach((node) => {
      const other = nodeMapB[node.nodeId];
      if (!other) {
        diffs.push({ type: "node", text: `Node "${node.label}" only in Run A` });
      } else if (node.status !== other.status) {
        diffs.push({
          type: "node",
          text: `Node "${node.label}": ${node.status} (A) vs ${other.status} (B)`,
        });
      }
    });

    nodesB.forEach((node) => {
      if (!nodesA.find((n) => n.nodeId === node.nodeId)) {
        diffs.push({ type: "node", text: `Node "${node.label}" only in Run B` });
      }
    });

    // Claim diffs
    const claimsA = detailA.claims || [];
    const claimsB = detailB.claims || [];

    claimsA.forEach((ca, idx) => {
      const cb = claimsB[idx];
      if (!cb) {
        diffs.push({ type: "claim", text: `Claim "${ca.statement.substring(0, 50)}..." only in Run A` });
      } else if (ca.status !== cb.status) {
        diffs.push({
          type: "claim",
          text: `Claim status changed: "${ca.statement.substring(0, 50)}..." — ${ca.status} (A) vs ${cb.status} (B)`,
        });
      }
    });

    if (claimsB.length > claimsA.length) {
      for (let i = claimsA.length; i < claimsB.length; i++) {
        diffs.push({
          type: "claim",
          text: `Claim "${claimsB[i].statement.substring(0, 50)}..." only in Run B`,
        });
      }
    }

    if (diffs.length === 0) {
      diffs.push({ type: "identical", text: "These runs are identical" });
    }

    return diffs;
  }, [detailA, detailB]);

  // --- Loading ---
  if (loading) {
    return (
      <div className="ec-panel">
        <div className="ec-header">
          <span className="ec-header-title">Comparing Executions</span>
          <button className="ec-close" onClick={onClose}>&times;</button>
        </div>
        <div className="ec-loading">
          <div className="ec-spinner"></div>
          <span>Loading execution data...</span>
        </div>
      </div>
    );
  }

  // --- Error ---
  if (error || !detailA || !detailB) {
    return (
      <div className="ec-panel">
        <div className="ec-header">
          <span className="ec-header-title">Comparing Executions</span>
          <button className="ec-close" onClick={onClose}>&times;</button>
        </div>
        <div className="ec-error">
          {error || "Could not load one or both executions"}
        </div>
      </div>
    );
  }

  const workflowName = detailA.workflow_name || detailB.workflow_name || "Workflow";

  return (
    <div className="ec-panel">
      <div className="ec-header">
        <span className="ec-header-title">Comparing: {workflowName}</span>
        <button className="ec-close" onClick={onClose}>&times;</button>
      </div>

      <div className="ec-scroll">
        <div className="ec-layout">
          <RunColumn run={detailA} label="Run A" />
          <RunColumn run={detailB} label="Run B" />
        </div>

        <div className="ec-diff-section">
          <div className="ec-diff-header">Differences</div>
          {differences.length === 0 ? (
            <div className="ec-empty">These runs are identical</div>
          ) : (
            <div className="ec-diff-list">
              {differences.map((diff, idx) => (
                <div key={idx} className={`ec-diff-item ec-diff-${diff.type}`}>
                  {diff.type === "identical" && <span className="ec-diff-identical-mark">&#10003;</span>}
                  <span>{diff.text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ExecutionCompare;
