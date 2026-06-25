"""Data Source API endpoints — upload, list, get, delete, parse, index, status.

All file storage is local under .decision_system/. No external services required.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel

from decision_system.identity.models import LocalUser, Permission
from decision_system.identity.permissions import (
    require_permission,
    require_workspace_permission,
)
from decision_system.data_sources.models import (
    DataSource,
    DataSourceChunk,
    DataSourceStatus,
    DatasetProfile,
    EvidenceSearchResponse,
    EvidenceSearchResult,
    ParseResult,
)
from decision_system.data_sources.parser import (
    get_supported_extensions,
    parse_document,
    profile_csv,
    profile_json_content,
    get_parser,
    PdfParser,
    DocxParser,
    XlsxParser,
)
from decision_system.data_sources.store import DataSourceStore, sanitize_filename

MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB

SUPPORTED_UPLOAD_EXTENSIONS: set[str] = {"txt", "md", "json", "csv", "pdf", "docx", "xlsx", "png", "jpg", "jpeg", "tiff", "tif", "bmp"}

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



    """Map file extension to source type."""
    doc_types = {"pdf", "docx", "txt", "md", "html", "json", "xml"}
    dataset_types = {"csv", "xlsx", "xls", "tsv"}
    if file_type in doc_types:
        return "document"
    elif file_type in dataset_types:
        return "dataset"
    return "unknown"
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
    user: LocalUser = Depends(require_workspace_permission(Permission.DATA_SOURCE_UPLOAD)),
    filename: str = Query(..., description="Original filename with extension"),
    content: bytes = Body(..., description="Raw file content as bytes"),
) -> dict[str, Any]:
    """Upload a local file as a workspace data source.

    Send file content as raw bytes in the request body.
    Filename is passed as a query parameter.

    Supported file types: txt, md, json, csv, pdf, docx, xlsx.
    Files are stored under .decision_system/files/{workspace_id}/.
    File size limited to 100 MB.
    """
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(filename).suffix.lower()
    file_type = _get_file_type(filename)
    source_type = _get_source_type(file_type)

    if file_type not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsupported_file_type",
                "message": f"Unsupported file type: {ext}. Supported types: {', '.join(sorted(SUPPORTED_UPLOAD_EXTENSIONS))}",
                "supported_extensions": sorted(SUPPORTED_UPLOAD_EXTENSIONS),
            },
        )

    size_bytes = len(content)
    if size_bytes > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "file_too_large",
                "message": f"File size {size_bytes} bytes exceeds maximum of {MAX_UPLOAD_SIZE_BYTES} bytes",
                "max_size_bytes": MAX_UPLOAD_SIZE_BYTES,
            },
        )
    content_hash = hashlib.sha256(content).hexdigest()

    # Sanitize filename for path traversal protection
    safe_filename = sanitize_filename(filename)
    if safe_filename != filename:
        filename = safe_filename

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
        source_id=source_id,
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
def list_data_sources(workspace_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ))) -> dict[str, Any]:
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
def get_data_source(workspace_id: str, source_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ))) -> dict[str, Any]:
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
def delete_data_source(
    workspace_id: str,
    source_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.DATA_SOURCE_DELETE)),
) -> dict[str, Any]:
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
def parse_data_source(
    workspace_id: str,
    source_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.DATA_SOURCE_PARSE_INDEX)),
) -> dict[str, Any]:
    """Parse a document or dataset file into chunks using the local parser.

    Supports txt, md, json, pdf, docx, csv, xlsx.
    PDF uses text extraction only (no OCR).
    XLSX and CSV also produce a dataset profile.
    """
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    file_path = Path(source.local_path) if source.local_path else None
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=400, detail="File not found on disk")

    store.update_status(workspace_id, source_id, DataSourceStatus.PARSING)
    _emit_audit_event("document_parse_started", {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "file_type": source.file_type,
    })

    ext = f".{source.file_type}"
    # CSV is handled via profile, not the parser registry
    if source.file_type == "csv":
        return _parse_csv(store, source, file_path, workspace_id, source_id)

    parser = get_parser(ext)
    if parser is None:
        store.update_status(workspace_id, source_id, DataSourceStatus.UNSUPPORTED,
                           f"No parser for {ext}")
        raise HTTPException(status_code=400,
                           detail=f"No parser available for file type: {source.file_type}")

    try:
        result = parser.parse(file_path, source_id, workspace_id)
    except Exception as e:
        store.update_status(workspace_id, source_id, DataSourceStatus.FAILED, str(e))
        _emit_audit_event("document_parse_failed", {
            "source_id": source_id,
            "workspace_id": workspace_id,
            "error": str(e),
        })
        raise HTTPException(status_code=400, detail=str(e))

    has_warnings = len(result.warnings) > 0
    has_chunks = len(result.chunks) > 0

    if has_chunks:
        store.save_chunks(result.chunks)

    status = DataSourceStatus.PARSED_WITH_WARNINGS if has_warnings else DataSourceStatus.PARSED
    store.update_status(workspace_id, source_id, status)

    # Save parser metadata
    meta = dict(source.metadata or {})
    meta["parser_name"] = result.parser_name
    meta["parser_version"] = result.parser_version or ""
    meta["chunk_count"] = len(result.chunks)
    meta["warnings"] = result.warnings
    # Reload to get updated status from update_status()
    source = store.load(workspace_id, source_id) or source
    source.metadata = meta
    store.save(source)

    # Generate profile for datasets
    profile_data = None
    if source.file_type == "csv":
        from datetime import datetime, timezone
        content = file_path.read_text(encoding="utf-8")
        profile_data = profile_csv(content, source_id, workspace_id)
        if "error" not in profile_data:
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
            meta["profile_available"] = True
    elif source.file_type == "xlsx":
        from datetime import datetime, timezone
        xlsx_parser = XlsxParser()
        profile_result = xlsx_parser.profile(file_path, source_id, workspace_id)
        if "error" not in profile_result:
            profile = DatasetProfile(
                profile_id=str(uuid4()),
                source_id=source_id,
                workspace_id=workspace_id,
                row_count=sum(s.get("row_count", 0) for s in profile_result.get("sheets", [])),
                column_count=sum(s.get("column_count", 0) for s in profile_result.get("sheets", [])),
                columns=[col for s in profile_result.get("sheets", []) for col in s.get("columns", [])],
                warnings=[w for s in profile_result.get("sheets", []) for w in s.get("warnings", [])],
                created_at=datetime.now(timezone.utc),
            )
            store.save_profile(profile)
            profile_data = profile_result
            meta["profile_available"] = True
    # Reload to get updated status from update_status()
    source = store.load(workspace_id, source_id) or source
    source.metadata = meta
    store.save(source)

    _emit_audit_event("document_parse_completed", {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "file_type": source.file_type,
        "chunk_count": len(result.chunks),
        "warnings_count": len(result.warnings),
    })

    return {
        "status": status,
        "source_id": source_id,
        "chunk_count": len(result.chunks),
        "warnings": result.warnings,
        "metadata": result.metadata,
        "profile": profile_data,
    }

@router.post("/workspaces/{workspace_id}/data-sources/{source_id}/index")
def index_data_source(
    workspace_id: str,
    source_id: str,
    user: LocalUser = Depends(require_workspace_permission(Permission.DATA_SOURCE_PARSE_INDEX)),
) -> dict[str, Any]:
    """Index a parsed data source into the vector store for evidence search.

    Falls back to keyword search if vector dependencies are unavailable.
    """
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    if source.status not in ("parsed", "parsed_with_warnings"):
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
                source_filename=source.original_filename or source.name,
                chunk_id=c.chunk_id,
                text=c.text,
                workspace_id=workspace_id,
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
def get_data_source_profile(workspace_id: str, source_id: str, user: LocalUser = Depends(require_workspace_permission(Permission.WORKSPACE_READ))) -> dict[str, Any]:
    """Get the profile of a dataset data source (CSV/JSON)."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")

    if source.file_type not in ("csv", "json", "xlsx"):
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
    workspace_id: str,
    request: EvidenceSearchRequest,
    user: LocalUser = Depends(require_workspace_permission(Permission.EVIDENCE_SEARCH)),
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
            workspace_id=workspace_id,
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

