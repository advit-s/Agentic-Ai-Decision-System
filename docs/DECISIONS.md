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
