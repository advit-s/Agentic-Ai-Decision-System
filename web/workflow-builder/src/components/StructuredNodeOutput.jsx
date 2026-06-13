// components/StructuredNodeOutput.jsx — Rich output views for specialist node types
import React from "react";
import "../styles/structured-output.css";

/* ── Researcher Output ────────────────────────────────────────────── */

function ResearcherOutput({ outputs }) {
  const findings = outputs.findings || [];
  const summary = outputs.summary || "";
  const gaps = outputs.gaps || [];

  return (
    <div className="structured-output">
      {summary && (
        <div className="so-summary-box">
          <strong>Summary:</strong> {summary}
        </div>
      )}
      {findings.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Findings ({findings.length})</div>
          {findings.map((f, i) => (
            <div key={i} className="so-finding-card">
              <div className="so-finding-statement">
                <span className="so-finding-num">{i + 1}.</span> {f.statement}
              </div>
              <div className="so-finding-meta">
                {f.confidence !== undefined && (
                  <span
                    className="so-confidence-badge"
                    style={{
                      background:
                        f.confidence >= 0.7 ? "#dcfce7" : f.confidence >= 0.4 ? "#fef9c3" : "#fee2e2",
                      color:
                        f.confidence >= 0.7 ? "#166534" : f.confidence >= 0.4 ? "#854d0e" : "#991b1b",
                    }}
                  >
                    {Math.round(f.confidence * 100)}%
                  </span>
                )}
                {f.citation && <span className="so-citation">📎 {f.citation}</span>}
                {f.source_type && <span className="so-source-type">{f.source_type}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      {gaps.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Information Gaps</div>
          <ul className="so-gap-list">
            {gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
      {outputs.fallback_reason && (
        <div className="so-fallback-note">⚠️ Fallback: {outputs.fallback_reason}</div>
      )}
    </div>
  );
}

/* ── Critic Output ─────────────────────────────────────────────────── */

const SEVERITY_CONFIG = {
  high: { bg: "#fee2e2", color: "#991b1b", label: "High" },
  medium: { bg: "#fef9c3", color: "#854d0e", label: "Medium" },
  low: { bg: "#f3f4f6", color: "#4b5563", label: "Low" },
};

const ISSUE_TYPE_ICONS = {
  contradiction: "⚡",
  unsupported: "❓",
  logical_fallacy: "🧠",
  misconfidence: "📊",
};

function CriticOutput({ outputs }) {
  const issues = outputs.issues || [];
  const summary = outputs.summary || "";
  const confAdj = outputs.confidence_adjustment || 0;
  const passed = outputs.passed;

  return (
    <div className="structured-output">
      <div className="so-critic-header">
        <span
          className="so-critic-pass-badge"
          style={{
            background: passed ? "#dcfce7" : "#fee2e2",
            color: passed ? "#166534" : "#991b1b",
          }}
        >
          {passed ? "✅ Passed" : "❌ Issues Found"}
        </span>
        {confAdj !== 0 && (
          <span className="so-confidence-adj">
            Confidence adjustment: {confAdj >= 0 ? "+" : ""}
            {confAdj.toFixed(2)}
          </span>
        )}
      </div>

      {summary && <div className="so-summary-box">{summary}</div>}

      {issues.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Issues ({issues.length})</div>
          {issues.map((issue, i) => {
            const sev = SEVERITY_CONFIG[issue.severity] || SEVERITY_CONFIG.low;
            return (
              <div key={i} className="so-issue-row">
                <span className="so-issue-type-icon">
                  {ISSUE_TYPE_ICONS[issue.type] || "●"}
                </span>
                <span className="so-issue-sev-badge" style={{ background: sev.bg, color: sev.color }}>
                  {sev.label}
                </span>
                <span className="so-issue-type-label">{issue.type.replace(/_/g, " ")}</span>
                <div className="so-issue-text">
                  <div className="so-issue-desc">{issue.description}</div>
                  {issue.location && <div className="so-issue-location">📍 {issue.location}</div>}
                  {issue.suggestion && (
                    <div className="so-issue-suggestion">💡 {issue.suggestion}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {outputs.fallback_reason && (
        <div className="so-fallback-note">⚠️ Fallback: {outputs.fallback_reason}</div>
      )}
    </div>
  );
}

/* ── Synthesizer Output ────────────────────────────────────────────── */

function SynthesizerOutput({ outputs }) {
  const options = outputs.options || [];
  const recommendation = outputs.recommendation || {};
  const tradeOffs = outputs.trade_offs_summary || "";

  return (
    <div className="structured-output">
      {recommendation.title && (
        <div className="so-recommendation-card">
          <div className="so-rec-label">🏆 Recommendation</div>
          <div className="so-rec-title">{recommendation.title}</div>
          {recommendation.rationale && (
            <div className="so-rec-rationale">{recommendation.rationale}</div>
          )}
          {recommendation.overall_confidence !== undefined && (
            <span
              className="so-confidence-badge"
              style={{
                background:
                  recommendation.overall_confidence >= 0.7
                    ? "#dcfce7"
                    : recommendation.overall_confidence >= 0.4
                      ? "#fef9c3"
                      : "#fee2e2",
                color:
                  recommendation.overall_confidence >= 0.7
                    ? "#166534"
                    : recommendation.overall_confidence >= 0.4
                      ? "#854d0e"
                      : "#991b1b",
              }}
            >
              {Math.round(recommendation.overall_confidence * 100)}% confident
            </span>
          )}
        </div>
      )}

      {options.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Options (ranked)</div>
          {options.map((opt, i) => (
            <div key={i} className="so-option-card">
              <div className="so-option-header">
                <span className="so-option-rank">#{i + 1}</span>
                <span className="so-option-title">{opt.title}</span>
                {opt.confidence !== undefined && (
                  <span className="so-option-confidence">{Math.round(opt.confidence * 100)}%</span>
                )}
              </div>
              {opt.description && <div className="so-option-desc">{opt.description}</div>}
              <div className="so-option-details">
                {opt.pros && opt.pros.length > 0 && (
                  <div className="so-option-pros">
                    <strong>Pros:</strong>
                    <ul>{opt.pros.map((p, j) => <li key={j}>{p}</li>)}</ul>
                  </div>
                )}
                {opt.cons && opt.cons.length > 0 && (
                  <div className="so-option-cons">
                    <strong>Cons:</strong>
                    <ul>{opt.cons.map((c, j) => <li key={j}>{c}</li>)}</ul>
                  </div>
                )}
                {opt.criteria_scores && Object.keys(opt.criteria_scores).length > 0 && (
                  <div className="so-option-scores">
                    {Object.entries(opt.criteria_scores).map(([key, val]) => (
                      <span key={key} className="so-score-pill">
                        {key}: {typeof val === "number" ? val.toFixed(1) : val}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {opt.risks && opt.risks.length > 0 && (
                <div className="so-risks-section">
                  <strong>Risks:</strong>
                  {opt.risks.map((r, j) => (
                    <div key={j} className="so-risk-row">
                      <span
                        className="so-risk-likelihood"
                        style={{
                          color:
                            r.likelihood === "high"
                              ? "#991b1b"
                              : r.likelihood === "medium"
                                ? "#854d0e"
                                : "#166534",
                        }}
                      >
                        {r.likelihood}
                      </span>
                      <span>{r.risk}</span>
                      {r.mitigation && <span className="so-risk-mitigation">→ {r.mitigation}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {tradeOffs && <div className="so-summary-box">{tradeOffs}</div>}
      {outputs.fallback_reason && (
        <div className="so-fallback-note">⚠️ Fallback: {outputs.fallback_reason}</div>
      )}
    </div>
  );
}

/* ── Data Analyst Output ───────────────────────────────────────────── */

function DataAnalystOutput({ outputs }) {
  const analysis = outputs.analysis || {};
  const summary = outputs.summary || "";
  const analysisType = analysis.analysis_type || outputs.analysis_type || "";
  const charts = outputs.charts || {};

  return (
    <div className="structured-output">
      {analysisType && (
        <div className="so-analysis-type-badge">{analysisType.toUpperCase()}</div>
      )}
      {summary && (
        <div className="so-summary-box">
          <strong>Summary:</strong> {summary}
        </div>
      )}
      {analysis && Object.keys(analysis).length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Analysis Details</div>
          <pre className="so-analysis-json">
            {JSON.stringify(analysis, null, 2)}
          </pre>
        </div>
      )}
      {charts && Object.keys(charts).length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Charts ({Object.keys(charts).length})</div>
          <pre className="so-analysis-json">{JSON.stringify(charts, null, 2)}</pre>
        </div>
      )}
      {outputs.fallback_reason && (
        <div className="so-fallback-note">⚠️ Fallback: {outputs.fallback_reason}</div>
      )}
    </div>
  );
}

/* ── Auto-detect and route ─────────────────────────────────────────── */

function isResearcherOutput(out) {
  return (
    out &&
    Array.isArray(out.findings) &&
    out.findings.length > 0 &&
    typeof out.findings[0].statement === "string"
  );
}

function isCriticOutput(out) {
  return out && typeof out.passed === "boolean" && Array.isArray(out.issues);
}

function isSynthesizerOutput(out) {
  return (
    out &&
    Array.isArray(out.options) &&
    out.options.length > 0 &&
    typeof out.options[0].title === "string"
  );
}

function isDataAnalystOutput(out) {
  return (
    out &&
    typeof out.analysis === "object" &&
    out.analysis !== null &&
    !Array.isArray(out.analysis) &&
    (out.analysis.analysis_type || out.analysis_type)
  );
}

export default function StructuredNodeOutput({ outputs }) {
  if (!outputs || Object.keys(outputs).length === 0) return null;

  if (isResearcherOutput(outputs)) return <ResearcherOutput outputs={outputs} />;
  if (isCriticOutput(outputs)) return <CriticOutput outputs={outputs} />;
  if (isSynthesizerOutput(outputs)) return <SynthesizerOutput outputs={outputs} />;
  if (isDataAnalystOutput(outputs)) return <DataAnalystOutput outputs={outputs} />;

  // Unknown shape — fall through to raw JSON (rendered by caller)
  return null;
}
