// mockData.js — Offline-safe mock data matching API response shapes

const MOCK_NODE_TYPES = [
  {
    type: "decision_system.trigger_manual",
    label: "Manual Trigger",
    description: "Start a workflow manually",
    categories: ["trigger"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { triggered: { type: "boolean" } } },
  },
  {
    type: "decision_system.input_text",
    label: "Input Text",
    description: "Provide text input for the workflow",
    categories: ["trigger"],
    config_schema: {
      type: "object",
      properties: {
        text: { type: "string", title: "Text", default: "" },
        label: { type: "string", title: "Label", default: "Enter text" },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { text: { type: "string" } } },
  },
  {
    type: "decision_system.retrieve",
    label: "Retrieve Evidence",
    description: "Retrieve documents from the vector store",
    categories: ["data"],
    config_schema: {
      type: "object",
      properties: {
        collection: { type: "string", title: "Collection", default: "company_docs" },
        top_k: { type: "integer", title: "Top K", default: 5 },
      },
    },
    input_schema: { type: "object", properties: { query: { type: "string" } } },
    output_schema: { type: "object", properties: { chunks: { type: "array" } } },
  },
  {
    type: "decision_system.technical_analyst",
    label: "Technical Analyst",
    description: "Analyze technical data and system information",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { analysis: { type: "object" } } },
  },
  {
    type: "decision_system.risk_analyst",
    label: "Risk Analyst",
    description: "Analyze risks and vulnerabilities",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { risks: { type: "array" } } },
  },
  {
    type: "decision_system.extract_claims",
    label: "Extract Claims",
    description: "Extract claims from analysis output",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        supported_types: { type: "array", title: "Supported Types", items: { type: "string" } },
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { text: { type: "string" } } },
    output_schema: { type: "object", properties: { claims: { type: "array" } } },
  },
  {
    type: "decision_system.verify_claims",
    label: "Verify Claims",
    description: "Verify extracted claims against evidence",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { claims: { type: "array" } } },
    output_schema: { type: "object", properties: { verified: { type: "array" } } },
  },
  {
    type: "decision_system.write_report",
    label: "Write Report",
    description: "Generate a decision report from verified claims",
    categories: ["output"],
    config_schema: {
      type: "object",
      properties: {
        format: { type: "string", title: "Format", default: "markdown", enum: ["markdown", "json"] },
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { claims: { type: "array" } } },
    output_schema: { type: "object", properties: { report: { type: "object" } } },
  },
  {
    type: "decision_system.extract_graph",
    label: "Extract Graph",
    description: "Extract entities and relationships from documents",
    categories: ["data"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { chunks: { type: "array" } } },
    output_schema: { type: "object", properties: { graph: { type: "object" } } },
  },
  {
    type: "decision_system.profile_data",
    label: "Profile Data",
    description: "Profile local CSV data files",
    categories: ["data"],
    config_schema: {
      type: "object",
      properties: {
        catalog_path: { type: "string", title: "Catalog Path", default: "company_data" },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { profiles: { type: "array" } } },
  },
  {
    type: "decision_system.map_ontology",
    label: "Map Ontology",
    description: "Map data profiles to ontology concepts",
    categories: ["output"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { profiles: { type: "array" } } },
    output_schema: { type: "object", properties: { ontology: { type: "object" } } },
  },
  {
    type: "decision_system.detect_patterns",
    label: "Detect Patterns",
    description: "Run pattern and vulnerability detection",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        severity_threshold: {
          type: "string", title: "Severity Threshold", default: "low",
          enum: ["low", "medium", "high", "critical"],
        },
      },
    },
    input_schema: { type: "object", properties: { profiles: { type: "array" } } },
    output_schema: { type: "object", properties: { insights: { type: "array" } } },
  },
  {
    type: "decision_system.war_room",
    label: "Run War Room",
    description: "Run the multi-role analysis protocol",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        question: { type: "string", title: "Question", description: "Business question", default: "" },
        provider: { type: "string", title: "Provider", default: "fake", enum: ["fake", "nvidia_nim", "ollama"] },
      },
    },
    input_schema: { type: "object", properties: { question: { type: "string" } } },
    output_schema: { type: "object", properties: { war_room_run: { type: "object" } } },
  },
  {
    type: "decision_system.filter",
    label: "Filter",
    description: "Filter data based on conditions",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        field: { type: "string", title: "Field to check", default: "" },
        operator: {
          type: "string", title: "Operator", default: "exists",
          enum: ["exists", "equals", "not_equals", "greater_than", "less_than"],
        },
        value: { type: "string", title: "Value", default: "" },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "array" } } },
    output_schema: { type: "object", properties: { filtered: { type: "array" } } },
  },
  {
    type: "decision_system.merge",
    label: "Merge",
    description: "Merge multiple data sources",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        strategy: {
          type: "string", title: "Strategy", default: "merge",
          enum: ["merge", "concat"],
        },
      },
    },
    input_schema: { type: "object", properties: { sources: { type: "array" } } },
    output_schema: { type: "object", properties: { merged: { type: "object" } } },
  },
  {
    type: "decision_system.code",
    label: "Code",
    description: "Execute a Python snippet",
    categories: ["flow"],
    config_schema: {
      type: "object",
      properties: {
        source: { type: "string", title: "Python Code", default: "# output = ...", format: "textarea" },
      },
    },
    input_schema: { type: "object", properties: { data: { type: "object" } } },
    output_schema: { type: "object", properties: { result: { type: "object" } } },
  },
];

