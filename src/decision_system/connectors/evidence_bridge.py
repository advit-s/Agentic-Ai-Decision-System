"""Bridge connector-fetched content into the local evidence system.

Transforms ``ConnectorFetchedContent`` from import/sync jobs into
workspace ``DataSource`` records, chunks them via the text parser,
and indexes them into Chroma for evidence search.

This module closes the gap identified in the repository audit between
connector import plumbing and searchable workspace evidence.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from decision_system._data_root import get_data_root
from decision_system.config import load_settings
from decision_system.connectors.models import ConnectorFetchedContent
from decision_system.data_sources.models import DataSource
from decision_system.data_sources.parser import parse_text
from decision_system.data_sources.store import DataSourceStore
from decision_system.rag.vector_store import index_chunks

logger = logging.getLogger(__name__)


def _find_existing_datasource(
    store: DataSourceStore,
    workspace_id: str,
    connector_id: str,
    external_id: str,
) -> DataSource | None:
    """Find an existing DataSource with matching connector_id + external_id metadata."""
    if not connector_id or not external_id:
        return None
    sources = store.list_by_workspace(workspace_id)
    for src in sources:
        if (
            src.metadata
            and src.metadata.get("connector_id") == connector_id
            and src.metadata.get("external_id") == external_id
        ):
            return src
    return None


def persist_connector_content(
    workspace_id: str,
    content_list: list[ConnectorFetchedContent],
    connector_name: str = "connector",
    connector_id: str = "",
) -> dict[str, Any]:
    """Persist connector-fetched content as workspace evidence.

    For each content item:
    1. Creates a ``DataSource`` record in the workspace data source store
    2. Parses text content into chunks
    3. Indexes chunks into Chroma for evidence search

    Args:
        workspace_id: Target workspace.
        content_list: Fetched content items from a connector import/sync.
        connector_name: Human-readable connector name (for data source names).
        connector_id: Connector identifier (for metadata).

    Returns:
        Summary dict with counts of data_sources, chunks, indexed.
    """
    store = DataSourceStore()
    settings = load_settings()
    all_chunks: list[Any] = []
    ds_count = 0
    chunk_count = 0
    errors: list[str] = []

    for item in content_list:
        if not item.content_text and not item.content_bytes:
            continue

        try:
            content_bytes = item.content_bytes or item.content_text.encode("utf-8")
            content_hash = hashlib.sha256(content_bytes).hexdigest()
            content_type = (item.metadata or {}).get("content_type", "text/plain")
            file_type = _content_type_to_file_type(content_type)
            url = (item.metadata or {}).get("url", "")

            # Check for existing DataSource with same connector_id + external_id
            existing_ds = _find_existing_datasource(
                store, workspace_id, connector_id, item.external_id
            )
            if existing_ds is not None:
                # Content unchanged — skip to avoid duplicate DataSource records
                if existing_ds.content_hash == content_hash:
                    continue
                # Content changed — update existing record
                existing_ds.content_hash = content_hash
                existing_ds.status = "parsed"
                existing_ds.updated_at = datetime.now(timezone.utc)
                existing_ds.metadata["imported_at"] = datetime.now(timezone.utc).isoformat()
                if url:
                    existing_ds.metadata["source_url"] = url
                source_id = existing_ds.source_id
                # Delete old chunks before re-parsing
                try:
                    store.delete_chunks(workspace_id, source_id)
                except Exception as del_err:
                    logger.warning("Failed to delete old chunks: %s", del_err)
                store.save(existing_ds)
                ds_count += 1
            else:
                # 1. Create a new DataSource record
                source_id = str(uuid4())
                source = DataSource(
                    source_id=source_id,
                    workspace_id=workspace_id,
                    name=item.title or item.filename or f"{connector_name}-{item.external_id[:20]}",
                    source_type="connector",
                    file_type=file_type,
                    original_filename=item.filename or f"{source_id}.txt",
                    content_hash=content_hash,
                    status="parsed",
                    metadata={
                        "connector_id": connector_id,
                        "connector_name": connector_name,
                        "external_id": item.external_id,
                        "source_url": url,
                        "imported_at": datetime.now(timezone.utc).isoformat(),
                        "content_type": content_type,
                    },
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                store.save(source)
                ds_count += 1

            # 2. Parse text content into chunks
            text = item.content_text or ""
            if not text and item.content_bytes:
                text = item.content_bytes.decode("utf-8", errors="replace")

            if text.strip():
                chunks = parse_text(text, source_id, workspace_id)
                # Add metadata to chunks for better provenance
                for c in chunks:
                    if c.metadata is None:
                        c.metadata = {}
                    c.metadata["connector_id"] = connector_id
                    c.metadata["external_id"] = item.external_id
                    if url:
                        c.metadata["source_url"] = url
                    if item.title:
                        c.metadata["title"] = item.title
                all_chunks.extend(chunks)
                chunk_count += len(chunks)

            # Save chunks to local store for keyword fallback search
            try:
                store.save_chunks(chunks)
            except Exception as chunk_save_err:
                logger.warning("Failed to save chunks locally: %s", chunk_save_err)

        except Exception as exc:
            logger.warning("Failed to persist connector item %s: %s", item.external_id, exc)
            errors.append(f"{item.external_id}: {exc}")

    # 3. Index chunks into Chroma
    indexed = 0
    if all_chunks:
        try:
            store_dir = (
                settings.store_dir if settings.store_dir else str(get_data_root() / "chroma")
            )
            indexed = index_chunks(
                chunks=[_to_evidence_chunk(c) for c in all_chunks],
                store_dir=store_dir,
                collection_name=settings.collection_name,
            )
        except Exception as exc:
            logger.warning("Failed to index connector chunks into Chroma: %s", exc)
            errors.append(f"chroma_index: {exc}")

    return {
        "data_sources_created": ds_count,
        "chunks_parsed": chunk_count,
        "chunks_indexed": indexed,
        "errors": errors,
    }


def _content_type_to_file_type(content_type: str) -> str:
    """Map MIME content type to a file type string for DataSource records."""
    ct = content_type.lower()
    if "html" in ct:
        return "html"
    if "csv" in ct:
        return "csv"
    if "json" in ct:
        return "json"
    if "xml" in ct:
        return "xml"
    if "markdown" in ct:
        return "md"
    if "text" in ct:
        return "txt"
    return "txt"


def _to_evidence_chunk(
    ds_chunk: Any,
) -> Any:
    """Convert a DataSourceChunk to an EvidenceChunk for Chroma indexing."""
    from decision_system.models import EvidenceChunk

    return EvidenceChunk(
        evidence_id=ds_chunk.chunk_id,
        document_id=ds_chunk.source_id,
        source_path=ds_chunk.metadata.get("source_url", "") if ds_chunk.metadata else "",
        source_filename=ds_chunk.metadata.get(
            "title", ds_chunk.metadata.get("original_filename", "")
        )
        if ds_chunk.metadata
        else "",
        chunk_id=ds_chunk.chunk_id,
        text=ds_chunk.text,
        workspace_id=ds_chunk.workspace_id,
        score=None,
    )
