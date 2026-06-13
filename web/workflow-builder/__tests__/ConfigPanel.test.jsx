// __tests__/ConfigPanel.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ConfigPanel from "../src/components/ConfigPanel";
import { MOCK_NODE_TYPES } from "../src/mockData";
import React from "react";

describe("ConfigPanel", () => {
  const retrieveNodeType = MOCK_NODE_TYPES.find(
    (n) => n.type === "decision_system.retrieve"
  );

  it("renders nothing when no node selected", () => {
    const { container } = render(
      <ConfigPanel
        selectedNode={null}
        nodeType={null}
        onUpdateConfig={() => {}}
        onDelete={() => {}}
      />
    );
    expect(container.textContent).toBe("");
  });

  it("shows node label and type when a node is selected", () => {
    const node = {
      id: "n1",
      type: "decision_system.retrieve",
      data: { label: "My Retrieve", config: {} },
    };
    render(
      <ConfigPanel
        selectedNode={node}
        nodeType={retrieveNodeType}
        onUpdateConfig={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByDisplayValue("My Retrieve")).toBeDefined();
    expect(screen.getByText("decision_system.retrieve")).toBeDefined();
  });

  it("renders config fields from the node type schema", () => {
    const node = {
      id: "n1",
      type: "decision_system.retrieve",
      data: { label: "My Retrieve", config: {} },
    };
    render(
      <ConfigPanel
        selectedNode={node}
        nodeType={retrieveNodeType}
        onUpdateConfig={() => {}}
        onDelete={() => {}}
      />
    );
    expect(screen.getByText("Collection")).toBeDefined();
    expect(screen.getByText("Top K")).toBeDefined();
  });

  it("calls onDelete when delete button is clicked", () => {
    const onDelete = [];
    const node = {
      id: "n1",
      type: "decision_system.retrieve",
      data: { label: "My Retrieve", config: {} },
    };
    render(
      <ConfigPanel
        selectedNode={node}
        nodeType={retrieveNodeType}
        onUpdateConfig={() => {}}
        onDelete={() => onDelete.push("deleted")}
      />
    );
    // Match button containing "Delete" text (emoji prefix splits text node)
    const deleteBtn = screen.getByRole("button", { name: /delete/i });
    fireEvent.click(deleteBtn);
    expect(onDelete.length).toBe(1);
  });
});
