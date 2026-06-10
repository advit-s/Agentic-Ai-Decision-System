# Agentic AI Decision System — Complete Overview

> A backend-first Company Intelligence Engine that turns local documents and data into auditable, evidence-cited decision reports.

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [The Problem It Solves](#2-the-problem-it-solves)
3. [Why This Architecture?](#3-why-this-architecture)
4. [How It Works End-to-End](#4-how-it-works-end-to-end)
5. [Key Design Principles](#5-key-design-principles)
6. [All Subsystems Explained](#6-all-subsystems-explained)
7. [CLI Commands Reference](#7-cli-commands-reference)
8. [How to Use It](#8-how-to-use-it)
9. [What It Is Not (Yet)](#9-what-it-is-not-yet)
10. [Project Roadmap](#10-project-roadmap)
11. [Project Structure](#11-project-structure)

---

## 1. What Is This?

This is a **backend-first AI prototype** that helps a company understand itself by analyzing its own documents and data.

You feed it:
- **Documents** (`.md`, `.txt`) — strategy docs, meeting notes, vendor contracts, risk assessments
- **Spreadsheets** (`.csv`) — sales, financials, customer feedback, operations data

It builds a **company-specific intelligence layer** — profiling your data, extracting relationships, mapping columns to business concepts, detecting patterns and risks.

Then you ask business questions and get back **auditable, evidence-cited reports** — not free-form AI chat. Every claim in the report comes from the claim ledger, which tracks whether each claim is:

| Status | Meaning |
|--------|---------|
| `verified` | Evidence supports this claim |
| `unsupported` | No evidence found — surfaced for human review |
| `contradicted` | Other documents say the opposite — flagged visibly |
| `pending` | Not yet checked |

**Contradictions, unsupported assumptions, confidence levels, and human-review flags are kept visible in the final report.** Nothing is smoothed away.

---

## 2. The Problem It Solves

Companies have data everywhere — documents, spreadsheets, internal wikis, meeting notes — but connecting the dots across all of it is hard for humans.

**The typical approach (ask ChatGPT) has problems:**
- It makes things up (hallucinates)
- It hides uncertainty (sounds confident even when wrong)
- It doesn't cite evidence you can verify
- It smooths over contradictions
- There's no audit trail of what was asked or answered
- Every question starts from zero — no persistent company knowledge

**How this project is different:**
- Every claim in a report cites the exact evidence chunk it came from
- Unsupported and contradicted claims stay visible — they're not hidden
- Reports show confidence levels and flag items needing human review
- All workflow state is saved and inspectable
- It builds a persistent intelligence layer (ontology, graph, profiles) that carries across questions

The tagline: **"Final reports come from verified claim ledger state, not uncontrolled agent chat."**

---

## 3. Why This Architecture?

### Comparison to Alternatives

| Concern | This Project | Plain ChatGPT | RAG Chatbot |
|---------|-------------|---------------|-------------|
| Evidence citations | ✅ Every claim cites source chunks | ❌ Makes up answers | ✅ Sometimes |
| Contradictions surfaced | ✅ Visible in report | ❌ Smoothed over | ❌ Usually hidden |
| Unsupported claims tracked | ✅ Shown as "unsupported" | ❌ Pretends to know | ❌ May guess |
| Offline, no API key needed | ✅ Default fake provider works fully | ❌ Requires API key | ❌ Requires API key |
| Audit trail | ✅ Every run saved, inspectable | ❌ No trail | ❌ Depends |
| Bounded workflow | ✅ Linear pipeline, no free chat | ❌ Uncontrolled | ❌ Uncontrolled |
| Multi-role analysis | ✅ War-cabinet with judge | ❌ Single persona | ❌ Single |
| Persistent company model | ✅ Ontology + graph + profiles persist | ❌ No memory | ❌ Vector DB only |

### Key Design Decision: Pipeline, Not Free Chat

The workflow is a **linear LangGraph state machine**, not an agent free-for-all:

```
START
  -> retrieve_evidence
  -> technical_analyst
  -> risk_analyst
  -> claim_extraction
  -> verifier
  -> report_writer
  -> END
```

- No back-edges, loops, or agent-to-agent chat
- Each node has a narrow, bounded responsibility
- Claims go through a verification gate before reaching the report
- The report writer renders FROM the claim ledger, not from raw model text

### Why "Fake" Provider?

The default `DECISION_PROVIDER=fake` generates realistic structured output **without calling any LLM**. This means:
- Every command works offline with zero API keys
- Tests pass with no external dependencies
- You can explore every feature immediately
- It's the safe default — no unexpected API costs, no data sent to third parties

Optional providers (NVIDIA NIM, Ollama) can be enabled when you want real LLM-generated memos, but the retrieval, verification, claim ledger, and report rendering are all identical regardless of provider.

---

## 4. How It Works End-to-End

### The Full Pipeline

```
company_docs/*.md, *.txt          company_data/*.csv
      |                                  |
      v                                  v
  [DOCUMENT LOADER]                 [DATA CATALOG]
      |                                  |
      v                                  v
  [CHUNKER]                         [CSV PROFILER]
  deterministic chunks               row counts, missing values,
  with stable evidence IDs           numeric summaries, warnings
      |                                  |
      v                                  v
  [CHROMA VECTOR STORE]             [DATA PROFILES]
  local, no cloud                    .decision_system/data_profiles/
      |                                  |
      v                                  v
  [DETERMINISTIC GRAPH]             [ONTOLOGY MAPPER]
  entity/relationship extraction     38 business concepts
  "X depends on Y", "X owns Y"       maps columns -> concepts
      |                                  |
      v                                  v
  [KNOWLEDGE GRAPH]                 [ONTOLOGY MAP]
  .decision_system/graph/            .decision_system/ontology/
      |                                  |
      +------->  [INSIGHT DETECTOR]  <----+
                  rule-based pattern detection
                  (revenue risk, concentration risk,
                   operations bottlenecks, contradictions...)
                      |
                      v
              [INSIGHTS]
              .decision_system/insights/

                          YOU ASK A QUESTION
                      "Should we migrate billing?"
                               |
                               v
                    [LANGGRAPH WORKFLOW]
                               |
              +-- retrieve_evidence (find relevant chunks)
              +-- technical_analyst (structured memo)
              +-- risk_analyst (risk assessment)
              +-- claim_extraction (material claims)
              +-- verifier (check evidence)
              +-- report_writer (render from ledger)
                               |
                               v
                    [CITED DECISION REPORT]
                 - Recommendation
                 - Evidence citations
                 - Verified / Unsupported / Contradicted claims
                 - Confidence level
                 - Human review flags
```

### The War-Room Layer (Multi-Role Analysis)

For complex questions, you can run a **war-cabinet** analysis:

```
question
  -> HIGHER CONTEXT (frozen, read-only for all agents)
  -> ROLE DISPATCH (selects: financial, risk, technical, marketing...)
  -> SPECIALIST ARTIFACTS (each role writes structured findings)
  -> COMMON WORKSPACE (append-only — no one can delete another's work)
  -> JUDGE (4 rules: unsupported claims, high-risk links, contradictions,
            low confidence)
  -> FINAL SUMMARY
```

This is still **deterministic** — no LLM calls, no free-form debate, no chat transcripts. Each role is a deterministic artifact generator.

---

## 5. Key Design Principles

These are the non-negotiable rules that the project follows:

| # | Principle | Why |
|---|-----------|-----|
| 1 | **Fake/offline is the default** | Zero API keys needed; tests pass offline |
| 2 | **No database** | Chroma + JSON files are sufficient for the prototype |
| 3 | **No auth** | All operations run as the local OS user |
| 4 | **No enterprise connectors** | Only `local-files` is real; GitHub/Jira/Slack/Email are stubs |
| 5 | **No free-form agent chat** | All workflows are bounded, linear, and testable |
| 6 | **Claims go through the ledger** | Nothing skips verification before the report |
| 7 | **Reports cite evidence** | Every claim traces back to source chunks |
| 8 | **Contradictions stay visible** | Never smoothed away in the final output |
| 9 | **Higher context is controlled** | Lower agents read it but cannot freely mutate it |
| 10 | **Judge/verifier is separate** | Not the same component that produces the work |
| 11 | **All work includes tests** | No feature ships without test coverage |
| 12 | **Generated state stays local** | `.decision_system/` is gitignored |

---

## 6. All Subsystems Explained

### 6.1 CLI (`src/decision_system/cli*.py`)
- **Entry point**: `decision-system` (Typer app)
- **50 commands** organized into sub-groups
- Main file split into modules: `cli.py` (core), `cli_security.py`, `cli_observability.py`, `cli_enterprise.py`, `cli_workspaces.py`, `cli_connectors.py`
- Uses Rich for formatted terminal output

### 6.2 FastAPI Backend (`src/decision_system/api/`)
- Uvicorn-based FastAPI app
- Serves both REST API endpoints and the static web UI
- Lazy-loads heavy route modules (chromadb, langgraph) so the server starts even if optional deps are missing
- Custom error envelope: all 404s return `{"error": {"code": "http_error", "message": "Not Found"}}`
- No auth, no database, no cloud services

### 6.3 RAG / Vector Store (`src/decision_system/rag/`)
- **Document loader**: reads `.md` and `.txt` files from `company_docs/`
- **Chunker**: deterministic split into chunks with stable evidence IDs (hash-based)
- **Chroma** vector store: local SQLite-backed embedding database
- **Retriever**: finds relevant chunks for a question
- No PDF support yet

### 6.4 Workflow / State Machine (`src/decision_system/graph/`)
- LangGraph `StateGraph` with 6 linear nodes
- **State**: `WorkflowState` TypedDict passed through the pipeline
- **Nodes**:
  1. `retrieve_evidence` — query Chroma for relevant chunks
  2. `technical_analyst` — structured memo with technical facts and risks
  3. `risk_analyst` — structured memo with risk assessment
  4. `claim_extraction` — extract `Claim` records from memos
  5. `verifier` — check claims against evidence (exists? contradicted?)
  6. `report_writer` — render final Markdown report from claim ledger

### 6.5 LLM Providers (`src/decision_system/llm/`)
- **Factory pattern**: picks provider based on `DECISION_PROVIDER` env var
- **Fake** (`src/decision_system/llm/fake_provider.py`): generates structured output without an LLM. The default.
- **NVIDIA NIM** (`src/decision_system/llm/nvidia_provider.py`): OpenAI-compatible API via `openai` package
- **Ollama** (`src/decision_system/llm/ollama_provider.py`): local model HTTP endpoint
- Provider experiments and evaluation harnesses in `provider_experiments/` and `provider_eval/`

### 6.6 Claim Ledger (`src/decision_system/ledger/`)
- `Claim` records with: ID, source agent, claim text, evidence IDs, status (pending/verified/unsupported/contradicted), confidence, verification notes
- Verifier checks: does cited evidence exist? Does a `CONTRADICTS:` marker appear?
- Deterministic rules — no semantic understanding yet

### 6.7 Knowledge Graph (`src/decision_system/graphing/`)
- Extracts `Entity` and `Relationship` objects from documents using deterministic patterns
- Relation types: `depends_on`, `owned_by`, `caused`, `affects`, `blocks`, `mitigates`, `related_to`, `contradicts`
- Pattern-based (regex), no LLM needed
- Stored as JSON in `.decision_system/graph/knowledge_graph.json`
- Every entity and relationship preserves source evidence IDs

### 6.8 Data Catalog (`src/decision_system/data_catalog/`)
- `company_data/` folder structure with category subdirectories
- `manifest.json` tracks metadata per dataset
- CSV profiler: row count, column count, missing values, numeric summaries, categorical top values, date detection, warnings
- Profile stored in `.decision_system/data_profiles/profiles.json`
- Demo data seeding and public dataset import support

### 6.9 Ontology (`src/decision_system/ontology/`)
- **38 deterministic business concepts** organized by type: entity, metric, relationship, risk, system
- Maps CSV column names to concepts using keyword matching
- Examples: `customer_name` -> Customer (entity), `revenue` -> Revenue (metric), `churn_rate` -> Churn Risk (risk)
- Stored in `.decision_system/ontology/ontology_map.json`

### 6.10 Insights (`src/decision_system/insights/`)
- **Rule-based pattern detection** — no LLM
- Detects: revenue risk, customer concentration, marketing ROI risk, competitor risk, operations bottlenecks, dependency risks, contradictions, missing data, data quality issues
- Conservative thresholds to minimize false positives
- Stored in `.decision_system/insights/insights.json`

### 6.11 Orchestration (`src/decision_system/orchestration/`)
- Determines what data, tools, and roles are needed for a question
- Pipeline: Problem Analyzer -> Planner -> Dispatcher -> Sandbox -> Detector -> Judge -> Persistence
- All deterministic — no LLM calls
- Decision types map to tool chains: financial -> profile + detect; strategic -> profile + graph + detect; technical -> graph only; general -> profile only

### 6.12 War Room (`src/decision_system/war_room/`)
- Multi-role bounded analysis protocol
- **HigherContext**: frozen, read-only shared context
- **PersonalAgentContext**: role-specific instructions
- **CommonWorkspace**: append-only structured artifacts
- **Judge**: 4 rules — unsupported artifacts, critical insight links, contradiction links, low confidence
- Deterministic specialist artifact generators (no LLM)
- Accessible via `plan-war-room`, `run-war-room`, `inspect-war-room`

### 6.13 Security (`src/decision_system/security/`)
- **Secret scanner**: finds API keys, tokens, private keys, AWS keys in tracked files
- **Redaction preview**: masks PII-like values (emails, keys) without modifying files
- **Policy checks**: 7 repository hygiene rules
- **Audit log**: security events recorded to `.decision_system/security/audit/audit_log.jsonl`
- **Approval workflow**: local approval records for human review (record-keeping only)
- All deterministic, offline, no auth server needed

### 6.14 Observability (`src/decision_system/observability/`)
- **Metrics**: named numeric metrics with labels, persisted to JSONL
- **Eval history**: pass/fail counts and durations per eval run
- **Quality reports**: aggregated evaluation summaries with scores
- **Trace summaries**: workflow run metadata (duration, node count, errors)
- All stored in `.decision_system/observability/`

### 6.15 Workspaces (`src/decision_system/storage/`)
- **Local SQLite** database at `.decision_system/workspaces/`
- Imports JSON artifacts from other subsystems for query convenience
- JSON outputs remain canonical — SQLite is a secondary index
- Export/import workspaces as JSON bundles
- No raw datasets in exports

### 6.16 Connectors (`src/decision_system/connectors/`)
- **`local-files`**: the only real connector — copies files with dry-run support
- **GitHub, Jira, Slack, Email**: offline stubs — `is_stub=True`, `supports_import=False`, no network calls
- No OAuth, no token storage, no external API calls
- Jobs tracked under `.decision_system/connectors/`

### 6.17 Web UI (`web/` and `src/decision_system/web/`)
- Static HTML/JS/CSS with **9 sections**:
  1. **Dashboard** — system readiness, provider status, quick links
  2. **Decision Brief** — ask questions, view claim-verified reports
  3. **Data & Ontology** — profiles, ontology, insights, knowledge graph
  4. **War Room** — multi-role analysis with judge interventions
  5. **Workspaces** — artifact tracking, import/export
  6. **Connectors** — local-files real + 4 stubs
  7. **Security & Governance** — policy, audit log, approvals
  8. **Observability** — metrics, eval history, quality, traces
  9. **Enterprise Readiness** — gap analysis
- **Mock-first**: works with JSON fixture fallbacks when API is down
- Served automatically by `decision-system serve-api`

### 6.18 Reports Exporter (`src/decision_system/reports/exporter.py`)
- Exports decision reports in Markdown, JSON, HTML formats
- Uses `ensure_safe_generated_write_path()` to confine writes under `.decision_system/`
- Includes evidence coverage scoring, audit timeline, and provider safety warnings

---

## 7. CLI Commands Reference

### Core Workflow
| Command | Description |
|---------|-------------|
| `decision-system index` | Index local docs into Chroma |
| `decision-system inspect-index` | Show index status |
| `decision-system ask "..."` | Run decision workflow → Markdown report |
| `decision-system ask "..." --show-evidence` | Show retrieved evidence before report |
| `decision-system ask "..." --json` | Structured JSON output |
| `decision-system ask "..." --save-run` | Save run to `.decision_system/runs/` |
| `decision-system ask "..." --include-insights` | Add insight-aware sections |
| `decision-system ask "..." --orchestrated` | Include orchestration context |
| `decision-system ask "..." --save-context` | Save context JSON |

### Data & Knowledge
| Command | Description |
|---------|-------------|
| `decision-system extract-graph` | Extract entities/relationships |
| `decision-system inspect-graph` | View knowledge graph summary |
| `decision-system init-data-catalog` | Create data catalog folders |
| `decision-system seed-demo-data` | Seed synthetic demo CSVs |
| `decision-system profile-data` | Profile CSV files |
| `decision-system inspect-data` | View data profile summary |
| `decision-system import-datasets` | Import public CSV/XLSX datasets |
| `decision-system inspect-imports` | View import manifest |
| `decision-system map-ontology` | Map columns to ontology concepts |
| `decision-system inspect-ontology` | View ontology map |
| `decision-system detect-patterns` | Run pattern/vulnerability detection |
| `decision-system inspect-insights` | View saved insights |

### Orchestration & War Room
| Command | Description |
|---------|-------------|
| `decision-system analyze-problem "..."` | Analyze question → required data/tools |
| `decision-system run-orchestration "..."` | Run orchestration pipeline |
| `decision-system inspect-orchestration` | View latest orchestration run |
| `decision-system build-context "..."` | Build decision context |
| `decision-system plan-war-room "..."` | Preview war-room dispatch |
| `decision-system run-war-room "..."` | Run war-room analysis |
| `decision-system inspect-war-room` | View war-room results |

### Evaluation
| Command | Description |
|---------|-------------|
| `decision-system eval` | Run bundled eval cases |
| `decision-system eval-war-room` | Run war-room eval |
| `decision-system eval-providers` | Run provider evaluation |
| `decision-system inspect-provider-evals` | View provider eval results |

### Providers
| Command | Description |
|---------|-------------|
| `decision-system provider-health` | Show provider config |
| `decision-system provider-smoke --provider X` | Quick provider test |
| `decision-system eval-provider --provider X` | Run provider experiments |

### Workspaces
| Command | Description |
|---------|-------------|
| `decision-system init-workspace <name>` | Create/activate workspace |
| `decision-system list-workspaces` | List all workspaces |
| `decision-system use-workspace <name>` | Switch active workspace |
| `decision-system workspace-status` | Show active workspace |
| `decision-system inspect-workspace` | View workspace details |
| `decision-system export-workspace` | Export workspace as JSON |
| `decision-system import-workspace <path>` | Import workspace JSON |

### Connectors
| Command | Description |
|---------|-------------|
| `decision-system connectors list` | List all connectors |
| `decision-system connectors inspect <id>` | Show connector details |
| `decision-system connectors dry-run <id> --path <dir>` | Preview import |
| `decision-system connectors import <id> --path <dir>` | Import files |
| `decision-system connectors inspect-jobs` | View import history |

### Security
| Command | Description |
|---------|-------------|
| `decision-system security scan-secrets` | Scan for credentials |
| `decision-system security scan-secrets --json` | Structured scan output |
| `decision-system security redact-preview "text"` | Preview PII redaction |
| `decision-system security audit-log` | View audit log |
| `decision-system security policy-check` | Run governance checks |
| `decision-system approval request --reason "..."` | Create approval record |
| `decision-system approval list` | List pending approvals |
| `decision-system approval inspect <id>` | View approval details |

### Observability
| Command | Description |
|---------|-------------|
| `decision-system metrics` | Show collected metrics |
| `decision-system eval-history` | Show eval run history |
| `decision-system quality-report` | Generate quality report |
| `decision-system trace-summary` | Show workflow traces |

### Enterprise & Hygiene
| Command | Description |
|---------|-------------|
| `decision-system enterprise-readiness` | Run gap analysis |
| `decision-system check-hygiene` | Verify repo hygiene |
| `decision-system serve-api` | Start FastAPI backend |

---

## 8. How to Use It

### Quick Start (Offline, No API Keys)

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Index demo documents
decision-system index
decision-system inspect-index

# Ask a question
decision-system ask "Should we migrate billing?"

# Explore more
decision-system extract-graph
decision-system inspect-graph
decision-system eval

# Start the web UI
decision-system serve-api
# Open http://localhost:8000
```

### Full Workflow for Real Data

```bash
# 1. Load your documents
mkdir -p company_docs
# Put .md, .txt files here (strategy docs, contracts, risk assessments, etc.)

# 2. Load your data
mkdir -p company_data/financials company_data/customers company_data/sales
# Put .csv files here

# 3. Index everything
decision-system index
decision-system profile-data
decision-system extract-graph
decision-system map-ontology

# 4. Detect patterns
decision-system detect-patterns
decision-system inspect-insights

# 5. Ask questions with full context
decision-system ask "What are our top revenue risks?" --include-insights
decision-system ask "Where are we losing money?" --orchestrated

# 6. Run multi-role analysis for complex questions
decision-system run-war-room "Should we restructure our pricing model?"
decision-system inspect-war-room

# 7. Start the API + web UI
decision-system serve-api
```

### Using Real LLM Providers

```bash
# Optional NVIDIA NIM
export DECISION_PROVIDER=nvidia_nim
export NVIDIA_NIM_BASE_URL=https://integrate.api.nvidia.com/v1
export NVIDIA_API_KEY=your-key-here

# Optional Ollama (local)
export DECISION_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434

# Per-command override
decision-system ask "Question" --provider nvidia_nim
```

### Workspace Management

```bash
decision-system init-workspace my-project
decision-system use-workspace my-project
decision-system workspace-status
decision-system import-artifacts    # import existing JSON state into workspace
decision-system export-workspace    # backup as JSON
```

---

## 9. What It Is NOT (Yet)

This is a **prototype**, not a production system. Here's what's missing:

| Area | Status | What's Needed |
|------|--------|---------------|
| **Authentication** | ❌ Not implemented | JWT/OAuth, login, session management |
| **Authorization** | ❌ Not implemented | RBAC, permission checks |
| **Database** | ❌ Chroma + JSON only | PostgreSQL or similar for durability |
| **Production frontend** | ❌ Static mock UI only | React/Vue, real dashboards |
| **Connectors** | ❌ Only local-files is real | Live GitHub/Jira/Slack/Email |
| **Secrets vault** | ❌ Env vars only | HashiCorp Vault, AWS Secrets Manager |
| **TLS** | ❌ No transport encryption | HTTPS certificates |
| **Rate limiting** | ❌ Not implemented | Request throttling |
| **Compliance** | ❌ Not implemented | SOC 2, GDPR, HIPAA controls |
| **Audit retention** | ❌ No policy | Formal log rotation and retention |
| **Encryption at rest** | ❌ All data unencrypted | Storage encryption |
| **Input sanitization** | ⚠️ Basic only | Pydantic validation exists but no comprehensive sanitization |
| **Autonomous actions** | ❌ Not implemented | No emails, tickets, or API calls |

The `decision-system enterprise-readiness` command documents all 12 working capabilities and 11 gaps.

---

## 10. Project Roadmap

### Completed

| Version | Focus | What Was Added |
|---------|-------|----------------|
| v0.1 | Decision Brief Core | LangGraph workflow, claim ledger, report writer, fake provider, document indexing |
| v0.2 | Knowledge Graph | Entity/relationship extraction, JSON graph store, graph inspection |
| v0.3 | Data Catalog | CSV profiling, data catalog, profile inspection |
| v0.4 | Intelligence Layer | Ontology mapping, insight detection, deterministic orchestration |
| v0.5 | Context & Reports | Decision context builder, insight-aware reports |
| v0.6 | War Cabinet | Multi-role analysis protocol, judge, sandbox, workspace |
| v0.7 | Provider Experiments | Provider harness for fake, NVIDIA NIM, Ollama |
| v0.7.1 | Provider Evaluation | Hardened provider eval with 8 cases |
| v0.8 | FastAPI Backend | REST API endpoints for all services |
| v0.9 | Web UI Prototype | Static 9-section HTML/JS/CSS UI with mock data |
| v1.0 | Workspaces | SQLite-backed workspace persistence, export/import |
| v1.1 | Connectors | Safe connector framework (local-files real; 4 stubs) |
| v1.2 | Security & Audit | Secret scanning, redaction, policy checks, audit log, approvals |
| v1.3 | Observability | Metrics, eval history, quality reports, traces |
| v1.4 | Docker & Deployment | Dockerfile, compose, dev scripts, release check |
| v1.5 | Enterprise Assessment | Honest gap analysis, readiness levels |
| v1.6 | Final Hardening | CLI refactoring, hygiene checker, 700+ tests |
| v1.7 | Product UI | Full 9-section web UI with API + mock fallback |
| v1.8 | Reports & Governance | Report exporter, lazy API imports, docs consistency |

### Planned

| Version | Focus |
|---------|-------|
| v2.0+ | Bounded specialist roles/tools with clear input/output/verification rules |
| v2.1+ | Production frontend, database, auth, connectors, saved workspaces |

---

## 11. Project Structure

```
/
├── company_docs/                    # Local documents (.md, .txt)
│   ├── demo_billing.md              # Demo doc for smoke tests
│   └── pricing.md
│
├── company_data/                    # Local CSV data
│   ├── manifest.json
│   ├── analytics/
│   ├── competitors/
│   ├── customers/
│   ├── feedback/
│   ├── financial/
│   ├── marketing/
│   ├── operations/
│   ├── products/
│   ├── sales/
│   └── strategic/
│
├── .decision_system/                # Generated state (gitignored)
│   ├── graph/                       # Knowledge graph JSON
│   ├── data_profiles/               # CSV profiles
│   ├── ontology/                    # Ontology maps
│   ├── insights/                    # Insight records
│   ├── contexts/                    # Decision contexts
│   ├── workspaces/                  # SQLite DB + exports
│   ├── connectors/                  # Connector job state
│   ├── runs/                        # Saved workflow runs
│   ├── war_room/                    # War-room runs
│   ├── evals/                       # Evaluation results
│   ├── provider_evals/              # Provider eval results
│   ├── observability/               # Metrics, traces, quality
│   └── security/                    # Audit log
│
├── src/decision_system/             # Main source
│   ├── __init__.py                  # Version: 1.8.0
│   ├── cli.py                       # Core CLI commands
│   ├── cli_security.py              # Security CLI sub-commands
│   ├── cli_observability.py         # Observability CLI sub-commands
│   ├── cli_enterprise.py            # Enterprise readiness CLI
│   ├── cli_workspaces.py            # Workspace CLI commands
│   ├── cli_connectors.py            # Connector CLI commands
│   ├── config.py                    # Settings dataclass
│   ├── models.py                    # Core Pydantic models
│   ├── path_util.py                 # Safe path guards
│   │
│   ├── agents/                      # Technical/risk analyst wrappers
│   ├── api/                         # FastAPI app + routes
│   ├── graph/                       # LangGraph workflow (state, nodes, builder)
│   ├── rag/                         # Document loading, chunking, Chroma, retrieval
│   ├── ledger/                      # Claim ledger + verifier
│   ├── llm/                         # Providers: fake, nvidia_nim, ollama
│   ├── reports/                     # Report renderer
│   ├── graphing/                    # Entity/relationship extraction
│   ├── data_catalog/                # CSV catalog + profiling
│   ├── context/                     # Decision context builder
│   ├── ontology/                    # 38 business concepts + mappings
│   ├── insights/                    # Pattern/vulnerability detection
│   ├── orchestration/               # Problem analysis + dispatch + judge
│   ├── war_room/                    # Multi-role protocol + artifacts
│   ├── security/                    # Secret scan, redaction, policy, audit
│   ├── observability/               # Metrics, traces, quality, eval history
│   ├── storage/                     # SQLite workspaces + export/import
│   ├── connectors/                  # Connector framework + stubs
│   ├── provider_experiments/        # Provider experiment harness
│   ├── provider_eval/               # Provider evaluation harness
│   ├── evals/                       # Eval runner + bundled cases
│   └── web/                         # Packaged web UI assets
│
├── web/                             # Source web UI (mock-first)
│   ├── index.html                   # 9-section UI
│   ├── app.js                       # JavaScript with API + mock fallback
│   ├── styles.css                   # Styling
│   ├── mock-data/                   # JSON fixtures per section
│   └── ...
│
├── tests/                           # Test suite (700+ tests)
│   ├── test_cli.py
│   ├── test_security.py
│   ├── test_observability.py
│   ├── test_web_ui.py
│   ├── test_api.py
│   └── ...
│
├── evals/                           # Eval case fixtures
│   ├── war_room_cases/
│   ├── provider_cases/
│   └── ...
│
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md
│   ├── PRODUCT_VISION.md
│   ├── DEPLOYMENT.md
│   ├── SECURITY_MODEL.md
│   ├── RELEASE_CHECKLIST.md
│   ├── DECISIONS.md
│   ├── ENTERPRISE_READINESS.md
│   └── CHANGELOG.md
│
├── scripts/                         # Dev/release helpers
│   ├── dev.sh / dev.ps1
│   ├── release-check.sh / release-check.ps1
│   ├── clean-generated.sh / clean-generated.ps1
│
├── pyproject.toml                   # Build config (Hatchling)
├── Dockerfile
├── docker-compose.yml
├── .env.example                     # Example env vars
├── .gitignore
├── .dockerignore
├── CLAUDE.md                        # Claude Code instructions
├── README.md
├── CHANGELOG.md
└── LICENSE                          # MIT
```
