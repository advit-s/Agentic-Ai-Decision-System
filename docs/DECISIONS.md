# Architecture Decisions

## ADR-001: Use Backend-First CLI Before Frontend

Status: Accepted

The first version uses a CLI because the critical risk is the reasoning and evidence workflow, not UI. This keeps v0.1 small, testable, and easy to run locally.

## ADR-002: Use a Linear LangGraph Workflow

Status: Accepted

The system uses LangGraph because the decision process has explicit state and ordered steps. v0.1 is intentionally linear to avoid agent loops and uncontrolled conversations.

## ADR-003: Use Local Chroma for v0.1

Status: Accepted

Local Chroma gives persistent vector search without adding a database or hosted service. It is suitable for local prototype indexing and smoke tests.

## ADR-004: Use Fake Provider by Default

Status: Accepted

The fake provider keeps the project runnable without API keys. It also makes tests deterministic and protects the early architecture from provider-specific behavior.

## ADR-005: Use Claim Ledger Before Final Report

Status: Accepted

The report must consume verified, unsupported, and contradicted claims from the ledger. This prevents raw agent prose from becoming final truth without verification.

## ADR-006: Keep OpenAI/Ollama as Stubs in v0.1

Status: Accepted

Real providers are useful later, but v0.1 proves the workflow shape first. Provider stubs preserve extension points without making external execution required.

## ADR-007: Do Not Add Database/Auth/Extra Agents Yet

Status: Accepted

Database, auth, and more agents would add complexity before the retrieval, verification, and reporting loop is proven. They remain future milestones after evaluation.

## ADR-008: Add NVIDIA NIM as Optional Hosted Provider

Status: Accepted

The fake provider remains the default for tests and offline use. NVIDIA NIM is available only when explicitly selected through `DECISION_PROVIDER=nvidia_nim` or `decision-system ask --provider nvidia_nim`, and credentials must come from `.env` or environment variables.

## ADR-017: Add Decision Context Builder Before LLM-Based Synthesis

Status: Accepted

v0.5 adds a `DecisionContextBuilder` that assembles structured context from local stores (ontology map, insights, orchestration sessions, knowledge graph) without calling external APIs. The context supports optional rendering in decision reports while keeping the default output unchanged for backward compatibility.

Key principles:
- All stores are loaded defensively: missing files return empty defaults.
- Insight selection always includes high and critical severity regardless of keyword match.
- Contradiction and missing_data insights create human review items automatically.
- Context is persistable under `.decision_system/contexts/` and ignored by Git.

## ADR-018: Keep Insight-Aware Sections Opt-In

Status: Accepted

Default `decision-system ask` output does not include insight-aware sections. Section inclusion is controlled by CLI flags (`--include-insights`, `--orchestrated`, `--save-context`). This preserves backward compatibility and keeps offline smoke tests stable.

## ADR-009: Add a Local JSON Knowledge Graph Before a Database

Status: Accepted

The Company Intelligence Engine needs entity and relationship structure, but v0.2 should not add a database. A local `.decision_system/graph/knowledge_graph.json` file keeps the graph inspectable, easy to test, and safe for offline use.

## ADR-010: Use Deterministic Graph Extraction in v0.2

Status: Accepted

Entity and relationship extraction starts with rule-based patterns for phrases such as `depends on`, `owned by`, `caused`, `affects`, `blocks`, `mitigates`, `related to`, and `CONTRADICTS:`. This keeps tests deterministic and avoids adding a real LLM, extra agents, or free-form extraction loops before the storage and inspection contracts are proven.

## ADR-011: Add Local CSV Data Catalog Before Connectors

Status: Accepted

v0.3 introduces `company_data/` as a local structured data intake area. It supports category folders, a manifest, and fake demo CSV files only. This gives the Company Intelligence Engine a place to inspect structured company data without adding enterprise connectors, auth, scheduled ingestion, or a database.

## ADR-012: Persist CSV Profiles as Generated Local JSON

Status: Accepted

CSV profiling writes summaries to `.decision_system/data_profiles/profiles.json`. The profile store is generated local state and should not be committed. Profiles contain shape and quality signals, not semantic decisions: row counts, column counts, missing values, numeric summaries, categorical top values, date-like columns, and warnings.

## ADR-014: Add Deterministic Insight Engine Before Real LLM Analysis

Status: Accepted

v0.4 introduces a rule-based insight engine that reads existing data profiles, local knowledge graph relationships, and raw CSV files to produce deterministic offline insights. No real LLM is called during detection. This keeps the Company Intelligence Engine testable, auditable, and runnable without API keys while providing visible value from existing data layers.

The engine is intentionally conservative: thresholds are set to minimise false positives, and detectors gracefully skip when upstream data is absent. Insights are persisted to ``.decision_system/insights/insights.json`` and inspected via CLI commands.

## ADR-015: Keep Insight Detection Offline and Testable

Status: Accepted

All v0.4 detectors are rule-based and deterministic. They run against cached data profiles and local files. No agent call, no free-form analysis, and no new LangGraph nodes are introduced. The insight engine is a standalone analysis layer that reads the output of existing subsystems (profiler, graph, CSV loader) without modifying their contracts.

## ADR-016: Import Public Datasets as Local CSV Copies

Status: Accepted

v0.3.2 imports local public `.csv`, `.xlsx`, and `.xls` files from ignored `datasets/` into categorized CSV files under `company_data/<category>/`. Imported files are named `imported_*.csv` and remain ignored by Git. This keeps raw public downloads and generated conversions out of commits while allowing the existing CSV profiler to inspect them.

SQL Server `.bak` files are skipped with a clear manifest record instead of adding native database restore support.
