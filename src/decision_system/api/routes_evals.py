"""Evaluation endpoints."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from decision_system.api.models import ApiRunResponse, api_error, to_jsonable
from decision_system.provider_eval.runner import (
    run_provider_eval_suite,
)
from decision_system.provider_eval.store import save_provider_eval_results
from decision_system.war_room.evals import (
    run_war_room_eval_suite,
    save_war_room_eval_results,
)

router = APIRouter(tags=["evals"])


class EvalRequest(BaseModel):
    save_results: bool = False


class ProviderEvalRequest(BaseModel):
    provider: str | None = None
    save_results: bool = False
    manual_real_provider: bool = False


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
    provider = (request.provider or "").strip().lower() or None

    if provider is not None and provider not in {"fake", "nvidia_nim", "ollama"}:
        raise api_error(
            400,
            "unknown_provider",
            f"Unknown provider '{provider}'. Expected one of: fake, nvidia_nim, ollama.",
        )

    # The new provider_eval harness handles mocked behavior for NIM/Ollama
    # by default. No API keys or Ollama daemon are required.
    try:
        suite = run_provider_eval_suite(
            provider_name=provider,
            manual_real_provider=request.manual_real_provider,
        )
    except Exception as exc:
        raise api_error(
            500,
            "provider_eval_error",
            f"Provider evaluation failed: {exc}",
        ) from exc

    data = to_jsonable(suite)
    if request.save_results:
        saved_path = save_provider_eval_results(suite)
        data["saved_path"] = str(saved_path)

    return ApiRunResponse(
        run_id=str(uuid4()),
        status="completed" if suite.failed_cases == 0 else "failed",
        data=data,
    )
