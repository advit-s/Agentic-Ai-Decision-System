# Implement Approved Plan

**Purpose:** Execute an already-approved implementation plan. No creative additions.

## Instructions

1. **Anchor on the approved plan.** Read whatever plan state is available (the approved milestone description, task list, or prior proposal). Do exactly what was approved - no additions.

2. **Enforce architectural guardrails.** Before each code change, verify it respects all architectural rules in `CLAUDE.md`:
   - Fake provider stays default
   - No frontend, database, auth, or enterprise connectors
   - No new agents or free agent chat
   - Workflow remains bounded and linear
   - Claims go through the ledger
   - Reports cite evidence
   - Every change ships with tests

3. **Implementation order:**
   - **Step 1:** Write or update tests first (TDD where possible).
   - **Step 2:** Implement code changes.
   - **Step 3:** Update `docs/DECISIONS.md` if any architectural decision was touched.
   - **Step 4:** Update `CHANGELOG.md` under the correct version section.
   - **Step 5:** Update `pyproject.toml` version if this is a milestone release.

4. **Testing gate:**
   ```
   python -m pytest -q
   ```
   This must pass before declaring implementation complete. If a test fails, investigate and fix before proceeding.

5. **Smoke test commands:** Run the most relevant CLI commands for the changed area. Examples:
   - For graph changes: `decision-system extract-graph` and `decision-system inspect-graph`
   - For index changes: `decision-system index && decision-system inspect-index`
   - For workflow changes: `decision-system ask "Should we migrate billing?"`
   - For eval changes: `decision-system eval`
   Record the output and confirm it works as expected.

6. **Deliver summary:** At the end, provide:
   - **Files changed:** list with one-line description per file
   - **Tests result:** pass/fail count, any skipped or xfailed
   - **Smoke test result:** command run + exit code
   - **Limitations:** anything deferred to a future milestone
   - **Behavior changes:** user-visible changes from this PR (or "none - bugfix/internal")

## Do-Nots

- Do not add features beyond the approved plan.
- Do not refactor code "while you're there" unless the plan explicitly calls for it.
- Do not bypass tests or the fake-provider default.
- Do not update version numbers in `pyproject.toml` unless the plan is a milestone release (major.minor bump).
- Do not mention `git commit` or PR creation unless the user asks for it.
