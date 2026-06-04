# Document Decision Brief Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend-first CLI MVP that indexes local company documents and produces cited decision reports through a bounded LangGraph workflow.

**Architecture:** The system uses local document loading, deterministic chunking, direct Chroma persistence, a fake offline LLM provider, a claim ledger, and a linear LangGraph workflow. The graph never loops and every final report is rendered from verified ledger state rather than raw agent prose.

**Tech Stack:** Python 3.11+, LangGraph, LangChain/Core, ChromaDB, Pydantic, Typer, python-dotenv, Rich, Pytest.

---

## File Structure

Create this structure:

```text
pyproject.toml
README.md
.env.example
company_docs/.gitkeep
src/decision_system/__init__.py
src/decision_system/cli.py
src/decision_system/config.py
src/decision_system/models.py
src/decision_system/graph/__init__.py
src/decision_system/graph/state.py
src/decision_system/graph/workflow.py
src/decision_system/graph/nodes.py
src/decision_system/agents/__init__.py
src/decision_system/agents/base.py
src/decision_system/agents/technical_analyst.py
src/decision_system/agents/risk_analyst.py
src/decision_system/agents/verifier.py
src/decision_system/agents/report_writer.py
src/decision_system/rag/__init__.py
src/decision_system/rag/loader.py
src/decision_system/rag/chunker.py
src/decision_system/rag/embeddings.py
src/decision_system/rag/vector_store.py
src/decision_system/rag/retriever.py
src/decision_system/ledger/__init__.py
src/decision_system/ledger/claim_ledger.py
src/decision_system/ledger/verifier.py
src/decision_system/reports/__init__.py
src/decision_system/reports/renderer.py
src/decision_system/llm/__init__.py
src/decision_system/llm/provider.py
src/decision_system/llm/fake_provider.py
src/decision_system/llm/openai_provider.py
src/decision_system/llm/ollama_provider.py
tests/test_document_loader.py
tests/test_chunker.py
tests/test_retriever.py
tests/test_claim_ledger.py
tests/test_verifier.py
tests/test_report_renderer.py
tests/test_workflow.py
tests/test_cli.py
```

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `.env.example`
- Create: `company_docs/.gitkeep`
- Create: package `__init__.py` files

- [ ] **Step 1: Write scaffold files**

Create `pyproject.toml` exactly:

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

Create `.env.example`:

```text
DECISION_DOCS_DIR=company_docs
DECISION_STORE_DIR=.decision_system/chroma
DECISION_COLLECTION=decision_chunks
DECISION_PROVIDER=fake
```

Create `README.md`:

````markdown
# Agentic Decision System

Backend-first v0.1 prototype for producing cited decision briefs from local company documents.

## Commands

```bash
decision-system index
decision-system ask "Should we proceed with Project X?"
```

The default provider is `fake`, so tests and local smoke runs do not require API keys.
````

Create empty `__init__.py` files in every package directory listed above.

- [ ] **Step 2: Verify scaffold imports**

Run:

```bash
python -m pytest -q
```

Expected: pytest starts and reports no tests collected or passes existing tests.

## Task 2: Shared Models and Workflow State

**Files:**
- Create: `src/decision_system/models.py`
- Create: `src/decision_system/graph/state.py`
- Test: `tests/test_claim_ledger.py`

- [ ] **Step 1: Write failing model smoke test**

Create `tests/test_claim_ledger.py` with:

```python
from decision_system.models import Claim, EvidenceChunk


def test_claim_defaults_to_pending():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="technical_analyst",
        claim_text="Billing migration requires rollback planning.",
        claim_type="technical",
    )

    assert claim.status == "pending"
    assert claim.evidence_ids == []
    assert claim.confidence == "low"


def test_evidence_chunk_preserves_source_metadata():
    chunk = EvidenceChunk(
        evidence_id="doc-a:chunk-0001",
        document_id="doc-a",
        source_path="company_docs/plan.md",
        source_filename="plan.md",
        chunk_id="chunk-0001",
        text="Migration requires rollback planning.",
    )

    assert chunk.source_filename == "plan.md"
    assert chunk.chunk_id == "chunk-0001"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_claim_ledger.py -q
```

Expected: FAIL because `decision_system.models` does not exist yet.

- [ ] **Step 3: Implement shared models**

Create `src/decision_system/models.py` with the model definitions from the design spec.

