"""Global pytest configuration for the decision system tests.

Monkey-patches starlette's threadpool runner and anyio's thread sync
to work around a Python 3.13 compatibility issue with
``anyio.to_thread.run_sync`` that causes sync FastAPI endpoint handlers
and Starlette's static file checks to hang when called through httpx's
async ``ASGITransport``.

The patches run sync functions inline (in the async task) rather than
offloading them to a thread pool.  This is safe for testing because all
our sync handlers and OS calls are short-lived CPU-bound operations.

Also provides an ``async_client`` fixture that uses ``httpx.AsyncClient``
with ``ASGITransport`` instead of Starlette's synchronous ``TestClient``,
which hangs in Python 3.13 + anyio 4.14 (the ``start_blocking_portal``
portal thread does not process ``call_soon_threadsafe`` callbacks).
"""

import pytest
from uuid import uuid4


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Apply threadpool workarounds before any tests run."""

    # Patch 1: FastAPI sync route handlers via starlette.concurrency
    import starlette.concurrency as sc

    async def _run_inline(func, *args, **kwargs):
        from functools import partial
        return partial(func, *args, **kwargs)()

    sc.run_in_threadpool = _run_inline

    # Patch 2: anyio thread sync (used by Starlette's StaticFiles.check_config
    # and other framework internals).  This patches both the module-level
    # function and the backend method to ensure all code paths are covered.
    import anyio.to_thread as tt
    import anyio._backends._asyncio as asyncio_backend

    async def _run_sync_inline(func, *args, **kwargs):
        from functools import partial
        return partial(func, *args)()

    tt.run_sync = _run_sync_inline
    # Also patch the backend method that anyio.to_thread.run_sync delegates to
    asyncio_backend.AsyncIOBackend.run_sync_in_worker_thread = _run_sync_inline


@pytest.fixture()
def async_client(tmp_path, monkeypatch):
    """Return an async HTTP client backed by ASGITransport.

    Sets up isolated temp directories and env vars the same way the
    sync TestClient fixtures did, but uses ``httpx.AsyncClient`` with
    ``ASGITransport`` to avoid Starlette's synchronous TestClient which
    hangs in Python 3.13 + anyio 4.14.
    """
    import httpx
    from httpx import ASGITransport

    docs_dir = tmp_path / "company_docs"
    store_dir = tmp_path / "chroma"
    docs_dir.mkdir()
    (docs_dir / "test.md").write_text("Test document.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DECISION_DOCS_DIR", str(docs_dir))
    monkeypatch.setenv("DECISION_STORE_DIR", str(store_dir))
    monkeypatch.setenv("DECISION_COLLECTION", f"api_chunks_{uuid4().hex}")
    monkeypatch.setenv("DECISION_PROVIDER", "fake")
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    from decision_system.api.app import set_scheduler_enabled
    set_scheduler_enabled(False)

    from decision_system.api.app import app

    transport = ASGITransport(app=app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    return client
