# Document Decision Brief MVP Design

## Goal

Build a backend-first Python CLI prototype that turns local company/project documents into a cited decision brief using a bounded LangGraph workflow.

The v0.1 user flow is:

```text
Place .md or .txt files in company_docs/
Run decision-system index
Run decision-system ask "Should we proceed with Project X?"
Receive a cited report with recommendations, risks, contradictions, unsupported assumptions, confidence, and human review items
```

## Scope

Included in v0.1:

- Local document loading from `company_docs/`
- Chunking with stable source metadata and chunk IDs
- Persistent local Chroma indexing
- Deterministic fake embeddings for offline tests
- CLI commands for indexing and asking a decision question
- Bounded LangGraph workflow
- Technical analyst, risk/red-team analyst, verifier, and report writer roles
- Claim ledger with `verified`, `unsupported`, and `contradicted` statuses
- Tests that pass without API keys

Not included in v0.1:

- Frontend
- Database
- Login, permissions, or enterprise connectors
- Slack, email, Jira, GitHub, contracts, or codebase integrations
- Free-form multi-agent chat
- Long-running autonomous actions
- Real OpenAI or Ollama execution as a required path
- Many specialist agents

## Dependency Plan

Create this `pyproject.toml` at the repository root:

```toml
[build-system]
requires = ["hatchling>=1.26,<2.0"]
build-backend = "hatchling.build"

[project]
name = "agentic-decision-system"
version = "0.1.0"
description = "Backend-first agentic decision brief prototype with LangGraph, Chroma, RAG, and a claim ledger."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "langgraph>=1.0,<2.0",
  "langchain>=1.0,<2.0",
  "langchain-core>=1.0,<2.0",
  "chromadb>=0.5,<2.0",
  "pydantic>=2.8,<3.0",
  "typer>=0.12,<1.0",
  "python-dotenv>=1.0,<2.0",
  "rich>=13.7,<15.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9.0"
]

[project.scripts]
decision-system = "decision_system.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

Notes:

- `langchain-community` is intentionally omitted in v0.1 because direct `chromadb` access is enough.
- `langchain` and `langchain-core` are included for compatibility with the LangGraph/LangChain ecosystem and future provider integrations.
- Real model provider packages such as `langchain-openai` and `langchain-ollama` are not required in v0.1. Provider stubs can be added without making them runtime dependencies.

## File Structure

```text
agentic_decision_system/
  pyproject.toml
  README.md
  .env.example

  company_docs/
    .gitkeep

  src/
    decision_system/
      __init__.py
      cli.py
      config.py
      models.py

      graph/
        __init__.py
        state.py
        workflow.py
        nodes.py

      agents/
        __init__.py
        base.py
        technical_analyst.py
        risk_analyst.py
        verifier.py
        report_writer.py

      rag/
        __init__.py
        loader.py
        chunker.py
        embeddings.py
        vector_store.py
        retriever.py

      ledger/
        __init__.py
        claim_ledger.py
        verifier.py

      reports/
        __init__.py
        renderer.py

      llm/
        __init__.py
        provider.py
        fake_provider.py
        openai_provider.py
        ollama_provider.py

  tests/
    test_document_loader.py
    test_chunker.py
    test_retriever.py
    test_claim_ledger.py
    test_verifier.py
    test_report_renderer.py
    test_workflow.py
    test_cli.py
```

## CLI Commands

The exact required commands are:

```bash
decision-system index
decision-system ask "question here"
```

Default behavior:

- `decision-system index`
  - Reads documents from `company_docs/`
  - Supports `.md` and `.txt` in v0.1
  - Chunks documents
  - Builds or refreshes the Chroma collection at `.decision_system/chroma`
  - Uses the deterministic local hash embedding function
  - Prints indexed document and chunk counts

- `decision-system ask "question here"`
  - Loads the existing Chroma index from `.decision_system/chroma`
  - Retrieves the top relevant evidence chunks
  - Runs the fixed LangGraph workflow
  - Prints a Markdown decision report to stdout
  - Uses `FakeProvider` by default so the pipeline works without API keys

Optional flags may be added, but the two commands above must work with defaults:

```bash
decision-system index --docs-dir company_docs --store-dir .decision_system/chroma
decision-system ask "question here" --top-k 6 --provider fake
```

## Data Models

All models except `WorkflowState` are Pydantic models in `src/decision_system/models.py`. `WorkflowState` is a `TypedDict` in `src/decision_system/graph/state.py`.

```python
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field