Create `src/decision_system/graph/state.py` with:

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

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_claim_ledger.py -q
```

Expected: PASS.

## Task 3: Document Loader and Chunker

**Files:**
- Create: `src/decision_system/rag/loader.py`
- Create: `src/decision_system/rag/chunker.py`
- Test: `tests/test_document_loader.py`
- Test: `tests/test_chunker.py`

- [ ] **Step 1: Write failing loader and chunker tests**

Create `tests/test_document_loader.py`:

```python
from decision_system.rag.loader import load_documents


def test_load_documents_reads_md_and_txt(tmp_path):
    docs_dir = tmp_path / "company_docs"
    docs_dir.mkdir()
    (docs_dir / "plan.md").write_text("Migration plan", encoding="utf-8")
    (docs_dir / "notes.txt").write_text("Incident notes", encoding="utf-8")
    (docs_dir / "ignore.json").write_text("{}", encoding="utf-8")

    docs = load_documents(docs_dir)

    assert len(docs) == 2
    assert {doc["source_filename"] for doc in docs} == {"plan.md", "notes.txt"}
    assert all(doc["document_id"].startswith("doc-") for doc in docs)
```

Create `tests/test_chunker.py`:

```python
from decision_system.rag.chunker import chunk_documents


def test_chunk_documents_preserves_stable_ids():
    docs = [
        {
            "document_id": "doc-test",
            "source_path": "company_docs/plan.md",
            "source_filename": "plan.md",
            "text": "A" * 1200,
        }
    ]

    chunks = chunk_documents(docs, chunk_size=1000, chunk_overlap=200)

    assert len(chunks) == 2
    assert chunks[0].evidence_id == "doc-test:chunk-0001"
    assert chunks[1].evidence_id == "doc-test:chunk-0002"
    assert chunks[0].source_filename == "plan.md"
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_document_loader.py tests/test_chunker.py -q
```

Expected: FAIL because loader and chunker modules do not exist.

- [ ] **Step 3: Implement loader and chunker**

`load_documents(path: Path | str) -> list[dict]`:

- Recursively reads `*.md` and `*.txt`
- Skips empty files
- Creates `document_id = "doc-" + sha1(relative_path.encode()).hexdigest()[:12]`
- Returns dicts with `document_id`, `source_path`, `source_filename`, `text`

`chunk_documents(documents, chunk_size=1000, chunk_overlap=200) -> list[EvidenceChunk]`:

- Splits by character windows
- Advances by `chunk_size - chunk_overlap`
- Creates chunk IDs `chunk-0001`, `chunk-0002`
- Creates evidence IDs `{document_id}:{chunk_id}`

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_document_loader.py tests/test_chunker.py -q
```

Expected: PASS.

## Task 4: Chroma Indexing and Retrieval

**Files:**
- Create: `src/decision_system/config.py`
- Create: `src/decision_system/rag/embeddings.py`
- Create: `src/decision_system/rag/vector_store.py`
- Create: `src/decision_system/rag/retriever.py`
- Test: `tests/test_retriever.py`

- [ ] **Step 1: Write failing retrieval test**

Create `tests/test_retriever.py`:

```python
from decision_system.models import EvidenceChunk
from decision_system.rag.vector_store import index_chunks
from decision_system.rag.retriever import retrieve_evidence


def test_retrieval_returns_citation_ready_evidence(tmp_path):
    store_dir = tmp_path / "chroma"
    chunks = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning and staged deployment.",
        )
    ]

    index_chunks(chunks, store_dir=store_dir, collection_name="test_chunks")
    results = retrieve_evidence(
        "billing rollback migration",
        store_dir=store_dir,
        collection_name="test_chunks",
        top_k=3,
    )

    assert len(results) == 1
    assert results[0].evidence_id == "doc-a:chunk-0001"
    assert results[0].source_filename == "billing.md"
    assert results[0].score is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_retriever.py -q
```

Expected: FAIL because vector store modules do not exist.

- [ ] **Step 3: Implement config, embeddings, vector store, and retriever**

Implementation requirements:

- `Settings` in `config.py` reads:
  - `DECISION_DOCS_DIR`, default `company_docs`
  - `DECISION_STORE_DIR`, default `.decision_system/chroma`
  - `DECISION_COLLECTION`, default `decision_chunks`
  - `DECISION_PROVIDER`, default `fake`
