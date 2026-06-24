# Example Issues — v1.34.0-dev

> **Version:** 1.34.0-dev
> **Milestone:** Local Beta Feedback Loop + Issue Templates
> **Date:** 2026-06-24

These examples help reviewers write better issues. Do not paste real private data.

---

## Good Bug Report

```markdown
**Version:** 1.34.0-dev
**OS:** macOS 14.3
**Python:** 3.11.7
**Setup:** Local scripts (setup-local.sh)

**Command:** decision-system ask "Should we migrate billing?"

**Expected:** Report with evidence-backed claims and citations.

**Actual:** Crashes with "KeyError: 'evidence_ids'" after retrieve_evidence step.

**Steps to Reproduce:**
1. ./scripts/setup-local.sh (fresh install)
2. cp .env.example .env
3. mkdir -p company_docs && cp demo/sample-data/*.md company_docs/
4. decision-system index
5. decision-system ask "Should we migrate billing?"

**Logs:**
```
$ decision-system ask "Should we migrate billing?"
Indexing company_docs/...
Retrieving evidence...
ERROR: KeyError: 'evidence_ids'
  File "src/decision_system/graph/nodes.py", line 142, in retrieve_evidence
    chunk = EvidenceChunk(**chunk_data)
```

**Diagnostics:** [Attached from collect-diagnostics.sh]

**Impact:** Affects demo path.
```

Why it's good: Version, OS, steps, actual error, and impact are all clear.

---

## Bad Bug Report

```markdown
**Title:** It doesn't work

The app is broken. I tried to ask a question and got an error. Please fix it.
```

Why it's bad: No version, no OS, no steps, no error message, no reproduction.

---

## Good Feature Request

```markdown
**Problem:** After running document analysis, I want to export the knowledge graph
as a PNG or SVG to include in presentations.

**Use Case:** I'm presenting company risk analysis to stakeholders. A visual
graph export would make the report more impactful than raw JSON.

**Proposed Behavior:**
- Add an "Export Graph" button in the Knowledge Graph page
- Export formats: PNG (for slides) and SVG (for editing)
- Export includes the visible graph canvas content

**Local-First Constraints:** ✅ Must work offline
**External Write Actions:** No

**Alternatives:** Currently screenshot the browser window, which is low quality.
```

Why it's good: Clear problem, concrete use case, specific proposal, constraints acknowledged.

---

## Good Beta Feedback

```markdown
**Install Experience:** Minor issues
**Demo Path Experience:** Partial
**UI Clarity:** Mostly clear

**Install Notes:** Setup worked but I had to install Tesseract manually for OCR.
The doctor script clearly told me it was missing, which was helpful.

**Demo Path Notes:** Got stuck at step 12 (workflow execution) because the
"Run" button was grayed out. I hadn't selected a provider. Adding a tooltip
would help.

**Confusing Parts:** The evidence search results show relevance scores but
don't explain what the score means. A tooltip or legend would help.

**What Worked Well:** Uploading documents was smooth. The file type detection
and parsing worked for all my test files.
```

Why it's good: Specific, actionable, balanced (positive + negative), references exact UI elements.

---

## Good Diagnostics Summary

```
App Version: 1.34.0-dev
Git Commit: 2fc984b
OS: Linux 6.8.0
Python: 3.11.7
Node: 20.11.0
Docker: Available
Doctor: 10 passed, 3 warnings, 0 failures
Validation: 15 passed, 0 failed
Backend: Running at http://localhost:8000
Frontend: Running at http://localhost:5173
Build: 1.34.0-dev
```

Why it's good: Complete, no secrets, useful for triage.
