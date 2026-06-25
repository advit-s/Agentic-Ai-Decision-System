# Phase 6: Bounded Specialist Agent Nodes — Design Spec

> **Status:** Draft for review
> **Version:** 1.0
> **Date:** 2026-06-13
> **Applies to:** Agentic Decision System v1.12.0

---

## 1. Goal

Add 3 new drag-and-drop AI-powered node types to the workflow builder — **Researcher**, **Critic/Judge**, and **Decision Synthesizer** — that use the LLM provider system (Phase 5) for real AI-powered analysis, with structured I/O schemas, verification rules, and deterministic fallback to fake when no provider is configured.

These nodes extend the workflow engine from a linear pipeline of basic analyst nodes into a composable war-cabinet architecture where information is retrieved, validated, and synthesized into weighted decisions.

---

## 2. Architecture Overview

### 2.1 Common Node Pattern

All 3 nodes follow the established `WorkflowNode` protocol:

```
WorkflowNode subclass
  ├── get_config_schema()  → JSON Schema        (rendered in ConfigPanel)
  ├── get_input_schema()   → JSON Schema        (connection validation)
  ├── get_output_schema()  → JSON Schema        (downstream contracts)
  └── execute(ctx: ExecutionContext) → dict
        ├── ctx.resolve_provider() → LLMClient or None
        │     └── LLMClient → calls chat_completion with structured JSON prompt
        │     └── None → calls deterministic fake fallback
        └── returns typed output matching output schema
```

### 2.2 Integration Points

| Component | Integration |
|-----------|-------------|
| **Node registry** | All 3 registered via `create_default_registry()` alongside existing 24+ node types |
| **DAG engine** | No changes needed — they are regular nodes in the DAG; execute() receives ExecutionContext |
| **Provider system** | `ctx.resolve_provider()` already wired from Phase 5; nodes call `LLMClient.chat_completion()` |
| **Fake fallback** | Fake outputs match same schema as LLM outputs — downstream nodes are provider-agnostic |
| **Frontend** | Each gets a Card.jsx component + ConfigPanel entry, same pattern as existing nodes |
| **WebSocket events** | Stream `node_start` / `node_complete` / `node_error` events via existing stream system |
| **Claim ledger** | Critic reads ledger for cross-referencing; Researcher and Synthesizer read for context |

### 2.3 Provider Resolution

```
per-node config override? → yes → use that provider
     ↓ no
system default provider?  → yes → use that provider
     ↓ no
use fake fallback (deterministic mock data)
```

### 2.4 Error Handling Pattern (common)

| Scenario | Behavior |
|----------|----------|
| LLM provider returns 429/rate-limit | Retry once with 1s backoff; if still fails, fall back to fake, include `"fallback_reason": "rate_limited"` |
| LLM provider returns 401/unauthorized | No retry; fall back to fake with `"fallback_reason": "auth_error"` |
| LLM provider returns 404/model-not-found | Fall back to fake with `"fallback_reason": "model_not_found"` |
| LLM provider timeout (>30s) | Fall back to fake with `"fallback_reason": "timeout"` |
| Fake provider (explicit or default) | Return deterministic output matching schema |
| Empty/null required input | Return error-shaped output matching schema with `"error": "description"` |

---

## 3. Node: Researcher

