# Agentic Decision System - Claude Code Project Context

## Product Vision

This is a **Company Intelligence Engine** - a backend-first prototype that uses past and present company data to find hidden patterns, vulnerabilities, relationships, contradictions, and risks that are hard for humans to see. It helps stakeholders make future decisions through evidence-backed analysis.

The key design principle: **final reports come from verified claim ledger state, not uncontrolled agent chat**. Contradictions, unsupported claims, citations, confidence, and human-review flags must remain visible rather than smoothed away.

The full product direction is captured in `docs/PRODUCT_VISION.md`. Claude should read that file before proposing major roadmap, orchestration, ontology, graph, agent, or context changes.

### Two-Phase Company Intelligence Model

**Phase 1: Company Data Understanding**

The system first processes company data and builds a company-specific intelligence layer. In the current prototype this means local documents, local CSVs, profiling, retrieval, deterministic ontology mapping, graph-like JSON stores, insights, and inspectability.

Avoid overclaiming that the system "trains ML on company data" today. Safer wording:

> The system builds a company-specific intelligence layer from local data using profiling, retrieval, ontology mapping, knowledge graph extraction, and later optional model adaptation.

Future model adaptation might include fine-tuning, adapters, embeddings, memory, or stronger retrieval-augmented context, but that is not part of the current offline default.

**Phase 2: Orchestration War Cabinet**

The future orchestration layer should reason over the company intelligence layer. A top-level controller/model analyzes the problem, sets higher context, selects relevant data/tools/roles, dispatches bounded specialist agents or tools, uses shared structured storage, and passes outputs through a judge/verifier before any final answer.

This should be a bounded war-cabinet workflow, not free-form agent chat.

### Ontology Versus Graph

A graph store represents connected data: entity -> relationship -> entity.

An ontology explains what those entities and relationships mean: customer, vendor, system, incident, project, risk, dependency, owner, contradiction, and similar business concepts.

The ontology is the semantic layer. It helps future LLMs and tools reason over company data without manually rediscovering every relationship from raw rows and text each time.

## Project State

The project is a CLI/backend-first prototype with a v0.9 local static UI for artifact inspection. It currently supports local document indexing, retrieval, bounded decision workflows, claim verification, cited reports, inspectability commands, local evaluation cases, optional NVIDIA NIM and Ollama configuration, deterministic graph extraction, local CSV data profiling, deterministic ontology mapping, deterministic insight detection, offline orchestration, insight-aware decision contexts/reports, the v0.6 war-cabinet agent context protocol, the v0.7 provider experiment harness, the v0.7.1 provider evaluation hardening harness, the v0.8 local FastAPI backend, and the v0.9 mock-first web UI prototype.

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

```
.decision_system/data_profiles + ontology + graph + insights + orchestration
  -> DecisionContextBuilder
  -> optional insight-aware report sections
  -> .decision_system/contexts/<run_id>.json
```

```
business question
  -> HigherContext (deep-frozen shared context)
  -> AgentDispatchSpec (role selection + personal contexts)
  -> CommonWorkspace (append-only artifacts)
  -> deterministic specialist artifact generators
  -> deterministic judge interventions
  -> .decision_system/war_room/runs/<run_id>.json
```

### Future Orchestration Shape

```text
business question
  -> top-level problem analysis
  -> higher context
  -> role/tool dispatch plan
  -> bounded specialist agents or tools
  -> shared structured storage
  -> judge / verifier
  -> final answer or decision report
```

Higher context is global problem framing and constraints. Lower-level agents/tools may read it but should not freely rewrite it.

Personal context is role-specific task context for a specialist worker.

Common storage is a structured shared workspace for evidence references, findings, contradictions, proposed claims, questions, and intermediate artifacts. It should not become uncontrolled chat.

### Tech Stack
- **Python 3.11+**, **Hatchling** build
- **LangGraph** (bounded linear workflow, no loops or free chat)
- **Chroma** (local vector store)
- **Pydantic** (all models)
- **Typer** (CLI)
- **FastAPI + Uvicorn** (local API backend)
- **Rich** (CLI output)
- **python-dotenv** (env config)
- **Static HTML/CSS/JavaScript** (v0.9 local UI prototype only)

