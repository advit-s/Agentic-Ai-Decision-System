"""Deterministic document chunking for citation-ready evidence.

Chunks are plain character windows in v0.1. The goal is stable IDs and simple
local behavior, not production-grade semantic splitting.
"""

from decision_system.models import EvidenceChunk


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[EvidenceChunk]:
    """Split loaded documents into stable `EvidenceChunk` records.

    Args:
        documents: Loader output dictionaries.
        chunk_size: Maximum characters per chunk.
        chunk_overlap: Overlapping characters between adjacent chunks.

    Returns:
        Evidence chunks with stable `chunk-0001` style IDs.

    Raises:
        ValueError: If chunk sizing would create invalid windows.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be zero or greater")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[EvidenceChunk] = []
    step = chunk_size - chunk_overlap

    for document in documents:
        text = document["text"]
        if not text:
            continue

        chunk_number = 1
        for start in range(0, len(text), step):
            chunk_text = text[start : start + chunk_size]
            if not chunk_text:
                continue

            chunk_id = f"chunk-{chunk_number:04d}"
            chunks.append(
                EvidenceChunk(
                    evidence_id=f"{document['document_id']}:{chunk_id}",
                    document_id=document["document_id"],
                    source_path=document["source_path"],
                    source_filename=document["source_filename"],
                    chunk_id=chunk_id,
                    text=chunk_text,
                )
            )

            chunk_number += 1
            if start + chunk_size >= len(text):
                break

    return chunks
