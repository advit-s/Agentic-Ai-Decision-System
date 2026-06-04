---
name: agent-orchestrator-builder
description: Use this when building, modifying, or reviewing the agent orchestrator for the company decision system, especially LangGraph routing, specialist agents, bounded loops, tool access, and structured agent outputs.
---

# Agent Orchestrator Builder

Use this skill to coordinate agents as bounded workflow components.

## Orchestration Rules

- Use LangGraph nodes and edges for orchestration.
- Give each agent a narrow role and structured output schema.
- Route through retrieval before analysis when evidence is required.
- Route through verification before report synthesis.
- Put tool permissions in code or middleware, not only in prompt text.
- Bound every loop with max steps, timeout, and fallback behavior.

## Expected Specialist Agents

- Technical analyst: feasibility, constraints, implementation path.
- Risk analyst: operational, legal, security, and business risks.
- Verifier: checks claims against retrieved evidence.
- Report agent: synthesizes final recommendation from ledger state.

## Review Checklist

- Can the graph resume from saved state?
- Can a human see why a node ran?
- Are agent outputs typed and testable?
- Are tool calls limited to the agent that needs them?
- Is there a clear failure path for low evidence or contradictions?
