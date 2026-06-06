"""Shared API request/response models and helpers."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field


class ApiError(BaseModel):
    """Consistent error envelope returned by the API."""

    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """Top-level API error response."""

    error: ApiError


class IndexRequest(BaseModel):
    """Optional overrides for indexing local documents."""

    docs_dir: str | None = None
    store_dir: str | None = None
    collection_name: str | None = None


class AskRequest(BaseModel):
    """Request body for running the decision report workflow."""

    question: str = Field(min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)
    provider: str | None = None
    include_insights: bool = False
    orchestrated: bool = False
    save_context: bool = False
    save_run: bool = False


class QuestionRequest(BaseModel):
    """Request body for endpoints that only need a business question."""

    question: str = Field(min_length=1)


class ApiRunResponse(BaseModel):
    """Structured response for an API operation with a run identifier."""

    run_id: str
    status: str = "completed"
    data: dict[str, Any] = Field(default_factory=dict)


class ApiReportResponse(BaseModel):
    """Structured decision report response."""

    run_id: str
    question: str
    status: str = "completed"
    report: dict[str, Any]
    data: dict[str, Any] = Field(default_factory=dict)


class ApiStatusResponse(BaseModel):
    """Structured response for health and read-only status endpoints."""

    status: str
    service: str | None = None
    version: str | None = None
    mode: str | None = None
    provider: str | None = None
    auth: str | None = None
    database: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


def api_error(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> HTTPException:
    """Build an HTTPException that the app-level handler renders consistently."""

    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "details": details,
        },
    )


def to_jsonable(value: Any) -> Any:
    """Convert Pydantic/domain objects into plain JSON-compatible values."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, tuple | set):
        return [to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    return value
