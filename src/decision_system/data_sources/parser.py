"""Local document parsing and chunking for supported file types.

Supports txt, md, json, and html (if lxml available) out of the box.
PDF and DOCX parsing are available only if the respective dependencies exist.
"""

from __future__ import annotations

import csv
import io
import json as json_lib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from decision_system.data_sources.models import DataSourceChunk


# ---------------------------------------------------------------------------
# Supported file types
# ---------------------------------------------------------------------------

PARSER_REGISTRY: dict[str, str] = {
    ".txt": "text",
    ".md": "markdown",
    ".json": "json",
}


def get_supported_extensions() -> list[str]:
    """Return list of supported file extensions for parsing."""
    return list(PARSER_REGISTRY.keys())


def is_parsable(ext: str) -> bool:
    """Check if a file extension is supported for parsing."""
    return ext.lower() in PARSER_REGISTRY


# ---------------------------------------------------------------------------
# Text/markdown parsing
# ---------------------------------------------------------------------------


def parse_text(content: str, source_id: str, workspace_id: str) -> list[DataSourceChunk]:
    """Parse plain text or markdown content into chunks.

    Chunking rules:
    - Split by double newlines first (paragraphs).
    - Combine small paragraphs to reach ~500 chars.
    - Each chunk gets a sequential index.
    """
    paragraphs = re.split(r"\n\s*\n", content)
    chunks: list[DataSourceChunk] = []
    current_text = ""
    current_start = 0
    chunk_index = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_text) + len(para) < 1000:
            if current_text:
                current_text += "\n\n" + para
            else:
                current_text = para
        else:
            if current_text:
                chunks.append(
                    DataSourceChunk(
                        chunk_id=str(uuid4()),
                        source_id=source_id,
                        workspace_id=workspace_id,
                        chunk_index=chunk_index,
                        text=current_text,
                        char_start=current_start,
                        char_end=current_start + len(current_text),
                        metadata={"parser": "text", "char_count": len(current_text)},
                        created_at=datetime.now(timezone.utc),
                    )
                )
                chunk_index += 1
            current_start += len(current_text) + 2 if current_text else 0
            current_text = para

    # Last chunk
    if current_text:
        chunks.append(
            DataSourceChunk(
                chunk_id=str(uuid4()),
                source_id=source_id,
                workspace_id=workspace_id,
                chunk_index=chunk_index,
                text=current_text,
                char_start=current_start,
                char_end=current_start + len(current_text),
                metadata={"parser": "text", "char_count": len(current_text)},
                created_at=datetime.now(timezone.utc),
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------


def parse_json(
    content: str, source_id: str, workspace_id: str
) -> list[DataSourceChunk]:
    """Parse JSON content into text chunks.

    Each top-level key or array element becomes a chunk.
    """
    try:
        data = json_lib.loads(content)
    except json_lib.JSONDecodeError:
        return []

    chunks: list[DataSourceChunk] = []
    chunk_index = 0

    if isinstance(data, dict):
        for key, value in data.items():
            text = f"{key}: {json_lib.dumps(value, indent=2, ensure_ascii=False)}"
            chunks.append(
                DataSourceChunk(
                    chunk_id=str(uuid4()),
                    source_id=source_id,
                    workspace_id=workspace_id,
                    chunk_index=chunk_index,
                    text=text,
                    metadata={"parser": "json", "key": key},
                    created_at=datetime.now(timezone.utc),
                )
            )
            chunk_index += 1
    elif isinstance(data, list):
        for i, item in enumerate(data):
            text = json_lib.dumps(item, indent=2, ensure_ascii=False)
            chunks.append(
                DataSourceChunk(
                    chunk_id=str(uuid4()),
                    source_id=source_id,
                    workspace_id=workspace_id,
                    chunk_index=chunk_index,
                    text=text,
                    metadata={"parser": "json", "index": i},
                    created_at=datetime.now(timezone.utc),
                )
            )
            chunk_index += 1
    else:
        # scalar JSON value
        chunks.append(
            DataSourceChunk(
                chunk_id=str(uuid4()),
                source_id=source_id,
                workspace_id=workspace_id,
                chunk_index=0,
                text=str(data),
                metadata={"parser": "json"},
                created_at=datetime.now(timezone.utc),
            )
        )

    return chunks


# ---------------------------------------------------------------------------
# Main parser dispatch
# ---------------------------------------------------------------------------

PARSER_MAP = {
    "text": parse_text,
    "markdown": parse_text,
    "json": parse_json,
}


def parse_document(
    content: str, ext: str, source_id: str, workspace_id: str
) -> tuple[list[DataSourceChunk], list[str]]:
    """Parse a document and return (chunks, warnings).

    Args:
        content: Raw text content of the file.
        ext: File extension (e.g. '.txt', '.md', '.json').
        source_id: Data source ID.
        workspace_id: Workspace ID.

    Returns:
        Tuple of (list of DataSourceChunk, list of warning strings).
    """
    warnings: list[str] = []
    ext_lower = ext.lower()

    parser_name = PARSER_REGISTRY.get(ext_lower)
    if parser_name is None:
        warnings.append(f"Unsupported file extension: {ext}")
        return [], warnings

    if not content.strip():
        warnings.append("File is empty")
        return [], warnings

    parser_fn = PARSER_MAP.get(parser_name)
    if parser_fn is None:
        warnings.append(f"No parser available for type: {parser_name}")
        return [], warnings

    try:
        chunks = parser_fn(content, source_id, workspace_id)
    except Exception as e:
        warnings.append(f"Parsing error: {e}")
        return [], warnings

    if not chunks:
        warnings.append("No chunks produced from file")

    return chunks, warnings


# ---------------------------------------------------------------------------
# CSV profiling
# ---------------------------------------------------------------------------


def profile_csv(
    content: str, source_id: str, workspace_id: str
) -> dict[str, Any]:
    """Profile CSV content and return a structured profile dict.

    Returns profile with row_count, column_count, column_types,
    missing_values, numeric_summary, categorical_summary, sample_rows.
    """
    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as e:
        return {"error": str(e), "row_count": 0}

    if not rows:
        return {
            "source_id": source_id,
            "workspace_id": workspace_id,
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "warnings": ["No data rows found"],
        }

    headers = reader.fieldnames or []
    col_count = len(headers)
    row_count = len(rows)

    columns = []
    column_types: dict[str, str] = {}
    missing_values: dict[str, int] = {}
    numeric_summary: dict[str, dict[str, float]] = {}
    categorical_summary: dict[str, list[tuple[str, int]]] = {}
    date_like_columns: list[str] = []

    for header in headers:
        col_values = [r.get(header, "") or "" for r in rows]
        non_empty = [v for v in col_values if v.strip()]
        missing = row_count - len(non_empty)

        # Detect type
        is_numeric = False
        nums = []
        for v in non_empty:
            cleaned = v.strip().replace(",", "").replace("$", "").replace("%", "")
            try:
                nums.append(float(cleaned))
            except ValueError:
                pass

        if nums and len(nums) == len(non_empty):
            is_numeric = True
            column_types[header] = "numeric"
            numeric_summary[header] = {
                "min": min(nums),
                "max": max(nums),
                "mean": round(sum(nums) / len(nums), 4),
                "count": len(nums),
            }
        else:
            column_types[header] = "categorical"
            freqs: dict[str, int] = {}
            for v in non_empty:
                freqs[v] = freqs.get(v, 0) + 1
            categorical_summary[header] = sorted(
                freqs.items(), key=lambda x: (-x[1], x[0])
            )[:10]

        missing_values[header] = missing
        columns.append({
            "name": header,
            "dtype": column_types[header],
            "missing": missing,
            "missing_pct": round(missing / row_count, 4) if row_count else 0,
        })

        # Date-like detection
        date_pattern = re.compile(
            r"date|time|month|year|day|period|week", re.IGNORECASE
        )
        if date_pattern.search(header) and not is_numeric:
            date_like_columns.append(header)

    warnings = []
    for col in columns:
        if col["missing_pct"] > 0.5:
            warnings.append(f"Column '{col['name']}' is >50% missing")

    return {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "row_count": row_count,
        "column_count": col_count,
        "columns": columns,
        "column_types": column_types,
        "missing_values": missing_values,
        "numeric_summary": numeric_summary,
        "categorical_summary": categorical_summary,
        "date_like_columns": date_like_columns,
        "sample_rows": rows[:5],
        "warnings": warnings,
    }


def profile_json_content(
    content: str, source_id: str, workspace_id: str
) -> dict[str, Any]:
    """Profile JSON content and return a structured profile dict."""
    try:
        data = json_lib.loads(content)
    except json_lib.JSONDecodeError as e:
        return {
            "source_id": source_id,
            "workspace_id": workspace_id,
            "error": str(e),
            "top_level_type": "unknown",
        }

    result: dict[str, Any] = {
        "source_id": source_id,
        "workspace_id": workspace_id,
        "top_level_type": type(data).__name__,
    }

    if isinstance(data, list):
        result["record_count"] = len(data)
        result["sample_records"] = data[:3] if data else []
        if data and isinstance(data[0], dict):
            result["field_paths"] = sorted(data[0].keys())
    elif isinstance(data, dict):
        result["field_paths"] = sorted(data.keys())
        result["sample_records"] = [dict(list(data.items())[:5])]
    else:
        result["sample_records"] = [str(data)]

    return result
