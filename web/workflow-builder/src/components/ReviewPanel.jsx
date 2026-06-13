// components/ReviewPanel.jsx — Human review queue panel
// Allows users to approve, reject, or request changes on reviews.

import React, { useState, useMemo } from "react";
import "../styles/execution-panel.css";

/* ── Helper ──────────────────────────────────────────────────────── */

function formatReviewData(data) {
  if (data === null || data === undefined) return "—";
  try {
    const str = typeof data === "object" ? JSON.stringify(data, null, 2) : String(data);
    if (str.length > 5000) return str.slice(0, 5000) + "\n… (truncated)";
    return str;
  } catch {
    return String(data);
  }
}

function shortId(id) {
  if (!id) return "";
  return id.length > 12 ? id.slice(0, 12) + "…" : id;
}

function getOutcomeLabel(status) {
  switch (status) {
    case "approved": return "Approved";
    case "rejected": return "Rejected";
    case "changes_requested": return "Changes Requested";
    default: return status;
  }
}

function getOutcomeBadgeClass(status) {
  switch (status) {
    case "approved": return "rp-badge-approved";
    case "rejected": return "rp-badge-rejected";
    case "changes_requested": return "rp-badge-changes";
    case "pending_review": return "rp-badge-pending";
    default: return "";
  }
}

/* ── Sub-components ─────────────────────────────────────────────── */

