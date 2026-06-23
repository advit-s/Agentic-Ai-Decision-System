"""Data Source API endpoints — upload, list, get, delete, parse, index, status.

All file storage is local under .decision_system/. No external services required.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

from decision_system.data_sources.models import (
    DataSource,
    EvidenceSearchResponse,
    EvidenceSearchResult,
)
from decision_system.data_sources.parser import (
    get_supported_extensions,
    parse_document,
    profile_csv,
    profile_json_content,
)
from decision_system.data_sources.store import DataSourceStore

router = APIRouter(tags=["data-sources"])

# Shared store instance (stateless, file-backed)
_store = DataSourceStore()


class EvidenceSearchRequest(BaseModel):
    query: str
    limit: int = 10
    source_ids: list[str] = []
    file_types: list[str] = []


def _get_store() -> DataSourceStore:
    return _store


def _get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower().lstrip(".")
    return ext if ext else "unknown"


def _get_source_type(file_type: str) -> str:
    if file_type in ("csv", "xlsx", "json"):
        return "dataset"
    return "document"



def _emit_audit_event(event_type: str, data: dict) -> None:
    """Emit an audit event."""
    try:
        from decision_system.observability.store import record_metric_point
        record_metric_point(
            name=f"audit.{event_type}",
            value=1.0,
            tags=data,
        )
    except Exception:
        pass


@router.post("/workspaces/{workspace_id}/data-sources/upload")
def upload_data_source(
    workspace_id: str,
    filename: str = Query(..., description="Original filename with extension"),
    content: bytes = Body(..., description="Raw file content"),
) -> dict[str, Any]:
    """Upload a local file as a workspace data source.

    Send file content as raw bytes in the request body.
    Filename is passed as a query parameter.

    Supported file types: txt, md, csv, json.
    Files are stored under .decision_system/files/{workspace_id}/.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(filename).suffix.lower()
    file_type = _get_file_type(filename)
    source_type = _get_source_type(file_type)

    if file_type not in ("txt", "md", "csv", "json"):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsupported_file_type",
                "message": f"Unsupported file type: {ext}. Supported types: .txt, .md, .csv, .json",
                "supported_extensions": get_supported_extensions(),
            },
        )

    size_bytes = len(content)
    content_hash = hashlib.sha256(content).hexdigest()

    # Create data source record
    source_id = str(uuid4())
    store = _get_store()

    # Store file locally
    local_path = store.store_uploaded_file(workspace_id, source_id, filename, content)

    source = store.create(
        workspace_id=workspace_id,
        name=filename,
        source_type=source_type,
        file_type=file_type,
        original_filename=filename,
        local_path=local_path,
        size_bytes=size_bytes,
        content_hash=content_hash,
        metadata={"original_filename": filename},
    )

    _emit_audit_event("data_source_uploaded", {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "file_type": file_type,
        "size_bytes": size_bytes,
        "filename": filename,
    })
    return {
        "status": "uploaded",
        "data_source": source.model_dump(mode="json"),
    }


@router.get("/workspaces/{workspace_id}/data-sources")
def list_data_sources(workspace_id: str) -> dict[str, Any]:
    """List all data sources in a workspace."""
    store = _get_store()
    sources = store.list_by_workspace(workspace_id)
    return {
        "status": "ok",
        "workspace_id": workspace_id,
        "data_sources": [s.model_dump(mode="json") for s in sources],
        "count": len(sources),
    }


@router.get("/workspaces/{workspace_id}/data-sources/{source_id}")
def get_data_source(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Get a single data source."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {
        "status": "ok",
        "data_source": source.model_dump(mode="json"),
    }


