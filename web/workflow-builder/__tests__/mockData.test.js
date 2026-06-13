// __tests__/mockData.test.js
import { describe, it, expect } from "vitest";
import { MOCK_NODE_TYPES, MOCK_WORKFLOWS, MOCK_EXECUTION_STATE, MOCK_EXECUTION_EVENTS } from "../src/mockData";

describe("mockData", () => {
  it("has 28 node types matching built-in nodes", () => {
    expect(MOCK_NODE_TYPES.length).toBe(28);
    const types = MOCK_NODE_TYPES.map((n) => n.type);
    expect(types).toContain("decision_system.trigger_manual");
    expect(types).toContain("decision_system.retrieve");
    expect(types).toContain("decision_system.technical_analyst");
    expect(types).toContain("decision_system.risk_analyst");
    expect(types).toContain("decision_system.extract_claims");
    expect(types).toContain("decision_system.verify_claims");
    expect(types).toContain("decision_system.write_report");
    expect(types).toContain("decision_system.extract_graph");
    expect(types).toContain("decision_system.profile_data");
    expect(types).toContain("decision_system.map_ontology");
    expect(types).toContain("decision_system.detect_patterns");
    expect(types).toContain("decision_system.war_room");
    expect(types).toContain("decision_system.input_text");
    expect(types).toContain("decision_system.filter");
    expect(types).toContain("decision_system.merge");
    expect(types).toContain("decision_system.code");
    expect(types).toContain("decision_system.planner");
    expect(types).toContain("decision_system.auditor");
    expect(types).toContain("decision_system.compliance_checker");
    expect(types).toContain("decision_system.code_runner");
  });

  it("has config_schema for every node type", () => {
    for (const node of MOCK_NODE_TYPES) {
      expect(node.config_schema).toBeDefined();
      expect(node.config_schema.type).toBe("object");
    }
  });

  it("has input_schema and output_schema for every node type", () => {
    for (const node of MOCK_NODE_TYPES) {
      expect(node.input_schema).toBeDefined();
      expect(node.output_schema).toBeDefined();
    }
  });

  it("has at least one sample workflow", () => {
    expect(MOCK_WORKFLOWS.length).toBeGreaterThanOrEqual(1);
    const wf = MOCK_WORKFLOWS[0];
    expect(wf.nodes.length).toBeGreaterThan(0);
    expect(wf.connections.length).toBeGreaterThan(0);
  });

  it("has execution state and events", () => {
    expect(MOCK_EXECUTION_STATE.execution_id).toBeDefined();
    expect(MOCK_EXECUTION_EVENTS.length).toBeGreaterThan(0);
    expect(MOCK_EXECUTION_EVENTS[0].event_type).toBeDefined();
  });
});
