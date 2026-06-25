// DemoFlow.jsx — Guided local demo flow (no cloud keys needed)
import React, { useState } from "react";
import {
  createWorkspace,
  uploadDataSource,
  parseDataSource,
  indexDataSource,
  listProviders,
  createProvider,
  setDefaultProvider,
  executeWorkflow,
  verifyWorkspaceClaims,
  extractGraph,
  getGraph,
} from "../api";
import { useToast } from "./Toast";

const DEMO_STEPS = [
  { id: "workspace", label: "Create Demo Workspace", icon: "📁" },
  { id: "data", label: "Add Sample Data", icon: "📂" },
  { id: "parse", label: "Parse/Index/OCR Data", icon: "🔍" },
  { id: "graph", label: "Extract Knowledge Graph", icon: "🔗" },
  { id: "provider", label: "Configure Fake Provider", icon: "🤖" },
  { id: "workflow", label: "Load Demo Workflow", icon: "⚡" },
  { id: "run", label: "Run Workflow", icon: "▶️" },
  { id: "verify", label: "Verify Claims", icon: "✅" },
  { id: "report", label: "Generate Trust Report", icon: "🛡️" },
  { id: "export", label: "Export Markdown", icon: "📄" },
];

function DemoFlow({ workspaceId, workspaceName, onWorkspaceChange, onNavigate, onLoadDemoWorkflow }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [running, setRunning] = useState(false);
  const [completed, setCompleted] = useState(new Set());
  const [demoWsId, setDemoWsId] = useState(null);
  const { showToast } = useToast();
  const [executionId, setExecutionId] = useState(null);

  const handleCreateWorkspace = async () => {
    setRunning(true);
    try {
      const result = await createWorkspace("Demo Workspace", "Demo workspace for exploring the product", true);
      const wsId = result.workspace?.workspace_id || "demo-workspace";
      setDemoWsId(wsId);
      if (onWorkspaceChange) onWorkspaceChange(wsId);
      setCompleted(new Set([...completed, "workspace"]));
      showToast("Demo workspace created", "success");
      setCurrentStep(1);
    } catch (err) {
      showToast("Failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleAddSampleData = async () => {
    const ws = demoWsId || workspaceId || "demo-workspace";
    setRunning(true);
    try {
      const sampleContent = `# Q2 Revenue Analysis

Revenue grew by 15% year-over-year in Q2 2026, reaching $2.5M.

Key findings:
- Customer acquisition cost decreased by 8% to $180 per customer
- Monthly recurring revenue (MRR) increased by 22%
- Churn rate dropped from 5.2% to 3.8%
- Enterprise segment grew 35% year-over-year
- International markets contributed 18% of total revenue

Risks and concerns:
- Cloud infrastructure costs increased 40% due to scaling
- Two key customers on monthly contracts are at risk of churn
- The APAC region underperformed by 12% against targets
- Security audit found 3 medium-severity vulnerabilities in the billing system

Recommendations:
- Migrate billing to the new payment provider by Q3 to improve reliability
- Invest in APAC sales team to close the performance gap
- Implement automated scaling to reduce cloud waste
- Address security vulnerabilities before next SOC 2 audit`;

      const sampleBlob = new Blob([sampleContent], { type: "text/plain" });
      await uploadDataSource(ws, "q2-revenue-analysis.md", sampleBlob, "md");

      setCompleted(new Set([...completed, "data"]));
      showToast("Sample data uploaded (parse/index in next step)", "success");
      setCurrentStep(2);
    } catch (err) {
      showToast("Failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleExtractGraph = async () => {
    if (!workspaceId) {
      showToast("Create workspace first", "warning");
      return;
    }
    setRunning(true);
    try {
      const sampleTexts = [
        {
          text: "Acme Corporation provides CloudSync SaaS platform. Revenue: $5M annually. Profit margin: 20%. Customers: 500+.",
          evidence_id: "demo-ev-1", source_id: "demo-src-1", chunk_id: "demo-ch-1",
        },
        {
          text: "Risk of vendor lock-in with FastCloud Ltd. Security vulnerability in payment gateway. Compliance with GDPR.",
          evidence_id: "demo-ev-2", source_id: "demo-src-2", chunk_id: "demo-ch-2",
        },
      ];
      const result = await extractGraph(workspaceId, sampleTexts);
      showToast(`Graph extracted: ${result.nodes_extracted} entities, ${result.risks_extracted} risks, ${result.metrics_extracted} metrics`, "success");
      setCurrentStep(4);
    } catch (err) {
      showToast("Extraction failed: " + err.message, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleParseIndex = async () => {
    const ws = demoWsId || workspaceId || "demo-workspace";
    setRunning(true);
    try {
      const resp = await fetch("/api/workspaces/" + ws + "/data-sources");
      const sources = await resp.json();
      const items = Array.isArray(sources) ? sources : (sources.sources || sources.items || []);
      let parsed = 0;
      for (const src of items) {
        const sid = src.source_id || src.id;
        if (sid) {
          await fetch("/api/workspaces/" + ws + "/data-sources/" + sid + "/parse", { method: "POST" });
          await fetch("/api/workspaces/" + ws + "/data-sources/" + sid + "/index", { method: "POST" });
          parsed++;
        }
      }
      setCompleted(new Set([...completed, "parse"]));
      showToast(parsed > 0 ? "Parsed and indexed " + parsed + " files (OCR applied where needed)" : "No files to parse", "success");
      setCurrentStep(3);
    } catch (err) {
      showToast("Parse/index failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleSetupProvider = async () => {
    setRunning(true);
    try {
      const providers = await listProviders();
      const provList = providers.providers || providers || [];
      const hasFake = provList.some(
        (p) => (p.name || "").toLowerCase() === "fake" || p.provider_type === "fake"
      );
      if (!hasFake) {
        await createProvider({
          name: "Fake Provider",
          provider_type: "fake",
          base_url: "",
          models: ["fake-model"],
        });
        try { await setDefaultProvider("Fake Provider"); } catch (e) { /* ignore */ }
      }
      setCompleted(new Set([...completed, "provider"]));
      showToast("Fake provider configured", "success");
      setCurrentStep(4);
    } catch (err) {
      showToast("Provider setup failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleLoadWorkflow = async () => {
    try {
      if (onLoadDemoWorkflow) onLoadDemoWorkflow();
      setCompleted(new Set([...completed, "workflow"]));
      showToast("Demo workflow loaded", "success");
      setCurrentStep(5);
    } catch (err) {
      showToast("Failed: " + (err.message || "unknown error"), "error");
    }
  };

  const handleRunDemo = async () => {
    setRunning(true);
    try {
      if (onNavigate) onNavigate("workflow");
      try {
        const ws = demoWsId || workspaceId || "demo-workspace";
        const wfResp = await fetch("/api/workspaces/" + ws + "/workflows");
        const wfs = await wfResp.json();
        const wfList = Array.isArray(wfs) ? wfs : (wfs.workflows || wfs.items || []);
        const demoWf = wfList.find(w => (w.name || "").toLowerCase().includes("demo") || (w.name || "").toLowerCase().includes("trust"));
       if (demoWf) {
          const execResp = await fetch("/api/workspaces/" + ws + "/workflows/" + (demoWf.id || demoWf.workflow_id) + "/execute", { method: "POST" });
          const execData = await execResp.json();
          const exId = execData.execution_id || execData.id;
          if (exId) setExecutionId(exId);
          showToast("Workflow execution started", "success");
        } else {
          showToast("Navigate to Workflow Builder and click Execute", "info");
        }
      } catch (e) {
        showToast("Navigate to Workflow Builder and click Execute", "info");
      }
      setCompleted(new Set([...completed, "run"]));
      setCurrentStep(6);
    } catch (err) {
      showToast("Execution failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleVerifyClaims = async () => {
    setRunning(true);
    try {
      const ws = demoWsId || workspaceId || "demo-workspace";
      try {
        await fetch("/api/workspaces/" + ws + "/claims/verify", { method: "POST" });
        await fetch("/api/workspaces/" + ws + "/contradictions/scan", { method: "POST" });
      } catch (e) { /* ignore */ }
      setCompleted(new Set([...completed, "verify"]));
      showToast("Claims verified and contradictions scanned", "success");
      setCurrentStep(7);
    } catch (err) {
      showToast("Verification failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleGenerateReport = async () => {
    setRunning(true);
    try {
      const ws = demoWsId || workspaceId || "demo-workspace";
     try {
        const exId = executionId;
        if (exId) {
          await fetch("/api/executions/" + exId + "/report", { method: "POST" });
        } else {
          showToast("Run the workflow first to generate a report", "warning");
          return;
        }
      } catch (e) { /* ignore */ }
      setCompleted(new Set([...completed, "report"]));
      showToast("Trust report generated", "success");
      setCurrentStep(8);
    } catch (err) {
      showToast("Report generation failed: " + (err.message || "unknown error"), "error");
    } finally {
      setRunning(false);
    }
  };

  const handleExportReport = async () => {
    try {
      if (onNavigate) onNavigate("reports");
      setCompleted(new Set([...completed, "export"]));
      showToast("Navigate to Reports section to export your Markdown report", "info");
    } catch (err) {
      showToast("Export failed: " + (err.message || "unknown error"), "error");
    }
  };

  const stepActions = {
    workspace: { action: handleCreateWorkspace, label: running ? "Creating..." : "Create Demo Workspace" },
    data: { action: handleAddSampleData, label: running ? "Adding..." : "Add Sample Data Files" },
    parse: { action: handleParseIndex, label: running ? "Parsing..." : "Parse, OCR & Index Files" },
    graph: { action: handleExtractGraph, label: running ? "Extracting..." : "Extract Knowledge Graph" },
    provider: { action: handleSetupProvider, label: running ? "Configuring..." : "Configure Fake Provider" },
    workflow: { action: handleLoadWorkflow, label: "Load Demo Workflow" },
    run: { action: handleRunDemo, label: running ? "Running..." : "Run Workflow" },
    verify: { action: handleVerifyClaims, label: running ? "Verifying..." : "Verify Claims" },
    report: { action: handleGenerateReport, label: running ? "Generating..." : "Generate Trust Report" },
    export: { action: handleExportReport, label: "Export Markdown Report" },
  };

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>🚀 Demo Flow</h2>
        <p className="section-subtitle">Guided tour — no API keys or cloud services needed. 10 steps to a trust report.</p>
      </div>
      <div className="section-content">
        <div className="demo-steps">
          {DEMO_STEPS.map((step, idx) => {
            const isCompleted = completed.has(step.id);
            const isCurrent = currentStep === idx;
            const isPast = idx < currentStep;
            return (
              <div
                key={step.id}
                className={`demo-step ${isCurrent ? "demo-step-current" : ""} ${isCompleted ? "demo-step-completed" : ""} ${isPast && !isCompleted ? "demo-step-past" : ""}`}
              >
                <div className="demo-step-number">
                  {isCompleted ? "✓" : isCurrent ? "→" : idx + 1}
                </div>
                <div className="demo-step-body">
                  <div className="demo-step-header">
                    <span className="demo-step-icon">{step.icon}</span>
                    <span className="demo-step-label">{step.label}</span>
                    {isCompleted && <span className="demo-step-done">Done</span>}
                    {!isCompleted && !isCurrent && <span className="demo-step-status-pending">Pending</span>}
                  </div>
                  {(isCurrent || !isCompleted) && (
                    <button
                      className="toolbar-btn toolbar-btn-primary"
                      onClick={stepActions[step.id].action}
                      disabled={running}
                      style={{ marginTop: 8 }}
                    >
                      {stepActions[step.id].label}
                    </button>
                  )}
                  {isCurrent && isCompleted && (
                    <span className="demo-step-success">✓ Completed</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {completed.size === DEMO_STEPS.length && (
          <div className="placeholder-card" style={{ textAlign: "center", borderColor: "#4ade80" }}>
            <div className="placeholder-icon">🎉</div>
            <h3>Demo Complete!</h3>
            <p className="text-muted">
              You've completed the demo flow. Your trust report is ready in the Reports section.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DemoFlow;
