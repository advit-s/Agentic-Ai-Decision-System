"""Evidence retrieval from the local Chroma index.

The retriever returns `EvidenceChunk` objects only. It never answers the user
question directly, preserving the separation between retrieval and synthesis.
"""

from pathlib import Path

import chromadb

from decision_system.models import EvidenceChunk
from decision_system.rag.embeddings import HashEmbeddingFunction


def retrieve_evidence(
    query: str,
    store_dir: Path | str,
    collection_name: str,
    top_k: int = 6,
) -> list[EvidenceChunk]:
    """Retrieve citation-ready evidence chunks for a question.

    Args:
        query: User decision question or retrieval query.
        store_dir: Local Chroma persistence directory.
        collection_name: Chroma collection to query.
        top_k: Maximum number of chunks to return.

    Returns:
        Ranked `EvidenceChunk` records with source metadata and distance score.
    """

    if top_k <= 0:
        return []

    client = chromadb.PersistentClient(path=str(store_dir))
    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=HashEmbeddingFunction(),
        )

        chunk_count = collection.count()
        if chunk_count == 0:
            return []

        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, chunk_count),
            include=["documents", "metadatas", "distances"],
        )

        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        evidence: list[EvidenceChunk] = []
        for index, evidence_id in enumerate(ids):
            metadata = metadatas[index] or {}
            evidence.append(
                EvidenceChunk(
                    evidence_id=str(metadata.get("evidence_id", evidence_id)),
                    document_id=str(metadata["document_id"]),
                    source_path=str(metadata["source_path"]),
                    source_filename=str(metadata["source_filename"]),
                    chunk_id=str(metadata["chunk_id"]),
                    text=documents[index],
                    score=float(distances[index]) if index < len(distances) else None,
                )
            )

        return evidence
    finally:
        client.close()
