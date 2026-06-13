// __tests__/ExecutionPanel.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ExecutionPanel from "../src/components/ExecutionPanel";
import React from "react";

/* Helper: click "Node View" to switch from ledger (default) to nodes view */
function switchToNodeView() {
  const btn = screen.getByText(/Node View/);
  fireEvent.click(btn);
}

describe("ExecutionPanel", () => {
  const nodeStatuses = [
    { nodeId: "n1", label: "Manual Trigger", status: "completed", duration: 0.02 },
    { nodeId: "n2", label: "Retrieve Evidence", status: "running", duration: 1.5 },
    { nodeId: "n3", label: "Tech Analyst", status: "pending" },
    { nodeId: "n4", label: "Write Report", status: "failed", duration: 0.5, error: "Timeout error" },
  ];

  it("renders execution status header", () => {
    render(
      <ExecutionPanel
        nodeStatuses={nodeStatuses}
        workflowStatus="running"
        elapsed={2.3}
        onClose={() => {}}
      />
    );
    switchToNodeView();
    expect(screen.getByText(/running/i)).toBeDefined();
  });

  it("renders all node statuses", () => {
    render(
      <ExecutionPanel
        nodeStatuses={nodeStatuses}
        workflowStatus="running"
        elapsed={2.3}
        onClose={() => {}}
      />
    );
    switchToNodeView();
    expect(screen.getByText("Manual Trigger")).toBeDefined();
    expect(screen.getByText("Retrieve Evidence")).toBeDefined();
    expect(screen.getByText("Tech Analyst")).toBeDefined();
  });

  it("shows error text for failed nodes", () => {
    render(
      <ExecutionPanel
        nodeStatuses={nodeStatuses}
        workflowStatus="failed"
        elapsed={3.0}
        onClose={() => {}}
      />
    );
    switchToNodeView();
    expect(screen.getByText(/Timeout error/)).toBeDefined();
  });
});
