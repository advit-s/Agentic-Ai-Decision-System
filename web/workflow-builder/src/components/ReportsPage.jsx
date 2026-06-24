// ReportsPage.jsx — View, export, and manage decision trust reports
import React, { useState, useEffect, useCallback } from "react";
import { getReport, exportReport, getReportMarkdown } from "../api";

function ReportsPage({ workspaceId }) {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedReport, setSelectedReport] = useState(null);
  const [reportContent, setReportContent] = useState(null);
  const [exporting, setExporting] = useState(false);

  // For mock mode, we don't have a list reports endpoint directly,
  // so we use getReport with known IDs or let the user generate from workflow
  // For now, show a message about generating reports

  const handleViewReport = async (reportId) => {
    setSelectedReport(reportId);
    setReportContent(null);
    setLoading(true);
    try {
      const data = await getReport(reportId);
      setReportContent(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (reportId, format = "md") => {
    setExporting(true);
    try {
      const result = await exportReport(reportId, format);
      if (result.content) {
        // Download as file
        const blob = new Blob([result.content], { type: "text/markdown" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = result.filename || `report-${reportId}.${format}`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  };

  if (!workspaceId) {
    return (
      <div className="section-page">
        <div className="section-header">
          <h2>📄 Reports</h2>
          <p className="section-subtitle">View and export decision reports</p>
        </div>
        <div className="section-content">
          <div className="placeholder-card">
            <h3>No Workspace Selected</h3>
            <p className="text-muted">Select a workspace in Settings to view reports.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>📄 Reports</h2>
        <p className="section-subtitle">View and export decision trust reports</p>
      </div>
      <div className="section-content">
        {error && <div className="workspace-error">{error}</div>}

        <div className="placeholder-card">
          <div className="placeholder-icon">📄</div>
          <h3>Decision Reports</h3>
          <p className="text-muted">
            Generate trust reports by running a workflow and clicking "Generate Report"
            in the Trust Dashboard. Reports will appear here for viewing and export.
          </p>
          <ol className="text-muted" style={{ marginTop: 12, lineHeight: 1.8 }}>
            <li>Go to <strong>Workflow Builder</strong></li>
            <li>Load or create a workflow</li>
            <li>Run the workflow</li>
            <li>Open <strong>Trust Dashboard</strong></li>
            <li>Click "Generate Trust Report"</li>
            <li>Return here to view and export</li>
          </ol>
        </div>

        {selectedReport && reportContent && (
          <div className="ds-detail">
            <div className="ds-detail-header">
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>
                📄 Report {selectedReport}
              </h3>
              <div style={{ display: "flex", gap: 4 }}>
                <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleExport(selectedReport, "md")} disabled={exporting}>
                  {exporting ? "⏳" : "📥 Export MD"}
                </button>
                <button className="toolbar-btn toolbar-btn-xs" onClick={() => { setSelectedReport(null); setReportContent(null); }}>
                  Close
                </button>
              </div>
            </div>
            <div className="ds-detail-content">
              <pre className="ds-chunk-text" style={{ maxHeight: "none", fontSize: 13 }}>
                {JSON.stringify(reportContent, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReportsPage;
