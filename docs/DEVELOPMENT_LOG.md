# Development Log

## 2026-06-04

### v0.2.0 GitHub Preparation

- Added optional NVIDIA NIM provider support through `ChatNVIDIA`.
- Kept fake provider as the default for tests, evals, and offline smoke runs.
- Added inspectability and eval commands for local debugging.
- Added GitHub-ready docs for setup, architecture, development, NVIDIA NIM, troubleshooting, and contributing.
- Removed non-demo local company docs from commit candidates.
- Updated `.gitignore` to exclude `.env`, generated app state, eval result JSON, and private company docs.

### What Was Implemented

- Backend-first v0.1 CLI prototype.
- Local `.md` and `.txt` ingestion from `company_docs/`.
- Deterministic chunking with stable chunk IDs and evidence IDs.
- Local Chroma indexing with a fake hash embedding function.
- Bounded LangGraph workflow with retrieval, technical analysis, risk analysis, claim extraction, verification, and report generation.
- Claim ledger with `verified`, `unsupported`, and `contradicted` statuses.
- Fake provider by default so tests and smoke runs do not require API keys.
- Markdown decision report renderer.
- Demo smoke document and documentation.

### Test Command and Result

```bash
python -m pytest -q
```

Latest recorded result:

```text
35 passed, 1 warning
```

### Smoke Test Command and Result

```bash
decision-system index
decision-system ask "Should we migrate billing?"
```

Latest recorded result shape:

```text
Indexed more than 0 documents into more than 0 chunks.

# Decision Report
...
## Evidence Citations
- doc-...:chunk-...
...
## Contradictions
- ... Cited evidence explicitly contradicts this claim.
...
## Human Review Required
- Resolve contradicted claims before taking action.
```

### Chroma Warning Note

Running tests on Python 3.14 emits a Chroma dependency warning:

```text
DeprecationWarning: 'asyncio.iscoroutinefunction' is deprecated and slated for removal in Python 3.16
```

This warning comes from Chroma internals, not project code.

### Known Limitations

- Fake hash embeddings are deterministic but not semantically strong.
- Contradiction detection uses the explicit `CONTRADICTS:` marker only.
- The claim ledger is in-memory during a workflow run.
- Provider stubs intentionally do not call OpenAI or Ollama.
- Only `.md` and `.txt` files are supported.

### Next Recommended Milestone

Improve evaluation before adding product surface area: create a small retrieval and claim-verification eval set, then measure whether the system retrieves relevant chunks, preserves citations, and marks unsupported or contradicted claims correctly.
