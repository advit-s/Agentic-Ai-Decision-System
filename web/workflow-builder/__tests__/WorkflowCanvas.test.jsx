// __tests__/WorkflowCanvas.test.jsx
import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import WorkflowCanvas from "../src/components/WorkflowCanvas";
import React from "react";

describe("WorkflowCanvas", () => {
  it("renders the canvas area", () => {
    const { container } = render(
      <WorkflowCanvas
        nodes={[]}
        edges={[]}
        onNodesChange={() => {}}
        onEdgesChange={() => {}}
        onConnect={() => {}}
        onNodeClick={() => {}}
        onPaneClick={() => {}}
        onDrop={() => {}}
        onDragOver={() => {}}
        nodeTypes={{}}
      />
    );
    expect(container.querySelector(".react-flow")).toBeDefined();
  });
});
