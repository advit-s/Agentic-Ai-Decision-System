# Agentic Decision System - Claude Code Project Context

## Product Vision

This is a **Company Intelligence Engine** - a backend-first prototype that uses past and present company data to find hidden patterns, vulnerabilities, relationships, contradictions, and risks that are hard for humans to see. It helps stakeholders make future decisions through evidence-backed analysis.

The key design principle: **final reports come from verified claim ledger state, not uncontrolled agent chat**. Contradictions, unsupported claims, citations, confidence, and human-review flags must remain visible rather than smoothed away.

## Project State

The project is a CLI/backend-first prototype. It currently supports local document indexing, retrieval, bounded decision workflows, claim verification, cited reports, inspectability commands, local evaluation cases, optional NVIDIA NIM configuration, deterministic graph extraction, and local CSV data profiling.

Generated local state belongs under `.decision_system/` and should not be committed. Private company documents and private CSV files should remain local; only fake demo documents/data are safe to commit.

## Current Architecture

```
company_docs/ (local .md/.txt files)
  -> document loader -> chunker -> Chroma vector store (local)
  -> retriever -> LangGraph workflow (linear, bounded)
       technical_analyst -> risk_analyst -> claim_extraction -> verifier -> report_writer
  -> Markdown Decision Report (cites evidence, shows contradictions, confidence)
```

```
company_docs/ (local .md/.txt files)
  -> chunker -> deterministic graph extractor (regex, no LLM)
  -> .decision_system/graph/knowledge_graph.json (local JSON store)
  -> inspect sub-package (counts, grouped types, top connected entities)
```

```
company_data/ (local fake/demo CSVs plus private ignored CSVs)
  -> manifest.json -> CSV profiler
  -> .decision_system/data_profiles/profiles.json (generated local JSON)
  -> inspect-data summary
```

### Tech Stack
- **Python 3.11+**, **Hatchling** build
- **LangGraph** (bounded linear workflow, no loops or free chat)
- **Chroma** (local vector store)
- **Pydantic** (all models)
- **Typer** (CLI)
- **Rich** (CLI output)
- **python-dotenv** (env config)

### Key Sub-packages
| Path | Purpose |
|------|---------|
| `src/decision_system/agents/` | Bounded technical/risk analyst wrappers |
| `src/decision_system/graph/` | LangGraph state, 6 node functions, workflow builder |
| `src/decision_system/rag/` | Document loading, chunking, hash embeddings, Chroma CRUD, retriever |
| `src/decision_system/ledger/` | Claim ledger + verifier |
| `src/decision_system/llm/` | Providers: `fake` (default), `nvidia_nim` |
| `src/decision_system/reports/` | Decision report renderer |
| `src/decision_system/evals/` | Local evaluation models and runner |
| `src/decision_system/graphing/` | Entity/relationship graph extraction, store, inspection |
| `src/decision_system/data_catalog/` | Local CSV catalog initialization, profiling, storage, inspection |

## Current CLI Commands

```
decision-system index                           - Index local .md/.txt docs into Chroma
decision-system inspect-index                   - Show collection name, chunk count, filenames
decision-system ask "question"                  - Run workflow, print Markdown report
decision-system ask "question" --show-evidence  - Print retrieved evidence before report
decision-system ask "question" --json           - Print structured workflow state as JSON
decision-system ask "question" --save-run       - Save full run payload under .decision_system/runs/
decision-system ask "question" --provider fake  - Override provider (fake or nvidia_nim)
decision-system ask "question" --provider nvidia_nim  - Use NVIDIA NIM
decision-system extract-graph                   - Extract entities/rels -> .decision_system/graph/knowledge_graph.json
decision-system inspect-graph                   - Print graph inspection summary
decision-system init-data-catalog               - Create company_data folders, manifest, fake demo CSVs
decision-system profile-data                    - Profile local CSV files -> .decision_system/data_profiles/profiles.json
decision-system inspect-data                    - Print saved profile summary
decision-system eval                            - Run local evaluation cases
decision-system eval --json                     - Print structured eval results
decision-system eval --save-results             - Save eval results under evals/results/
```

Entry point: `decision_system.cli:app` in `src/decision_system/cli.py`.

## Version History

### v0.3.0 (2026-06-04)
- Local `company_data/` folder structure
- Data catalog manifest with category metadata and fake demo CSV entries
- CSV profiling for row count, column count, missing values, numeric summaries, categorical top values, and warnings
- Generated profile store at `.decision_system/data_profiles/profiles.json`
- `init-data-catalog`, `profile-data`, and `inspect-data` commands

### v0.2.0 (2026-06-04)
- Entity and relationship extraction (7 relation types + CONTRADICTS)
- `Entity`, `Relationship`, `KnowledgeGraph` Pydantic models
- Rule-based extraction - no LLM involved
- Local JSON graph store at `.decision_system/graph/knowledge_graph.json`
- `extract-graph` and `inspect-graph` commands
- Graph inspection with type grouping and top connected entities
- Optional NVIDIA NIM provider via LangChain `ChatNVIDIA`
- Provider factory (`fake` default)
- `decision-system ask --provider nvidia_nim`

