# Product Vision: Company Intelligence Engine

## North Star

The project is evolving from a decision brief generator into a Company Intelligence Engine.

The long-term goal is software that helps a company understand itself: past decisions, current data, hidden relationships, contradictions, vulnerabilities, risks, and future options. It should make patterns visible that are hard for humans to connect manually across documents, spreadsheets, systems, teams, vendors, customers, incidents, and decisions.

The system should not become an uncontrolled chat tool. It should remain an auditable intelligence layer where evidence, ontology, graph relationships, claim verification, human review, and final reports are all inspectable.

## Two-Phase Product Model

### Phase 1: Company Data Understanding

The first phase processes company data and builds a company-specific intelligence layer.

Inputs may eventually include local documents, structured CSVs, public datasets, internal system exports, tickets, logs, customer feedback, financial data, sales data, operational data, and strategy documents. In the current project, this begins with local `.md`, `.txt`, and `.csv` files only.

Phase 1 should:

- load and profile company data
- detect data quality issues and missing data
- chunk and index document evidence
- extract entities and relationships
- map columns and concepts into an ontology layer
- build a graph-like representation of systems, projects, teams, risks, incidents, vendors, customers, decisions, and technologies
- surface deterministic insights and vulnerabilities
- keep everything inspectable through local JSON stores and CLI commands

The phrase "train on company data" should be treated carefully. For now, the safer framing is:

> The system builds a company-specific intelligence layer from local data using profiling, retrieval, ontology mapping, knowledge graph extraction, and later optional model adaptation.

Future model adaptation may include fine-tuning, adapters, embeddings, memory, or retrieval-augmented context, but that is not required for the current offline prototype.

### Phase 2: Orchestration War Cabinet

The second phase is an orchestration layer that uses the company intelligence layer to reason about a business problem.

The intended shape is a bounded "war cabinet" rather than free-form agent chat:

```text
business question
  -> top-level problem analysis
  -> higher context
  -> role/tool dispatch plan
  -> bounded specialist agents or tools
  -> shared storage
  -> judge / verifier
  -> final answer or decision report
```

The top-level model or controller analyzes the problem and decides which data, tools, roles, and artifacts are relevant. It sets a higher context that lower-level agents can read but not freely rewrite.

Specialist agents or tools may receive personal context, such as role, objective, allowed tools, task boundaries, and output schema. Examples of future roles include financial analyst, engineer, legal reviewer, risk analyst, strategy analyst, operations analyst, customer analyst, and market analyst.

The system should support multiple perspectives, but those perspectives must remain bounded, auditable, and verified. The final answer should not be raw agent debate. It should be a synthesized result checked by a judge/verifier and grounded in the company intelligence layer.

## Higher Context, Personal Context, and Common Storage

The orchestration design has three important context layers:

- **Higher context:** Global problem framing, company-level context, constraints, current objective, relevant ontology concepts, and rules. Lower-level agents can read this but should not freely edit it.
- **Personal context:** Role-specific instructions and task-specific context given to a specialist agent or tool. This includes what the role should inspect, which tools are allowed, and what output schema is expected.
- **Common storage:** Shared structured workspace where agents/tools can write findings, evidence references, intermediate artifacts, contradictions, questions, and proposed claims.

Common storage is how future agents can coordinate without uncontrolled direct chat. It should be structured, typed, append-only where possible, and inspectable.

## Ontology Versus Graph

The ontology layer and a graph database are related, but they are not the same thing.

A graph store represents connected data:

```text
Entity A -> relationship -> Entity B
```

An ontology explains what those entities and relationships mean:

```text
customer, vendor, system, incident, project, risk, dependency, owner, contradiction
```

The ontology is the semantic layer. It gives meaning to columns, entities, relationships, and business concepts so future LLMs and tools can reason over company data more easily.

For example, raw movement data might show that a vehicle repeatedly stops at the same address in the evening. A graph can store vehicle-to-location visits. An ontology can help interpret those visits as a possible relationship pattern, such as a frequent-contact location, while still requiring human review before any sensitive conclusion is accepted.

In the company setting, the same idea applies to business data:

- a system repeatedly appears in incidents
- a vendor appears across delays and support tickets
- a team owns multiple blocked projects
- a customer segment appears in churn, refunds, and low product usage
- a strategic goal has constraints but no accountable owner
- two documents contradict each other about a migration risk

The ontology makes these patterns easier to name, inspect, and reason about.

## Current Foundation

The current implementation already contains early pieces of the Company Intelligence Engine:

- local document indexing
- RAG retrieval over local evidence
- bounded LangGraph workflow
- claim ledger and verifier
- cited decision reports
- inspectability commands
- local evaluation harness
- entity and relationship extraction
- graph-like local JSON store
- company data catalog and CSV profiling
- demo dataset seeding and public dataset importing
- deterministic ontology mapping
- deterministic pattern and vulnerability detection
- offline orchestration foundation
- insight-aware decision context and reports

This is still a backend-first prototype. The goal is to prove data understanding, verification, and orchestration discipline before adding frontend, database, auth, connectors, or autonomous external actions.

## Safety and Architecture Rules

The system should keep these rules as it grows:

- Fake/offline mode remains the default for tests and local development.
- No final report should be based only on raw agent prose.
- Material claims should pass through a claim ledger or equivalent verification step.
- Evidence citations, contradictions, unsupported assumptions, and human-review items should remain visible.
- Agents and tools should be bounded by explicit state, roles, schemas, and allowed actions.
- Shared storage should be inspectable.
- High-risk or externally visible actions require human approval.
- The judge/verifier should be separate from the workers it reviews.
- The ontology and graph should preserve source references.
- Generated local state should remain under `.decision_system/` and out of Git.

## Near-Term Direction

The next product milestones should strengthen Phase 1 before expanding Phase 2 too aggressively:

1. Improve ontology quality and concept coverage.
2. Improve relationship extraction beyond simple deterministic patterns.
3. Add richer context packages for decision questions.
4. Improve insight ranking and deduplication.
5. Compare fake provider behavior with optional hosted providers.
6. Add bounded specialist roles only when their inputs, outputs, tools, and verification rules are clear.
7. Introduce a backend API only after the CLI workflow is stable.

The product should grow toward the war-cabinet idea, but the implementation should stay incremental, inspectable, and testable.
