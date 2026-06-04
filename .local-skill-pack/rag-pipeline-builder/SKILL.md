---
name: rag-pipeline-builder
description: Use this when building or modifying retrieval-augmented generation for the agentic company decision system, including ingestion, chunking, embeddings, retrievers, rerankers, citations, and retrieval evaluation.
---

# RAG Pipeline Builder

Use this skill to build retrieval that produces inspectable evidence, not just plausible answers.

## Pipeline

1. Load documents from approved local or uploaded sources.
2. Normalize metadata: document ID, title, path, owner, version, timestamp.
3. Chunk text with stable chunk IDs.
4. Embed chunks and store vectors with metadata.
5. Retrieve candidate chunks for a decision question.
6. Rerank or filter for relevance.
7. Return evidence objects with citations.

## Rules

- Keep chunk IDs stable across reruns when document content is unchanged.
- Store source metadata with every chunk.
- Return cited evidence separately from generated analysis.
- Avoid answering from model memory when retrieval is expected.
- Add retrieval tests for missing documents, irrelevant documents, and conflicting evidence.

## Output Shape

Prefer structured evidence objects:

```json
{
  "evidence_id": "doc-001:chunk-003",
  "document_id": "doc-001",
  "quote_or_summary": "Relevant evidence summary",
  "relevance_reason": "Why this supports or challenges the decision"
}
```
