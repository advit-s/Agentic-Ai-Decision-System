// __tests__/WorkflowToolbar.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import WorkflowToolbar from "../src/components/WorkflowToolbar";
import React from "react";

describe("WorkflowToolbar", () => {
  it("renders all toolbar buttons", () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="My Workflow"
        isExecuting={false}
      />
    );
    expect(screen.getByText("+ New")).toBeDefined();
    expect(screen.getByText(/Save/)).toBeDefined();
    expect(screen.getByText(/Load/)).toBeDefined();
    expect(screen.getByText(/Execute/)).toBeDefined();
    expect(screen.getByText(/Export/)).toBeDefined();
  });

  it("shows current workflow name", () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="Test Workflow"
        isExecuting={false}
      />
    );
    expect(screen.getByText("Test Workflow")).toBeDefined();
  });

  it("disables execute button when isExecuting is true", () => {
    render(
      <WorkflowToolbar
        onNew={() => {}}
        onSave={() => {}}
        onLoad={() => {}}
        onExecute={() => {}}
        onExport={() => {}}
        workflows={[]}
        currentWorkflowName="Test"
        isExecuting={true}
      />
    );
    expect(screen.getByText(/Running/)).toBeDefined();
    // The execute button should have the disabled attribute
    const btn = screen.getByText(/Running/);
    expect(btn.disabled).toBe(true);
  });
});
