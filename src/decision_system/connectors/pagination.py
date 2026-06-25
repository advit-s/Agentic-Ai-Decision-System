"""Pagination support for connector item listing (v1.31).

Provides a standard paginated response model and helpers for
paginating item lists across all connector types.
"""

from __future__ import annotations

import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from decision_system.connectors.models import ConnectorRuntimeItem

T = TypeVar("T")


class PaginatedResult(BaseModel, Generic[T]):
    """Generic paginated result wrapper."""

    items: list[T] = Field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 50
    has_more: bool = False
    next_cursor: str | None = None


def paginate_items(
    items: list[Any],
    page: int = 1,
    page_size: int = 50,
    max_page_size: int = 200,
) -> PaginatedResult:
    """Paginate a list of items.

    Args:
        items: Full list of items to paginate.
        page: 1-based page number.
        page_size: Number of items per page.
        max_page_size: Maximum allowed page size.

    Returns:
        PaginatedResult with the requested slice.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, max_page_size))
    total = len(items)
    max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    sliced = items[start:end]
    has_more = end < total
    next_cursor = str(page + 1) if has_more else None

    return PaginatedResult(
        items=sliced,
        total_count=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
        next_cursor=next_cursor,
    )


def apply_pagination_params(
    items: list[ConnectorRuntimeItem],
    page: int = 1,
    page_size: int = 50,
    cursor: str | None = None,
) -> PaginatedResult:
    """Apply pagination to ConnectorRuntimeItem list.

    Supports both offset-based (page/page_size) and cursor-based pagination.
    When cursor is provided, uses it as an offset.
    """
    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    total = len(items)

    # If cursor is provided, use it as offset
    offset = 0
    if cursor:
        try:
            offset = int(cursor)
        except (ValueError, TypeError):
            offset = (page - 1) * page_size
    else:
        offset = (page - 1) * page_size

    end = offset + page_size
    sliced = items[offset:end]
    has_more = end < total

    return PaginatedResult(
        items=sliced,
        total_count=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
        next_cursor=str(end) if has_more else None,
    )