### Key Sub-packages
| Path | Purpose |
|------|---------|
| `src/decision_system/agents/` | Bounded technical/risk analyst wrappers |
| `src/decision_system/api/` | Local FastAPI app, API models, and route modules |
| `src/decision_system/graph/` | LangGraph state, 6 node functions, workflow builder |
| `src/decision_system/rag/` | Document loading, chunking, hash embeddings, Chroma CRUD, retriever |
| `src/decision_system/ledger/` | Claim ledger + verifier |
| `src/decision_system/llm/` | Providers: `fake` (default), `nvidia_nim`, `ollama` |
| `src/decision_system/provider_experiments/` | Provider smoke/eval harness for fake, NIM, and Ollama |
| `src/decision_system/provider_eval/` | Offline/mock provider evaluation harness for fake, NIM, and Ollama |
| `src/decision_system/reports/` | Decision report renderer |
| `src/decision_system/evals/` | Local evaluation models and runner |
| `src/decision_system/graphing/` | Entity/relationship graph extraction, store, inspection |
| `src/decision_system/data_catalog/` | Local CSV catalog initialization, profiling, storage, inspection |
| `src/decision_system/context/` | Decision context builder, selector, store, and inspector for insight-aware reports |
| `src/decision_system/ontology/` | Deterministic ontology concepts and column mappings |
| `src/decision_system/insights/` | Deterministic pattern and vulnerability detection |
| `src/decision_system/orchestration/` | Offline problem analysis, planning, dispatch, sandbox, session, and judge summary |
| `src/decision_system/war_room/` | War-cabinet context protocol, role dispatch, append-only workspace, judge interventions |
| `web/` | Local mock-first static UI and lightweight JSON fixtures |

## Current CLI Commands

```
decision-system index                           - Index local .md/.txt docs into Chroma
decision-system inspect-index                   - Show collection name, chunk count, filenames
decision-system ask "question"                  - Run workflow, print Markdown report
decision-system ask "question" --show-evidence  - Print retrieved evidence before report
decision-system ask "question" --json           - Print structured workflow state as JSON
decision-system ask "question" --save-run       - Save full run payload under .decision_system/runs/
decision-system ask "question" --provider fake  - Override provider (fake, nvidia_nim, or ollama)
decision-system ask "question" --provider nvidia_nim  - Use NVIDIA NIM
decision-system ask "question" --provider ollama      - Use local Ollama
decision-system extract-graph                   - Extract entities/rels -> .decision_system/graph/knowledge_graph.json
decision-system inspect-graph                   - Print graph inspection summary
decision-system init-data-catalog               - Create company_data folders, manifest, fake demo CSVs
decision-system profile-data                    - Profile local CSV files -> .decision_system/data_profiles/profiles.json
decision-system inspect-data                    - Print saved profile summary
decision-system seed-demo-data                  - Seed fake synthetic demo CSV data
decision-system import-datasets                 - Convert local public CSV/XLS/XLSX datasets into categorized CSVs
decision-system inspect-imports                 - Inspect public dataset import manifest
decision-system map-ontology                    - Map profiled columns to ontology concepts
decision-system inspect-ontology                - Inspect local ontology map
decision-system detect-patterns                 - Run deterministic pattern/vulnerability detection
decision-system inspect-insights                - Inspect saved insights
decision-system analyze-problem "question"      - Analyze data categories, roles, tools, ontology, and tiers
decision-system run-orchestration "question"    - Run offline orchestration foundation
decision-system inspect-orchestration           - Inspect latest orchestration run
decision-system build-context "question"        - Build decision context from ontology, insights, graph, orchestration
decision-system build-context "question" --json - Print structured decision context JSON
decision-system ask "question" --include-insights  - Add insight-aware report sections
decision-system ask "question" --orchestrated      - Add orchestration summary/judge context
decision-system ask "question" --save-context      - Save .decision_system/contexts/<run_id>.json
decision-system plan-war-room "question"       - Preview war-room role dispatch and shared context
decision-system run-war-room "question"        - Run deterministic specialist artifacts and judge review
decision-system inspect-war-room               - Inspect latest saved war-room run
decision-system eval                            - Run local evaluation cases
decision-system eval --json                     - Print structured eval results
decision-system eval --save-results             - Save eval results under evals/results/
decision-system provider-health                 - Inspect fake/NIM/Ollama provider configuration
decision-system provider-smoke --provider fake  - Run one provider smoke test
decision-system eval-provider --provider fake   - Run provider experiment cases
decision-system eval-providers                  - Run offline/mock provider evaluation cases
decision-system inspect-provider-evals          - Inspect saved provider evaluation results
decision-system serve-api                       - Run the local FastAPI development API
```

