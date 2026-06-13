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

/* ── Planner Output ────────────────────────────────────────────────── */

function PlannerOutput({ outputs }) {
  const plan = outputs.plan || [];
  const summary = outputs.summary || "";
  const totalSteps = outputs.total_steps || 0;
  const estDuration = outputs.estimated_duration || "";

  return (
    <div className="structured-output">
      {summary && (
        <div className="so-summary-box">
          <strong>Plan:</strong> {summary}
        </div>
      )}
      {totalSteps > 0 && (
        <div className="so-plan-meta">
          <span className="so-plan-meta-badge">{totalSteps} step{totalSteps !== 1 ? "s" : ""}</span>
          {estDuration && <span className="so-plan-meta-badge">{estDuration}</span>}
        </div>
      )}
      {plan.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Steps</div>
          {plan.map((step, i) => (
            <div key={i} className="so-plan-step-card">
              <div className="so-plan-step-header">
                <span className="so-plan-step-num">Step {step.step_number || i + 1}</span>
                <span className="so-plan-step-title">{step.title}</span>
                {step.estimated_effort && (
                  <span className="so-plan-effort-badge">{step.estimated_effort}</span>
                )}
              </div>
              {step.description && (
                <div className="so-plan-step-desc">{step.description}</div>
              )}
              {step.dependencies && step.dependencies.length > 0 && (
                <div className="so-plan-step-deps">
                  Depends on: step(s) {step.dependencies.join(", ")}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
      {outputs.fallback_reason && (
        <div className="so-fallback-note">⚠️ Fallback: {outputs.fallback_reason}</div>
      )}
    </div>
  );
}

/* ── Auditor Output ───────────────────────────────────────────────── */

const AUDIT_SEVERITY_CONFIG = {
  high: { bg: "#fee2e2", color: "#991b1b", label: "High" },
  medium: { bg: "#fef9c3", color: "#854d0e", label: "Medium" },
  low: { bg: "#f3f4f6", color: "#4b5563", label: "Low" },
};

function AuditorOutput({ outputs }) {
  const findings = outputs.findings || [];
  const summary = outputs.summary || "";
  const passed = outputs.passed;
  const score = outputs.score;
  const issuesFound = outputs.issues_found || 0;
  const recommendations = outputs.recommendations || [];

  return (
    <div className="structured-output">
      <div className="so-audit-header">
        <span
          className="so-audit-pass-badge"
          style={{
            background: passed ? "#dcfce7" : "#fee2e2",
            color: passed ? "#166534" : "#991b1b",
          }}
        >
          {passed ? "✅ Passed" : "❌ Failed"}
        </span>
        {score !== undefined && (
          <div className="so-audit-score-bar">
            <div className="so-audit-score-label">Score: {Math.round(score * 100)}%</div>
            <div className="so-audit-score-track">
              <div
                className="so-audit-score-fill"
                style={{
                  width: `${Math.round(score * 100)}%`,
                  background: score >= 0.7 ? "#22c55e" : score >= 0.4 ? "#eab308" : "#ef4444",
                }}
              />
            </div>
          </div>
        )}
      </div>

      {summary && <div className="so-summary-box">{summary}</div>}

      {issuesFound > 0 && (
        <div className="so-section">
          <div className="so-section-title">Findings ({issuesFound})</div>
          {findings.map((f, i) => {
            const sev = AUDIT_SEVERITY_CONFIG[f.severity] || AUDIT_SEVERITY_CONFIG.low;
            return (
              <div key={i} className="so-audit-finding-row">
                <span className="so-audit-finding-cat">{f.category}</span>
                <span className="so-issue-sev-badge" style={{ background: sev.bg, color: sev.color }}>
                  {sev.label}
                </span>
                <div className="so-audit-finding-desc">{f.description}</div>
                {f.recommendation && (
                  <div className="so-audit-finding-rec">💡 {f.recommendation}</div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Recommendations</div>
          <ul className="so-audit-rec-list">
            {recommendations.map((r, i) => (
              <li key={i}>{r}</li>
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

/* ── Compliance Checker Output ────────────────────────────────────── */

const RISK_COLORS = {
  critical: { bg: "#7f1d1d", color: "#fca5a5", label: "Critical" },
  high: { bg: "#991b1b", color: "#fecaca", label: "High" },
  medium: { bg: "#854d0e", color: "#fef9c3", label: "Medium" },
  low: { bg: "#166534", color: "#dcfce7", label: "Low" },
};

const COMPLIANCE_SEVERITY_COLORS = {
  critical: { bg: "#fee2e2", color: "#7f1d1d" },
  high: { bg: "#fee2e2", color: "#991b1b" },
  medium: { bg: "#fef9c3", color: "#854d0e" },
  low: { bg: "#f3f4f6", color: "#4b5563" },
};

function ComplianceCheckerOutput({ outputs }) {
  const violations = outputs.violations || [];
  const summary = outputs.summary || "";
  const compliant = outputs.compliant;
  const riskLevel = outputs.risk_level || "low";
  const score = outputs.score;
  const passedChecks = outputs.passed_checks || 0;
  const failedChecks = outputs.failed_checks || 0;

  const riskColor = RISK_COLORS[riskLevel] || RISK_COLORS.low;

  return (
    <div className="structured-output">
      <div className="so-compliance-header">
        <span
          className="so-compliance-badge"
          style={{
            background: compliant ? "#dcfce7" : "#fee2e2",
            color: compliant ? "#166534" : "#991b1b",
          }}
        >
          {compliant ? "✅ Compliant" : "❌ Non-Compliant"}
        </span>
        <span className="so-risk-badge" style={{ background: riskColor.bg, color: riskColor.color }}>
          {riskColor.label} Risk
        </span>
      </div>

      {summary && <div className="so-summary-box">{summary}</div>}

      {score !== undefined && (
        <div className="so-audit-score-bar">
          <div className="so-audit-score-label">Score: {Math.round(score * 100)}% ({passedChecks} passed / {failedChecks} failed)</div>
          <div className="so-audit-score-track">
            <div
              className="so-audit-score-fill"
              style={{
                width: `${Math.round(score * 100)}%`,
                background: score >= 0.7 ? "#22c55e" : score >= 0.4 ? "#eab308" : "#ef4444",
              }}
            />
          </div>
        </div>
      )}

      {violations.length > 0 && (
        <div className="so-section">
          <div className="so-section-title">Violations ({violations.length})</div>
          {violations.map((v, i) => {
            const sevColor = COMPLIANCE_SEVERITY_COLORS[v.severity] || COMPLIANCE_SEVERITY_COLORS.low;
            return (
              <div key={i} className="so-violation-row">
                <div className="so-violation-header">
                  <span className="so-violation-rule">{v.rule}</span>
                  <span className="so-issue-sev-badge" style={{ background: sevColor.bg, color: sevColor.color }}>
                    {v.severity}
                  </span>
                </div>
                <div className="so-violation-desc">{v.description}</div>
                {v.remediation && (
                  <div className="so-violation-remediation">🔧 {v.remediation}</div>
                )}
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

/* ── Code Runner Output ───────────────────────────────────────────── */

function CodeRunnerOutput({ outputs }) {
  const success = outputs.success;
  const result = outputs.result;
  const stdout = outputs.stdout || "";
  const error = outputs.error;
  const execTime = outputs.execution_time_ms;

  return (
    <div className="structured-output">
      <div className="so-coderunner-header">
        <span
          className="so-coderunner-badge"
          style={{
            background: success ? "#dcfce7" : "#fee2e2",
            color: success ? "#166534" : "#991b1b",
          }}
        >
          {success ? "✅ Success" : "❌ Failed"}
        </span>
        {execTime !== undefined && (
          <span className="so-coderunner-time">{execTime.toFixed(1)}ms</span>
        )}
      </div>

      {stdout && (
        <div className="so-section">
          <div className="so-section-title">Standard Output</div>
          <pre className="so-coderunner-stdout">{stdout}</pre>
        </div>
      )}

      {error && (
        <div className="so-section">
          <div className="so-section-title">Error</div>
          <pre className="so-coderunner-error">{error}</pre>
        </div>
      )}

      {result !== null && result !== undefined && (
        <div className="so-section">
          <div className="so-section-title">Result</div>
          <pre className="so-coderunner-result">{JSON.stringify(result, null, 2)}</pre>
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

function isPlannerOutput(out) {
  return (
    out &&
    Array.isArray(out.plan) &&
    typeof out.summary === "string" &&
    typeof out.total_steps === "number"
  );
}

function isAuditorOutput(out) {
  return (
    out &&
    typeof out.passed === "boolean" &&
    typeof out.score === "number" &&
    Array.isArray(out.findings)
  );
}

function isComplianceCheckerOutput(out) {
  return (
    out &&
    typeof out.compliant === "boolean" &&
    Array.isArray(out.violations) &&
    typeof out.risk_level === "string"
  );
}

function isCodeRunnerOutput(out) {
  return (
    out &&
    typeof out.success === "boolean" &&
    (out.stdout !== undefined || out.result !== undefined || out.error !== undefined)
  );
}

export default function StructuredNodeOutput({ outputs }) {
  if (!outputs || Object.keys(outputs).length === 0) return null;

  if (isPlannerOutput(outputs)) return <PlannerOutput outputs={outputs} />;
  if (isAuditorOutput(outputs)) return <AuditorOutput outputs={outputs} />;
  if (isComplianceCheckerOutput(outputs)) return <ComplianceCheckerOutput outputs={outputs} />;
  if (isCodeRunnerOutput(outputs)) return <CodeRunnerOutput outputs={outputs} />;
  if (isResearcherOutput(outputs)) return <ResearcherOutput outputs={outputs} />;
  if (isCriticOutput(outputs)) return <CriticOutput outputs={outputs} />;
  if (isSynthesizerOutput(outputs)) return <SynthesizerOutput outputs={outputs} />;
  if (isDataAnalystOutput(outputs)) return <DataAnalystOutput outputs={outputs} />;

  // Unknown shape — fall through to raw JSON (rendered by caller)
  return null;
}
