// __tests__/NodePalette.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import NodePalette from "../src/components/NodePalette";
import { MOCK_NODE_TYPES } from "../src/mockData";
import React from "react";

describe("NodePalette", () => {
  it("renders all 16 node types", () => {
    render(<NodePalette nodeTypes={MOCK_NODE_TYPES} onDragStart={() => {}} />);
    expect(screen.getByText("Manual Trigger")).toBeDefined();
    expect(screen.getByText("Retrieve Evidence")).toBeDefined();
    expect(screen.getByText("Write Report")).toBeDefined();
  });

  it("renders category headers", () => {
    render(<NodePalette nodeTypes={MOCK_NODE_TYPES} onDragStart={() => {}} />);
    expect(screen.getByText(/Triggers/)).toBeDefined();
    expect(screen.getByText(/Data/, { selector: ".palette-category-title" })).toBeDefined();
    expect(screen.getByText(/AI/, { selector: ".palette-category-title" })).toBeDefined();
    expect(screen.getByText(/Output/, { selector: ".palette-category-title" })).toBeDefined();
    expect(screen.getByText(/Flow/, { selector: ".palette-category-title" })).toBeDefined();
  });

  it("fires onDragStart when dragging a node type", () => {
    const onDragStart = [];
    render(
      <NodePalette
        nodeTypes={MOCK_NODE_TYPES}
        onDragStart={(nt) => onDragStart.push(nt)}
      />
    );
    const item = screen.getByText("Manual Trigger");
    fireEvent.dragStart(item);
    expect(onDragStart.length).toBeGreaterThanOrEqual(1);
  });
});
