# Plan Next

**Purpose:** Propose a small, scoped implementation milestone before writing any code.

## Instructions

1. **Read project context** (all of the following):
   - `README.md`
   - `CHANGELOG.md`
   - `docs/ARCHITECTURE.md`
   - `docs/DECISIONS.md`
   - `CLAUDE.md`

2. **Inspect the current codebase:**
   - List modified and untracked files (git status)
   - Read `src/decision_system/` source files relevant to the area of change
   - Read `tests/` to understand current test coverage
   - Note any failing tests

3. **Propose a milestone:**

   Based on the current state and roadmap, propose **one** of:

   - A new feature milestone (e.g., "v0.3: hybrid retrieval")
   - A bugfix or refactor milestone
   - A testing or quality milestone
   - A documentation milestone

   For each proposal include:
   - **Milestone name and version** (e.g., "v0.3 - Hybrid Retrieval")
   - **Scope**: 1-3 concrete changes, no more
   - **Files to create/modify** (exact paths)
   - **Tests to add or update** (exact test names or new test files)
   - **Architectural rules check**: confirm each change respects all architectural rules in CLAUDE.md
   - **Risks or unknowns**: anything that might block implementation
   - **Estimated test coverage impact**: new tests added, existing tests potentially affected

4. **Present the plan clearly** with a summary section and a detail section.

5. **Wait for approval.** Do not write any code until the user explicitly approves the plan.

## Output Format

```markdown
## Summary
[2-3 sentences describing what the milestone does and why]

## Detail

### Change 1: [title]
- **File(s):** `path/to/file.py`
- **Test(s):** `tests/test_thing.py::test_specific_case`
- **What changes:** brief description
- **Rule check:** which architectural rules this touches and how it respects them

### Change 2: ...

## Risks / Unknowns
- ...

## Alternative Considered (if any)
- ...
```
