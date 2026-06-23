// components/OnboardingPanel.jsx — First-run onboarding for new local users
import React, { useState } from "react";

const STEPS = [
  {
    icon: "📁",
    title: "Create a Workspace",
    description: "Start by creating a workspace to organize your documents, data, and workflows.",
    action: "Use the sidebar to create your first workspace.",
  },
  {
    icon: "📄",
    title: "Upload Local Data",
    description: "Add Markdown or text documents to your workspace for evidence searching.",
    action: "Use Data Sources or command line: decision-system seed-demo-data",
  },
  {
    icon: "🤖",
    title: "Configure a Provider",
    description: "The Fake Provider works offline with no API key. Open Provider Manager to configure.",
    action: "Click the 'Providers' button in the toolbar to get started.",
  },
  {
    icon: "📋",
    title: "Load a Demo Workflow",
    description: "Choose a template workflow to see the builder in action.",
    action: "Click 'Templates' in the toolbar and select 'Local Evidence Search'.",
  },
  {
    icon: "▶️",
    title: "Run the Workflow",
    description: "Validate your workflow, then click Execute to see it run step by step.",
    action: "Use Validate to check, then Execute to run.",
  },
  {
    icon: "✅",
    title: "Verify Claims & Export Report",
    description: "After execution, verify claims, scan contradictions, and export a trust report.",
    action: "Use the Trust Dashboard and Execution Panel to inspect results.",
  },
];

function OnboardingPanel({ onDismiss }) {
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem("wfBuilderOnboardingDismissed") === "true";
    } catch {
      return false;
    }
  });

  if (dismissed) return null;

  const handleDismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem("wfBuilderOnboardingDismissed", "true");
    } catch {}
    if (onDismiss) onDismiss();
  };

  return (
    <div className="onboarding-panel">
      <div className="onboarding-header">
        <span className="onboarding-title">🚀 Welcome to the Workflow Builder</span>
        <button className="onboarding-dismiss" onClick={handleDismiss} title="Dismiss">
          ✕
        </button>
      </div>
      <div className="onboarding-steps">
        {STEPS.map((step, i) => (
          <div key={i} className="onboarding-step">
            <div className="onboarding-step-icon">{step.icon}</div>
            <div className="onboarding-step-body">
              <div className="onboarding-step-title">{step.title}</div>
              <div className="onboarding-step-desc">{step.description}</div>
              <div className="onboarding-step-action">{step.action}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="onboarding-footer">
        <button className="onboarding-btn" onClick={handleDismiss}>
          Got it — let's start
        </button>
      </div>
    </div>
  );
}

export default OnboardingPanel;