const MOCK_WORKFLOWS = [
  {
    id: "wf-sample-1",
    name: "Quarterly Risk Review",
    description: "Analyze company data and generate a risk report",
    nodes: [
      { id: "node-1", type: "decision_system.trigger_manual", label: "Start", config: {}, error_policy: "fail_workflow" },
      { id: "node-2", type: "decision_system.input_text", label: "Business Question", config: { text: "Where are we losing money?" }, error_policy: "fail_workflow" },
      { id: "node-3", type: "decision_system.retrieve", label: "Retrieve Evidence", config: { collection: "company_docs", top_k: 5 }, error_policy: "fail_workflow" },
      { id: "node-4", type: "decision_system.technical_analyst", label: "Tech Analysis", config: { provider: "fake" }, error_policy: "fail_workflow" },
      { id: "node-5", type: "decision_system.risk_analyst", label: "Risk Analysis", config: { provider: "fake" }, error_policy: "fail_workflow" },
      { id: "node-6", type: "decision_system.extract_claims", label: "Extract Claims", config: { provider: "fake" }, error_policy: "fail_workflow" },
      { id: "node-7", type: "decision_system.write_report", label: "Generate Report", config: { format: "markdown", provider: "fake" }, error_policy: "fail_workflow" },
    ],
    connections: [
      { source_node: "node-1", source_output: "default", target_node: "node-2", target_input: "default" },
      { source_node: "node-2", source_output: "default", target_node: "node-3", target_input: "default" },
      { source_node: "node-3", source_output: "default", target_node: "node-4", target_input: "default" },
      { source_node: "node-3", source_output: "default", target_node: "node-5", target_input: "default" },
      { source_node: "node-4", source_output: "default", target_node: "node-6", target_input: "default" },
      { source_node: "node-5", source_output: "default", target_node: "node-6", target_input: "default" },
      { source_node: "node-6", source_output: "default", target_node: "node-7", target_input: "default" },
    ],
    created_at: "2026-06-12T00:00:00Z",
    updated_at: "2026-06-12T00:00:00Z",
  },
];

const MOCK_EXECUTION_STATE = {
  execution_id: "exec-mock-1",
  workflow_id: "wf-sample-1",
  status: "running",
  node_states: {},
  started_at: "2026-06-12T00:00:00Z",
  completed_at: null,
  error: null,
};

const MOCK_EXECUTION_EVENTS = [
  { event_type: "node_started", node_id: "node-1", data: { node_type: "decision_system.trigger_manual" } },
  { event_type: "node_completed", node_id: "node-1", data: { outputs: { triggered: true } } },
  { event_type: "node_started", node_id: "node-2", data: { node_type: "decision_system.input_text" } },
  { event_type: "node_completed", node_id: "node-2", data: { outputs: { text: "Where are we losing money?" } } },
  { event_type: "node_started", node_id: "node-3", data: { node_type: "decision_system.retrieve" } },
  { event_type: "node_completed", node_id: "node-3", data: { outputs: { chunks: [] } } },
  { event_type: "node_started", node_id: "node-4", data: { node_type: "decision_system.technical_analyst" } },
  { event_type: "node_completed", node_id: "node-4", data: { outputs: { analysis: { summary: "Mock analysis" } } } },
  { event_type: "node_started", node_id: "node-5", data: { node_type: "decision_system.risk_analyst" } },
  { event_type: "node_completed", node_id: "node-5", data: { outputs: { risks: [] } } },
  { event_type: "workflow_completed", node_id: null, data: { status: "completed" } },
];

export { MOCK_NODE_TYPES, MOCK_WORKFLOWS, MOCK_EXECUTION_STATE, MOCK_EXECUTION_EVENTS };
