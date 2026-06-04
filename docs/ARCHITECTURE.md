# Architecture

## System Purpose

The v0.1 system creates evidence-backed decision reports from local company or project documents. It is intentionally backend-first: users place documents in `company_docs/`, index them locally, then ask a decision question from the CLI.

The system is not an autonomous decision-maker. It produces a decision brief that separates cited evidence, verified claims, contradicted claims, unsupported assumptions, risk notes, confidence, and human review needs.

## v0.1 Architecture Diagram

```text
company_docs/
  -> loader
  -> chunker
  -> hash embeddings
  -> local Chroma collection
  -> retriever
  -> LangGraph workflow
       -> technical analyst
       -> risk analyst / red team
       -> claim extraction
       -> verifier
       -> report writer
  -> Markdown decision report
```

## CLI Flow

```text
decision-system index
  -> read settings
  -> load .md and .txt files
  -> chunk documents
  -> write chunks to local Chroma

decision-system ask "Should we migrate billing?"
  -> read settings
  -> build the fixed LangGraph workflow
  -> retrieve evidence
  -> create structured agent memos
  -> extract claims
  -> verify claims
  -> render the final report
```

## RAG Flow

Documents are loaded from `company_docs/`, normalized into source metadata, chunked into stable `EvidenceChunk` records, embedded with the deterministic v0.1 hash embedding function, and persisted in `.decision_system/chroma/`.

Retrieval returns `EvidenceChunk` objects, not answers. Each returned chunk carries:

- evidence ID
- document ID
- source path
- source filename
- chunk ID
- chunk text
- retrieval score

This keeps generation separate from evidence retrieval.

## LangGraph Node Flow

The graph is linear and terminating:

```text
START
  -> retrieve_evidence
  -> technical_analyst
  -> risk_analyst
  -> claim_extraction
  -> verifier
  -> report_writer
  -> END
```

There are no back edges, free-form debate loops, or agent-to-agent chat edges in v0.1.

## Claim Ledger Flow

Agents produce structured `AgentMemo` objects. Claim extraction converts memo claims into `Claim` records. Verification marks each material claim as:

- `verified`
- `unsupported`
- `contradicted`

Contradicted claims are preserved rather than deleted. This makes uncertainty visible in the final report.

## Report Generation Rules

The report is generated from the claim ledger, not raw agent conversation. The report must:

- cite verified evidence IDs
- list risks
- list contradictions
- list unsupported assumptions
- set confidence conservatively
- require human review for contradictions or unsupported evidence

## Why Agents Do Not Freely Chat

Free-form agent chat makes hallucination cascades, agreement traps, loops, and token waste more likely. v0.1 treats agents as bounded workflow components. Each agent gets a narrow task, structured input, and structured output.

## v0.1 Limitations

- No frontend.
- No database.
- No auth or permission model.
- No enterprise connectors.
- No real OpenAI/Ollama execution.
- No PDF parsing.
- No hybrid keyword search.
- No semantic contradiction verifier.
- No long-term persisted claim ledger.
- Fake hash embeddings are for local testing, not production retrieval quality.

## Future Extension Points

- Real model providers behind the existing provider interface.
- Production embeddings.
- PDF and office document parsing.
- Hybrid keyword plus vector retrieval.
- Reranking.
- FastAPI endpoint.
- Web UI.
- PostgreSQL-backed claim ledger.
- User auth and document permissions.
- Human approval gates.
- More specialist agents after evaluation proves the core workflow useful.