- `HashEmbeddingFunction` returns deterministic normalized vectors.
- `index_chunks` resets or recreates the target collection before adding chunks.
- `retrieve_evidence` returns `list[EvidenceChunk]` reconstructed from Chroma IDs, documents, metadata, and distances.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_retriever.py -q
```

Expected: PASS.

## Task 5: Claim Ledger and Verifier

**Files:**
- Create: `src/decision_system/ledger/claim_ledger.py`
- Create: `src/decision_system/ledger/verifier.py`
- Test: `tests/test_claim_ledger.py`
- Test: `tests/test_verifier.py`

- [ ] **Step 1: Extend claim ledger tests**

Add to `tests/test_claim_ledger.py`:

```python
from decision_system.ledger.claim_ledger import ClaimLedger


def test_ledger_preserves_contradicted_claims():
    ledger = ClaimLedger()
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="risk_analyst",
        claim_text="Migration can happen without downtime.",
        claim_type="risk",
    )

    ledger.add_claims([claim])
    ledger.update_status(
        claim_id="claim-1",
        status="contradicted",
        confidence="high",
        verification_notes="Evidence explicitly contradicts the claim.",
        contradicting_evidence_ids=["doc-a:chunk-0001"],
    )

    stored = ledger.all_claims()[0]
    assert stored.status == "contradicted"
    assert stored.contradicting_evidence_ids == ["doc-a:chunk-0001"]
```

Create `tests/test_verifier.py`:

```python
from decision_system.ledger.verifier import verify_claims
from decision_system.models import Claim, EvidenceChunk


def test_verifier_marks_claim_without_evidence_as_unsupported():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="technical_analyst",
        claim_text="The legacy server supports OAuth2.",
        claim_type="technical",
    )

    updated, results = verify_claims([claim], [])

    assert updated[0].status == "unsupported"
    assert results[0].verification_notes


