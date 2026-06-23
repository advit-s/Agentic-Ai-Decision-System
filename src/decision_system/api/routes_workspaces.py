"""Workspace management endpoints for the local API."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from decision_system.api.models import ApiError, ErrorResponse, to_jsonable
from decision_system.config import load_settings
from decision_system.storage.export_import import (
    WorkspaceExporter,
    init_workspace_dir,
)
from decision_system.storage.models import (
    ArtifactType,
    Workspace,
)
from decision_system.storage.repositories import (
    ArtifactRepository,
    WorkspaceRepository,
)
from decision_system.storage.sqlite_store import DatabaseConnection
from decision_system.storage.migrations import run_migrations

router = APIRouter(tags=["workspaces"])


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)
    description: str = Field(default="")
    activate: bool = Field(default=True)


class ActivateWorkspaceRequest(BaseModel):
    name: str = Field(min_length=1)


class ImportArtifactsResponse(BaseModel):
    imported: list[dict[str, Any]] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)


def _connect() -> DatabaseConnection:
    settings = load_settings()
    init_workspace_dir()
    db = DatabaseConnection(Path(settings.workspace_db_path))
    db.connect()
    run_migrations(db.connect())
    return db


@router.get("/workspaces/status")
def workspace_status() -> dict[str, Any]:
    """Return the active workspace summary and artifact counts."""
    db = _connect()
    try:
        ws_repo = WorkspaceRepository(db)
        ws = ws_repo.get_active()
        if ws is None:
            return {
                "status": "no_active_workspace",
                "workspace": None,
                "artifact_counts": {},
                "database_path": _db_path(),
            }
        art_repo = ArtifactRepository(db)
        counts = art_repo.count_by_type(ws.workspace_id)

        # Gather data source and evidence stats
        try:
            from decision_system.data_sources.store import DataSourceStore
            ds_store = DataSourceStore()
            data_sources = ds_store.list_by_workspace(ws.workspace_id)
            ds_count = len(data_sources)
            doc_count = sum(1 for s in data_sources if s.source_type == "document")
            dataset_count = sum(1 for s in data_sources if s.source_type == "dataset")
            indexed_count = sum(1 for s in data_sources if s.status == "indexed")
            failed_count = sum(1 for s in data_sources if s.status == "failed")

            # Chunk count from store
            chunk_count = 0
            for s in data_sources:
                chunks = ds_store.load_chunks(ws.workspace_id, s.source_id)
                chunk_count += len(chunks)
        except Exception:
            ds_count = 0
            doc_count = 0
            dataset_count = 0
            indexed_count = 0
            failed_count = 0
            chunk_count = 0

        # Claim stats
        try:
            from decision_system.workflow_engine.stores.claim_store import JSONClaimStore
            from pathlib import Path
            claim_store = JSONClaimStore(Path(".decision_system"))
            claim_summary = claim_store.summary(workspace_id=ws.workspace_id)
        except Exception:
            claim_summary = {}

        # Report count
        report_count = 0
        reports_dir = Path(".decision_system") / "reports" / ws.workspace_id
        if reports_dir.exists():
            report_count = len(list(reports_dir.glob("*.json")))

        return {
            "status": "ok",
            "workspace": to_jsonable(ws),
            "artifact_counts": counts,
            "database_path": _db_path(),
            "data_source_count": ds_count,
            "document_count": doc_count,
            "dataset_count": dataset_count,
            "indexed_document_count": indexed_count,
            "failed_source_count": failed_count,
            "chunk_count": chunk_count,
            "claim_count": claim_summary.get("total", 0),
            "claims_with_evidence": claim_summary.get("claims_with_evidence", 0),
            "claims_without_evidence": claim_summary.get("claims_without_evidence", 0),
            "evidence_coverage_score": claim_summary.get("evidence_coverage_score_v2", 0),
            "report_count": report_count,
        }
    finally:
        db.close()


@router.post("/workspaces")
def create_workspace(req: CreateWorkspaceRequest) -> dict[str, Any]:
    """Create (or accept existing) workspace. Optionally activate."""
    db = _connect()
    try:
        ws_repo = WorkspaceRepository(db)
        existing = ws_repo.get_by_name(req.name)
        if existing is not None:
            if req.activate:
                ws_repo.set_active(existing.workspace_id)
                existing = ws_repo.get_by_id(existing.workspace_id)
            return {
                "status": "exists",
                "workspace": to_jsonable(existing),
            }
        workspace_id = (
            req.name.strip()
            .lower()
            .replace(" ", "-")
            .replace("_", "-")
        )
        ws = Workspace(
            workspace_id=workspace_id,
            name=req.name.strip(),
            description=req.description,
            active=req.activate,
        )
        ws_repo.ensure_exists(ws)
        if req.activate:
            ws_repo.set_active(ws.workspace_id)
        created = ws_repo.get_by_id(ws.workspace_id)
        return {
            "status": "created",
            "workspace": to_jsonable(created),
        }
    finally:
        db.close()


@router.get("/workspaces")
def list_workspaces() -> dict[str, Any]:
    """List all known workspaces."""
    db = _connect()
    try:
        ws_repo = WorkspaceRepository(db)
        workspaces = ws_repo.list_all()
        active = ws_repo.get_active()
        active_id = active.workspace_id if active else None
        return {
            "status": "ok",
            "workspaces": [to_jsonable(w) for w in workspaces],
            "active_workspace_id": active_id,
        }
    finally:
        db.close()


@router.post("/workspaces/{name}/activate")
def activate_workspace(name: str) -> dict[str, Any]:
    """Set the named workspace as active. Deactivates others."""
    db = _connect()
    try:
        ws_repo = WorkspaceRepository(db)
        ws = ws_repo.get_by_name(name)
        if ws is None:
            from fastapi.responses import JSONResponse
            error = ApiError(
                code="workspace_not_found",
                message=f"Workspace '{name}' not found.",
            )
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(error=error).model_dump(mode="json", exclude_none=True),
            )
        ws_repo.set_active(ws.workspace_id)
        updated = ws_repo.get_by_id(ws.workspace_id)
        return {
            "status": "ok",
            "workspace": to_jsonable(updated),
        }
    finally:
        db.close()


def _db_path() -> str:
    return str(Path(load_settings().workspace_db_path))
