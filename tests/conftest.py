"""Global pytest configuration for the decision system tests.

Monkey-patches starlette's threadpool runner to work around a Python 3.13
compatibility issue with ``anyio.to_thread.run_sync`` that causes sync
FastAPI endpoint handlers to hang when called through httpx's async
``ASGITransport``.

The patch runs sync functions inline (in the async task) rather than
offloading them to a thread pool.  This is safe for testing because all
our sync handlers are short-lived CPU-bound lookups.
"""

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_sessionstart(session):
    """Apply the threadpool workaround before any tests run."""
    import starlette.concurrency as sc

    async def _run_inline(func, *args, **kwargs):
        from functools import partial
        return partial(func, *args, **kwargs)()

    sc.run_in_threadpool = _run_inline
