// components/ValidationDialog.jsx — Modal dialog showing workflow validation results
import React from "react";

function ValidationDialog({ isOpen, result, nodeErrors, onClose, onFocusNode }) {
  if (!isOpen || !result) return null;

  const hasErrors = result.errors && result.errors.length > 0;
  const hasWarnings = result.warnings && result.warnings.length > 0;

  return (
    <div className="template-overlay" onClick={onClose}>
      <div className="template-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="template-dialog-header">
          <span className="template-dialog-title">
            {hasErrors ? "⚠️ Workflow has errors" : hasWarnings ? "⚠️ Workflow has warnings" : "✅ Workflow is valid"}
          </span>
          <button className="template-close-btn" onClick={onClose} title="Close">
            ✕
          </button>
        </div>
        <div className="template-dialog-body">
          {hasErrors && (
            <div className="validation-section">
              <div className="validation-section-title validation-section-errors">
                Errors ({result.errors.length})
              </div>
              <div className="validation-list">
                {result.errors.map((err, i) => (
                  <div key={i} className="validation-item validation-item-error">
                    <span className="validation-icon">✕</span>
                    <span className="validation-text">{err}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {hasWarnings && (
            <div className="validation-section">
              <div className="validation-section-title validation-section-warnings">
                Warnings ({result.warnings.length})
              </div>
              <div className="validation-list">
                {result.warnings.map((warn, i) => (
                  <div key={i} className="validation-item validation-item-warning">
                    <span className="validation-icon">⚠</span>
                    <span className="validation-text">{warn}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {!hasErrors && !hasWarnings && (
            <div className="validation-empty">
              <div className="validation-empty-icon">✅</div>
              <p className="validation-empty-text">
                All checks passed. The workflow is ready to execute.
              </p>
            </div>
          )}

          <div className="validation-footer">
            <button className="template-close-btn validation-close-btn" onClick={onClose}>
              {hasErrors ? "Fix errors before running" : "Close"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ValidationDialog;
