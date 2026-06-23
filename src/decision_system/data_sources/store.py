"""JSON file-backed data source store.

Provides durable local storage for data sources, chunks, and dataset profiles.
Data persists across restarts under .decision_system/ directories.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.data_sources.models import (
    DataSource,
    DataSourceChunk,
    DatasetProfile,
    EvidenceSearchResult,
)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    path.write_text(
        json.dumps(data, indent=2, default=str, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class DataSourceStore:
    """Persistent data source store backed by JSON files.

    Each data source is stored as a JSON file under:
        .decision_system/data_sources/{workspace_id}/{source_id}.json

    An index per workspace tracks all source IDs for efficient listing.
    """

    def __init__(self, base_dir: str | Path = ".decision_system") -> None:
        self._base = Path(base_dir)
        self._sources_dir = self._base / "data_sources"
        _ensure_dir(self._sources_dir)

    def _workspace_dir(self, workspace_id: str) -> Path:
        d = self._sources_dir / workspace_id
        _ensure_dir(d)
        return d

    def _source_path(self, workspace_id: str, source_id: str) -> Path:
        return self._workspace_dir(workspace_id) / f"{source_id}.json"

    def _index_path(self, workspace_id: str) -> Path:
        return self._workspace_dir(workspace_id) / "_index.json"

    def _load_index(self, workspace_id: str) -> list[str]:
        data = _read_json(self._index_path(workspace_id))
        return data if isinstance(data, list) else []

    def _save_index(self, workspace_id: str, ids: list[str]) -> None:
        _write_json(self._index_path(workspace_id), ids)

    # ------------------------------------------------------------------
    # Data source CRUD
    # ------------------------------------------------------------------

    def save(self, source: DataSource) -> DataSource:
        """Save or update a data source."""
        source.updated_at = datetime.now(timezone.utc)
        _write_json(
            self._source_path(source.workspace_id, source.source_id),
            source.model_dump(mode="json"),
        )
        ids = self._load_index(source.workspace_id)
        if source.source_id not in ids:
            ids.append(source.source_id)
            self._save_index(source.workspace_id, ids)
        return source

    def load(self, workspace_id: str, source_id: str) -> DataSource | None:
        """Load a data source by workspace_id and source_id."""
        data = _read_json(self._source_path(workspace_id, source_id))
        if data is None:
            return None
        return DataSource(**data)

    def list_by_workspace(self, workspace_id: str) -> list[DataSource]:
        """List all data sources in a workspace."""
        sources: list[DataSource] = []
        for sid in self._load_index(workspace_id):
            s = self.load(workspace_id, sid)
            if s is not None:
                sources.append(s)
        return sources

    def delete(self, workspace_id: str, source_id: str) -> bool:
        """Delete a data source and its index entry."""
        path = self._source_path(workspace_id, source_id)
        existed = path.exists()
        if existed:
            path.unlink()
        ids = self._load_index(workspace_id)
        if source_id in ids:
            ids.remove(source_id)
            self._save_index(workspace_id, ids)
        return existed

    def create(
        self,
        workspace_id: str,
        name: str,
        source_type: str,
        file_type: str,
        original_filename: str,
        local_path: str,
        size_bytes: int = 0,
        content_hash: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> DataSource:
        """Create a new data source with an auto-generated ID."""
        source = DataSource(
            source_id=str(uuid4()),
            workspace_id=workspace_id,
            name=name,
            source_type=source_type,
            file_type=file_type,
            original_filename=original_filename,
            local_path=local_path,
            size_bytes=size_bytes,
            content_hash=content_hash,
            status="uploaded",
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return self.save(source)

    def update_status(
        self,
        workspace_id: str,
        source_id: str,
        status: str,
        error_message: str | None = None,
    ) -> DataSource | None:
        """Update the status of a data source."""
        source = self.load(workspace_id, source_id)
        if source is None:
            return None
        source.status = status
        source.updated_at = datetime.now(timezone.utc)
        if error_message is not None:
            source.error_message = error_message
        return self.save(source)

    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------

    def store_uploaded_file(
        self, workspace_id: str, source_id: str, filename: str, content: bytes
    ) -> str:
        """Store an uploaded file under .decision_system/files/{workspace_id}/."""
        files_dir = self._base / "files" / workspace_id
        _ensure_dir(files_dir)
        dest = files_dir / f"{source_id}_{filename}"
        dest.write_bytes(content)
        return str(dest)

    def get_uploaded_file_path(self, workspace_id: str, source_id: str, filename: str) -> Path:
        return (self._base / "files" / workspace_id / f"{source_id}_{filename}").resolve()

    def delete_uploaded_file(self, workspace_id: str, source_id: str, filename: str) -> bool:
        path = self.get_uploaded_file_path(workspace_id, source_id, filename)
        if path.exists():
            path.unlink()
            return True
        return False

    # ------------------------------------------------------------------
    # Chunk storage
    # ------------------------------------------------------------------

    def _chunks_dir(self, workspace_id: str, source_id: str) -> Path:
        d = self._base / "chunks" / workspace_id / source_id
        _ensure_dir(d)
        return d

    def save_chunks(self, chunks: list[DataSourceChunk]) -> None:
        """Save parsed chunks for a data source."""
        for chunk in chunks:
            path = (
                self._chunks_dir(chunk.workspace_id, chunk.source_id)
                / f"{chunk.chunk_id}.json"
            )
            _write_json(path, chunk.model_dump(mode="json"))

    def load_chunks(
        self, workspace_id: str, source_id: str
    ) -> list[DataSourceChunk]:
        """Load all chunks for a data source."""
        chunks: list[DataSourceChunk] = []
        chunks_dir = self._base / "chunks" / workspace_id / source_id
        if not chunks_dir.exists():
            return chunks
        for f in sorted(chunks_dir.glob("*.json")):
            data = _read_json(f)
            if data is not None:
                chunks.append(DataSourceChunk(**data))
        return chunks

    def delete_chunks(self, workspace_id: str, source_id: str) -> None:
        """Delete all chunks for a data source."""
        chunks_dir = self._base / "chunks" / workspace_id / source_id
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir)

    def search_chunks_keyword(
        self,
        workspace_id: str,
        query: str,
        limit: int = 10,
        source_ids: list[str] | None = None,
        file_types: list[str] | None = None,
    ) -> list[EvidenceSearchResult]:
        """Keyword search over stored chunks (fallback when vector deps missing)."""
        query_lower = query.lower()
        query_terms = query_lower.split()
        results: list[EvidenceSearchResult] = []
        source_ids_set = set(source_ids) if source_ids else None
        file_types_set = set(file_types) if file_types else None

        # Walk all workspace chunk dirs
        chunks_base = self._base / "chunks" / workspace_id
        if not chunks_base.exists():
            return []

        for src_dir in chunks_base.iterdir():
            if not src_dir.is_dir():
                continue
            src_id = src_dir.name
            if source_ids_set is not None and src_id not in source_ids_set:
                continue

            for chunk_file in sorted(src_dir.glob("*.json")):
                data = _read_json(chunk_file)
                if data is None:
                    continue

                text = data.get("text", "")
                if not text:
                    continue

                # Simple keyword scoring: count matching terms
                text_lower = text.lower()
                score = sum(1 for term in query_terms if term in text_lower)

                if score > 0:
                    results.append(
                        EvidenceSearchResult(
                            evidence_id=f"kw-{src_id}-{data.get('chunk_id', '')}",
                            workspace_id=workspace_id,
                            source_id=src_id,
                            source_name=data.get("metadata", {}).get("source_name", src_id),
                            chunk_id=data.get("chunk_id", ""),
                            text=text,
                            score=score,
                            metadata=data.get("metadata", {}),
                        )
                    )

        # Sort by score descending, limit results
        results.sort(key=lambda r: -r.score)
        return results[:limit]

    # ------------------------------------------------------------------
    # Dataset profiles
    # ------------------------------------------------------------------

    def _profiles_dir(self, workspace_id: str, source_id: str) -> Path:
        d = self._base / "datasets" / workspace_id / source_id
        _ensure_dir(d)
        return d

    def save_profile(self, profile: DatasetProfile) -> None:
        """Save a dataset profile."""
        path = self._profiles_dir(profile.workspace_id, profile.source_id) / "profile.json"
        _write_json(path, profile.model_dump(mode="json"))

    def load_profile(self, workspace_id: str, source_id: str) -> DatasetProfile | None:
        """Load a dataset profile."""
        path = self._profiles_dir(workspace_id, source_id) / "profile.json"
        data = _read_json(path)
        if data is None:
            return None
        return DatasetProfile(**data)

    def delete_profile(self, workspace_id: str, source_id: str) -> None:
        """Delete a dataset profile."""
        profile_dir = self._profiles_dir(workspace_id, source_id)
        if profile_dir.exists():
            shutil.rmtree(profile_dir)

    # ------------------------------------------------------------------
    # Index storage
    # ------------------------------------------------------------------

    def save_index_metadata(
        self, workspace_id: str, source_id: str, metadata: dict[str, Any]
    ) -> None:
        """Save indexing metadata for a data source."""
        index_dir = self._base / "index" / workspace_id
        _ensure_dir(index_dir)
        path = index_dir / f"{source_id}.json"
        _write_json(path, metadata)

    def get_index_metadata(
        self, workspace_id: str, source_id: str
    ) -> dict[str, Any] | None:
        """Get indexing metadata for a data source."""
        path = self._base / "index" / workspace_id / f"{source_id}.json"
        return _read_json(path)

    def delete_index_metadata(self, workspace_id: str, source_id: str) -> None:
        """Delete indexing metadata for a data source."""
        path = self._base / "index" / workspace_id / f"{source_id}.json"
        if path.exists():
            path.unlink()
