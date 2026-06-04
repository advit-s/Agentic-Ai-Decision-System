---
name: decision-agent-architecture
description: Use this whenever building or modifying the agentic company decision system, especially LangGraph workflows, RAG agents, verifier agents, claim ledgers, decision reports, human approval, or agent state. Enforces the project architecture rules before implementation.
---

# Decision Agent Architecture

Use this skill to keep the company decision-agent system disciplined and auditable.

## Architecture Rules

- Build agent flows as explicit LangGraph state machines.
- Keep state typed and durable enough to resume important runs.
- Use a claim ledger before any final report is written.
- Require evidence citations for important claims.
- Run a verifier step before synthesis.
- Mark each material claim as `verified`, `unsupported`, or `contradicted`.
- Put human approval gates before high-risk external actions.
- Set max-turn, max-token, and timeout limits for every agent loop.
- Avoid free-form infinite agent conversations.

## Recommended Flow

1. Accept the decision question.
2. Retrieve relevant documents and evidence.
3. Run specialist analysis agents with bounded prompts.
4. Write candidate claims to the ledger.
5. Verify claims against evidence.
6. Synthesize a decision report only from verified or explicitly qualified claims.

## Implementation Checklist

- Define the graph state before nodes.
- Define node inputs and outputs as structured data.
- Keep retrieval, analysis, verification, and synthesis as separate graph nodes.
- Save traceable run IDs for retrieval results, agent outputs, claims, and final reports.
- Add tests for unsupported claims and contradictory evidence.
