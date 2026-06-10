"""Document indexing endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from decision_system.api.models import ApiRunResponse, ApiStatusResponse, IndexRequest, to_jsonable
from decision_system.config import load_settings
from decision_system.rag.chunker import chunk_documents
from decision_system.rag.loader import load_documents
from decision_system.rag.vector_store import index_chunks, inspect_collection


router = APIRouter(tags=["documents"])

# ---------------------------------------------------------------------------
# Safe-path helpers
# ---------------------------------------------------------------------------

_APPROVED_DOCS_DIRS: tuple[str, ...] = ("company_docs",)
_APPROVED_STORE_PREFIX = ".decision_system"


def _reject_unsafe_path(path: Path, label: str) -> Path:
    """Reject traversal and absolute-escape paths, returning a safe resolved path.

    Raises HTTPException(400) when the path is unsafe.
    """
    resolved = path.resolve()

    # Reject path-traversal components that escape the intended root.
    if ".." in str(path.resolve()):
        # Some resolved paths normalize .. away — recheck before resolution too.
        if ".." in str(path):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "unsafe_path",
                    "message": f"{label} must not contain path-traversal (..) elements",
                    "details": {"path": str(path)},
                },
            )

    # Reject absolute paths pointing to system directories.
    try:
        resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "unsafe_path",
                "message": f"{label} must be inside the project directory",
                "details": {"path": str(path)},
            },
        )
    return resolved


@router.post("/documents/index", response_model=ApiRunResponse)
def index_documents(request: IndexRequest | None = None) -> ApiRunResponse:
    request = request or IndexRequest()
    settings = load_settings()
    docs_dir = Path(request.docs_dir) if request.docs_dir else settings.docs_dir
    store_dir = Path(request.store_dir) if request.store_dir else settings.store_dir
    collection_name = request.collection_name or settings.collection_name

    # --- Path safety checks ---
    docs_dir_resolved = _reject_unsafe_path(docs_dir, "docs_dir")
    store_dir_resolved = _reject_unsafe_path(store_dir, "store_dir")

    # Restrict docs_dir to approved repo-local folders (or the configured default).
    if request.docs_dir is not None:
        try:
            docs_dir_resolved.relative_to(Path.cwd().resolve())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "unsafe_path",
                    "message": "docs_dir must be inside the project directory",
                    "details": {"path": request.docs_dir},
                },
            )

    # Restrict store_dir to .decision_system/...
    if request.store_dir is not None:
        try:
            store_dir_resolved.relative_to(
                (Path.cwd().resolve() / _APPROVED_STORE_PREFIX).resolve()
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "unsafe_path",
                    "message": f"store_dir must be under {_APPROVED_STORE_PREFIX}/",
                    "details": {"path": request.store_dir},
                },
            )

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
