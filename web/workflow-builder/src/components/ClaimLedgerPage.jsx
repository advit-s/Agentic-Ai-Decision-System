// ClaimLedgerPage.jsx — View and verify claims from workflow executions
import React, { useState, useEffect, useCallback } from "react";
import {
  getWorkspaceVerificationSummary,
  verifyWorkspaceClaims,
  scanWorkspaceContradictions,
} from "../api";
import { usePermission } from "../hooks/usePermission";
import { useToast } from "./Toast";

function ClaimLedgerPage({ workspaceId }) {
    const { can } = usePermission();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [contradictions, setContradictions] = useState(null);
  const [showContradictions, setShowContradictions] = useState(false);
  const { showToast } = useToast();

  const loadSummary = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getWorkspaceVerificationSummary(workspaceId);
      setSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleVerifyAll = async () => {
    if (!can("claim.verify")) {
      showToast("Claim verification permission denied", "error");
      return;
    }
    setVerifying(true);
    try {
      const result = await verifyWorkspaceClaims(workspaceId);
      showToast(`Verified claims`, "success");
      await loadSummary();
    } catch (err) {
      showToast(`Verification failed: ${err.message}`, "error");
    } finally {
      setVerifying(false);
    }
  };

  const handleScanContradictions = async () => {
    setVerifying(true);
    try {
      const result = await scanWorkspaceContradictions(workspaceId);
      setContradictions(result.contradictions || []);
      setShowContradictions(true);
      showToast(`Found ${result.count || 0} contradictions`, result.count > 0 ? "warning" : "success");
    } catch (err) {
      showToast(`Scan failed: ${err.message}`, "error");
    } finally {
      setVerifying(false);
    }
  };

  const claimStatuses = summary ? {
    supported: summary.supported_claims || summary.supported || 0,
    contradicted: summary.contradicted_claims || summary.contradicted || 0,
    unsupported: summary.unsupported_claims || summary.unsupported || 0,
    uncertain: summary.uncertain_claims || summary.uncertain || 0,
    needs_review: summary.needs_review_claims || summary.needs_review || 0,
    total: summary.total_claims || summary.total || 0,
  } : null;

  if (!workspaceId) {
    return (
      <div className="section-page">
        <div className="section-header">
          <h2>📋 Claim Ledger</h2>
          <p className="section-subtitle">Inspect and verify workflow claims</p>
        </div>
        <div className="section-content">
          <div className="placeholder-card">
            <h3>No Workspace Selected</h3>
            <p className="text-muted">Select a workspace in Settings to view claims.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>📋 Claim Ledger</h2>
        <p className="section-subtitle">Verify and manage claims</p>
      </div>
      <div className="section-content">
        {error && <div className="workspace-error">{error}</div>}

        <div className="claim-actions">
          <button className="toolbar-btn" onClick={handleVerifyAll} disabled={verifying}>
            {verifying ? "⏳ Verifying..." : "✓ Verify All Claims"}
          </button>
          <button className="toolbar-btn" onClick={handleScanContradictions} disabled={verifying}>
            {verifying ? "⏳" : "🔄 Scan Contradictions"}
          </button>
        </div>

        {loading ? (
          <p className="text-muted">Loading...</p>
        ) : claimStatuses ? (
          <div className="claim-summary-cards">
            <div className="claim-stat-card claim-stat-total">
              <span className="claim-stat-value">{claimStatuses.total}</span>
              <span className="claim-stat-label">Total Claims</span>
            </div>
            <div className="claim-stat-card claim-stat-supported">
              <span className="claim-stat-value">{claimStatuses.supported}</span>
              <span className="claim-stat-label">Supported</span>
            </div>
            <div className="claim-stat-card claim-stat-contradicted">
              <span className="claim-stat-value">{claimStatuses.contradicted}</span>
              <span className="claim-stat-label">Contradicted</span>
            </div>
            <div className="claim-stat-card claim-stat-unsupported">
              <span className="claim-stat-value">{claimStatuses.unsupported}</span>
              <span className="claim-stat-label">Unsupported</span>
            </div>
            <div className="claim-stat-card claim-stat-uncertain">
              <span className="claim-stat-value">{claimStatuses.uncertain}</span>
              <span className="claim-stat-label">Uncertain</span>
            </div>
            <div className="claim-stat-card claim-stat-review">
              <span className="claim-stat-value">{claimStatuses.needs_review}</span>
              <span className="claim-stat-label">Needs Review</span>
            </div>
          </div>
        ) : (
          <div className="placeholder-card">
            <h3>No Claims</h3>
            <p className="text-muted">Run a workflow to generate claims, then verify them here.</p>
          </div>
        )}

        {showContradictions && contradictions && (
          <div className="ds-detail">
            <div className="ds-detail-header">
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>
                🔄 Contradictions ({contradictions.length})
              </h3>
              <button className="toolbar-btn toolbar-btn-xs" onClick={() => setShowContradictions(false)}>
                Close
              </button>
            </div>
            <div className="ds-detail-content">
              {contradictions.length === 0 ? (
                <p className="text-muted">No contradictions found.</p>
              ) : (
                contradictions.map((c, i) => (
                  <div key={c.claim_id || i} className="ds-chunk">
                    <div className="ds-chunk-header">
                      <span className="ds-chunk-index">Claim: {c.claim_text || c.claim_id}</span>
                    </div>
                    <pre className="ds-chunk-text">
                      {c.evidence_text || c.details || JSON.stringify(c, null, 2)}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ClaimLedgerPage;