def test_verifier_marks_explicit_contradiction():
    claim = Claim(
        claim_id="claim-1",
        run_id="run-1",
        source_agent="risk_analyst",
        claim_text="Migration can happen without downtime.",
        claim_type="risk",
        evidence_ids=["doc-a:chunk-0001"],
    )
    evidence = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="CONTRADICTS: Migration can happen without downtime.",
        )
    ]

    updated, results = verify_claims([claim], evidence)

    assert updated[0].status == "contradicted"
    assert results[0].contradicting_evidence_ids == ["doc-a:chunk-0001"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_claim_ledger.py tests/test_verifier.py -q
```

Expected: FAIL because ledger and verifier modules do not exist.

- [ ] **Step 3: Implement ledger and verifier**

`ClaimLedger` methods:

- `add_claims(claims: list[Claim]) -> None`
- `all_claims() -> list[Claim]`
- `update_status(...) -> Claim`

`verify_claims(claims, evidence)` rules:

- No valid `evidence_ids`: `unsupported`
- Any cited evidence text containing `CONTRADICTS:`: `contradicted`
- Otherwise valid cited evidence: `verified`

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python -m pytest tests/test_claim_ledger.py tests/test_verifier.py -q
```

Expected: PASS.

## Task 6: Fake Provider and Bounded Agents

**Files:**
- Create: `src/decision_system/llm/provider.py`
- Create: `src/decision_system/llm/fake_provider.py`
- Create: `src/decision_system/llm/openai_provider.py`
- Create: `src/decision_system/llm/ollama_provider.py`
- Create: `src/decision_system/agents/base.py`
- Create: `src/decision_system/agents/technical_analyst.py`
- Create: `src/decision_system/agents/risk_analyst.py`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Add fake provider tests to workflow test file**

Create `tests/test_workflow.py` with:

```python
from decision_system.llm.fake_provider import FakeProvider
from decision_system.models import AgentMemo, EvidenceChunk


def test_fake_provider_returns_structured_memos_and_claims():
    evidence = [
        EvidenceChunk(
            evidence_id="doc-a:chunk-0001",
            document_id="doc-a",
            source_path="company_docs/billing.md",
            source_filename="billing.md",
            chunk_id="chunk-0001",
            text="Billing migration requires rollback planning.",
        )
    ]
    provider = FakeProvider()

    technical = provider.technical_memo("Should we migrate billing?", evidence)
    risk = provider.risk_memo("Should we migrate billing?", evidence, technical)
    claims = provider.extract_claims("run-1", [technical, risk])

    assert isinstance(technical, AgentMemo)
    assert isinstance(risk, AgentMemo)
    assert claims
    assert claims[0].evidence_ids == ["doc-a:chunk-0001"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_workflow.py -q
```

Expected: FAIL because provider modules do not exist.

- [ ] **Step 3: Implement provider interface, fake provider, and agent wrappers**

Implementation requirements:

- `LLMProvider` protocol exposes the methods from the design spec.
- `FakeProvider` creates deterministic memos using the first retrieved evidence chunk.
- `FakeProvider.extract_claims` creates one claim per cited memo claim.
- Provider stubs for OpenAI/Ollama raise `NotImplementedError`.
- Agent modules are thin wrappers around provider methods and return structured models.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_workflow.py -q
```

Expected: PASS.

## Task 7: Report Renderer

**Files:**
- Create: `src/decision_system/reports/renderer.py`
- Create: `src/decision_system/agents/report_writer.py`
- Test: `tests/test_report_renderer.py`

- [ ] **Step 1: Write failing report test**

Create `tests/test_report_renderer.py`:

```python
from decision_system.models import Claim
from decision_system.reports.renderer import render_decision_report


def test_report_includes_required_sections_and_ledger_claims():
    claims = [
        Claim(
            claim_id="claim-1",
            run_id="run-1",
            source_agent="technical_analyst",
            claim_text="Billing migration requires rollback planning.",
            claim_type="technical",
            status="verified",
            evidence_ids=["doc-a:chunk-0001"],
            confidence="high",
            verification_notes="Cited evidence supports the claim.",
        ),
        Claim(
            claim_id="claim-2",
            run_id="run-1",
            source_agent="risk_analyst",
            claim_text="Migration can happen without downtime.",
            claim_type="risk",
            status="contradicted",
            contradicting_evidence_ids=["doc-a:chunk-0002"],
            confidence="high",
            verification_notes="Contradiction marker found.",
        ),
    ]

    report = render_decision_report("Should we migrate billing?", "run-1", claims)

    assert "## Recommendation" in report.markdown
    assert "## Evidence Citations" in report.markdown
    assert "doc-a:chunk-0001" in report.markdown
    assert report.contradictions[0].claim_id == "claim-2"
    assert report.human_review_required
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_report_renderer.py -q
```

Expected: FAIL because renderer does not exist.

- [ ] **Step 3: Implement report renderer**

`render_decision_report(question, run_id, claims) -> DecisionReport`:

- Builds recommendation from verified claims.
- Includes all required Markdown sections.
- Adds citations from verified claim evidence IDs.
- Lists contradicted claims.
- Lists unsupported claims.
- Sets confidence:
  - `low` if no verified claims or any contradiction exists
  - `medium` if verified claims exist and unsupported claims exist
  - `high` if verified claims exist and no unsupported or contradicted claims exist
- Adds human review items for contradictions and unsupported assumptions.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_report_renderer.py -q
```

Expected: PASS.

## Task 8: LangGraph Workflow

**Files:**
- Create: `src/decision_system/graph/nodes.py`
- Create: `src/decision_system/graph/workflow.py`
- Modify: `tests/test_workflow.py`

- [ ] **Step 1: Add graph execution test**

Add to `tests/test_workflow.py`:

```python
from decision_system.graph.workflow import build_workflow


def test_workflow_runs_to_final_report_without_loops():
    graph = build_workflow()
    result = graph.invoke(
        {
            "run_id": "run-1",
            "question": "Should we migrate billing?",
            "top_k": 3,
            "retrieved_evidence": [
                EvidenceChunk(
                    evidence_id="doc-a:chunk-0001",
                    document_id="doc-a",
                    source_path="company_docs/billing.md",
                    source_filename="billing.md",
                    chunk_id="chunk-0001",
                    text="Billing migration requires rollback planning.",
                )
            ],
        }
    )

    assert result["final_report"].markdown.startswith("# Decision Report")
    assert result["claims"]
    assert all(claim.status != "pending" for claim in result["claims"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_workflow.py -q
```

Expected: FAIL because workflow does not exist.

- [ ] **Step 3: Implement graph nodes and workflow**

`nodes.py` functions:

- `retrieve_evidence_node(state) -> dict`
- `technical_analyst_node(state) -> dict`
- `risk_analyst_node(state) -> dict`
- `claim_extraction_node(state) -> dict`
- `verifier_node(state) -> dict`
- `report_writer_node(state) -> dict`

`workflow.py`:

```python
from langgraph.graph import END, START, StateGraph

from decision_system.graph.nodes import (
    claim_extraction_node,
    report_writer_node,
    retrieve_evidence_node,
    risk_analyst_node,
    technical_analyst_node,
    verifier_node,
)
from decision_system.graph.state import WorkflowState


def build_workflow():
    builder = StateGraph(WorkflowState)
    builder.add_node("retrieve_evidence", retrieve_evidence_node)
    builder.add_node("technical_analyst", technical_analyst_node)
    builder.add_node("risk_analyst", risk_analyst_node)
    builder.add_node("claim_extraction", claim_extraction_node)
    builder.add_node("verifier", verifier_node)
    builder.add_node("report_writer", report_writer_node)
    builder.add_edge(START, "retrieve_evidence")
    builder.add_edge("retrieve_evidence", "technical_analyst")
    builder.add_edge("technical_analyst", "risk_analyst")
    builder.add_edge("risk_analyst", "claim_extraction")
    builder.add_edge("claim_extraction", "verifier")
    builder.add_edge("verifier", "report_writer")
    builder.add_edge("report_writer", END)
    return builder.compile()
```

`retrieve_evidence_node` should return existing `retrieved_evidence` unchanged when present. This keeps workflow tests independent from Chroma.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_workflow.py -q
```

Expected: PASS.

## Task 9: CLI Commands

**Files:**
- Create: `src/decision_system/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from decision_system.cli import app


def test_cli_index_and_ask(tmp_path, monkeypatch):
    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "billing.md").write_text(
        "Billing migration requires rollback planning.",
        encoding="utf-8",
    )
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", "test_cli_chunks")

    runner = CliRunner()
    index_result = runner.invoke(app, ["index"])
    ask_result = runner.invoke(app, ["ask", "Should we migrate billing?"])

    assert index_result.exit_code == 0
    assert "Indexed" in index_result.output
    assert ask_result.exit_code == 0
    assert "# Decision Report" in ask_result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_cli.py -q
