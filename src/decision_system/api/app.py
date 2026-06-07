"""FastAPI application factory for the local decision-system API."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from decision_system import __version__
from decision_system.api.models import ApiError, ErrorResponse
from decision_system.api import routes_context
from decision_system.api import routes_data
from decision_system.api import routes_documents
from decision_system.api import routes_evals
from decision_system.api import routes_health
from decision_system.api import routes_insights
from decision_system.api import routes_ontology
from decision_system.api import routes_orchestration
from decision_system.api import routes_reports
from decision_system.api import routes_war_room


def create_app() -> FastAPI:
    """Create the local-development FastAPI app."""

    api = FastAPI(
        title="Agentic Decision System API",
        version=__version__,
        description="Local FastAPI wrapper over the offline decision-system backend.",
    )

    api.include_router(routes_health.router)
    api.include_router(routes_documents.router)
    api.include_router(routes_reports.router)
    api.include_router(routes_context.router)
    api.include_router(routes_orchestration.router)
    api.include_router(routes_war_room.router)
    api.include_router(routes_ontology.router)
    api.include_router(routes_insights.router)
    api.include_router(routes_data.router)
    api.include_router(routes_evals.router)

    # Mount the static files for the web UI prototype at the root.
    # We do this after registering all API routes so they take precedence.
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles

    # Prefer package-relative web assets (survives pip install).
    package_web = Path(__file__).resolve().parent / "web"
    # Fallback to repo-root for editable installs and existing tests.
    repo_web = Path(__file__).resolve().parents[3] / "web"
    web_dir = package_web if package_web.exists() else repo_web
    if web_dir.exists():
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