ClaimStatus = Literal["pending", "verified", "unsupported", "contradicted"]
ConfidenceLevel = Literal["low", "medium", "high"]

class EvidenceChunk(BaseModel):
    evidence_id: str
    document_id: str
    source_path: str
    source_filename: str
    chunk_id: str
    text: str
    score: float | None = None

class AgentMemo(BaseModel):
    agent_name: str
    question: str
    summary: str
    claims: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    options: list[str] = Field(default_factory=list)
    cited_evidence_ids: list[str] = Field(default_factory=list)

class Claim(BaseModel):
    claim_id: str
    run_id: str
    source_agent: str
    claim_text: str
    claim_type: Literal["technical", "risk", "option", "recommendation", "assumption"]
    status: ClaimStatus = "pending"
    evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel = "low"
    verification_notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VerificationResult(BaseModel):
    claim_id: str
    status: Literal["verified", "unsupported", "contradicted"]
    evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: ConfidenceLevel
    verification_notes: str

class DecisionReport(BaseModel):
    run_id: str
    question: str
    recommendation: str
    options: list[str] = Field(default_factory=list)
    evidence_citations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    contradictions: list[Claim] = Field(default_factory=list)
    unsupported_assumptions: list[Claim] = Field(default_factory=list)
    confidence_level: ConfidenceLevel
    human_review_required: list[str] = Field(default_factory=list)
    markdown: str
```

```python
from typing_extensions import TypedDict
from decision_system.models import AgentMemo, Claim, DecisionReport, EvidenceChunk, VerificationResult

class WorkflowState(TypedDict, total=False):
    run_id: str
    question: str
    top_k: int
    retrieved_evidence: list[EvidenceChunk]
    technical_memo: AgentMemo
    risk_memo: AgentMemo
    claims: list[Claim]
    verification_results: list[VerificationResult]
    final_report: DecisionReport
    errors: list[str]
```

## RAG Design

### Loader

`rag/loader.py` loads `.md` and `.txt` files recursively from `company_docs/`.

Each loaded document gets:

- `document_id`: stable hash from relative path
- `source_path`: absolute or repository-relative path
- `source_filename`: basename
- `text`: normalized file text

Empty files are skipped with a warning.

### Chunker

`rag/chunker.py` splits documents into deterministic chunks:

- Default chunk size: 1000 characters
- Default overlap: 200 characters
- Stable `chunk_id`: `chunk-0001`, `chunk-0002`, etc. within the document
- Stable `evidence_id`: `{document_id}:{chunk_id}`

Every chunk preserves source filename and path.

### Embeddings

`rag/embeddings.py` implements `HashEmbeddingFunction`.

This is intentionally simple:

- No API keys
- Deterministic
- Suitable for tests and local smoke runs
- Produces fixed-size vectors from normalized token hashes

Real embeddings can be added later behind the same interface.

### Vector Store

`rag/vector_store.py` uses `chromadb.PersistentClient`.

Default path:

```text
.decision_system/chroma
```

Collection name:

```text
decision_chunks
```

Stored metadata:

- `evidence_id`
- `document_id`
- `source_path`
- `source_filename`
- `chunk_id`

### Retriever

`rag/retriever.py` queries Chroma and returns `list[EvidenceChunk]`.

The retriever returns evidence objects only. It does not answer the user question.

## LLM Provider Design

`llm/provider.py` defines a protocol-style interface:

```python
class LLMProvider(Protocol):
    def technical_memo(self, question: str, evidence: list[EvidenceChunk]) -> AgentMemo: ...
    def risk_memo(self, question: str, evidence: list[EvidenceChunk], technical_memo: AgentMemo) -> AgentMemo: ...
    def extract_claims(self, run_id: str, memos: list[AgentMemo]) -> list[Claim]: ...
    def write_report(self, question: str, claims: list[Claim], evidence: list[EvidenceChunk]) -> DecisionReport: ...
