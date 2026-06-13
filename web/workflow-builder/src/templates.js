// templates.js — Pre-built workflow template definitions
//
// Each template is a serialized workflow that can be loaded into the canvas.
// Nodes use stable template IDs and are remapped to fresh IDs on load.

const TEMPLATES = [
  {
    name: "Blank Canvas",
    description: "Start from scratch with an empty workflow",
    icon: "⬜",
    category: "starter",
    nodes: [],
    connections: [],
  },
  {
    name: "Research Pipeline",
    description: "Research question → retrieve evidence → analyze → synthesize → report",
    icon: "🔬",
    category: "research",
    nodes: [
      {
        id: "tpl-r-1", type: "decision_system.trigger_manual",
        label: "Start Research", config: {},
        position_x: 40, position_y: 160,
      },
      {
        id: "tpl-r-2", type: "decision_system.researcher",
        label: "Researcher", config: { max_sources: 5, depth: "balanced" },
        position_x: 280, position_y: 160,
      },
      {
        id: "tpl-r-3", type: "decision_system.critic",
        label: "Critic", config: { criteria: ["contradictions", "unsupported_claims"], strictness: "balanced" },
        position_x: 520, position_y: 160,
      },
      {
        id: "tpl-r-4", type: "decision_system.synthesizer",
        label: "Synthesizer", config: { decision_framework: "weighted_matrix", max_options: 3 },
        position_x: 760, position_y: 160,
      },
      {
        id: "tpl-r-5", type: "decision_system.write_report",
        label: "Write Report", config: { format: "markdown" },
        position_x: 1000, position_y: 160,
      },
    ],
    connections: [
      { source_node: "tpl-r-1", source_output: "default", target_node: "tpl-r-2", target_input: "default" },
      { source_node: "tpl-r-2", source_output: "default", target_node: "tpl-r-3", target_input: "default" },
      { source_node: "tpl-r-3", source_output: "default", target_node: "tpl-r-4", target_input: "default" },
      { source_node: "tpl-r-4", source_output: "default", target_node: "tpl-r-5", target_input: "default" },
    ],
  },
  {
    name: "Data Analysis",
    description: "Ingest structured data → profile → detect patterns → report",
    icon: "📊",
    category: "data",
    nodes: [
      {
        id: "tpl-d-1", type: "decision_system.trigger_manual",
        label: "Start Analysis", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-d-2", type: "decision_system.input_text",
        label: "Query", config: { label: "Analysis question" },
        position_x: 40, position_y: 340,
      },
      {
        id: "tpl-d-3", type: "decision_system.retrieve",
        label: "Retrieve Evidence", config: { top_k: 5 },
        position_x: 280, position_y: 200,
      },
      {
        id: "tpl-d-4", type: "decision_system.data_analyst",
        label: "Data Analyst", config: { analysis_type: "summary", max_rows: 1000 },
        position_x: 520, position_y: 200,
      },
      {
        id: "tpl-d-5", type: "decision_system.write_report",
        label: "Report", config: { format: "markdown" },
        position_x: 760, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-d-1", source_output: "default", target_node: "tpl-d-3", target_input: "default" },
      { source_node: "tpl-d-2", source_output: "default", target_node: "tpl-d-3", target_input: "query" },
      { source_node: "tpl-d-3", source_output: "default", target_node: "tpl-d-4", target_input: "default" },
      { source_node: "tpl-d-4", source_output: "default", target_node: "tpl-d-5", target_input: "default" },
    ],
  },
  {
    name: "Compliance Audit",
    description: "Full compliance review: retrieve → analyze risks → extract claims → verify → human gate → report",
    icon: "🛡️",
    category: "compliance",
    nodes: [
      {
        id: "tpl-c-1", type: "decision_system.trigger_manual",
        label: "Start Audit", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-c-2", type: "decision_system.technical_analyst",
        label: "Technical Analyst", config: {},
        position_x: 280, position_y: 120,
      },
      {
        id: "tpl-c-3", type: "decision_system.risk_analyst",
        label: "Risk Analyst", config: {},
        position_x: 280, position_y: 320,
      },
      {
        id: "tpl-c-4", type: "decision_system.extract_claims",
        label: "Extract Claims", config: {},
        position_x: 520, position_y: 220,
      },
      {
        id: "tpl-c-5", type: "decision_system.verify_claims",
        label: "Verify Claims", config: {},
        position_x: 760, position_y: 220,
      },
      {
        id: "tpl-c-6", type: "decision_system.review_gate",
        label: "Human Review", config: { require_notes: true, allow_edit: true },
        position_x: 1000, position_y: 220,
      },
      {
        id: "tpl-c-7", type: "decision_system.write_report",
        label: "Audit Report", config: { format: "markdown" },
        position_x: 1240, position_y: 220,
      },
    ],
    connections: [
      { source_node: "tpl-c-1", source_output: "default", target_node: "tpl-c-2", target_input: "default" },
      { source_node: "tpl-c-1", source_output: "default", target_node: "tpl-c-3", target_input: "default" },
      { source_node: "tpl-c-2", source_output: "default", target_node: "tpl-c-4", target_input: "default" },
      { source_node: "tpl-c-3", source_output: "default", target_node: "tpl-c-4", target_input: "default" },
      { source_node: "tpl-c-4", source_output: "default", target_node: "tpl-c-5", target_input: "default" },
      { source_node: "tpl-c-5", source_output: "default", target_node: "tpl-c-6", target_input: "default" },
      { source_node: "tpl-c-6", source_output: "default", target_node: "tpl-c-7", target_input: "default" },
    ],
  },
  {
    name: "Full Decision Pipeline",
    description: "End-to-end: trigger → research → critique → synthesize → verify → gate → war room → report",
    icon: "🏛️",
    category: "full",
    nodes: [
      {
        id: "tpl-f-1", type: "decision_system.trigger_manual",
        label: "Trigger", config: {},
        position_x: 40, position_y: 300,
      },
      {
        id: "tpl-f-2", type: "decision_system.researcher",
        label: "Researcher", config: { max_sources: 5, depth: "deep" },
        position_x: 260, position_y: 120,
      },
      {
        id: "tpl-f-3", type: "decision_system.retrieve",
        label: "Retrieve", config: { top_k: 10 },
        position_x: 260, position_y: 320,
      },
      {
        id: "tpl-f-4", type: "decision_system.data_analyst",
        label: "Data Analyst", config: { analysis_type: "profile" },
        position_x: 260, position_y: 500,
      },
      {
        id: "tpl-f-5", type: "decision_system.critic",
        label: "Critic", config: { criteria: ["contradictions", "unsupported_claims", "logical_fallacies"], strictness: "strict" },
        position_x: 500, position_y: 200,
      },
      {
        id: "tpl-f-6", type: "decision_system.synthesizer",
        label: "Synthesizer", config: { decision_framework: "tiered_recommendation", include_risks: true },
        position_x: 740, position_y: 200,
      },
      {
        id: "tpl-f-7", type: "decision_system.verify_claims",
        label: "Verify Claims", config: {},
        position_x: 980, position_y: 120,
      },
      {
        id: "tpl-f-8", type: "decision_system.war_room",
        label: "War Room", config: { question: "" },
        position_x: 980, position_y: 340,
      },
      {
        id: "tpl-f-9", type: "decision_system.review_gate",
        label: "Review Gate", config: { require_notes: true },
        position_x: 1220, position_y: 240,
      },
      {
        id: "tpl-f-10", type: "decision_system.write_report",
        label: "Report", config: { format: "markdown" },
        position_x: 1460, position_y: 240,
      },
    ],
    connections: [
      { source_node: "tpl-f-1", source_output: "default", target_node: "tpl-f-2", target_input: "default" },
      { source_node: "tpl-f-1", source_output: "default", target_node: "tpl-f-3", target_input: "default" },
      { source_node: "tpl-f-1", source_output: "default", target_node: "tpl-f-4", target_input: "default" },
      { source_node: "tpl-f-2", source_output: "default", target_node: "tpl-f-5", target_input: "default" },
      { source_node: "tpl-f-3", source_output: "default", target_node: "tpl-f-5", target_input: "default" },
      { source_node: "tpl-f-4", source_output: "default", target_node: "tpl-f-5", target_input: "default" },
      { source_node: "tpl-f-5", source_output: "default", target_node: "tpl-f-6", target_input: "default" },
      { source_node: "tpl-f-6", source_output: "default", target_node: "tpl-f-7", target_input: "default" },
      { source_node: "tpl-f-6", source_output: "default", target_node: "tpl-f-8", target_input: "default" },
      { source_node: "tpl-f-7", source_output: "default", target_node: "tpl-f-9", target_input: "default" },
      { source_node: "tpl-f-8", source_output: "default", target_node: "tpl-f-9", target_input: "default" },
      { source_node: "tpl-f-9", source_output: "default", target_node: "tpl-f-10", target_input: "default" },
    ],
  },
];

export default TEMPLATES;
