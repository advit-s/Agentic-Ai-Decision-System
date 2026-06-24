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
} from "../api";
import { useToast } from "./Toast";

const DEMO_STEPS = [
  { id: "workspace", label: "Create Demo Workspace", icon: "📁" },
  { id: "data", label: "Add Sample Data", icon: "📂" },
  { id: "provider", label: "Configure Fake Provider", icon: "🤖" },
  { id: "workflow", label: "Load Demo Workflow", icon: "⚡" },
  { id: "run", label: "Run Demo", icon: "▶️" },
  { id: "report", label: "Open Trust Report", icon: "🛡️" },
];

function DemoFlow({ workspaceId, workspaceName, onWorkspaceChange, onNavigate, onLoadDemoWorkflow }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [running, setRunning] = useState(false);
  const [completed, setCompleted] = useState(new Set());
  const [demoWsId, setDemoWsId] = useState(null);
  const { showToast } = useToast();

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
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleAddSampleData = async () => {
    const ws = demoWsId || workspaceId || "demo-workspace";
    setRunning(true);
    try {
      // Upload a sample text file
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
      const uploadResult = await uploadDataSource(ws, "q2-revenue-analysis.md", sampleBlob, "md");
      const sourceId = uploadResult.data_source?.source_id;

      if (sourceId) {
        await parseDataSource(ws, sourceId);
        await indexDataSource(ws, sourceId);
      }

      setCompleted(new Set([...completed, "data"]));
      showToast("Sample data added and indexed", "success");
      setCurrentStep(2);
    } catch (err) {
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleSetupProvider = async () => {
    setRunning(true);
    try {
      // Check if fake provider already exists
      const providers = await listProviders();
      const hasFake = (providers.providers || providers || []).some(
        (p) => (p.name || "").toLowerCase() === "fake"
      );

      if (!hasFake) {
        await createProvider({
          name: "fake",
          provider_type: "fake",
          base_url: "",
          models: ["mock-model"],
        });
      }
      await setDefaultProvider("fake");
      setCompleted(new Set([...completed, "provider"]));
      showToast("Fake provider configured", "success");
      setCurrentStep(3);
    } catch (err) {
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleLoadWorkflow = async () => {
    try {
      if (onLoadDemoWorkflow) onLoadDemoWorkflow();
      setCompleted(new Set([...completed, "workflow"]));
      showToast("Demo workflow loaded", "success");
      setCurrentStep(4);
    } catch (err) {
      showToast(`Failed: ${err.message}`, "error");
    }
  };

  const handleRunDemo = async () => {
    setRunning(true);
    try {
      // Navigate to workflow builder and execute
      if (onNavigate) onNavigate("workflow");
      setCompleted(new Set([...completed, "run"]));
      showToast("Navigate to Workflow Builder and click Execute", "info");
      setCurrentStep(5);
    } catch (err) {
      showToast(`Failed: ${err.message}`, "error");
    } finally {
      setRunning(false);
    }
  };

  const handleOpenReport = () => {
    if (onNavigate) onNavigate("trust");
    setCompleted(new Set([...completed, "report"]));
    showToast("Open Trust Dashboard to view and export report", "info");
  };

  const stepActions = {
    workspace: { action: handleCreateWorkspace, label: running ? "Creating..." : "Create Demo Workspace" },
    data: { action: handleAddSampleData, label: running ? "Adding..." : "Add Sample Data File" },
    provider: { action: handleSetupProvider, label: running ? "Configuring..." : "Configure Fake Provider" },
    workflow: { action: handleLoadWorkflow, label: "Load Demo Workflow" },
    run: { action: handleRunDemo, label: "Go to Workflow Builder" },
    report: { action: handleOpenReport, label: "Open Trust Dashboard" },
  };

  return (
    <div className="section-page">
      <div className="section-header">
        <h2>🚀 Demo Flow</h2>
        <p className="section-subtitle">Guided tour — no API keys or cloud services needed</p>
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
              You've completed the demo flow. You can now explore the app freely.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default DemoFlow;
