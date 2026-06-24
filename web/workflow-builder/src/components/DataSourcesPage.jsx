// DataSourcesPage.jsx — Upload, parse, index, preview, and manage data sources
import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  listDataSources,
  uploadDataSource,
  deleteDataSource,
  parseDataSource,
  indexDataSource,
  getDataSourceStatus,
  getDataSourceProfile,
  getDataSourceChunks,
  getDataSourcePreview,
} from "../api";
import { useToast } from "./Toast";

const SUPPORTED_TYPES = ["pdf", "docx", "xlsx", "csv", "json", "txt", "md"];
const SUPPORTED_EXTENSIONS = [".pdf", ".docx", ".xlsx", ".csv", ".json", ".txt", ".md"];

function DataSourcesPage({ workspaceId, onNavigate }) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSource, setSelectedSource] = useState(null);
  const [detailView, setDetailView] = useState(null); // null | "chunks" | "profile"
  const [detailData, setDetailData] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);
  const { showToast } = useToast();

  const loadSources = useCallback(async () => {
    if (!workspaceId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listDataSources(workspaceId);
      setSources(data.data_sources || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    loadSources();
  }, [loadSources]);

  const handleUpload = async (file) => {
    const ext = "." + (file.name.split(".").pop() || "").toLowerCase();
    if (!SUPPORTED_EXTENSIONS.includes(ext)) {
      showToast(`Unsupported file type: ${ext}. Supported: ${SUPPORTED_EXTENSIONS.join(", ")}`, "error");
      return;
    }
    setUploading(true);
    try {
      const content = await file.arrayBuffer();
      const fileType = ext.replace(".", "");
      await uploadDataSource(workspaceId, file.name, content, fileType);
      showToast(`Uploaded ${file.name}`, "success");
      await loadSources();
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, "error");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) handleUpload(files[0]);
  }, [workspaceId]);

  const handleDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const handleDragLeave = () => setDragOver(false);

  const handleBrowseClick = () => fileInputRef.current?.click();
  const handleFileChange = (e) => {
    if (e.target.files.length > 0) {
      handleUpload(e.target.files[0]);
      e.target.value = "";
    }
  };

  const handleParse = async (sourceId) => {
    try {
      const result = await parseDataSource(workspaceId, sourceId);
      showToast(`Parsed: ${result.chunk_count || 0} chunks`, "success");
      await loadSources();
    } catch (err) {
      showToast(`Parse failed: ${err.message}`, "error");
    }
  };

  const handleIndex = async (sourceId) => {
    try {
      const result = await indexDataSource(workspaceId, sourceId);
      showToast(`Indexed (${result.retrieval_mode || "keyword"})`, "success");
      await loadSources();
    } catch (err) {
      showToast(`Index failed: ${err.message}`, "error");
    }
  };

  const handleDelete = async (sourceId) => {
    if (!window.confirm("Delete this data source?")) return;
    try {
      await deleteDataSource(workspaceId, sourceId);
      showToast("Deleted", "success");
      if (selectedSource === sourceId) {
        setSelectedSource(null);
        setDetailView(null);
        setDetailData(null);
      }
      await loadSources();
    } catch (err) {
      showToast(`Delete failed: ${err.message}`, "error");
    }
  };

  const handleViewChunks = async (sourceId) => {
    setSelectedSource(sourceId);
    setDetailView("chunks");
    setDetailData(null);
    try {
      const data = await getDataSourceChunks(workspaceId, sourceId);
      setDetailData(data.chunks || []);
    } catch (err) {
      setDetailData([]);
      showToast(`Failed to load chunks: ${err.message}`, "error");
    }
  };

  const handleViewProfile = async (sourceId) => {
    setSelectedSource(sourceId);
    setDetailView("profile");
    setDetailData(null);
    try {
      const data = await getDataSourceProfile(workspaceId, sourceId);
      setDetailData(data.profile || null);
    } catch (err) {
      setDetailData(null);
    }
  };

  const getStatusIcon = (status) => {
    const icons = {
      uploaded: "📄",
      parsing: "⏳",
      parsed: "✅",
      parsed_with_warnings: "⚠️",
      indexing: "⏳",
      indexed: "📚",
      failed: "❌",
      unsupported: "🚫",
      deleted: "🗑️",
    };
    return icons[status] || "📄";
  };

  if (!workspaceId) {
    return (
      <div className="section-page">
        <div className="section-header">
          <h2>📁 Data Sources</h2>
          <p className="section-subtitle">Upload, parse, and index documents for evidence retrieval</p>
        </div>
        <div className="section-content">
          <div className="placeholder-card">
            <div className="placeholder-icon">📁</div>
            <h3>No Workspace Selected</h3>
            <p className="text-muted">Select or create a workspace in Settings to manage data sources.</p>
            <button className="toolbar-btn" onClick={() => onNavigate("settings")} style={{ marginTop: 12 }}>
              Go to Settings
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>📁 Data Sources</h2>
        <p className="section-subtitle">Upload, parse, and index documents</p>
      </div>
      <div className="section-content">
        {/* Upload zone */}
        <div
          className={`upload-zone ${dragOver ? "upload-zone-active" : ""}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={handleBrowseClick}
        >
          {uploading ? (
            <p>⏳ Uploading...</p>
          ) : (
            <>
              <div className="upload-zone-icon">📂</div>
              <p><strong>Drop files here</strong> or click to browse</p>
              <p className="text-muted" style={{ fontSize: 12, marginTop: 4 }}>
                Supported: PDF, DOCX, XLSX, CSV, JSON, TXT, MD
              </p>
            </>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.xlsx,.csv,.json,.txt,.md"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
        </div>

        {/* Error */}
        {error && <div className="workspace-error">{error}</div>}

        {/* Source list */}
        <div className="ds-list">
          <h3 style={{ margin: "0 0 12px", fontSize: 15, fontWeight: 600 }}>
            Data Sources ({sources.length})
          </h3>
          {loading ? (
            <p className="text-muted">Loading...</p>
          ) : sources.length === 0 ? (
            <div className="placeholder-card" style={{ padding: 16 }}>
              <p className="text-muted">No data sources yet. Upload a file above.</p>
            </div>
          ) : (
            <div className="ds-table">
              <div className="ds-table-header">
                <span className="ds-col-name">Name</span>
                <span className="ds-col-type">Type</span>
                <span className="ds-col-status">Status</span>
                <span className="ds-col-actions">Actions</span>
              </div>
              {sources.map((ds) => (
                <div
                  key={ds.source_id}
                  className={`ds-row ${selectedSource === ds.source_id ? "ds-row-selected" : ""}`}
                >
                  <span className="ds-col-name" title={ds.original_filename || ds.name}>
                    {ds.original_filename || ds.name}
                  </span>
                  <span className="ds-col-type">
                    <span className="ds-badge ds-badge-type">{ds.file_type || "?"}</span>
                  </span>
                  <span className="ds-col-status">
                    <span className={`ds-status-badge ds-status-${ds.status || "unknown"}`}>
                      {getStatusIcon(ds.status)} {ds.status || "unknown"}
                    </span>
                  </span>
                  <span className="ds-col-actions">
                    {ds.status === "uploaded" && (
                      <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleParse(ds.source_id)}>
                        Parse
                      </button>
                    )}
                    {(ds.status === "parsed" || ds.status === "parsed_with_warnings") && (
                      <>
                        <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleIndex(ds.source_id)}>
                          Index
                        </button>
                        <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleViewChunks(ds.source_id)}>
                          Chunks
                        </button>
                      </>
                    )}
                    {ds.status === "indexed" && (
                      <>
                        <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleViewChunks(ds.source_id)}>
                          Chunks
                        </button>
                        {(ds.file_type === "csv" || ds.file_type === "xlsx" || ds.file_type === "json") && (
                          <button className="toolbar-btn toolbar-btn-xs" onClick={() => handleViewProfile(ds.source_id)}>
                            Profile
                          </button>
                        )}
                      </>
                    )}
                    <button className="toolbar-btn toolbar-btn-xs toolbar-btn-danger" onClick={() => handleDelete(ds.source_id)}>
                      Delete
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detail panel for selected source */}
        {detailView && detailData !== undefined && (
          <div className="ds-detail">
            <div className="ds-detail-header">
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>
                {detailView === "chunks" ? "📄 Chunks" : "📊 Profile"}
              </h3>
              <button className="toolbar-btn toolbar-btn-xs" onClick={() => { setDetailView(null); setDetailData(null); setSelectedSource(null); }}>
                Close
              </button>
            </div>
            <div className="ds-detail-content">
              {detailView === "chunks" && (
                Array.isArray(detailData) && detailData.length > 0 ? (
                  detailData.map((chunk, i) => (
                    <div key={chunk.chunk_id || i} className="ds-chunk">
                      <div className="ds-chunk-header">
                        <span className="ds-chunk-index">#{chunk.chunk_index ?? i}</span>
                        <span className="ds-chunk-id">{chunk.chunk_id || ""}</span>
                      </div>
                      <pre className="ds-chunk-text">{(chunk.text || "").slice(0, 500)}{(chunk.text || "").length > 500 ? "..." : ""}</pre>
                    </div>
                  ))
                ) : (
                  <p className="text-muted">No chunks available.</p>
                )
              )}
              {detailView === "profile" && detailData && (
                <div className="ds-profile">
                  <p><strong>Rows:</strong> {detailData.row_count || 0}</p>
                  <p><strong>Columns:</strong> {detailData.column_count || 0}</p>
                  {detailData.columns && detailData.columns.length > 0 && (
                    <div>
                      <h4 style={{ margin: "12px 0 8px", fontSize: 13 }}>Columns</h4>
                      <table className="ds-profile-table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Missing</th>
                          </tr>
                        </thead>
                        <tbody>
                          {detailData.columns.map((col, i) => (
                            <tr key={i}>
                              <td>{col.name || col.column || `Column ${i}`}</td>
                              <td>{col.type || col.dtype || "?"}</td>
                              <td>{col.missing_count || col.null_count || 0}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default DataSourcesPage;
