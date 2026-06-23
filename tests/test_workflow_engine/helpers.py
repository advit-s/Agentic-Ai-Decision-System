"""Test helpers for workflow engine API tests.

Uses httpx AsyncClient with ASGITransport instead of the synchronous
TestClient, which has compatibility issues with httpx 0.28+.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from httpx import ASGITransport, AsyncClient

from decision_system.api.app import set_scheduler_enabled, create_app


@asynccontextmanager
async def async_api_client() -> AsyncIterator[AsyncClient]:
    """Create an async test client for the decision system API.

    Usage::

        async with async_api_client() as client:
            resp = await client.get("/health")
            assert resp.status_code == 200
    """
    set_scheduler_enabled(False)
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
