# Architecture

## System Purpose

The Agentic AI Decision System creates evidence-backed decision reports from local documents. It is backend-first and CLI-first: users place documents in `company_docs/`, index them locally, then ask a decision question.

The system is not an autonomous decision-maker. It produces a decision brief that separates cited evidence, verified claims, contradicted claims, unsupported assumptions, risk notes, confidence, and human review needs.

## Bounded Workflow

The workflow is a linear LangGraph state machine:

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

There are no back edges, free-form debate loops, or agent-to-agent chat edges. Each node has a narrow responsibility and passes structured state to the next node.

## Evidence Pipeline

```text
company_docs/
  -> document loader
  -> chunker
  -> hash embeddings
  -> local Chroma collection
  -> retriever
  -> EvidenceChunk objects
```

Retrieval returns `EvidenceChunk` objects, not answers. Each chunk includes an evidence ID, source filename, chunk ID, text, and retrieval score.

## Analysts

The technical analyst and risk analyst produce structured `AgentMemo` objects. They do not own final truth. Their claims must pass through the claim ledger and verifier before the report writer can use them as evidence-backed statements.

## Claim Ledger

Claim extraction converts memos into `Claim` records. The ledger keeps claim IDs, source agent, claim text, evidence IDs, status, confidence, and verification notes.

Claim statuses are:

- `pending`
- `verified`
- `unsupported`
- `contradicted`

Contradicted and unsupported claims are preserved for auditability.

## Verifier

The verifier checks whether cited evidence exists and whether a deterministic `CONTRADICTS:` marker is present. This is intentionally simple and testable. It is not a semantic truth engine yet.

## Report Writer

The report writer renders from claim ledger state, not raw model prose. Reports include recommendation, options, evidence citations, risks, contradictions, unsupported assumptions, confidence level, human review requirements, and the original question.

## Inspectability

The CLI exposes debug surfaces:

- `decision-system inspect-index`
- `decision-system ask "..." --show-evidence`
- `decision-system ask "..." --json`
- `decision-system ask "..." --save-run`

These commands make retrieved evidence, workflow state, claim verification, and final report output inspectable.

## Evaluation Harness

`decision-system eval` runs local cases from `evals/cases/`. Each case writes temporary documents, indexes a temporary Chroma store, runs the normal workflow with the fake provider, and checks expectations.

Eval cases cover:

- useful billing evidence
- empty context
- explicit contradiction markers

Eval results are printed by default and are only saved under `evals/results/` when `--save-results` is passed.

## Optional Providers

The provider factory supports:

- `fake`: deterministic offline provider and default
- `nvidia_nim`: optional hosted provider using NVIDIA NIM

The fake provider remains the default for tests, evals, and offline runs.

## NVIDIA NIM Provider

`NvidiaNimProvider` uses LangChain's `ChatNVIDIA` integration. It reads credentials and generation settings from `.env` or environment variables only. It asks the model for strict JSON and validates responses into Pydantic models before they enter workflow state.

The local report renderer still owns final report writing.

## Current Limits

- No frontend.
- No database.
- No auth or permission model.
- No enterprise connectors.
- No autonomous external actions.
- No PDF parsing.
- No hybrid keyword search.
- No semantic contradiction verifier.
- No long-term persisted claim ledger.
- Hash embeddings are for local testing, not production retrieval quality.
