# AGENTS.md - Agent Instructions for the Agentic Decision System

This file is for coding agents (Codex, Claude Code, and similar) who modify this
repository. Read it before changing code, docs, or tests.

## Project Purpose

This is a **Company Intelligence Engine** - a backend-first CLI prototype that
uses local company documents and data to produce evidence-backed decision reports.
It indexes `.md`/`.txt` documents in a local Chroma vector store, runs a bounded
LangGraph workflow, extracts claims, verifies them, and produces cited Markdown
reports. It also extracts entities/relationships into a local JSON graph, profiles
CSV data, maps columns to an ontology, detects patterns/vulnerabilities, and runs
a bounded war-cabinet agent context protocol.

The product is CLI-first, offline-capable, and testable without API keys.

## Architecture Summary

```text
company_docs/ -> chunker -> Chroma -> retriever -> LangGraph workflow:
  retrieve_evidence -> technical_analyst -> risk_analyst -> claim_extraction ->
  verifier -> report_writer -> Markdown Decision Report

company_docs/ -> deterministic graph extractor -> .decision_system/graph/

company_data/ -> CSV profiler -> .decision_system/data_profiles/

.data stores + graph + ontology + insights + orchestration -> context builder

Business question -> HigherContext -> AgentDispatchSpec -> CommonWorkspace
  -> deterministic specialist artifacts -> deterministic judge -> persisted run
```

Key sub-packages: `rag/`, `graph/`, `ledger/`, `reports/`, `graphing/`,
`data_catalog/`, `ontology/`, `insights/`, `orchestration/`, `war_room/`,
`evals/`, `devtools/`.

## Non-Negotiable Rules

1. **Fake/offline mode is the default.** `DECISION_PROVIDER=fake` in `.env.example`.
   No test requires a real API key.
2. **No production frontend, no database, no auth, no enterprise connectors.**
   The v0.9 `web/` folder is the only approved local static UI prototype; core
   logic must stay backend/CLI owned.
3. **No real external API calls in tests.** Tests must pass offline.
4. **No unbounded agent chat.** The war-cabinet protocol uses structured,
   append-only artifacts - not chat transcripts.
5. **Final reports must remain evidence/ledger/context grounded.** Claims go
   through the claim ledger. The report writer renders from ledger state, not
   raw agent prose.
6. **Generated state stays out of commits.** `.decision_system/`, `__pycache__/`,
   `.pytest_cache/`, `evals/results/*.json`, and `company_data/imported_*` are
   generated or local. They must remain untracked.
7. **Tests are mandatory.** Every feature or fix ships with tests.
8. **Agent instructions are balanced.** Fix small and medium issues directly.
   Escalate only when a change is large enough to warrant a written patch plan.

## Commands

```bash
# Install (editable with dev extras)
python -m venv .venv && .venv\Scripts\activate   # Windows
python -m venv .venv && source .venv/bin/activate # macOS/Linux
python -m pip install -e ".[dev]"

# Tests (gating step - run before claiming done)
python -m pytest -q

# Smoke commands (offline, no API key needed)
decision-system index
decision-system inspect-index
decision-system ask "Should we migrate billing?"
decision-system eval
decision-system eval-war-room

# Data pipeline
decision-system init-data-catalog
decision-system seed-demo-data --force
decision-system profile-data
decision-system detect-patterns

# Repo hygiene
decision-system check-hygiene
decision-system check-hygiene --json

# Graph / ontology / orchestration / war-room
decision-system extract-graph
decision-system map-ontology
decision-system run-orchestration "Where are we losing money?"
decision-system run-war-room "Where are we losing money?"
```

## Review Checklist

Before submitting work:

- [ ] `python -m pytest -q` passes (exit code 0).
- [ ] No new `.env` or real API keys in any tracked file.
- [ ] `git status --short` shows no tracked artifacts (`.decision_system/`,
      `__pycache__/`, `.pytest_cache/`, `*.pyc`, imported CSVs).
- [ ] `gitignore` covers generated files.
- [ ] README and CHANGELOG updated if behavior changed.
- [ ] Tests added for new functionality.
- [ ] `decision-system check-hygiene` passes (warnings are OK, failures are not).
- [ ] CLAUDE.md version history updated if scope changed.
- [ ] No scope creep: no production frontend beyond the approved v0.9 static UI,
      no database, no auth, no connectors, no new LLM providers, no unbounded
      agents.

## Codex Guidance

**Fix small/medium issues directly.** If a change touches a few files, adds a
small helper, fixes a bug, or updates a test - do it. Do not open a review
request for trivial work.

**Large scope changes require a patch plan first.** If a change involves new
agents, new workflow nodes, new providers, new sub-packages, or any change to
the bounded workflow contract, write a brief plan (2-5 bullet points: what,
why, files affected, tests, risks) and present it before implementing.

Both Claude Code and Codex follow these rules.