def _parse_csv(store, source, file_path, workspace_id, source_id):
    """Parse a CSV file: generate profile and return result."""
    from datetime import datetime, timezone
    content = file_path.read_text(encoding="utf-8")
    profile_data = profile_csv(content, source_id, workspace_id)

    if "error" in profile_data:
        store.update_status(workspace_id, source_id, DataSourceStatus.FAILED, profile_data["error"])
        raise HTTPException(status_code=400, detail=profile_data["error"])

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
        categorical_summary=profile_data.get("categorical_summary", []),
        date_like_columns=profile_data.get("date_like_columns", []),
        sample_rows=profile_data.get("sample_rows", []),
        warnings=profile_data.get("warnings", []),
        created_at=datetime.now(timezone.utc),
    )
    store.save_profile(profile)
    store.update_status(workspace_id, source_id, DataSourceStatus.PARSED)

    # Update source metadata
    source = store.load(workspace_id, source_id) or source
    meta = dict(source.metadata or {})
    meta["parser_name"] = "csv-profiler"
    meta["profile_available"] = True
    meta["warnings"] = profile_data.get("warnings", [])
    source.metadata = meta
    store.save(source)

    return {
        "status": DataSourceStatus.PARSED,
        "source_id": source_id,
        "chunk_count": 0,
        "warnings": profile_data.get("warnings", []),
        "metadata": {"parser": "csv-profiler"},
        "profile": profile_data,
    }



@router.get("/workspaces/{workspace_id}/data-sources/{source_id}/chunks")
def get_data_source_chunks(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Retrieve parsed chunks for a data source."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    chunks = store.load_chunks(workspace_id, source_id)
    return {
        "source_id": source_id,
        "chunk_count": len(chunks),
        "chunks": [c.model_dump(mode="json") for c in chunks],
    }


@router.get("/workspaces/{workspace_id}/data-sources/{source_id}/preview")
def get_data_source_preview(workspace_id: str, source_id: str) -> dict[str, Any]:
    """Preview a parsed data source: first chunks, metadata, warnings, profile."""
    store = _get_store()
    source = store.load(workspace_id, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found")
    chunks = store.load_chunks(workspace_id, source_id)
    profile = store.load_profile(workspace_id, source_id)
    return {
        "source_id": source_id,
        "name": source.name,
        "file_type": source.file_type,
        "status": source.status,
        "chunk_count": len(chunks),
        "preview_chunks": [c.model_dump(mode="json") for c in chunks[:5]],
        "warnings": source.metadata.get("warnings", []) if source.metadata else [],
        "metadata": source.metadata,
        "profile": profile.model_dump(mode="json") if profile else None,
        "error_message": source.error_message,
    }
