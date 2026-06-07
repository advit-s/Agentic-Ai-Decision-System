"""Health endpoint for the local API."""

from __future__ import annotations

from fastapi import APIRouter

from decision_system import __version__
from decision_system.api.models import ApiStatusResponse
from decision_system.config import load_settings


router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiStatusResponse)
def health() -> ApiStatusResponse:
    settings = load_settings()
    return ApiStatusResponse(
        status="ok",
        service="decision-system-api",
        version=__version__,
        mode="local-development",
        provider=settings.provider,
        auth="none",
        database="none",
    )