@router.delete("/workspaces/{workspace_id}/data-sources/{source_id}")
def delete_data_source(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Delete a data source and its associated files/chunks."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    # Delete file
    if source.original_filename:
        store.delete_uploaded_file(workspace_id, source_id, source.original_filename)

    # Delete chunks
    store.delete_chunks(workspace_id, source_id)

    # Delete profile
    store.delete_profile(workspace_id, source_id)

    # Delete index metadata
    store.delete_index_metadata(workspace_id, source_id)

    # Delete metadata record
    store.delete(workspace_id, source_id)

    _emit_audit_event("data_source_deleted", {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "file_type": source.file_type,
        "original_filename": source.original_filename,
    })
    return {"status": "deleted", "source_id": source_id}


@router.post("/workspaces/{workspace_id}/data-sources/{source_id}/parse")
def parse_data_source(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Parse a document or dataset data source into chunks.

    For document types (txt, md, json): produces text chunks.
    For dataset types (csv): produces a profile.
    """
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    if source.file_type == "csv":
        # Profile CSV
        file_path = Path(source.local_path) if source.local_path else None
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=400, detail="File not found on disk")

        content = file_path.read_text(encoding="utf-8")
        profile_data = profile_csv(content, source_id, workspace_id)

        if "error" in profile_data:
            store.update_status(workspace_id, source_id, "failed", profile_data["error"])
            raise HTTPException(status_code=400, detail=profile_data["error"])

        # Save the profile
        from datetime import datetime, timezone
        from decision_system.data_sources.models import DatasetProfile
        profile = DatasetProfile(
            profile_id=str(uuid4()),
            source_id=source_id,
            workspace_id=workspace_id,
            row_count=profile_data.get("row_count", 0),
            column_count=profile_data.get("column_count", 0),
            columns=profile_data.get("columns", []),
            column_types=profile_data.get("column_types", {}),
            missing_values=profile_data.get("missing_values", {}),
            numeric_summary=profile_data.get("numeric_summary", {}),
            categorical_summary=profile_data.get("categorical_summary", {}),
            date_like_columns=profile_data.get("date_like_columns", []),
            sample_rows=profile_data.get("sample_rows", []),
            warnings=profile_data.get("warnings", []),
            created_at=datetime.now(timezone.utc),
        )
        store.save_profile(profile)
        store.update_status(workspace_id, source_id, "parsed")

        return {
            "status": "parsed",
            "source_id": source_id,
            "profile": profile_data,
            "warnings": profile_data.get("warnings", []),
        }

    elif source.file_type in ("txt", "md", "json"):
        # Parse document
        file_path = Path(source.local_path) if source.local_path else None
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=400, detail="File not found on disk")

        content = file_path.read_text(encoding="utf-8")
        ext = f".{source.file_type}"
        chunks, warnings = parse_document(content, ext, source_id, workspace_id)

        if not chunks and not warnings:
            store.update_status(workspace_id, source_id, "failed", "No content parsed")
            raise HTTPException(status_code=400, detail="No content to parse")

        store.save_chunks(chunks)
        status = "parsed" if not any("error" in w.lower() for w in warnings) else "failed"
        store.update_status(workspace_id, source_id, status)

        return {
            "status": status,
            "source_id": source_id,
            "chunk_count": len(chunks),
            "warnings": warnings,
        }

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Parsing not supported for file type: {source.file_type}",
        )


@router.post("/workspaces/{workspace_id}/data-sources/{source_id}/index")
def index_data_source(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Index a parsed data source into the vector store for evidence search.

    Falls back to keyword search if vector dependencies are unavailable.
    """
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    if source.status != "parsed":
        raise HTTPException(
            status_code=400,
            detail=f"Data source must be parsed before indexing. Current status: {source.status}",
        )

    # Load chunks
    chunks = store.load_chunks(workspace_id, source_id)
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks found to index")

    # Try Chroma vector indexing
    retrieval_mode = "keyword"
    try:
        from decision_system.rag.vector_store import index_chunks as index_to_chroma
        from decision_system.models import EvidenceChunk

        chroma_chunks = [
            EvidenceChunk(
                evidence_id=f"ds-{source_id}-{c.chunk_id}",
                document_id=source_id,
                source_path=source.local_path,
                source_filename=source.name,
                chunk_id=c.chunk_id,
                text=c.text,
                metadata={
                    "workspace_id": workspace_id,
                    "source_id": source_id,
                    "file_type": source.file_type,
                    "chunk_index": c.chunk_index,
                    "content_hash": source.content_hash,
                    "created_at": source.created_at.isoformat() if source.created_at else "",
                },
            )
            for c in chunks
        ]

        from decision_system.config import load_settings
        settings = load_settings()

        index_to_chroma(
            chroma_chunks,
            store_dir=settings.store_dir,
            collection_name=settings.collection_name,
        )
        retrieval_mode = "vector"
    except Exception:
        # Fallback to keyword (chunks are already stored for keyword search)
        pass

    # Save index metadata
    from datetime import datetime, timezone
    store.save_index_metadata(workspace_id, source_id, {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "source_name": source.name,
        "file_type": source.file_type,
        "chunk_count": len(chunks),
        "retrieval_mode": retrieval_mode,
        "indexed_at": datetime.now(timezone.utc).isoformat(),
    })

    store.update_status(workspace_id, source_id, "indexed")

    _emit_audit_event("document_indexed", {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "chunk_count": len(chunks),
        "retrieval_mode": retrieval_mode,
    })
    return {
        "status": "indexed",
        "source_id": source_id,
        "chunk_count": len(chunks),
        "retrieval_mode": retrieval_mode,
    }


@router.get("/workspaces/{workspace_id}/data-sources/{source_id}/status")
def get_data_source_status(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Get the current status of a data source."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    return {
        "status": source.status,
        "source_id": source_id,
        "workspace_id": workspace_id,
        "error_message": source.error_message,
        "updated_at": source.updated_at.isoformat() if source.updated_at else None,
    }


@router.get("/workspaces/{workspace_id}/data-sources/{source_id}/profile")
def get_data_source_profile(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Get the profile of a dataset data source (CSV/JSON)."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    if source.file_type not in ("csv", "json"):
        raise HTTPException(
            status_code=400,
            detail=f"Profiling not supported for file type: {source.file_type}",
        )

    profile = store.load_profile(workspace_id, source_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found. Parse the data source first.")

    return {
        "status": "ok",
        "profile": profile.model_dump(mode="json"),
    }


@router.post("/workspaces/{workspace_id}/evidence/search")
def search_evidence(
    workspace_id: str, request: EvidenceSearchRequest
) -> EvidenceSearchResponse:
    """Search workspace evidence.

    Uses Chroma vector search when available, falls back to keyword search.
    Results are always workspace-scoped.
    """
    store = _get_store()

    # Try vector search first
    try:
        from decision_system.config import load_settings
        from decision_system.rag.retriever import retrieve_evidence

        settings = load_settings()
        chunks = retrieve_evidence(
            query=request.query,
            store_dir=settings.store_dir,
            collection_name=settings.collection_name,
            top_k=request.limit,
        )

        if chunks:
            results = [
                EvidenceSearchResult(
                    evidence_id=c.evidence_id,
                    workspace_id=workspace_id,
                    source_id=c.document_id,
                    source_name=c.source_filename,
                    chunk_id=c.chunk_id,
                    text=c.text,
                    score=c.score or 0.0,
                    metadata={"source_path": c.source_path},
                )
                for c in chunks
            ]
            _emit_audit_event("evidence_search_run", {
                "workspace_id": workspace_id,
                "query": request.query,
                "limit": request.limit,
                "retrieval_mode": "vector",
                "result_count": len(results),
            })
            return EvidenceSearchResponse(
                results=results,
                query=request.query,
                limit=request.limit,
                retrieval_mode="vector",
                total_results=len(results),
            )
    except Exception:
        pass

    # Fallback to keyword search
    results = store.search_chunks_keyword(
        workspace_id=workspace_id,
        query=request.query,
        limit=request.limit,
        source_ids=request.source_ids if request.source_ids else None,
        file_types=request.file_types if request.file_types else None,
    )

    _emit_audit_event("evidence_search_run", {
        "workspace_id": workspace_id,
        "query": request.query,
        "limit": request.limit,
        "retrieval_mode": "keyword",
        "result_count": len(results),
    })
    return EvidenceSearchResponse(
        results=results,
        query=request.query,
        limit=request.limit,
        retrieval_mode="keyword",
        total_results=len(results),
    )