```

Expected: FAIL because CLI does not exist.

- [ ] **Step 3: Implement CLI**

Implementation requirements:

- Use Typer.
- `index` command:
  - Load settings.
  - Load docs.
  - Chunk docs.
  - Index chunks.
  - Print `Indexed {document_count} documents into {chunk_count} chunks.`
- `ask` command:
  - Load settings.
  - Generate `run_id`.
  - Build workflow.
  - Invoke graph with question, run ID, and top_k.
  - Print `final_report.markdown` with Rich.

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
python -m pytest tests/test_cli.py -q
```

Expected: PASS.

## Task 10: Full Verification and Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Expand README usage**

Add:

````markdown
## Setup

```bash
python -m pip install -e ".[dev]"
```

## Example

```bash
mkdir -p company_docs
echo "Billing migration requires rollback planning." > company_docs/billing.md
decision-system index
decision-system ask "Should we migrate billing?"
```

## v0.1 Limits

- Uses fake provider by default.
- Supports `.md` and `.txt`.
- Does not include a frontend or database.
- Does not execute external actions.
````

- [ ] **Step 2: Run all tests**

Run:

```bash
python -m pytest -q
```

Expected: all tests PASS.

- [ ] **Step 3: Run CLI smoke test**

Run:

```bash
decision-system index
decision-system ask "Should we migrate billing?"
```

Expected: the first command prints indexed document and chunk counts. The second command prints a Markdown decision report.

## Acceptance Checklist

- [ ] Documents load from `company_docs/`.
- [ ] Chunks preserve source filename and chunk ID.
- [ ] Retrieval returns citation-ready evidence.
- [ ] Claims are marked `verified`, `unsupported`, or `contradicted`.
- [ ] Report uses the claim ledger, not raw agent text.
- [ ] Workflow terminates without loops.
- [ ] Tests pass without real API keys.
- [ ] `FakeProvider` is the default.
- [ ] OpenAI and Ollama providers are stubs only.
- [ ] No frontend is added.
- [ ] No database complexity is added.
- [ ] No extra agents are added.
