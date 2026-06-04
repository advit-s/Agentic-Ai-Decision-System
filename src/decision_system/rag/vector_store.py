"""Persistent local Chroma indexing for evidence chunks.

The vector store is a local development dependency in v0.1. It is refreshed by
`decision-system index` and read by `decision-system ask`.
"""

from pathlib import Path

import chromadb

from decision_system.models import EvidenceChunk
from decision_system.rag.embeddings import HashEmbeddingFunction


def _client(store_dir: Path | str):
    """Create a persistent Chroma client for the configured local store."""

    return chromadb.PersistentClient(path=str(store_dir))


def index_chunks(
    chunks: list[EvidenceChunk],
    store_dir: Path | str,
    collection_name: str,
) -> int:
    """Refresh a Chroma collection with evidence chunks.

    Args:
        chunks: Evidence chunks to index.
        store_dir: Local persistent Chroma directory.
        collection_name: Target collection name.

    Returns:
        Number of chunks written.

    Side effects:
        Deletes and recreates the named local Chroma collection.
    """

    client = _client(store_dir)
    try:
        # v0.1 refreshes the whole collection for predictable local behavior.
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=HashEmbeddingFunction(),
    )

    if not chunks:
        return 0

    collection.add(
        ids=[chunk.evidence_id for chunk in chunks],
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "evidence_id": chunk.evidence_id,
                "document_id": chunk.document_id,
                "source_path": chunk.source_path,
                "source_filename": chunk.source_filename,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in chunks
        ],
    )
    return len(chunks)
