// EvidenceSearchPage.jsx — Search workspace evidence with filters
import React, { useState, useCallback } from "react";
import { searchEvidence } from "../api";

const FILE_TYPE_OPTIONS = ["", "pdf", "docx", "xlsx", "csv", "json", "txt", "md"];

function EvidenceSearchPage({ workspaceId }) {
  const [query, setQuery] = useState("");
  const [limit, setLimit] = useState(10);
  const [fileType, setFileType] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await searchEvidence(workspaceId, query.trim(), limit, undefined, fileType || undefined);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [query, limit, fileType, workspaceId]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleSearch();
  };

  const copyRef = (evidenceId) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(evidenceId);
    }
  };

  const getFileTypeIcon = (ft) => {
    const icons = { pdf: "📕", docx: "📘", xlsx: "📗", csv: "📊", json: "📋", txt: "📄", md: "📝" };
    return icons[ft] || "📄";
  };

  if (!workspaceId) {
    return (
      <div className="section-page">
        <div className="section-header">
          <h2>🔍 Evidence Search</h2>
          <p className="section-subtitle">Search indexed documents for evidence</p>
        </div>
        <div className="section-content">
          <div className="placeholder-card">
            <h3>No Workspace Selected</h3>
            <p className="text-muted">Select a workspace in Settings to search evidence.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>🔍 Evidence Search</h2>
        <p className="section-subtitle">Search workspace documents for evidence</p>
      </div>
      <div className="section-content">
        <div className="evidence-search-bar">
          <input
            type="text"
            placeholder="Search query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <select value={fileType} onChange={(e) => setFileType(e.target.value)}>
            <option value="">All types</option>
            {FILE_TYPE_OPTIONS.filter(Boolean).map((ft) => (
              <option key={ft} value={ft}>{ft.toUpperCase()}</option>
            ))}
          </select>
          <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
            <option value={5}>5 results</option>
            <option value={10}>10 results</option>
            <option value={20}>20 results</option>
          </select>
          <button onClick={handleSearch} disabled={loading || !query.trim()}>
            {loading ? "⏳" : "🔍 Search"}
          </button>
        </div>

        {error && <div className="workspace-error">{error}</div>}

        {results && (
          <div className="evidence-results">
            <p className="text-muted" style={{ marginBottom: 8 }}>
              {results.total_results || results.results?.length || 0} results ({results.retrieval_mode || "keyword"})
            </p>
            {results.results && results.results.length > 0 ? (
              <div className="evidence-list">
                {results.results.map((r, i) => (
                  <div key={r.evidence_id || i} className="evidence-card">
                    <div className="evidence-card-header">
                      <span className="evidence-source" title={r.source_name || r.source_id}>
                        {getFileTypeIcon(r.metadata?.file_type)} {r.source_name || "Unknown"}
                      </span>
                      <span className="evidence-score">
                        {(r.score !== undefined && r.score !== null) ? `Score: ${typeof r.score === 'number' ? r.score.toFixed(2) : r.score}` : ""}
                      </span>
                    </div>
                    <pre className="evidence-text">{r.text || ""}</pre>
                    <div className="evidence-meta">
                      {r.metadata?.page_number && <span>p.{r.metadata.page_number}</span>}
                      {r.metadata?.sheet_name && <span>{r.metadata.sheet_name}</span>}
                      {r.metadata?.block_type && <span>{r.metadata.block_type}</span>}
                      {r.evidence_id && (
                        <button
                          className="evidence-copy-btn"
                          onClick={() => copyRef(r.evidence_id)}
                          title="Copy evidence ID"
                        >
                          📋 Copy ref
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="placeholder-card">
                <p className="text-muted">No results found for "{query}".</p>
              </div>
            )}
          </div>
        )}

        {!results && !loading && !error && (
          <div className="placeholder-card">
            <div className="placeholder-icon">🔍</div>
            <h3>Search Workspace Evidence</h3>
            <p className="text-muted">
              Enter a query above to search indexed documents.
              Results include source name, file type, and metadata.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default EvidenceSearchPage;
