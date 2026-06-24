"""Persistent local Chroma indexing for evidence chunks.

The vector store is a local development dependency in v0.1. It is refreshed by
`decision-system index` and read by `decision-system ask`.
"""

from pathlib import Path

import chromadb
from pydantic import BaseModel, Field

from decision_system.models import EvidenceChunk
from decision_system.rag.embeddings import HashEmbeddingFunction


class CollectionInspection(BaseModel):
    """Inspectable summary of the configured Chroma collection."""

    collection_name: str
    chunk_count: int = 0
    source_filenames: list[str] = Field(default_factory=list)
    exists: bool = False


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
                    "workspace_id": chunk.workspace_id or "",
                }
                for chunk in chunks
            ],
        )
        return len(chunks)
    finally:
        client.close()


def inspect_collection(
    store_dir: Path | str,
    collection_name: str,
) -> CollectionInspection:
    """Read collection count and source filenames without mutating documents.

    Missing collections are reported as an empty inspection so the CLI can be
    used before the first successful index run.
    """

    client = _client(store_dir)
    try:
        try:
            collection = client.get_collection(
                name=collection_name,
                embedding_function=HashEmbeddingFunction(),
            )
        except Exception:
            return CollectionInspection(collection_name=collection_name)

        chunk_count = collection.count()
        if chunk_count == 0:
            return CollectionInspection(
                collection_name=collection_name,
                chunk_count=0,
                exists=True,
            )

        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", []) or []
        source_filenames = sorted(
            {
                str(metadata["source_filename"])
                for metadata in metadatas
                if metadata and metadata.get("source_filename")
            }
        )
        return CollectionInspection(
            collection_name=collection_name,
            chunk_count=chunk_count,
            source_filenames=source_filenames,
            exists=True,
        )
    finally:
        client.close()
