"""FastAPI application factory for the local decision-system API.

Route modules that import heavy dependencies (chromadb, langgraph, workflow,
war-room, provider-eval) are loaded lazily inside ``create_app()`` so that
lightweight endpoints (``/health``, ``/dashboard``, ``/workspaces/*``,
``/security/*``, ``/enterprise-readiness``, etc.) work even when those
dependencies are not installed.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

from decision_system import __version__
from decision_system.api.models import ApiError, ErrorResponse

# ---------------------------------------------------------------------------
# Lightweight route modules — imported eagerly because they do not pull in
# optional heavy packages (chromadb, langgraph, etc.).  Heavy route modules
# are loaded lazily inside create_app() via _lazy_router().
# ---------------------------------------------------------------------------
from decision_system.api import routes_health
from decision_system.api import routes_connectors
from decision_system.api import routes_dashboard
from decision_system.api import routes_data
from decision_system.api import routes_ontology
from decision_system.api import routes_security
from decision_system.api import routes_workspaces
from decision_system.api import routes_enterprise
from decision_system.api import routes_observability
from decision_system.workflow_engine.api import router as routes_workflow


def _lazy_router(api: FastAPI, module_name: str) -> None:
    """Import and register a route module, swallowing ImportError.

    Modules that depend on optional heavy packages (chromadb, langgraph)
    may raise ImportError when those packages are absent.  This helper
    registers them when available and logs a debug line — the running API
    simply doesn't expose those endpoints when the deps are missing.
    """
    import importlib
    import logging
    try:
        mod = importlib.import_module(module_name)
        api.include_router(mod.router)
    except ImportError:
        logging.getLogger(__name__).debug(
            "Skipped route module %s (optional dep not installed)", module_name
        )


def create_app() -> FastAPI:
    """Create the local-development FastAPI app."""

    api = FastAPI(
        title="Agentic Decision System API",
        version=__version__,
        description="Local FastAPI wrapper over the offline decision-system backend.",
    )

    # --- Lightweight routes (always available) ---
    api.include_router(routes_health.router)
    api.include_router(routes_connectors.router)
    api.include_router(routes_dashboard.router)
    api.include_router(routes_data.router)
    api.include_router(routes_ontology.router)
    api.include_router(routes_security.router)
    api.include_router(routes_workspaces.router)
    api.include_router(routes_enterprise.router)
    api.include_router(routes_observability.router)
    api.include_router(routes_workflow)

    # --- Heavy routes (lazy-loaded — skip silently if deps absent) ---
    _lazy_router(api, "decision_system.api.routes_documents")
    _lazy_router(api, "decision_system.api.routes_reports")
    _lazy_router(api, "decision_system.api.routes_context")
    _lazy_router(api, "decision_system.api.routes_orchestration")
    _lazy_router(api, "decision_system.api.routes_war_room")
    _lazy_router(api, "decision_system.api.routes_insights")
    _lazy_router(api, "decision_system.api.routes_evals")

    # Mount the static files for the web UI prototype at the root.
    # We do this after registering all API routes so they take precedence.
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    # Prefer package-relative web assets via importlib.resources
    # (survives pip install / wheel install correctly).
    import importlib.resources as _res

    web_dir: Path | None = None

    try:
        with _res.as_file(_res.files("decision_system").joinpath("web")) as _pkg_web:
            if _pkg_web.is_dir():
                web_dir = _pkg_web.resolve()
    except (ModuleNotFoundError, TypeError, ValueError, Exception):
        pass

    # Fallback to repo-root for editable installs and existing tests.
    if web_dir is None:
        repo_web = Path(__file__).resolve().parents[3] / "web"
        if repo_web.exists():
            web_dir = repo_web.resolve()

    if web_dir is not None and web_dir.is_dir():
        # Mount the workflow-builder SPA at /workflow-builder/ (before root)
        _wf_dir = web_dir / "workflow-builder" / "dist"
        if not _wf_dir.is_dir():
            # Fallback: repo root (editable install, built dist)
            _repo_wf = Path(__file__).resolve().parents[3] / "web" / "workflow-builder" / "dist"
            if _repo_wf.is_dir():
                _wf_dir = _repo_wf
        if _wf_dir.is_dir():
            api.mount("/workflow-builder", StaticFiles(directory=str(_wf_dir), html=True), name="workflow-builder")

        api.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")

    @api.exception_handler(HTTPException)
    async def handle_http_exception(
        _request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            error = ApiError(
                code=str(detail.get("code", "http_error")),
                message=str(detail.get("message", "Request failed.")),
                details=detail.get("details"),
            )
        else:
            error = ApiError(code="http_error", message=str(detail))
        return _error_response(exc.status_code, error)

    @api.exception_handler(StarletteHTTPException)
    async def handle_starlette_http(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            error = ApiError(
                code=str(detail.get("code", "http_error")),
                message=str(detail.get("message", "Request failed.")),
                details=detail.get("details"),
            )
        else:
            error = ApiError(code="http_error", message=str(detail))
        return _error_response(exc.status_code, error)

    @api.exception_handler(RequestValidationError)
    async def handle_validation_exception(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        error = ApiError(
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
        )
        return _error_response(422, error)

    @api.exception_handler(Exception)
    async def handle_unexpected_exception(
        _request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        error = ApiError(
            code="internal_error",
            message="The API request failed. Check local inputs and generated stores.",
        )
        return _error_response(500, error)

    return api


def _error_response(status_code: int, error: ApiError) -> JSONResponse:
    payload = ErrorResponse(error=error).model_dump(mode="json", exclude_none=True)
    return JSONResponse(status_code=status_code, content=payload)


app = create_app()