Entry point: `decision_system.cli:app` in `src/decision_system/cli.py`.

## Version History

### v0.9.0 (2026-06-06)
- Local mock-first web UI prototype under `web/`
- Ask, Reports, Insights, Ontology, War Room, Provider Evals, Data Profiles, and Graph views
- Optional API base URL configuration with fallback to mock JSON
- Tests for static files, mock data contracts, and optional FastAPI route detection
- No auth, database, real provider requirement, or raw dataset assets

### v0.8.0 (2026-06-06)
- Local FastAPI application
- API endpoints for documents, ask/report, context, orchestration, war-room, ontology, insights, and evals
- `decision-system serve-api`
- Offline FastAPI `TestClient` tests
- No auth, database, frontend, new provider, or external API requirement

### v0.7.1 (2026-06-06)
- Provider evaluation hardening harness for fake, NVIDIA NIM, and Ollama
- `decision-system eval-providers`
- `decision-system inspect-provider-evals`
- Offline/mock evaluation by default for optional providers
- Manual real provider mode gated by `--manual-real-provider`
- Saved provider eval results under `.decision_system/provider_evals/`

### v0.7.0 (2026-06-05)
- Provider experiment harness for fake, NVIDIA NIM, and Ollama
- Optional Ollama provider using local HTTP only
- `decision-system provider-health`
- `decision-system provider-smoke --provider ...`
- `decision-system eval-provider --provider ...`
- Provider eval cases under `evals/provider_cases/`
- Fake provider remains default; real provider tests remain mocked/offline

### v0.6.0 (2026-06-05)
- War-cabinet agent context protocol
- Deep-frozen shared `HigherContext`
- Role-specific read-only `PersonalAgentContext`
- Append-only `CommonWorkspace`
- Deterministic role dispatch and specialist artifact simulation
- Deterministic judge interventions for unsupported, high-risk, contradiction, and low-confidence cases
- `decision-system plan-war-room`, `run-war-room`, and `inspect-war-room`
- War-room run persistence under `.decision_system/war_room/runs/`

### v0.5.0 (2026-06-05)
- Decision context builder for local ontology, insight, graph, and orchestration stores
- `decision-system build-context` with text, `--json`, and `--save` modes
- Insight-aware report sections controlled by `ask --include-insights`
- Orchestration summary and judge context controlled by `ask --orchestrated`
- Context persistence under `.decision_system/contexts/` via `ask --save-context`
- Backward-compatible default `decision-system ask "question"` behavior

### v0.4.1 (2026-06-05)
- Editable install/package hardening for `python -m pip install -e ".[dev]"`
- Removed the direct `langchain-nvidia-ai-endpoints` dependency conflict
- NVIDIA NIM provider now uses NVIDIA NIM's OpenAI-compatible API via the `openai` Python package
- Added `NVIDIA_NIM_BASE_URL`
- Ontology cleanup with 38 deterministic concepts and improved column mappings
- Insights include ontology concept IDs