### v0.1.2 (2026-06-04)
- `decision-system eval` for repeatable local evaluation cases
- Evaluation case models and structured suite results
- Offline eval runner that indexes temporary case documents and runs the normal workflow
- Bundled billing, empty-context, and contradiction eval cases
- `decision-system eval --json` and `decision-system eval --save-results`

### v0.1.1 (2026-06-04)
- `inspect-index`
- `ask --show-evidence`
- `ask --json`
- `ask --save-run`
- Saved runs under `.decision_system/runs/`

### v0.1.0 (2026-06-04)
- Backend-first Python CLI prototype
- Local `.md` and `.txt` documents in `company_docs/`
- Deterministic chunking with stable evidence IDs
- Chroma local vector store
- Fake offline provider by default
- Bounded LangGraph workflow (no loops, no free chat)
- Technical analyst, risk analyst, verifier, report writer
- Claim ledger (`verified`, `unsupported`, `contradicted`)
- Final report uses claim ledger, not raw agent prose
- Test suite without real API keys

## Important Architectural Rules

These are non-negotiable constraints that must be preserved in every change:

1. **Fake/offline mode is the default.** `DECISION_PROVIDER=fake`. Tests must pass without any API key.
2. **This is a CLI/backend project.** No frontend, UI, dashboards, or web UI components at this stage.
3. **No database yet.** Chroma + local JSON files are sufficient.
4. **No auth yet.** No JWT, OAuth, RBAC.
5. **No enterprise connectors yet.** (Slack, Jira, email, GitHub, Salesforce, etc.)
6. **No new agents unless explicitly planned and approved.** Each agent requires explicit scoping and bounded inputs.
7. **No additional real LLM providers without approval.** Only `fake` (default) and `nvidia_nim` are accepted.
8. **Agents do not freely chat.** The LangGraph workflow is strictly linear: retrieve -> tech analyst -> risk analyst -> claim extraction -> verifier -> report writer.
9. **Workflows remain bounded and testable.** No unbounded loops, no recursive agent calls.
10. **All important claims go through the claim ledger.** Nothing skips the ledger.
11. **Reports cite evidence and expose unsupported/contradicted claims.** The claim ledger drives the report; raw agent prose does not.
12. **All new work must include tests.** Every feature or fix ships with tests.
13. **Run `python -m pytest -q` before saying done.** This is the gating step.

## What Not To Add Without Approval

- Web frontend, UI components, dashboards
- PostgreSQL, SQLAlchemy, ORM, any database
- JWT, OAuth, RBAC, any auth
- Slack/Jira/email/GitHub/Salesforce connectors
- Autonomous external actions (send emails, create tickets)
- Semantic contradiction detection (beyond the simple markdown marker)
- Hybrid search or reranking
- PDF parsing
- Additional LangGraph nodes or agent types without explicit design approval
- New LLM providers beyond `fake` and `nvidia_nim`

## Scope Guardrails

Any proposed change must be checked against these rules **before** implementation begins:
- Does it respect the above list of "not to add" items?
- Does it keep agents bounded and non-conversational?
- Does it route claims through the ledger before reaching the report?
- Does it include tests?
- Does it work with no API key (fake provider)?

If the answer to any of these is "no," the change is out of scope for this phase.

## Next Roadmap

| Version | Focus |
|---------|-------|
| **v0.4** | FastAPI backend |
| **v0.5** | Frontend |
| **v0.6** | Database and saved decision history |

## How Claude Should Work in This Repo

### Session Start
Before making any code changes, always read `CLAUDE.md` (this file), `README.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`. Use the `plan-next` workflow command to propose milestones.

### Before Coding
1. Invoke the `brainstorming` skill for creative work (new features, behavior changes).
2. Propose a scoped plan using the `.claude/commands/plan-next.md` workflow.
3. Wait for user approval.
4. Use the `.claude/commands/implement-approved-plan.md` workflow for execution.

### During Implementation
- Keep changes minimal and scoped to the approved plan.
- Write tests first where possible (TDD).
- Keep `fake` provider as default.
- All changes must pass `python -m pytest -q`.

### Before Handoff
Use `.claude/commands/review-before-handoff.md` to:
- Run tests and smoke commands
- Summarize changed files and behavior changes
- List risks and uncertain areas
- Prepare a clear handoff note for review

### Versioning
- Update `CHANGELOG.md` and `pyproject.toml` version when a feature milestone is reached.
- Use semantic versioning: major.minor.patch.

### Key Source Files
| File | Purpose |
|------|---------|
| `src/decision_system/cli.py` | Typer CLI entry point and command wiring |
| `src/decision_system/graph/workflow.py` | LangGraph StateGraph builder |
| `src/decision_system/graph/nodes.py` | 6 bounded node functions |
| `src/decision_system/graph/state.py` | WorkflowState TypedDict |
| `src/decision_system/models.py` | Core Pydantic models |
| `src/decision_system/config.py` | Settings dataclass |
| `src/decision_system/rag/chunker.py` | Deterministic chunking |
| `src/decision_system/rag/vector_store.py` | Chroma CRUD |
| `src/decision_system/ledger/claim_ledger.py` | Claim tracking |
| `src/decision_system/graphing/` | Extraction, store, inspection |
| `src/decision_system/evals/` | Evaluation runner and bundled cases |
| `src/decision_system/data_catalog/` | CSV catalog initialization, profiling, storage, inspection |
