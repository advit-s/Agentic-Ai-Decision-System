"""Evaluation endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from decision_system.api.models import ApiRunResponse, api_error, to_jsonable
from decision_system.config import load_settings
from decision_system.provider_experiments.runner import (
    load_eval_cases as load_provider_eval_cases,
    run_experiment_suite,
)
from decision_system.provider_experiments.store import save_experiment_results
from decision_system.war_room.evals import (
    run_war_room_eval_suite,
    save_war_room_eval_results,
)


router = APIRouter(tags=["evals"])


class EvalRequest(BaseModel):
    save_results: bool = False


class ProviderEvalRequest(BaseModel):
    provider: str = "fake"
    save_results: bool = False
    require_configured: bool = False


@router.post("/evals/war-room", response_model=ApiRunResponse)
def eval_war_room(request: EvalRequest | None = None) -> ApiRunResponse:
    request = request or EvalRequest()
    suite = run_war_room_eval_suite()
    if request.save_results:
        suite = save_war_room_eval_results(suite)
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed" if suite.failed_cases == 0 else "failed",
        data=to_jsonable(suite),
    )


@router.post("/evals/providers", response_model=ApiRunResponse)
def eval_providers(request: ProviderEvalRequest | None = None) -> ApiRunResponse:
    request = request or ProviderEvalRequest()
    settings = load_settings()
    provider = request.provider.strip().lower()
    if provider not in {"fake", "nvidia_nim", "ollama"}:
        raise api_error(
            400,
            "unknown_provider",
            f"Unknown provider '{provider}'. Expected one of: fake, nvidia_nim, ollama.",
        )

    if provider == "nvidia_nim" and (
        not settings.nvidia_api_key or not settings.nvidia_nim_model
    ):
        if request.require_configured:
            raise api_error(
                400,
                "provider_not_ready",
                "nvidia_nim is not configured (missing API key or model).",
            )
        return ApiRunResponse(
            run_id=str(uuid4()),
            status="skipped",
            data={"provider_name": provider, "reason": "nvidia_nim is not configured"},
        )

    if provider == "ollama" and not settings.ollama_model:
        if request.require_configured:
            raise api_error(
                400,
                "provider_not_ready",
                "ollama is not configured (missing OLLAMA_MODEL).",
            )
        return ApiRunResponse(
            run_id=str(uuid4()),
            status="skipped",
            data={"provider_name": provider, "reason": "ollama is not configured"},
        )

    suite = run_experiment_suite(
        load_provider_eval_cases(),
        provider_name=provider,
        settings=settings,
    )
    data = to_jsonable(suite)
    if request.save_results:
        data["saved_path"] = str(save_experiment_results(suite))
    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed" if suite.failed_cases == 0 else "failed",
        data=data,
    )
