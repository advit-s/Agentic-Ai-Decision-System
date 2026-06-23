// __tests__/integration.test.jsx
import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";
import React from "react";

describe("App integration", () => {
  beforeEach(() => {
    localStorage.removeItem("wfBuilderApiBaseUrl");
  });

  it("renders the toolbar", async () => {
    render(<App />);
    expect(screen.getByText("+ New")).toBeDefined();
    expect(screen.getByText(/Save/)).toBeDefined();
  });

  it("renders the node palette", async () => {
    render(<App />);
    // Node palette loads async via fetchNodeTypes
    const trigger = await screen.findByText("Manual Trigger");
    expect(trigger).toBeDefined();
    expect(screen.getByText(/Core/)).toBeDefined();
  });

  it("shows Untitled Workflow initially", () => {
    render(<App />);
    expect(screen.getByText("Untitled Workflow")).toBeDefined();
  });
});
