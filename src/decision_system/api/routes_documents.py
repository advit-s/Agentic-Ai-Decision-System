"""Document indexing endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter

from decision_system.api.models import ApiRunResponse, ApiStatusResponse, IndexRequest, to_jsonable
from decision_system.config import load_settings
from decision_system.rag.chunker import chunk_documents
from decision_system.rag.loader import load_documents
from decision_system.rag.vector_store import index_chunks, inspect_collection


router = APIRouter(tags=["documents"])


@router.post("/documents/index", response_model=ApiRunResponse)
def index_documents(request: IndexRequest | None = None) -> ApiRunResponse:
    request = request or IndexRequest()
    settings = load_settings()
    docs_dir = Path(request.docs_dir) if request.docs_dir else settings.docs_dir
    store_dir = Path(request.store_dir) if request.store_dir else settings.store_dir
    collection_name = request.collection_name or settings.collection_name

    documents = load_documents(docs_dir)
    chunks = chunk_documents(documents)
    chunk_count = index_chunks(
        chunks,
        store_dir=store_dir,
        collection_name=collection_name,
    )
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed",
        data={
            "document_count": len(documents),
            "chunk_count": chunk_count,
            "docs_dir": str(docs_dir),
            "store_dir": str(store_dir),
            "collection_name": collection_name,
        },
    )


@router.get("/documents/index/inspect", response_model=ApiStatusResponse)
def inspect_document_index() -> ApiStatusResponse:
    settings = load_settings()
    inspection = inspect_collection(
        store_dir=settings.store_dir,
        collection_name=settings.collection_name,
    )
    return ApiStatusResponse(
        status="ok",
        service="decision-system-api",
        data=to_jsonable(inspection),
    )
