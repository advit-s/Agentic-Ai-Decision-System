// __tests__/api.test.js
import { describe, it, expect, beforeEach } from "vitest";
import {
  fetchNodeTypes,
  listWorkflows,
  getWorkflow,
  saveWorkflow,
  deleteWorkflow,
  executeWorkflow,
  getExecution,
  isMockMode,
} from "../src/api";

describe("api client (mock mode)", () => {
  beforeEach(() => {
    localStorage.removeItem("wfBuilderApiBaseUrl");
  });

  it("is in mock mode when no base URL configured", () => {
    expect(isMockMode()).toBe(true);
  });

  it("fetches node types", async () => {
    const types = await fetchNodeTypes();
    expect(types.length).toBe(28);
    const typeNames = types.map((t) => t.type);
    expect(typeNames).toContain("decision_system.planner");
    expect(typeNames).toContain("decision_system.auditor");
    expect(typeNames).toContain("decision_system.compliance_checker");
    expect(typeNames).toContain("decision_system.code_runner");
  });

  it("lists workflows", async () => {
    const list = await listWorkflows();
    expect(Array.isArray(list)).toBe(true);
  });

  it("gets a specific workflow by id", async () => {
    const list = await listWorkflows();
    const wf = await getWorkflow(list[0].id);
    expect(wf.name).toBeDefined();
    expect(wf.nodes).toBeDefined();
    expect(wf.connections).toBeDefined();
  });

  it("saves a new workflow", async () => {
    const wf = {
      id: "wf-test-1",
      name: "Test Workflow",
      description: "A test",
      nodes: [],
      connections: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    const saved = await saveWorkflow(wf);
    expect(saved.id).toBe("wf-test-1");

    const list = await listWorkflows();
    expect(list.find((w) => w.id === "wf-test-1")).toBeDefined();
  });

  it("deletes a workflow", async () => {
    const result = await deleteWorkflow("wf-test-1");
    expect(result.success).toBe(true);
  });

  it("executes a workflow", async () => {
    const state = await executeWorkflow("wf-sample-1");
    expect(state.execution_id).toBeDefined();
    expect(state.status).toBe("running");
  });

  it("gets execution state", async () => {
    const state = await getExecution("exec-mock-1");
    expect(state.status).toBe("completed");
  });
});
