---
name: red-team-reviewer
description: Use this when red-teaming the agentic company decision system, final reports, RAG pipeline, tool access, human approval flow, or claim verification logic. Looks for failure modes, misuse, prompt injection, missing evidence, and unsafe automation.
---

# Red Team Reviewer

Use this skill to challenge the decision-agent system before trusting its output.

## Review Areas

- Prompt injection in retrieved documents.
- Tool access that is broader than the agent needs.
- Missing human approval for high-risk actions.
- Reports that hide uncertainty or unsupported claims.
- Retrieval that ignores contradictory evidence.
- Agent loops that can run too long or compound errors.
- Database writes that lack audit trails.

## Output Format

For each issue, include:

- Severity: `high`, `medium`, or `low`
- Affected component
- Failure mode
- Why it matters
- Recommended fix
- Test to prevent recurrence

## Bias

Prefer concrete, reproducible risks over vague criticism. If evidence is not available, label the concern as a hypothesis.