```

`FakeProvider` is the default and must be implemented first. It produces deterministic structured outputs from retrieved evidence so tests and CLI smoke runs need no API keys.

`OpenAIProvider` and `OllamaProvider` are stubs in v0.1:

- They expose the same class names and method signatures.
- They raise `NotImplementedError` with a clear message.
- They are not required for tests.

## Agent Design

Agents are bounded role functions, not chat participants.

### Technical Analyst

Inputs:

- User question
- Retrieved evidence

Output:

- `AgentMemo`

Job:

- Identify technical constraints, feasibility concerns, implementation options, and technical claims from the evidence.

### Risk Analyst / Red Team

Inputs:

- User question
- Retrieved evidence
- Technical memo

Output:

- `AgentMemo`

Job:

- Identify operational, security, legal, financial, or business risks.
- Challenge weak assumptions.
- Add risk claims, not open-ended discussion.

### Claim Extraction

Inputs:

- Technical memo
- Risk memo

Output:

- `list[Claim]`

Job:

- Convert important memo statements into ledger claims.
- Claims with no citations start as `pending` with empty `evidence_ids`.

### Verifier

Inputs:

- Claims
- Retrieved evidence

Output:

- Updated claims
- `list[VerificationResult]`

Rules:

- A claim with no valid evidence IDs becomes `unsupported`.
- A claim with valid supporting evidence becomes `verified`.
- A claim whose cited evidence contains an explicit contradiction marker becomes `contradicted`.
- Contradicted claims are preserved, not deleted.
- Every non-pending result must include verification notes.

The explicit contradiction marker for v0.1 tests is:

```text
CONTRADICTS:
```

Example:

```text
CONTRADICTS: The billing migration can be completed without downtime.
```

This gives deterministic contradiction tests now. A real semantic verifier can replace this later.

### Report Writer

Inputs:

- Question
- Claim ledger
- Retrieved evidence

Output:

- `DecisionReport`

Rules:

- Must consume verified, unsupported, and contradicted ledger claims.
- Must not use raw agent memo prose as final factual truth.
- Must cite evidence IDs for important claims.
- Must name unsupported assumptions and contradictions.
- Must include human review items when evidence is weak, unsupported, or contradicted.

## LangGraph Node Flow

The exact v0.1 graph is linear and terminating:

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

Node responsibilities:

- `retrieve_evidence`: query Chroma, return `retrieved_evidence`
- `technical_analyst`: call provider technical memo, return `technical_memo`
- `risk_analyst`: call provider risk memo, return `risk_memo`
- `claim_extraction`: call provider claim extraction, return `claims`
- `verifier`: update claim statuses, return `claims` and `verification_results`
- `report_writer`: render final report from ledger state, return `final_report`

No node routes backward. No node runs an unbounded loop. There are no agent-to-agent chat edges.

## Report Format

The Markdown report must include these sections:

```text
# Decision Report

## Recommendation
## Options
## Evidence Citations
## Risks
## Contradictions
## Unsupported Assumptions
## Confidence Level
## Human Review Required
```

The report should be conservative:

- If no evidence is retrieved, confidence is `low`.
- If any material claim is contradicted, human review is required.
- If unsupported assumptions affect the recommendation, human review is required.

## Acceptance Criteria

- Documents load from `company_docs/`.
- Chunks preserve source filename and chunk ID.
- Retrieval returns citation-ready `EvidenceChunk` objects.
- Claims are marked `verified`, `unsupported`, or `contradicted`.
- The final report uses the claim ledger, not raw agent text.
- The workflow terminates without loops.
- Tests pass without real API keys.
- `decision-system index` works with default paths.
- `decision-system ask "question here"` works with default paths after indexing.
- No frontend is created.
- No database is added.
- No extra agents are added beyond the requested v0.1 roles.

## Test Plan

Unit tests:

- `test_document_loader.py`: loads `.md` and `.txt`, skips empty files.
- `test_chunker.py`: chunk IDs and evidence IDs are stable.
- `test_retriever.py`: retrieval returns `EvidenceChunk` with source metadata.
- `test_claim_ledger.py`: ledger stores and updates claims without deleting contradicted claims.
- `test_verifier.py`: unsupported claims remain unsupported; contradiction markers create contradicted status.
- `test_report_renderer.py`: final report includes required sections and consumes ledger claims.
- `test_workflow.py`: graph runs from question to final report and terminates.
- `test_cli.py`: CLI commands run with fake provider and temporary docs.

## Future Extension Points

Later versions can add:

- OpenAI or Ollama provider implementations
- Better embeddings
- PDF parsing
- Hybrid keyword + vector retrieval
- Reranking
- FastAPI endpoint
- UI
- PostgreSQL-backed claim ledger
- User permissions
- More specialist agents
- Human approval gates
- LangSmith or OpenTelemetry tracing