**Category:** `ai_analysis`
**Color:** Blue (#3B82F6)
**Icon:** Magnifying glass

### 3.1 Purpose

Retrieves and synthesizes information from connected data sources (Chroma vector store, knowledge graph, or SSE stream call results). Produces structured findings with citations and confidence scores.

### 3.2 Schema

**Config schema:**
```json
{
  "max_sources":    {"type": "integer", "default": 5, "minimum": 1, "maximum": 50},
  "depth":          {"type": "string", "enum": ["quick", "balanced", "deep"], "default": "balanced"},
  "include_graph":  {"type": "boolean", "default": false},
  "source_filter":  {"type": "string", "default": "all", "enum": ["all", "documents", "graph", "data_profiles"]}
}
```

**Input schema:**
```json
{
  "query":               {"type": "string", "description": "Research question or topic"},
  "context":             {"type": "string", "default": "", "description": "Additional context for the query"},
  "source_references":   {"type": "array", "items": {"type": "string"}, "default": [], "description": "Specific document IDs or source labels to constrain search"}
}
```

**Output schema:**
```json
{
  "findings": [
    {
      "statement":   {"type": "string"},
      "citation":    {"type": "string"},
      "confidence":  {"type": "number", "minimum": 0, "maximum": 1},
      "source_type": {"type": "string", "enum": ["document", "graph", "data_profile", "web"]}
    }
  ],
  "summary":      {"type": "string"},
  "gaps":         {"type": "array", "items": {"type": "string"}},
  "fallback_reason": {"type": "string", "default": ""}
}
```

### 3.3 Execution Flow

```
execute(ctx)
  │
  ├─ 1. Parse query + config from execution state
  │
  ├─ 2. If depth=deep, expand query into 2-3 sub-queries via LLM
  │     (fake: use query as-is, no expansion)
  │
  ├─ 3. Retrieve from available sources:
  │     ├── Chroma vector store (if indexed documents exist)
  │     ├── Knowledge graph (if include_graph is true)
  │     └── passed-in source_references
  │
  ├─ 4. Resolve provider via ctx.resolve_provider()
  │     ├── LLMClient available → synthesize findings with citations
  │     └── No provider → deterministic fake findings based on query keywords
  │
  └─ 5. Return structured output matching schema
```

### 3.4 LLM Prompt

**System prompt (structured):**
```
You are a Research Analyst in a workflow automation system.
Given the query "{query}" and the following evidence:

{evidence_snippets}

Produce structured findings as JSON. Each finding must cite its source.
Flag information gaps in the "gaps" array. Assign confidence scores
based on evidence quality.
```

**Response format target:**
The LLM is instructed to return pure JSON matching the output schema. The response is validated and parsed; if it fails, the node falls back to fake.

### 3.5 Fake Fallback

When no provider is available, the Researcher returns deterministic findings based on keyword matching against the query string from a built-in mock dataset (e.g., queries containing "revenue" → mock financial findings, "risk" → mock risk findings). This ensures workflows that don't need real analysis still produce valid output for testing and development.

---

## 4. Node: Critic/Judge

**Category:** `ai_analysis`
**Color:** Amber (#F59E0B)
**Icon:** Shield with checkmark

### 4.1 Purpose

Reviews outputs from other nodes — checks for contradictions, unsupported claims, logical fallacies, and confidence calibration. Acts as the quality gate the product vision demands.

### 4.2 Schema

**Config schema:**
```json
{
  "criteria": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": ["contradictions", "unsupported_claims", "logical_fallacies", "confidence_calibration"]
    },
    "default": ["contradictions", "unsupported_claims"]
  },
  "strictness": {"type": "string", "enum": ["lenient", "balanced", "strict"], "default": "balanced"},
  "max_issues": {"type": "integer", "default": 20, "minimum": 1, "maximum": 100}
}
```

**Input schema:**
```json
{
  "target_type": {
    "type": "string",
    "enum": ["claims_list", "report_text", "findings_list"]
  },
  "target_data": {
    "type": "object",
    "description": "Accepts a list of claims { statements, confidence, evidence }, a report object { sections, claims }, or findings from Researcher"
  },
  "context": {"type": "string", "default": ""}
}
```

**Output schema:**
```json
{
  "passed": {"type": "boolean"},
  "issues": [
    {
      "type":        {"type": "string", "enum": ["contradiction", "unsupported", "logical_fallacy", "misconfidence"]},
      "severity":    {"type": "string", "enum": ["low", "medium", "high"]},
      "location":    {"type": "string"},
      "description": {"type": "string"},
      "suggestion":  {"type": "string"}
    }
  ],
  "summary":              {"type": "string"},
  "confidence_adjustment": {"type": "number", "description": "Negative value: reduce downstream confidence"},
  "fallback_reason": {"type": "string", "default": ""}
}
```

### 4.3 Execution Flow

```
execute(ctx)
  │
  ├─ 1. Normalize target_data into internal representation
  │     ├── claims_list → extract statements + evidence
  │     ├── report_text → extract embedded claims
  │     └── findings_list → normalize to claim-like structure
  │
  ├─ 2. For each enabled criterion, run the check:
  │     ├── contradictions → pairwise comparison of claims
  │     ├── unsupported_claims → cross-ref against evidence
  │     ├── logical_fallacies → pattern matching in reasoning
  │     └── confidence_calibration → flag thin high-confidence claims
  │
  ├─ 3. Resolve provider via ctx.resolve_provider()
  │     ├── LLMClient → deep semantic analysis with nuanced flagging
  │     └── No provider → deterministic rule-based checks
  │
  ├─ 4. Determine passed = true if zero issues at severity ≥ medium
  │
  └─ 5. Return structured output
```

### 4.4 Deterministic Check Rules (fake fallback)

| Criterion | Deterministic Behavior |
|-----------|----------------------|
| **Contradictions** | String-level: flag pairs of claims where one contains negations of the other's keywords (e.g., "revenue increased" vs "revenue decreased") |
| **Unsupported claims** | Flag claims where `evidence` array is empty or contains only empty strings |
| **Logical fallacies** | Pattern-match for trigger phrases ("everyone knows", "clearly", "obviously") |
| **Confidence calibration** | Flag claims with `confidence > 0.8` and zero or thin evidence |

### 4.5 Edge Cases

| Scenario | Behavior |
|----------|----------|
| Empty input | `{passed: true, issues: [], summary: "Nothing to review"}` |
| All claims verified | Still runs logical_fallacies if enabled |
| Report with no claims | Focuses on logical flow and evidence references |
| Max issues hit | Truncate issues list, note in summary: "Found N+ issues, showing first 20" |

### 4.6 Integration with Claim Ledger

- Reads existing claims from ledger for cross-referencing context
- Does NOT write directly to ledger — outputs are consumed by downstream nodes or human review
- Complements existing verifier: the verifier checks claim-vs-evidence match; the Judge checks everything else (logic, confidence calibration, contradictions across claims)

---

## 5. Node: Decision Synthesizer

**Category:** `ai_analysis`
**Color:** Purple (#8B5CF6)
**Icon:** Scale / balance

### 5.1 Purpose

Takes multiple evidence/analysis streams (research findings, data analysis, prior claims) and synthesizes them into weighted decision options with trade-off analysis and a recommended course of action.

### 5.2 Schema

**Config schema:**
```json
{
  "decision_framework": {
    "type": "string",
    "enum": ["pros_cons", "weighted_matrix", "tiered_recommendation"],
    "default": "weighted_matrix"
  },
  "max_options":  {"type": "integer", "default": 5, "minimum": 2, "maximum": 10},
  "include_risks": {"type": "boolean", "default": true}
}
```

**Input schema:**
```json
{
  "question": {"type": "string"},
  "evidence_streams": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "source_label": {"type": "string"},
        "content":      {"type": "object"}
      }
    },
    "minItems": 1
  },
  "criteria": {
    "type": "array",
    "items": {
      "type": "object",
      "properties": {
        "name":   {"type": "string"},
        "weight": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "default": [
      {"name": "feasibility", "weight": 0.3},
      {"name": "impact",      "weight": 0.3},
      {"name": "cost",        "weight": 0.2},
      {"name": "risk",        "weight": 0.2}
    ]
  }
}
```

The `evidence_streams` array lets multiple upstream nodes feed in — for example, a Researcher (findings) + Critic/Judge (validated issues) side by side.

**Output schema:**
```json
{
  "options": [
    {
      "title":           {"type": "string"},
      "description":     {"type": "string"},
      "pros":            {"type": "array", "items": {"type": "string"}},
      "cons":            {"type": "array", "items": {"type": "string"}},
      "confidence":      {"type": "number", "minimum": 0, "maximum": 1},
      "criteria_scores": {"type": "object"},
      "risks": [
        {
          "risk":        {"type": "string"},
          "likelihood":  {"type": "string", "enum": ["low", "medium", "high"]},
          "mitigation":  {"type": "string"}
        }
      ]
    }
  ],
  "recommendation": {
    "title":              {"type": "string"},
    "rationale":          {"type": "string"},
    "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1}
  },
  "trade_offs_summary": {"type": "string"},
  "fallback_reason": {"type": "string", "default": ""}
}
```

### 5.3 Execution Flow

```
execute(ctx)
  │
  ├─ 1. Parse question + criteria from input
  │
  ├─ 2. Normalize each evidence_stream into unified context
  │
  ├─ 3. Generate candidate options:
  │     ├── LLM available → analyze evidence, generate distinct options scored against criteria
  │     └── No provider → 3 deterministic options with rule-based pros/cons
  │
  ├─ 4. If include_risks, generate risk assessments per option
  │
  ├─ 5. Score each option against criteria, compute weighted totals
  │
  ├─ 6. Select recommendation = highest weighted score
  │
  └─ 7. Return structured output
```

### 5.4 DAG Composition Examples

**Linear pipeline (existing pattern):**
```
Trigger → Researcher → Critic/Judge → Output
```

**Multi-stream synthesis:**
```
Trigger → Researcher ─┐
         Data Analyst ─┤→ Decision Synthesizer → Critic/Judge → Output
                      └→ Extract Claims ────────┘
```

**Validation gate:**
```
Trigger → Researcher → Decision Synthesizer → Critic/Judge → Conditional
                                                              ├── passed → Output
                                                              └── failed → Loop back to refine
```

### 5.5 Error Handling

| Scenario | Behavior |
|----------|----------|
| No evidence streams | Single option based on question alone, confidence 0.2 |
| Single evidence stream | Works fine, lower cross-stream synthesis value |
| Conflicting evidence | Flag conflicts in trade_offs_summary, lower confidence |
| All criteria weights sum to zero | Equal weighting, flag in trade_offs_summary |
| LLM timeout | Fall back to fake with `overall_confidence: 0.1` |

---

## 6. Frontend Changes

### 6.1 New Components

| File | Purpose |
|------|---------|
| `src/components/nodes/ResearcherCard.jsx` | Card with config form, source selector, depth toggle |
| `src/components/nodes/CriticCard.jsx` | Card with criteria checkboxes, strictness slider |
| `src/components/nodes/SynthesizerCard.jsx` | Card with framework selector, criteria weight editor |
| `src/styles/node-cards.css` | Styles for the 3 new card types (follow Catppuccin theme) |

### 6.2 Card.jsx Pattern

Each card follows the existing node-card pattern:
- Header with node name, type badge ("AI Analysis"), color strip
- Expandable config form with labeled fields
- Connection ports (1 input, 1 output for Researcher; 1 input, 1 output for Critic; 1+ input, 1 output for Synthesizer)
- Execution status indicator (idle/running/done/error)

### 6.3 Node Registry Update

Add 3 entries to the node type palette in `App.jsx` under the "AI Analysis" category, alongside existing TechAnalyst/RiskAnalyst nodes.

---

## 7. Testing Plan

### 7.1 Unit Tests (per node)

| Test | Researcher | Critic | Synthesizer |
|------|:---:|:---:|:---:|
| Fake fallback returns valid schema | ✅ | ✅ | ✅ |
| LLM path with mock provider returns valid schema | ✅ | ✅ | ✅ |
| Empty input handled gracefully | ✅ | ✅ | ✅ |
| Config defaults applied correctly | ✅ | ✅ | ✅ |
| Error paths produce fallback with reason | ✅ | ✅ | ✅ |
| Output schema matches contract | ✅ | ✅ | ✅ |

### 7.2 Integration Tests

- **Node chaining:** Researcher → Critic/Judge (feed output to input)
- **Multi-stream:** Researcher + ExtractClaims → Synthesizer
- **Validation gate:** Synthesizer → Critic → Conditional (test both pass/fail paths)
- **Provider resolution:** Per-node override works, system default works, fake fallback works

### 7.3 Frontend Tests

- Each card renders config form from schema
- Config form binds correctly to node state
- Connection ports accept/reject correct types

---

## 8. Files to Create/Modify

### New files (10):
| File | Purpose |
|------|---------|
| `src/decision_system/workflow_engine/nodes/specialist/researcher.py` | Researcher node class + fake fallback |
| `src/decision_system/workflow_engine/nodes/specialist/critic.py` | Critic/Judge node class + deterministic rules |
| `src/decision_system/workflow_engine/nodes/specialist/synthesizer.py` | Decision Synthesizer node class + fake fallback |
| `src/decision_system/workflow_engine/nodes/specialist/__init__.py` | Package init, export all 3 |
| `web/workflow-builder/src/components/nodes/ResearcherCard.jsx` | Frontend card |
| `web/workflow-builder/src/components/nodes/CriticCard.jsx` | Frontend card |
| `web/workflow-builder/src/components/nodes/SynthesizerCard.jsx` | Frontend card |
| `web/workflow-builder/src/components/nodes/__init__.js` | Re-export all node cards |
| `web/workflow-builder/src/styles/node-cards.css` | Shared card styles |
| `tests/test_workflow_engine/test_specialist_nodes/` | Test directory |

### Modified files (5):
| File | Change |
|------|--------|
| `src/decision_system/workflow_engine/nodes/__init__.py` | Import specialist nodes, add to `_ALL_BUILTIN_NODES` and `create_default_registry()` |
| `src/decision_system/workflow_engine/nodes/builtin/__init__.py` | No changes needed (specialist nodes get their own package) |
| `web/workflow-builder/src/components/ConfigPanel.jsx` | Add 3 new card imports |
| `web/workflow-builder/src/mockData.js` | Add mock data for 3 new node types |
| `web/workflow-builder/src/api.js` | No changes needed (node execution uses existing API) |

---

## 9. Out of Scope

- **Data Analyst node** — deferred to Phase 7 (needs data profiling infrastructure integration)
- **Web search source** for Researcher — uses only local sources (Chroma, KG, data profiles)
- **Persistent decision history** — outputs exist in execution state, not a permanent storage
- **UI drag-reordering of criteria weights** — Synthesizer uses text-based weight inputs
- **Multi-language support** — prompts and outputs in English only
- **Real-time streaming of node reasoning** — nodes return complete results, not partial progress (streaming is at the DAG level, not the individual node level)
- **Self-modifying workflows** — no node changes its own config or creates new nodes at runtime

---

## 10. Dependencies

- **Phase 5 (LLM Provider Integration)** — ✅ Complete. ProviderStore, LLMClient, `resolve_provider()` all available.
- **Phase 1 (DAG Engine)** — ✅ Complete. execute(), ExecutionContext, node registry all available.
- **Phase 2 (Flow Control)** — ✅ Complete. Condition, Loop, Merge nodes enable the validation-gate pattern.
