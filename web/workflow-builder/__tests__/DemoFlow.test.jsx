// __tests__/DemoFlow.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import DemoFlow from "../src/components/DemoFlow";
import { ToastProvider } from "../src/components/Toast";

function renderWithProviders(ui) {
  return render(<ToastProvider>{ui}</ToastProvider>);
}

describe("DemoFlow", () => {
  it("renders the demo title", () => {
    renderWithProviders(<DemoFlow />);
    expect(screen.getByText(/Demo Flow/)).toBeDefined();
  });

  it("renders all 9 demo steps", () => {
    renderWithProviders(<DemoFlow />);
    // Use getAllByText since labels appear both in step header and button
    expect(screen.getAllByText("Create Demo Workspace").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Add Sample Data").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Parse/Index/OCR Data").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Configure Fake Provider").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Load Demo Workflow").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Run Workflow").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Verify Claims").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Generate Trust Report").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Export Markdown").length).toBeGreaterThanOrEqual(1);
  });

  it("has action buttons for first step", () => {
    renderWithProviders(<DemoFlow />);
    const buttons = screen.getAllByRole("button");
    const createBtn = buttons.find(b => b.textContent.includes("Create Demo Workspace"));
    expect(createBtn).toBeDefined();
  });

  it("shows pending status on non-current steps", () => {
    renderWithProviders(<DemoFlow />);
    const pendingLabels = screen.getAllByText("Pending");
    expect(pendingLabels.length).toBeGreaterThanOrEqual(8);
  });
});
