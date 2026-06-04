# Review Before Handoff

**Purpose:** Prepare work for independent review by a second implementation agent (e.g., Codex). Generate a structured, actionable handoff note.

## Instructions

1. **Establish the baseline:**
   - Record current git state: which files were changed, staged, or untracked
   - Confirm the working tree is clean or list uncommitted changes
   - Note the current branch

2. **Run verification suite:**
   ```
   python -m pytest -q
   ```
   Record: total passed, failed, skipped, and error count. If any fail, list the failing test names and error summaries.

3. **Run smoke commands** (run every CLI command relevant to the changed area):
   - `decision-system inspect-index` (if vector store touched)
   - `decision-system ask "Should we migrate billing?"` (if workflow touched)
   - `decision-system ask "Should we migrate billing?" --show-evidence` (if evidence display changed)
   - `decision-system ask "Should we migrate billing?" --json` (if output format changed)
   - `decision-system extract-graph && decision-system inspect-graph` (if graph code changed)
   - `decision-system eval` (if evaluation or agents changed)
   Record exit codes and any unexpected output.

4. **Summarize changed files:**
   For each file that was added, modified, or deleted:
   - **Path** (relative to repo root)
   - **Why changed:** intended purpose
   - **Risk level:** low / medium / high
   - **Review priority:** first pass / background

5. **Summarize behavior changes:**
   - What does the system do differently now?
   - What remains the same?
   - Are there any breaking CLI changes (flags removed, output format changed)?

6. **List risks and uncertain areas:**
   - Untested edge cases
   - Assumptions that could be wrong
   - Areas where the implementation deviates from docs/ARCHITECTURE.md or docs/DECISIONS.md
   - Any TODOs or FIXMEs left in the code

7. **Explicit reviewer instructions:**

   Tell the reviewer (Codex) to specifically verify:
   - Test coverage: are there scenarios not covered?
   - Boundary cases: empty inputs, very large inputs, malformed input
   - Architectural rule compliance: does the change respect all architectural rules in `CLAUDE.md`?
   - Security: are there any paths where user input could be injected?
   - Performance: does the change introduce unnecessary computation or memory use?
   - Backward compatibility: can existing saved runs / graph files be loaded?

## Output Format

```markdown
## Git State
[Branch name, uncommitted changes]

## Test Results
[pass/fail summary, failing tests if any]

## Smoke Tests
[commands + exit codes + notes]

## Changed Files
| File | Why Changed | Risk | Priority |

## Behavior Changes
[What changed and what didn't]

## Risks and Uncertainties
- ...

## Reviewer Checklist (for Codex)
- [ ] ...
- [ ] ...
```
