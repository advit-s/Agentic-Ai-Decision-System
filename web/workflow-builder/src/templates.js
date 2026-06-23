// templates.js — Pre-built workflow template definitions
//
// Each template is a serialized workflow that can be loaded into the canvas.
// v1.22 templates are designed for the demo path with Evidence/AI/Verification flows.

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
    name: "Local Evidence Search",
    description: "Search local workspace evidence by keyword. No AI provider needed.",
    icon: "🔍",
    category: "evidence",
    nodes: [
      {
        id: "tpl-es-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-es-2", type: "decision_system.evidence_search",
        label: "Evidence Search", config: { query: "", limit: 5, workspace_id: "" },
        position_x: 280, position_y: 200,
      },
      {
        id: "tpl-es-3", type: "decision_system.verification_summary",
        label: "Verification Summary", config: {},
        position_x: 520, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-es-1", source_output: "default", target_node: "tpl-es-2", target_input: "default" },
      { source_node: "tpl-es-2", source_output: "default", target_node: "tpl-es-3", target_input: "default" },
    ],
  },
  {
    name: "Evidence → AI Synthesis → Verify",
    description: "Full pipeline: search evidence, synthesize with AI, verify claims, generate report.",
    icon: "🤖",
    category: "full",
    nodes: [
      {
        id: "tpl-ai-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-ai-2", type: "decision_system.evidence_search",
        label: "Search Evidence", config: { query: "", limit: 10, workspace_id: "" },
        position_x: 260, position_y: 200,
      },
      {
        id: "tpl-ai-3", type: "decision_system.evidence_synthesis",
        label: "Synthesize", config: { question: "", synthesis_mode: "summary", auto_verify: false },
        position_x: 500, position_y: 200,
      },
      {
        id: "tpl-ai-4", type: "decision_system.contradiction_scan",
        label: "Contradiction Scan", config: {},
        position_x: 740, position_y: 200,
      },
      {
        id: "tpl-ai-5", type: "decision_system.verify_claims",
        label: "Verify Claims", config: { workspace_id: "" },
        position_x: 980, position_y: 200,
      },
      {
        id: "tpl-ai-6", type: "decision_system.write_report",
        label: "Trust Report", config: { format: "markdown", include_evidence: true, include_contradictions: true },
        position_x: 1220, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-ai-1", source_output: "default", target_node: "tpl-ai-2", target_input: "default" },
      { source_node: "tpl-ai-2", source_output: "default", target_node: "tpl-ai-3", target_input: "default" },
      { source_node: "tpl-ai-3", source_output: "default", target_node: "tpl-ai-4", target_input: "default" },
      { source_node: "tpl-ai-4", source_output: "default", target_node: "tpl-ai-5", target_input: "default" },
      { source_node: "tpl-ai-5", source_output: "default", target_node: "tpl-ai-6", target_input: "default" },
    ],
  },
  {
    name: "Risk Review Workflow",
    description: "Search evidence, analyze risks, verify claims, and generate risk report.",
    icon: "🛡️",
    category: "compliance",
    nodes: [
      {
        id: "tpl-rr-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-rr-2", type: "decision_system.evidence_search",
        label: "Search Evidence", config: { query: "risk", limit: 10, workspace_id: "" },
        position_x: 260, position_y: 200,
      },
      {
        id: "tpl-rr-3", type: "decision_system.risk_analyst",
        label: "Risk Analyst", config: {},
        position_x: 500, position_y: 200,
      },
      {
        id: "tpl-rr-4", type: "decision_system.extract_claims",
        label: "Extract Claims", config: {},
        position_x: 740, position_y: 200,
      },
      {
        id: "tpl-rr-5", type: "decision_system.verify_claims",
        label: "Verify Claims", config: { workspace_id: "" },
        position_x: 980, position_y: 200,
      },
      {
        id: "tpl-rr-6", type: "decision_system.review_gate",
        label: "Review Gate", config: { instructions: "Review risk findings before report", risk_level: "medium" },
        position_x: 1220, position_y: 200,
      },
      {
        id: "tpl-rr-7", type: "decision_system.write_report",
        label: "Risk Report", config: { format: "markdown" },
        position_x: 1460, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-rr-1", source_output: "default", target_node: "tpl-rr-2", target_input: "default" },
      { source_node: "tpl-rr-2", source_output: "default", target_node: "tpl-rr-3", target_input: "default" },
      { source_node: "tpl-rr-3", source_output: "default", target_node: "tpl-rr-4", target_input: "default" },
      { source_node: "tpl-rr-4", source_output: "default", target_node: "tpl-rr-5", target_input: "default" },
      { source_node: "tpl-rr-5", source_output: "default", target_node: "tpl-rr-6", target_input: "default" },
      { source_node: "tpl-rr-6", source_output: "default", target_node: "tpl-rr-7", target_input: "default" },
    ],
  },
  {
    name: "Trust Report Generator",
    description: "Verify claims, scan contradictions, and generate a trust report with evidence.",
    icon: "📄",
    category: "report",
    nodes: [
      {
        id: "tpl-tr-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-tr-2", type: "decision_system.evidence_search",
        label: "Search Evidence", config: { query: "", limit: 10, workspace_id: "" },
        position_x: 260, position_y: 200,
      },
      {
        id: "tpl-tr-3", type: "decision_system.extract_claims",
        label: "Extract Claims", config: {},
        position_x: 500, position_y: 200,
      },
      {
        id: "tpl-tr-4", type: "decision_system.verify_claims",
        label: "Verify Claims", config: { workspace_id: "" },
        position_x: 740, position_y: 200,
      },
      {
        id: "tpl-tr-5", type: "decision_system.contradiction_scan",
        label: "Contradiction Scan", config: {},
        position_x: 980, position_y: 200,
      },
      {
        id: "tpl-tr-6", type: "decision_system.write_report",
        label: "Trust Report", config: { format: "markdown", include_evidence: true, include_contradictions: true },
        position_x: 1220, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-tr-1", source_output: "default", target_node: "tpl-tr-2", target_input: "default" },
      { source_node: "tpl-tr-2", source_output: "default", target_node: "tpl-tr-3", target_input: "default" },
      { source_node: "tpl-tr-3", source_output: "default", target_node: "tpl-tr-4", target_input: "default" },
      { source_node: "tpl-tr-4", source_output: "default", target_node: "tpl-tr-5", target_input: "default" },
      { source_node: "tpl-tr-5", source_output: "default", target_node: "tpl-tr-6", target_input: "default" },
    ],
  },
  {
    name: "Data Profile Summary",
    description: "Profile structured data, detect patterns, and generate a data quality report.",
    icon: "📊",
    category: "data",
    nodes: [
      {
        id: "tpl-dp-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
        position_x: 40, position_y: 200,
      },
      {
        id: "tpl-dp-2", type: "decision_system.input_text",
        label: "Query", config: { label: "Analysis question", text: "" },
        position_x: 40, position_y: 340,
      },
      {
        id: "tpl-dp-3", type: "decision_system.profile_data",
        label: "Profile Data", config: { max_rows: 1000 },
        position_x: 280, position_y: 200,
      },
      {
        id: "tpl-dp-4", type: "decision_system.detect_patterns",
        label: "Detect Patterns", config: {},
        position_x: 520, position_y: 200,
      },
      {
        id: "tpl-dp-5", type: "decision_system.verification_summary",
        label: "Summary", config: {},
        position_x: 760, position_y: 200,
      },
    ],
    connections: [
      { source_node: "tpl-dp-1", source_output: "default", target_node: "tpl-dp-3", target_input: "default" },
      { source_node: "tpl-dp-2", source_output: "default", target_node: "tpl-dp-3", target_input: "query" },
      { source_node: "tpl-dp-3", source_output: "default", target_node: "tpl-dp-4", target_input: "default" },
      { source_node: "tpl-dp-4", source_output: "default", target_node: "tpl-dp-5", target_input: "default" },
    ],
  },
  {
    name: "Research Pipeline",
    description: "Research question → retrieve evidence → analyze → synthesize → report",
    icon: "🔬",
    category: "research",
    nodes: [
      {
        id: "tpl-r-1", type: "decision_system.trigger_manual",
        label: "Start", config: {},
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