function ReviewActionBar({ review, onApprove, onReject, onRequestChanges }) {
  const [showNotes, setShowNotes] = useState(false);
  const [actionType, setActionType] = useState(null);
  const [notes, setNotes] = useState("");
  const [modifiedData, setModifiedData] = useState("");

  const requireNotes = actionType === "reject" || actionType === "request_changes";

  const handleConfirm = () => {
    if (requireNotes && !notes.trim()) return;

    let parsedModified = null;
    if (actionType === "request_changes" && modifiedData.trim()) {
      try {
        parsedModified = JSON.parse(modifiedData);
      } catch {
        return; // invalid JSON — user must fix
      }
    }

    if (actionType === "approve") {
      onApprove(review.review_id || review.id, notes.trim());
    } else if (actionType === "reject") {
      onReject(review.review_id || review.id, notes.trim());
    } else if (actionType === "request_changes") {
      onRequestChanges(review.review_id || review.id, notes.trim(), parsedModified);
    }

    setShowNotes(false);
    setActionType(null);
    setNotes("");
    setModifiedData("");
  };

  const handleCancel = () => {
    setShowNotes(false);
    setActionType(null);
    setNotes("");
    setModifiedData("");
  };

  if (showNotes) {
    return (
      <div className="rp-action-confirm">
        <div className="rp-action-label">
          {actionType === "approve" && "Confirm Approval"}
          {actionType === "reject" && "Confirm Rejection"}
          {actionType === "request_changes" && "Request Changes"}
        </div>
        <textarea
          className={"rp-notes-textarea" + (requireNotes && !notes.trim() ? " rp-notes-invalid" : "")}
          placeholder={
            requireNotes
              ? "Review notes are required…"
              : "Optional review notes…"
          }
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
        />
        {requireNotes && !notes.trim() && (
          <div className="rp-notes-hint">Notes are required for this action.</div>
        )}
        {actionType === "request_changes" && (
          <div className="rp-modified-section">
            <div className="rp-modified-label">Modified Data (JSON)</div>
            <textarea
              className="rp-modified-editor"
              placeholder='{"key": "value"}'
              value={modifiedData}
              onChange={(e) => setModifiedData(e.target.value)}
              rows={5}
            />
            {modifiedData.trim() && (() => {
              try {
                JSON.parse(modifiedData);
                return null;
              } catch {
                return <div className="rp-notes-hint">Invalid JSON — please fix.</div>;
              }
            })()}
          </div>
        )}
        <div className="rp-confirm-actions">
          <button className="rp-btn rp-btn-cancel" onClick={handleCancel}>
            Cancel
          </button>
          <button
            className={
              "rp-btn rp-btn-confirm" +
              (actionType === "approve" ? " rp-btn-green" : "") +
              (actionType === "reject" ? " rp-btn-red" : "") +
              (actionType === "request_changes" ? " rp-btn-amber" : "")
            }
            onClick={handleConfirm}
            disabled={requireNotes && !notes.trim()}
          >
            Confirm
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="rp-action-bar">
      <button
        className="rp-btn rp-btn-green"
        onClick={() => { setActionType("approve"); setShowNotes(true); }}
        title="Approve and continue"
      >
        ✓ Approve
      </button>
      <button
        className="rp-btn rp-btn-red"
        onClick={() => { setActionType("reject"); setShowNotes(true); }}
        title="Reject and stop"
      >
        ✕ Reject
      </button>
      <button
        className="rp-btn rp-btn-amber"
        onClick={() => { setActionType("request_changes"); setShowNotes(true); }}
        title="Request modifications"
      >
        ✎ Request Changes
      </button>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────── */

function ReviewPanel({ reviews, onApprove, onReject, onRequestChanges, onClose }) {
  const [tab, setTab] = useState("pending");
  const [selectedReview, setSelectedReview] = useState(null);

  const pendingReviews = useMemo(
    () => (reviews || []).filter((r) => r.status === "pending_review"),
    [reviews],
  );

  const resolvedReviews = useMemo(
    () => (reviews || []).filter((r) => r.status !== "pending_review"),
    [reviews],
  );

  const handleApprove = (reviewId, notes) => {
    if (onApprove) onApprove(reviewId, notes);
  };

  const handleReject = (reviewId, notes) => {
    if (onReject) onReject(reviewId, notes);
  };

  const handleRequestChanges = (reviewId, notes, modifiedData) => {
    if (onRequestChanges) onRequestChanges(reviewId, notes, modifiedData);
  };

  // ── Full review detail view ──
  if (selectedReview) {
    const review = selectedReview;
    const isPending = review.status === "pending_review";

    return (
      <div className="rp-panel">
        <div className="rp-header">
          <div className="rp-header-title">
            <span className="rp-header-back" onClick={() => setSelectedReview(null)} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") setSelectedReview(null); }}>
              ← Back
            </span>
            <span>Review Detail</span>
          </div>
          {onClose && (
            <button className="execution-close" onClick={onClose}>✕</button>
          )}
        </div>

        <div className="rp-review-detail">
          <div className="rp-detail-section">
            <div className="rp-detail-label">Review ID</div>
            <div className="rp-detail-value">{review.review_id || review.id}</div>
          </div>

          {review.instructions && (
            <div className="rp-detail-section">
              <div className="rp-detail-label">Instructions</div>
              <div className="rp-detail-value rp-instructions-text">{review.instructions}</div>
            </div>
          )}

          <div className="rp-detail-section">
            <div className="rp-detail-label">Status</div>
            <span className={"rp-status-badge " + getOutcomeBadgeClass(review.status)}>
              {getOutcomeLabel(review.status)}
            </span>
          </div>

          {/* Data being reviewed */}
          <div className="rp-data-section">
            <div className="rp-data-section-title">Data Under Review</div>
            <pre className="rp-data-pre">{formatReviewData(review.data)}</pre>
          </div>

          {/* Audit trail */}
          <div className="rp-detail-section">
            <div className="rp-detail-label">Timeline</div>
            <div className="rp-detail-value">
              <div>Created: {review.created_at ? new Date(review.created_at).toLocaleString() : "—"}</div>
              {review.resolved_at && (
                <div>Resolved: {new Date(review.resolved_at).toLocaleString()}</div>
              )}
            </div>
          </div>

          {/* Resolved info */}
          {!isPending && review.action && (
            <div className="rp-detail-section">
              <div className="rp-detail-label">Resolution</div>
              <div className="rp-detail-value">
                <div>Action: {review.action}</div>
                {review.review_notes && <div>Notes: {review.review_notes}</div>}
                {review.reviewed_by && <div>Reviewed by: {review.reviewed_by}</div>}
              </div>
            </div>
          )}

          {/* Modified data */}
          {review.modified_data && (
            <div className="rp-data-section">
              <div className="rp-data-section-title">Modified Data</div>
              <pre className="rp-data-pre">{formatReviewData(review.modified_data)}</pre>
            </div>
          )}

          {/* Review actions (only for pending) */}
          {isPending && (
            <ReviewActionBar
              review={review}
              onApprove={handleApprove}
              onReject={handleReject}
              onRequestChanges={handleRequestChanges}
            />
          )}
        </div>
      </div>
    );
  }

  // ── Tab: Pending ──
  const renderPendingList = () => {
    if (pendingReviews.length === 0) {
      return (
        <div className="rp-empty">
          <div className="rp-empty-icon">🎉</div>
          <div className="rp-empty-text">All reviews completed</div>
          <div className="rp-empty-hint">No pending reviews require your attention.</div>
        </div>
      );
    }

    return (
      <div className="rp-review-list">
        {pendingReviews.map((review) => (
          <div
            key={review.review_id || review.id}
            className="rp-review-card"
            onClick={() => setSelectedReview(review)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter") setSelectedReview(review); }}
          >
            <div className="rp-card-header">
              <span className="rp-card-id">{shortId(review.review_id || review.id)}</span>
              <span className={"rp-status-badge rp-badge-pending"}>Pending</span>
            </div>
            {review.instructions && (
              <div className="rp-card-instructions">
                {review.instructions.length > 120
                  ? review.instructions.slice(0, 120) + "…"
                  : review.instructions
                }
              </div>
            )}
            <div className="rp-card-meta">
              {review.created_at && (
                <span className="rp-card-time">
                  {new Date(review.created_at).toLocaleString()}
                </span>
              )}
              {review.workflow_id && (
                <span className="rp-card-workflow">{review.workflow_id}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // ── Tab: Resolved ──
  const renderResolvedList = () => {
    if (resolvedReviews.length === 0) {
      return (
        <div className="rp-empty">
          <div className="rp-empty-icon">📋</div>
          <div className="rp-empty-text">No resolved reviews</div>
          <div className="rp-empty-hint">No reviews have been resolved yet.</div>
        </div>
      );
    }

    return (
      <div className="rp-review-list">
        {resolvedReviews.map((review) => (
          <div
            key={review.review_id || review.id}
            className="rp-review-card"
            onClick={() => setSelectedReview(review)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === "Enter") setSelectedReview(review); }}
          >
            <div className="rp-card-header">
              <span className="rp-card-id">{shortId(review.review_id || review.id)}</span>
              <span className={"rp-status-badge " + getOutcomeBadgeClass(review.status)}>
                {getOutcomeLabel(review.status)}
              </span>
            </div>
            {review.review_notes && (
              <div className="rp-card-notes">
                {review.review_notes.length > 120
                  ? review.review_notes.slice(0, 120) + "…"
                  : review.review_notes
                }
              </div>
            )}
            <div className="rp-card-meta">
              {review.resolved_at && (
                <span className="rp-card-time">
                  Resolved: {new Date(review.resolved_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // ── Layout ──
  return (
    <div className="rp-panel">
      <div className="rp-header">
        <div className="rp-header-title">
          <span>Review Queue</span>
          {pendingReviews.length > 0 && (
            <span className="rp-count-badge">{pendingReviews.length}</span>
          )}
        </div>
        {onClose && (
          <button className="execution-close" onClick={onClose}>✕</button>
        )}
      </div>

      {/* Tabs */}
      <div className="rp-tabs">
        <button
          className={"rp-tab" + (tab === "pending" ? " active" : "")}
          onClick={() => setTab("pending")}
        >
          Pending {pendingReviews.length > 0 && `(${pendingReviews.length})`}
        </button>
        <button
          className={"rp-tab" + (tab === "resolved" ? " active" : "")}
          onClick={() => setTab("resolved")}
        >
          Resolved {resolvedReviews.length > 0 && `(${resolvedReviews.length})`}
        </button>
      </div>

      <div className="rp-content">
        {tab === "pending" ? renderPendingList() : renderResolvedList()}
      </div>
    </div>
  );
}

export default ReviewPanel;
