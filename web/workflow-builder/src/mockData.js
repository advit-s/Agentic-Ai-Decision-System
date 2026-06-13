// mockData.js — Offline-safe mock data matching API response shapes

const MOCK_NODE_TYPES = [
  {
    type: "decision_system.trigger_manual",
    label: "Manual Trigger",
    description: "Start a workflow manually",
    icon: "⚡",
    color: "#3b82f6",
    categories: ["trigger"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: {} },
    output_schema: { type: "object", properties: { triggered: { type: "boolean" } } },
  },
  {
    type: "decision_system.input_text",
    label: "Input Text",
    description: "Provide text input for the workflow",
    icon: "✏️",
    color: "#14b8a6",
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
    icon: "🔍",
    color: "#f59e0b",
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
    icon: "🔧",
    color: "#8b5cf6",
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
    icon: "🛡️",
    color: "#a855f7",
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
    icon: "📌",
    color: "#7c3aed",
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
    icon: "✅",
    color: "#9333ea",
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
    icon: "📝",
    color: "#6d28d9",
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
    icon: "🕸️",
    color: "#d97706",
    categories: ["data"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { chunks: { type: "array" } } },
    output_schema: { type: "object", properties: { graph: { type: "object" } } },
  },
  {
    type: "decision_system.profile_data",
    label: "Profile Data",
    description: "Profile local CSV data files",
    icon: "📋",
    color: "#ea580c",
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
    icon: "🧩",
    color: "#7e22ce",
    categories: ["output"],
    config_schema: { type: "object", properties: {} },
    input_schema: { type: "object", properties: { profiles: { type: "array" } } },
    output_schema: { type: "object", properties: { ontology: { type: "object" } } },
  },
  {
    type: "decision_system.detect_patterns",
    label: "Detect Patterns",
    description: "Run pattern and vulnerability detection",
    icon: "🔮",
    color: "#a21caf",
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
    icon: "🏛️",
    color: "#6b21a8",
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
    icon: "🧪",
    color: "#6b7280",
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
    icon: "🔀",
    color: "#4b5563",
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
    icon: "💻",
    color: "#374151",
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
  // --- Phase 4: Schedule Trigger Nodes ---
  {
    type: "decision_system.trigger_cron",
    label: "Cron Trigger",
    description: "Trigger a workflow on a cron schedule",
    icon: "🕐",
    color: "#6366f1",
    categories: ["trigger"],
    config_schema: {
      type: "object",
      properties: {
        expression: {
          type: "string", title: "Cron Expression",
          default: "0 9 * * 1",
          description: "Five-field cron expression (minute hour day-of-month month day-of-week)",
        },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: {
      type: "object",
      properties: {
        triggered: { type: "boolean" },
        expression: { type: "string" },
        trigger_type: { type: "string" },
      },
    },
  },
  {
    type: "decision_system.trigger_webhook",
    label: "Webhook Trigger",
    description: "Trigger a workflow via an HTTP webhook",
    icon: "🔗",
    color: "#4f46e5",
    categories: ["trigger"],
    config_schema: {
      type: "object",
      properties: {
        webhook_path: {
          type: "string", title: "Webhook Path",
          default: "my-webhook",
          description: "Unique path for the webhook endpoint",
        },
      },
    },
    input_schema: { type: "object", properties: { payload: { type: "object" } } },
    output_schema: {
      type: "object",
      properties: {
        triggered: { type: "boolean" },
        webhook_path: { type: "string" },
      },
    },
  },
  {
    type: "decision_system.trigger_file_watch",
    label: "File Watch Trigger",
    description: "Trigger a workflow when new files appear in a directory",
    icon: "👁️",
    color: "#8b5cf6",
    categories: ["trigger"],
    config_schema: {
      type: "object",
      properties: {
        directory: { type: "string", title: "Directory", default: "/tmp/watch", description: "Directory to watch" },
        pattern: { type: "string", title: "File Pattern", default: "*.csv", description: "Glob pattern to match" },
      },
    },
    input_schema: { type: "object", properties: {} },
    output_schema: {
      type: "object",
      properties: {
        triggered: { type: "boolean" },
        directory: { type: "string" },
        pattern: { type: "string" },
        _changed_files: { type: "array" },
      },
    },
  },
  // --- Phase 6: Specialist Agent Nodes ---
  {
    type: "decision_system.researcher",
    label: "Researcher",
    description: "Retrieve and synthesize information from connected data sources",
    icon: "📚",
    color: "#8b5cf6",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake" },
        max_sources: { type: "integer", title: "Max Sources", default: 5, minimum: 1, maximum: 50 },
        depth: { type: "string", title: "Research Depth", default: "balanced", enum: ["quick", "balanced", "deep"] },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Research question or topic" },
        context: { type: "string", description: "Additional context" },
      },
      required: ["query"],
    },
    output_schema: {
      type: "object",
      properties: {
        findings: { type: "array" },
        summary: { type: "string" },
        gaps: { type: "array" },
        fallback_reason: { type: "string" },
      },
    },
  },
  {
    type: "decision_system.critic",
    label: "Critic / Judge",
    description: "Review outputs for contradictions, unsupported claims, and logical fallacies",
    icon: "⚖️",
    color: "#c026d3",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake" },
        criteria: {
          type: "array", title: "Review Criteria",
          items: { type: "string", enum: ["contradictions", "unsupported_claims", "logical_fallacies", "confidence_calibration"] },
          default: ["contradictions", "unsupported_claims"],
        },
        strictness: { type: "string", title: "Strictness", default: "balanced", enum: ["lenient", "balanced", "strict"] },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        target_type: { type: "string", enum: ["claims_list", "report_text", "findings_list"] },
        target_data: { type: "object", description: "Data to review" },
      },
      required: ["target_data"],
    },
    output_schema: {
      type: "object",
      properties: {
        passed: { type: "boolean" },
        issues: { type: "array" },
        summary: { type: "string" },
        confidence_adjustment: { type: "number" },
        fallback_reason: { type: "string" },
      },
    },
  },
  {
    type: "decision_system.synthesizer",
    label: "Decision Synthesizer",
    description: "Synthesize multiple evidence streams into weighted decisions",
    icon: "🎯",
    color: "#a855f7",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake" },
        decision_framework: {
          type: "string", title: "Decision Framework", default: "weighted_matrix",
          enum: ["pros_cons", "weighted_matrix", "tiered_recommendation"],
        },
        max_options: { type: "integer", title: "Max Options", default: 5, minimum: 2, maximum: 10 },
        include_risks: { type: "boolean", title: "Include Risk Assessments", default: true },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        question: { type: "string", description: "Decision question" },
        evidence_streams: { type: "array", description: "Evidence sources to synthesize" },
        criteria: { type: "array", description: "Decision criteria with weights" },
      },
      required: ["question"],
    },
    output_schema: {
      type: "object",
      properties: {
        options: { type: "array" },
        recommendation: { type: "object" },
        trade_offs_summary: { type: "string" },
        fallback_reason: { type: "string" },
      },
    },
  },
  // --- Phase 7: Data Analyst Node ---
  {
    type: "decision_system.data_analyst",
    label: "Data Analyst",
    description: "Analyze structured data — profiles, trends, anomalies, and correlations",
    icon: "📊",
    color: "#7c3aed",
    categories: ["ai"],
    config_schema: {
      type: "object",
      properties: {
        provider: { type: "string", title: "Provider", default: "fake" },
        analysis_type: {
          type: "string", title: "Analysis Type", default: "summary",
          enum: ["profile", "summary", "trend", "anomaly", "correlation"],
        },
        max_rows: { type: "integer", title: "Max Rows", default: 1000, minimum: 1, maximum: 100000 },
        include_charts: { type: "boolean", title: "Include Charts", default: false },
      },
    },
    input_schema: {
      type: "object",
      properties: {
        data: { type: "array", items: { type: "object" }, description: "Structured data to analyze" },
        analysis_type: { type: "string", description: "Override analysis type" },
        columns: { type: "array", items: { type: "string" }, description: "Focus on specific columns" },
      },
      required: ["data"],
    },
    output_schema: {
      type: "object",
      properties: {
        analysis: { type: "object" },
        summary: { type: "string" },
        charts: { type: "object" },
        fallback_reason: { type: "string" },
      },
    },
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

const MOCK_SCHEDULES = [
  {
    id: "sch-mock-001",
    workflow_id: "wf-sample-1",
    trigger_type: "cron",
    trigger_config: { expression: "0 9 * * 1", _node_id: "cron-1" },
    enabled: true,
    last_fired: null,
    created_at: "2026-06-12T00:00:00Z",
    updated_at: "2026-06-12T00:00:00Z",
  },
];

const MOCK_PROVIDERS = [
  {
    name: "opencode",
    api_base: "https://opencode.ai/zen/v1",
    api_key_configured: false,
    default_model: "claude-sonnet-4-20250514",
  },
  {
    name: "openai",
    api_base: "https://api.openai.com/v1",
    api_key_configured: false,
    default_model: "gpt-4o",
  },
];

export { MOCK_NODE_TYPES, MOCK_WORKFLOWS, MOCK_EXECUTION_STATE, MOCK_EXECUTION_EVENTS, MOCK_SCHEDULES, MOCK_PROVIDERS };
