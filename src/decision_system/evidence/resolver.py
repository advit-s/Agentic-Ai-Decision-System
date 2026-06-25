"""Workspace-scoped evidence resolver.

Resolves evidence references (evidence_id, source_id, chunk_id) into
snippets with metadata. Workspace-scoped and handles missing references
gracefully.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ResolvedEvidence:
    """Resolved evidence snippet with metadata."""

    def __init__(
        self,
        evidence_id: str,
        source_id: str = "",
        chunk_id: str = "",
        source_name: str = "",
        source_type: str = "",
        file_type: str = "",
        chunk_text: str = "",
        chunk_index: int = 0,
        local_path: str = "",
        metadata: dict[str, Any] | None = None,
        workspace_id: str = "",
        warning: str | None = None,
    ):
        self.evidence_id = evidence_id
        self.source_id = source_id
        self.chunk_id = chunk_id
        self.source_name = source_name
        self.source_type = source_type
        self.file_type = file_type
        self.chunk_text = chunk_text
        self.chunk_index = chunk_index
        self.local_path = local_path
        self.metadata = metadata or {}
        self.workspace_id = workspace_id
        self.warning = warning

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "chunk_id": self.chunk_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "file_type": self.file_type,
            "chunk_text": self.chunk_text,
            "chunk_index": self.chunk_index,
            "local_path": self.local_path,
            "metadata": self.metadata,
            "workspace_id": self.workspace_id,
            "warning": self.warning,
        }


class EvidenceResolver:
    """Resolves evidence references into local snippets.

    Workspace-scoped: returns warnings if evidence belongs to a different
    workspace. Returns structured warnings instead of crashing on missing
    references.
    """

    def __init__(self, store_dir: str | Path | None = None):
        self._store_dir = Path(store_dir) if store_dir else None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        evidence_id: str | None = None,
        source_id: str | None = None,
        chunk_id: str | None = None,
        workspace_id: str | None = None,
    ) -> ResolvedEvidence:
        """Resolve a single evidence reference.

        At least one of evidence_id, source_id, or chunk_id must be provided.
        """
        if not evidence_id and not source_id and not chunk_id:
            return ResolvedEvidence(
                evidence_id="",
                warning="No evidence identifier provided.",
            )

        eid = evidence_id or ""

        # Try resolving by evidence_id first
        if evidence_id:
            result = self._resolve_by_evidence_id(evidence_id, workspace_id)
            if result.warning is None:
                return result

        # Fallback: try source + chunk
        if source_id:
            return self._resolve_by_source_chunk(source_id, chunk_id, workspace_id, eid)

        # Try chunk_id only
        if chunk_id:
            return self._resolve_by_chunk_id(chunk_id, workspace_id, eid)

        return ResolvedEvidence(
            evidence_id=eid,
            warning=f"Could not resolve evidence: {eid or '(no id)'}",
        )

    def resolve_many(
        self,
        evidence_ids: list[str] | None = None,
        source_ids: list[str] | None = None,
        chunk_ids: list[str] | None = None,
        workspace_id: str | None = None,
    ) -> list[ResolvedEvidence]:
        """Resolve multiple evidence references."""
        resolved: list[ResolvedEvidence] = []
        seen: set[str] = set()

        if evidence_ids:
            for eid in evidence_ids:
                if eid and eid not in seen:
                    seen.add(eid)
                    resolved.append(self.resolve(evidence_id=eid, workspace_id=workspace_id))

        if source_ids:
            for sid in source_ids:
                if sid and sid not in seen:
                    seen.add(sid)
                    resolved.append(self.resolve(source_id=sid, workspace_id=workspace_id))

        if chunk_ids:
            for cid in chunk_ids:
                if cid and cid not in seen:
                    seen.add(cid)
                    resolved.append(self.resolve(chunk_id=cid, workspace_id=workspace_id))

        return resolved

    # ------------------------------------------------------------------
    # Internal resolution methods
    # ------------------------------------------------------------------

    def _resolve_by_evidence_id(
        self, evidence_id: str, workspace_id: str | None
    ) -> ResolvedEvidence:
        """Search chunk stores for evidence by ID."""
        # Try Chroma-based documents first
        chunk = self._find_chunk_by_evidence_id(evidence_id)
        if chunk:
            return self._chunk_to_resolved(chunk, evidence_id, workspace_id)

        # Try workspace chunk store
        chunk_data = self._find_workspace_chunk(evidence_id, workspace_id)
        if chunk_data:
            return self._chunk_data_to_resolved(chunk_data, evidence_id, workspace_id)

        return ResolvedEvidence(
            evidence_id=evidence_id,
            warning=f"Evidence '{evidence_id}' not found in any store.",
        )

    def _resolve_by_source_chunk(
        self,
        source_id: str,
        chunk_id: str | None,
        workspace_id: str | None,
        evidence_id: str,
    ) -> ResolvedEvidence:
        """Resolve using source + chunk reference."""
        chunk_data = self._find_workspace_chunk_by_source(source_id, chunk_id, workspace_id)
        if chunk_data:
            return self._chunk_data_to_resolved(chunk_data, evidence_id or source_id, workspace_id)
        return ResolvedEvidence(
            evidence_id=evidence_id or source_id,
            source_id=source_id,
            chunk_id=chunk_id or "",
            warning=f"Source '{source_id}' not found in workspace.",
        )

    def _resolve_by_chunk_id(
        self, chunk_id: str, workspace_id: str | None, evidence_id: str
    ) -> ResolvedEvidence:
        """Resolve by chunk ID alone."""
        chunk_data = self._find_chunk_by_id(chunk_id, workspace_id)
        if chunk_data:
            return self._chunk_data_to_resolved(chunk_data, evidence_id or chunk_id, workspace_id)
        return ResolvedEvidence(
            evidence_id=evidence_id or chunk_id,
            chunk_id=chunk_id,
            warning=f"Chunk '{chunk_id}' not found.",
        )

    # ------------------------------------------------------------------
    # Store lookups
    # ------------------------------------------------------------------

    def _find_chunk_by_evidence_id(self, evidence_id: str) -> Any:
        """Look for a Chroma document by evidence_id."""
        try:
            from decision_system.config import load_settings
            from decision_system.rag.retriever import retrieve_evidence

            settings = load_settings()
            chunks = retrieve_evidence(
                query=evidence_id,
                store_dir=settings.store_dir,
                collection_name=settings.collection_name,
                top_k=1,
            )
            for chunk in chunks:
                if chunk.evidence_id == evidence_id:
                    return chunk
        except Exception:
            pass
        return None

    def _find_workspace_chunk(self, evidence_id: str, workspace_id: str | None) -> Any:
        """Look for a chunk in workspace chunk store."""
        try:
            from decision_system.data_sources.store import DataSourceStore

            store = DataSourceStore()
            ws_id = workspace_id or ""
            chunks = store.get_chunks_by_evidence_id(ws_id, evidence_id)
            if chunks:
                return chunks[0]
        except Exception:
            pass
        return None

    def _find_workspace_chunk_by_source(
        self, source_id: str, chunk_id: str | None, workspace_id: str | None
    ) -> Any:
        """Look for chunks by source ID."""
        try:
            from decision_system.data_sources.store import DataSourceStore

            store = DataSourceStore()
            ws_id = workspace_id or ""
            chunks = store.get_chunks(ws_id, source_id)
            if chunk_id:
                chunks = [
                    c
                    for c in chunks
                    if getattr(c, "chunk_id", None) == chunk_id
                    or getattr(c, "id", None) == chunk_id
                ]
            if chunks:
                return chunks[0]
        except Exception:
            pass
        return None

    def _find_chunk_by_id(self, chunk_id: str, workspace_id: str | None) -> Any:
        """Generic chunk lookup by any ID."""
        try:
            from decision_system.data_sources.store import DataSourceStore

            store = DataSourceStore()
            ws_id = workspace_id or ""
            return store.get_chunk_by_id(ws_id, chunk_id)
        except Exception:
            pass
        return None

    def _chunk_to_resolved(
        self, chunk: Any, evidence_id: str, workspace_id: str | None
    ) -> ResolvedEvidence:
        """Convert a Chroma EvidenceChunk to ResolvedEvidence."""
        return ResolvedEvidence(
            evidence_id=evidence_id,
            source_id=getattr(chunk, "document_id", ""),
            chunk_id=getattr(chunk, "chunk_id", ""),
            source_name=getattr(chunk, "source_filename", ""),
            source_type="document",
            file_type="",
            chunk_text=getattr(chunk, "text", ""),
            chunk_index=0,
            local_path=getattr(chunk, "source_path", ""),
            metadata={"document_id": getattr(chunk, "document_id", "")},
            workspace_id=workspace_id or "",
        )

    def _chunk_data_to_resolved(
        self, chunk_data: Any, evidence_id: str, workspace_id: str | None
    ) -> ResolvedEvidence:
        """Convert a workspace store chunk to ResolvedEvidence."""
        return ResolvedEvidence(
            evidence_id=evidence_id,
            source_id=getattr(chunk_data, "source_id", getattr(chunk_data, "document_id", "")),
            chunk_id=getattr(chunk_data, "chunk_id", getattr(chunk_data, "id", "")),
            source_name=getattr(
                chunk_data, "source_name", getattr(chunk_data, "source_filename", "")
            ),
            source_type="data_source",
            file_type=getattr(chunk_data, "file_type", ""),
            chunk_text=getattr(chunk_data, "text", getattr(chunk_data, "content", "")),
            chunk_index=getattr(chunk_data, "chunk_index", 0),
            local_path=getattr(chunk_data, "local_path", getattr(chunk_data, "source_path", "")),
            metadata={},
            workspace_id=workspace_id or "",
        )