### v0.4.0 (2026-06-05)
- Deterministic orchestration foundation
- Problem analyzer, planner, dispatcher, sandbox wrapper, and judge summary
- Ontology mapping and local insight detection
- Orchestration, ontology, and insight inspection CLI commands

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
- Optional NVIDIA NIM provider
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
2. **This is a CLI/backend project with one approved static UI exception.** The v0.9 `web/` prototype may inspect artifacts with mock JSON; do not expand it into a production frontend, auth surface, database app, or core decision engine.
3. **No database yet.** Chroma + local JSON files are sufficient.
4. **No auth yet.** No JWT, OAuth, RBAC.
5. **No enterprise connectors yet.** (Slack, Jira, email, GitHub, Salesforce, etc.)
6. **No new agents unless explicitly planned and approved.** Each agent requires explicit scoping and bounded inputs.
7. **No additional real LLM providers without approval.** Only `fake` (default), `nvidia_nim`, and `ollama` are accepted.
8. **Agents do not freely chat.** The LangGraph workflow is strictly linear: retrieve -> tech analyst -> risk analyst -> claim extraction -> verifier -> report writer.
9. **Workflows remain bounded and testable.** No unbounded loops, no recursive agent calls.
10. **All important claims go through the claim ledger.** Nothing skips the ledger.
11. **Reports cite evidence and expose unsupported/contradicted claims.** The claim ledger drives the report; raw agent prose does not.
12. **All new work must include tests.** Every feature or fix ships with tests.
13. **Run `python -m pytest -q` before saying done.** This is the gating step.
14. **Higher context is controlled.** Future lower-level agents/tools may read higher context but must not freely mutate it.
15. **Shared storage is structured.** Use typed, inspectable artifacts instead of agent chat transcripts as coordination.
16. **Judge/verifier remains separate.** Worker outputs need review before they influence final reports or high-risk recommendations.

## What Not To Add Without Approval

- Production web frontend, saved workspace app, or dashboard beyond the approved v0.9 static prototype
- PostgreSQL, SQLAlchemy, ORM, any database
- JWT, OAuth, RBAC, any auth
- Slack/Jira/email/GitHub/Salesforce connectors
- Autonomous external actions (send emails, create tickets)
- Semantic contradiction detection (beyond the simple markdown marker)
- Hybrid search or reranking
- PDF parsing
- Additional LangGraph nodes or agent types without explicit design approval
- New LLM providers beyond `fake`, `nvidia_nim`, and `ollama`
- Unbounded war-room / war-cabinet agent debate
- Model fine-tuning or training workflows unless explicitly scoped and approved

## Scope Guardrails

Any proposed change must be checked against these rules **before** implementation begins:
- Does it respect the above list of "not to add" items?
- Does it keep agents bounded and non-conversational?
- Does it route claims through the ledger before reaching the report?
- Does it preserve source references for ontology, graph, insight, and context outputs?
- Does it keep shared storage structured and inspectable?
- Does it include tests?
- Does it work with no API key (fake provider)?

If the answer to any of these is "no," the change is out of scope for this phase.

## Next Roadmap

| Version | Focus |
|---------|-------|
| **v1.0** | Carefully scoped bounded specialist roles/tools, if inputs/outputs/verification rules are clear |
| **v1.1+** | Production frontend, database, auth, connectors, and saved workspaces after backend discipline is proven |

## How Claude Should Work in This Repo

### Session Start
Before making any code changes, always read `CLAUDE.md` (this file), `README.md`, `CHANGELOG.md`, `docs/PRODUCT_VISION.md`, `docs/ARCHITECTURE.md`, and `docs/DECISIONS.md`. Use the `plan-next` workflow command to propose milestones.

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
- Run `.claude/commands/review-before-handoff.md` or `/review-before-handoff` if available.
- Run tests and smoke commands.
- Summarize changed files and behavior changes.
- List risks and uncertain areas.
- Prepare a clear handoff note for review.

### Agent Collaboration
- Use installed skills/workflows where relevant.
- Codex is expected to fix small/medium issues directly during review - do not open a review request for trivial work.
- Do not leave generated artifacts in the repo (`.decision_system/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`). Run `decision-system check-hygiene` to verify.

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
| `src/decision_system/context/` | Decision context building, selection, persistence, and inspection |
| `src/decision_system/ontology/` | Ontology mapping and inspection |
| `src/decision_system/insights/` | Deterministic insight detectors and stores |
| `src/decision_system/orchestration/` | Offline orchestration foundation and judge summary |
