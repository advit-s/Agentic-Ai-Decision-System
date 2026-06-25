"""Pydantic models for workspace-scoped data sources."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class DataSourceStatus(str):
    """Status values for a data source lifecycle."""

    UPLOADED = "uploaded"
    PARSED = "parsed"
    INDEXED = "indexed"
    FAILED = "failed"
    PARSING = "parsing"
    PARSED_WITH_WARNINGS = "parsed_with_warnings"
    INDEXING = "indexing"
    UNSUPPORTED = "unsupported"
    DELETED = "deleted"


class DataSource(BaseModel):
    """A local uploaded/imported file or dataset owned by a workspace."""

    source_id: str
    workspace_id: str
    name: str
    source_type: str = "unknown"  # document | dataset | folder | unknown
    file_type: str = "unknown"  # pdf | docx | txt | md | csv | xlsx | json | html | unknown
    original_filename: str = ""
    local_path: str = ""
    content_hash: str = ""
    size_bytes: int = 0
    status: str = "uploaded"  # uploaded | parsed | indexed | failed
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DataSourceChunk(BaseModel):
    """A text chunk produced by parsing a data source document."""

    chunk_id: str
    source_id: str
    workspace_id: str
    chunk_index: int = 0
    text: str = ""
    char_start: int | None = None
    char_end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatasetProfile(BaseModel):
    """Profile of a CSV/JSON dataset."""

    profile_id: str
    source_id: str
    workspace_id: str
    row_count: int = 0
    column_count: int = 0
    columns: list[dict[str, Any]] = Field(default_factory=list)
    column_types: dict[str, str] = Field(default_factory=dict)
    missing_values: dict[str, int] = Field(default_factory=dict)
    numeric_summary: dict[str, dict[str, float]] = Field(default_factory=dict)
    categorical_summary: dict[str, list[tuple[str, int]]] = Field(default_factory=dict)
    date_like_columns: list[str] = Field(default_factory=list)
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParseResult(BaseModel):
    """Result from a document parser."""

    source_id: str
    workspace_id: str
    text: str = ""
    pages: list[dict[str, Any]] | None = None
    tables: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    parser_name: str = ""
    parser_version: str | None = None
    chunks: list[DataSourceChunk] = Field(default_factory=list)


class ParsedBlock(BaseModel):
    """A structured block from a parsed document (paragraph, heading, table)."""

    block_type: str  # paragraph | heading | table
    text: str = ""
    index: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSearchResult(BaseModel):
    """A single evidence search result item."""

    evidence_id: str
    workspace_id: str
    source_id: str
    source_name: str = ""
    chunk_id: str = ""
    text: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceSearchResponse(BaseModel):
    """Response from a workspace evidence search."""

    results: list[EvidenceSearchResult] = Field(default_factory=list)
    query: str = ""
    limit: int = 10
    retrieval_mode: str = "keyword"  # vector | keyword
    total_results: int = 0
